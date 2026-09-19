#!/usr/bin/env python3
"""
a2loader.py — Apple II file format detection and image loading
Usage: python3 a2loader.py <file> [--org 0x2000] [--raw] [--json]

Detects, in this order:
  1. AppleSingle (magic 00 05 16 00) — ProDOS file info entry gives the file
     type and aux type; for BIN ($06) the aux type is the load address, SYS
     ($FF) loads at $2000. This is what CiderPress / AppleCommander "-as"
     and cc65 produce.
  2. DOS 3.3 'B' file header — 4 bytes: load address (LE) + length (LE),
     accepted only when the length matches the file size exactly.
  3. CiderPress-style filename suffix NAME#062000 / NAME#FF2000 — type and
     load address from the name.
  4. Raw binary — --org, else a ROM-size guess ($F800 for 2K, $D000 for
     12K, $C000 for 16K, $C600 for 256 bytes), else $2000 with a warning.

ROM images are recognised from their size and the 6502 vectors at $FFFA
(RESET $FA62 = Autostart monitor, $FF59 = original monitor) and the machine
ID bytes at $FBB3/$FBC0, which also give a CPU hint (enhanced IIe / IIc
ROMs run on a 65C02).

Shared by dasm6502.py and xref.py via load_image(), so every tool sees the
same segments and entry address.
"""

import sys
import os
import re
import json
import hashlib
import argparse

# md5 -> (name, org, cpu). Empty on purpose: add hashes of ROMs you own.
KNOWN_ROM_MD5: dict[str, tuple[str, int, str]] = {}

# Plausible load address for a raw file of a given size
ROM_SIZE_ORG = {
    256: 0xC600,     # slot ROM (Disk II boot ROM lives in slot 6)
    2048: 0xF800,    # 2K monitor ROM
    4096: 0xF000,    # 4K ROM pair
    12288: 0xD000,   # Applesoft + monitor (II+)
    16384: 0xC000,   # IIe/IIc CD+EF ROM ($C000-$C0FF is I/O, not ROM)
}

PRODOS_TYPES = {
    0x00: "NON", 0x01: "BAD", 0x04: "TXT", 0x06: "BIN", 0x0F: "DIR",
    0x19: "ADB", 0x1A: "AWP", 0x1B: "ASP", 0xB3: "S16", 0xF0: "CMD",
    0xFA: "INT", 0xFB: "IVR", 0xFC: "BAS", 0xFD: "VAR", 0xFE: "REL",
    0xFF: "SYS",
}

APPLESINGLE_MAGIC = b"\x00\x05\x16\x00"
APPLEDOUBLE_MAGIC = b"\x00\x05\x16\x07"

# Bytes at the start of the 16-sector Disk II boot ROM (P5A)
DISK2_BOOT_SIG = bytes.fromhex("A220A000A203")

# $FBB3 / $FBC0 machine identification bytes (Apple II Technical Note #7)
MACHINE_IDS = {
    (0x38, None): ("Apple II", "6502"),
    (0xEA, None): ("Apple II+", "6502"),
    (0x06, 0xEA): ("Apple IIe (unenhanced)", "6502"),
    (0x06, 0xE0): ("Apple IIe (enhanced)", "65c02"),
    (0x06, 0x00): ("Apple IIc", "65c02"),
}


def _le16(b: bytes, off: int) -> int:
    return b[off] | (b[off + 1] << 8)


def _be16(b: bytes, off: int) -> int:
    return (b[off] << 8) | b[off + 1]


def _be32(b: bytes, off: int) -> int:
    return (b[off] << 24) | (b[off + 1] << 16) | (b[off + 2] << 8) | b[off + 3]


def parse_applesingle(data: bytes) -> dict | None:
    """Parse an AppleSingle container. Returns dict with data fork, name,
    prodos type/aux, or None if not AppleSingle."""
    if len(data) < 26 or data[:4] != APPLESINGLE_MAGIC:
        return None
    version = _be32(data, 4)
    count = _be16(data, 24)
    entries = {}
    pos = 26
    for _ in range(count):
        if pos + 12 > len(data):
            break
        eid = _be32(data, pos)
        off = _be32(data, pos + 4)
        ln = _be32(data, pos + 8)
        entries[eid] = data[off:off + ln]
        pos += 12

    info = {"version": version >> 16, "name": None, "prodos_type": None,
            "aux_type": None, "access": None, "data": entries.get(1, b"")}
    if 3 in entries:
        info["name"] = entries[3].decode("ascii", errors="replace")
    if 11 in entries and len(entries[11]) >= 8:
        fi = entries[11]
        info["access"] = _be16(fi, 0)
        info["prodos_type"] = _be16(fi, 2)
        info["aux_type"] = _be32(fi, 4)
    return info


def parse_dos33_header(data: bytes) -> tuple[int, bytes] | None:
    """DOS 3.3 binary file as extracted with its 4-byte header intact."""
    if len(data) < 5:
        return None
    addr = _le16(data, 0)
    length = _le16(data, 2)
    if length == len(data) - 4 and length > 0 and addr < 0xC000:
        return addr, data[4:]
    return None


def org_from_filename(path: str) -> tuple[int, int] | None:
    """NAME#TTAAAA suffix (CiderPress / a2tools): returns (type, aux)."""
    m = re.search(r"#([0-9A-Fa-f]{2})([0-9A-Fa-f]{4})(?:\.[A-Za-z0-9]+)?$",
                  os.path.basename(path))
    if m:
        return int(m.group(1), 16), int(m.group(2), 16)
    return None


def load_addr_for_type(ptype: int | None, aux: int | None) -> int | None:
    if ptype == 0xFF:
        return 0x2000
    if ptype == 0x06 and aux is not None:
        return aux
    return None


def _tbl(addr, count, rts=False, stride=2, hi=None, name=""):
    return {"addr": addr, "count": count, "rts": rts, "stride": stride, "hi": hi, "name": name}


def known_tables(at) -> list:
    """Dispatch tables recognized by signature (at(addr) -> byte or None).

    Applesoft: keyword table "END" at $D0D0 means the standard layout:
    statement handlers (address-1) at $D000, functions at $D080, operator
    table at $D0B2 (precedence byte + address-1, so words at $D0B3). Monitor: TOSUB at $FFBE
    (LDA #hi / PHA / LDA SUBTBL,Y / PHA) gives the command table.
    """
    tables = []
    if at(0xD0D0) == 0x45 and at(0xD0D1) == 0x4E and at(0xD0D2) == 0xC4:
        tables += [_tbl(0xD000, 64, rts=True, name="Applesoft statements"),
                   _tbl(0xD080, 25, name="Applesoft functions"),
                   _tbl(0xD0B3, 10, rts=True, stride=3, name="Applesoft operators")]
    if at(0xFFBE) == 0xA9 and at(0xFFC0) == 0x48 and at(0xFFC1) == 0xB9 and at(0xFFC4) == 0x48:
        sub = at(0xFFC2) | (at(0xFFC3) << 8)
        if 0xFF00 <= sub < 0xFFFA:
            tables.append(_tbl(sub, 0xFFFA - sub, rts=True, stride=1, hi=at(0xFFBF),
                               name="Monitor commands"))
    return tables


def rom_signature(data: bytes, org: int) -> dict:
    """Inspect a candidate ROM image: 6502 vectors, machine ID, boot ROM sig."""
    sig = {"is_rom": False, "rom_name": None, "cpu_hint": None,
           "vectors": None, "machine": None, "tables": []}
    end = org + len(data) - 1

    def at(addr):
        return data[addr - org] if org <= addr <= end else None

    if org <= 0xFFFA and end >= 0xFFFF:
        nmi = at(0xFFFA) | (at(0xFFFB) << 8)
        rst = at(0xFFFC) | (at(0xFFFD) << 8)
        irq = at(0xFFFE) | (at(0xFFFF) << 8)
        sig["vectors"] = {"NMI": nmi, "RESET": rst, "IRQ": irq}
        if org <= rst <= end:
            sig["is_rom"] = True
            if rst == 0xFA62:
                sig["rom_name"] = "Autostart Monitor (II+/IIe/IIc)"
            elif rst == 0xFF59:
                sig["rom_name"] = "Original Apple II Monitor"
            else:
                sig["rom_name"] = f"ROM image (RESET -> ${rst:04X})"
        b3, c0 = at(0xFBB3), at(0xFBC0)
        if b3 is not None:
            key = (b3, c0 if b3 == 0x06 else None)
            if key in MACHINE_IDS:
                name, cpu = MACHINE_IDS[key]
                sig["machine"] = name
                sig["cpu_hint"] = cpu
                if sig["is_rom"]:
                    sig["rom_name"] = f"{name} ROM"
        sig["tables"] = known_tables(at)
    elif len(data) == 256 and data[:6] == DISK2_BOOT_SIG:
        sig["is_rom"] = True
        sig["rom_name"] = "Disk II 16-sector boot ROM (P5A)"
    return sig


def identify_file(path: str, org: int | None = None, raw: bool = False) -> dict:
    """Identify an Apple II file. Returns a dict describing format, segments
    (org + bytes), entry address, ProDOS metadata and ROM hints."""
    with open(path, "rb") as f:
        data = f.read()

    info = {
        "file": path,
        "size": len(data),
        "md5": hashlib.md5(data).hexdigest(),
        "format": "raw",
        "name": None,
        "prodos_type": None,
        "prodos_type_name": None,
        "aux_type": None,
        "segments": [],
        "entry": None,
        "is_rom": False,
        "rom_name": None,
        "machine": None,
        "cpu_hint": None,
        "vectors": None,
        "tables": [],
        "exclude": [],
        "notes": [],
    }

    payload = data
    load = None
    ptype = None
    aux = None

    if not raw:
        asf = parse_applesingle(data)
        if asf is not None:
            info["format"] = "applesingle"
            info["name"] = asf["name"]
            ptype = asf["prodos_type"]
            aux = asf["aux_type"]
            payload = asf["data"]
            load = load_addr_for_type(ptype, aux)
            if ptype is None:
                info["notes"].append("AppleSingle without ProDOS file info entry; --org needed")
        elif data[:4] == APPLEDOUBLE_MAGIC:
            info["notes"].append("AppleDouble header file: data fork is in the companion file")
        else:
            d33 = parse_dos33_header(data)
            if d33 is not None:
                info["format"] = "dos33_bin"
                load, payload = d33
                ptype = 0x06
            else:
                fn = org_from_filename(path)
                if fn is not None:
                    info["format"] = "raw+name"
                    ptype, aux = fn
                    load = load_addr_for_type(ptype, aux)

    if ptype is not None:
        info["prodos_type"] = ptype
        info["prodos_type_name"] = PRODOS_TYPES.get(ptype, f"${ptype:02X}")
        info["aux_type"] = aux

    if org is not None:
        if load is not None and load != org:
            info["notes"].append(f"--org ${org:04X} overrides file load address ${load:04X}")
        load = org
    elif load is None:
        guess = ROM_SIZE_ORG.get(len(payload))
        if guess is not None:
            load = guess
            info["notes"].append(f"No load address in file; ROM-size guess ${load:04X} (override with --org)")
        else:
            load = 0x2000
            info["notes"].append("No load address in file; assuming $2000 (override with --org)")

    if load + len(payload) > 0x10000:
        info["notes"].append(f"Image exceeds $FFFF from ${load:04X}; truncated")
        payload = payload[:0x10000 - load]

    info["segments"] = [{"org": load, "length": len(payload), "data": payload}]
    info["entry"] = load

    known = KNOWN_ROM_MD5.get(info["md5"])
    sig = rom_signature(payload, load)
    info.update({k: sig[k] for k in ("is_rom", "rom_name", "machine", "cpu_hint", "vectors", "tables")})
    if known:
        info["is_rom"] = True
        info["rom_name"] = known[0]
        info["cpu_hint"] = known[2]
    if info["is_rom"]:
        info["entry"] = sig["vectors"]["RESET"] if sig["vectors"] else load
        if load <= 0xC000 and load + len(payload) > 0xC0FF:
            info["exclude"].append((0xC000, 0xC0FF))
            info["notes"].append("$C000-$C0FF is I/O space in this image; treated as data")
    if ptype == 0xFF:
        info["notes"].append("ProDOS SYS file: loads at $2000, entered at $2000")
    return info


def load_image(path: str, org: int | None = None, raw: bool = False):
    """Return ([(org, bytes), ...], info) for the disassembler tools."""
    info = identify_file(path, org=org, raw=raw)
    segments = [(s["org"], s["data"]) for s in info["segments"]]
    return segments, info


def print_report(info: dict):
    print(f"File:     {info['file']}")
    print(f"Size:     {info['size']} bytes")
    print(f"MD5:      {info['md5']}")
    print(f"Format:   {info['format']}")
    if info["name"]:
        print(f"Name:     {info['name']}")
    if info["prodos_type"] is not None:
        aux = f" aux=${info['aux_type']:04X}" if info["aux_type"] is not None else ""
        print(f"ProDOS:   type ${info['prodos_type']:02X} ({info['prodos_type_name']}){aux}")
    for s in info["segments"]:
        end = s["org"] + s["length"] - 1
        print(f"Segment:  ${s['org']:04X}-${end:04X} ({s['length']} bytes)")
    if info["entry"] is not None:
        print(f"Entry:    ${info['entry']:04X}")
    if info["is_rom"]:
        print(f"ROM:      {info['rom_name']}")
    if info["machine"]:
        print(f"Machine:  {info['machine']}")
    if info["cpu_hint"]:
        print(f"CPU hint: {info['cpu_hint']}")
    if info["vectors"]:
        v = info["vectors"]
        print(f"Vectors:  NMI=${v['NMI']:04X} RESET=${v['RESET']:04X} IRQ=${v['IRQ']:04X}")
    for t in info["tables"]:
        kind = f"low bytes, hi=${t['hi']:02X}" if t["hi"] is not None else "words"
        print(f"Table:    ${t['addr']:04X} x{t['count']} {kind}{' (address-1)' if t['rts'] else ''}"
              f" — {t['name']} (auto)")
    for n in info["notes"]:
        print(f"Note:     {n}")


def main():
    parser = argparse.ArgumentParser(description="Apple II file / ROM analyzer")
    parser.add_argument("file", help="File to analyze")
    parser.add_argument("--org", type=lambda x: int(x, 0), default=None,
                        help="Load address override (e.g. 0x2000)")
    parser.add_argument("--raw", action="store_true", help="Skip container detection")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    info = identify_file(args.file, org=args.org, raw=args.raw)
    if args.json:
        out = dict(info)
        out["segments"] = [{"org": s["org"], "length": s["length"]} for s in info["segments"]]
        print(json.dumps(out, indent=2))
    else:
        print_report(info)


if __name__ == "__main__":
    main()

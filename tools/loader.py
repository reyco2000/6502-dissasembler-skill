#!/usr/bin/env python3
"""
loader.py — 6502 file format detection and image loading
Usage: python3 loader.py <file> [--org 0x2000] [--raw] [--machine c64] [--bank N] [--json]

Other machines first (each sets the machine id):
  iNES .nes (PRG banks; --bank N maps a 16K bank at $8000), Atari .xex
  (segments, RUNAD/INITAD entries), Atari800 .car, Lynx BLL .o / .lnx,
  BBC .inf sidecar (load/exec), CBM .prg / .P00 (load address, BASIC
  SYS stub -> entry). Headerless files: OS ROM signatures (CBM KERNAL,
  Acorn MOS, Atari OS, Lynx boot ROM), BBC sideways-ROM and C64 CBM80
  cartridge headers, then the size guesses below.

Apple II formats, in this order:
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

try:
    from tools import machines
except ImportError:
    import machines

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


# ---------------------------------------------------------------------------
# Other 6502 machines: containers
# ---------------------------------------------------------------------------

# BASIC start address of a PRG -> machine (VIC-20: unexpanded / +3K / +8K)
CBM_BASIC_STARTS = {0x0801: "c64", 0x1001: "vic20", 0x0401: "vic20", 0x1201: "vic20",
                    0x1C01: "c128"}


def parse_cbm_prg(data: bytes, path: str) -> dict | None:
    """CBM program file: 2-byte load address + data (also PC64 .P00).
    Accepted by extension, or when the load address is a BASIC start and
    the first line link points inside the file."""
    hdr = 0
    if data[:8] == b"C64File\x00" and len(data) > 28:
        hdr = 26
    ext = os.path.splitext(path)[1].lower()
    body = data[hdr:]
    if len(body) < 3:
        return None
    load = _le16(body, 0)
    payload = body[2:]
    if not (hdr or ext == ".prg" or re.match(r"^\.p\d\d$", ext)):
        if load not in CBM_BASIC_STARTS or len(payload) < 6:
            return None
        link = _le16(payload, 0)
        if not (load + 5 <= link < load + len(payload)):
            return None
    res = {"load": load, "data": payload, "machine": CBM_BASIC_STARTS.get(load), "sys": None}
    if load in CBM_BASIC_STARTS:
        res["sys"] = basic_sys_address(payload)
    return res


def basic_sys_address(prog: bytes) -> int | None:
    """Target of a 'SYS nnnn' in the first BASIC line (token $9E)."""
    if len(prog) < 6:
        return None
    i = 4                          # skip link + line number
    end = min(len(prog), 80)
    while i < end and prog[i] != 0x00:
        if prog[i] == 0x9E:
            i += 1
            while i < end and prog[i] in (0x20, 0x28):   # spaces, '('
                i += 1
            digits = b""
            while i < end and 0x30 <= prog[i] <= 0x39:
                digits += bytes([prog[i]])
                i += 1
            return int(digits) if digits and int(digits) <= 0xFFFF else None
        i += 1
    return None


def parse_atari_xex(data: bytes) -> dict | None:
    """Atari DOS binary load file: $FFFF, then (start, end) segments.
    RUNAD ($02E0) and INITAD ($02E2) segments become entry points instead
    of memory contents."""
    if len(data) < 7 or data[:2] != b"\xff\xff":
        return None
    pos, segs, run, inits = 2, [], None, []
    while pos + 4 <= len(data):
        if _le16(data, pos) == 0xFFFF:
            pos += 2
            continue
        start, end = _le16(data, pos), _le16(data, pos + 2)
        pos += 4
        n = end - start + 1
        if n <= 0 or pos + n > len(data):
            return None
        chunk = data[pos:pos + n]
        pos += n
        if start <= 0x02E0 and start + n - 1 >= 0x02E1:
            run = chunk[0x02E0 - start] | (chunk[0x02E1 - start] << 8)
        if start <= 0x02E2 and start + n - 1 >= 0x02E3:
            inits.append(chunk[0x02E2 - start] | (chunk[0x02E3 - start] << 8))
        # keep everything except the RUNAD/INITAD bytes, split into runs
        run_start = None
        for off in range(n + 1):
            keep = off < n and not 0x02E0 <= start + off <= 0x02E3
            if keep and run_start is None:
                run_start = off
            elif not keep and run_start is not None:
                segs.append((start + run_start, chunk[run_start:off]))
                run_start = None
    if pos != len(data) or not segs:
        return None
    return {"segments": segs, "run": run, "inits": inits}


def parse_atari_car(data: bytes) -> dict | None:
    """Atari800-emulator .car: 'CART' + type + checksum + 4 unused bytes."""
    if len(data) < 16 + 4096 or data[:4] != b"CART":
        return None
    body = data[16:]
    org = {8192: 0xA000, 16384: 0x8000}.get(len(body))
    if org is None:
        return None
    return {"load": org, "data": body, "type": _be32(data, 4)}


def parse_ines(data: bytes, bank: int | None) -> dict | None:
    """iNES / NES 2.0 header. NROM-128 loads at $C000, NROM-256 at $8000,
    bank-switched carts get their last (fixed) 16K bank at $C000 and,
    with --bank N, bank N at $8000."""
    if len(data) < 16 + 16384 or data[:4] != b"NES\x1a":
        return None
    prg_n, chr_n, f6, f7 = data[4], data[5], data[6], data[7]
    mapper = (f6 >> 4) | (f7 & 0xF0)
    start = 16 + (512 if f6 & 0x04 else 0)
    prg = data[start:start + prg_n * 16384]
    if prg_n == 0 or len(prg) < prg_n * 16384:
        return None
    notes = [f"iNES: mapper {mapper}, {prg_n} x 16K PRG, {chr_n} x 8K CHR, "
             f"{'vertical' if f6 & 1 else 'horizontal'} mirroring"
             f"{', battery RAM' if f6 & 2 else ''}{', trainer' if f6 & 4 else ''}"]
    if prg_n == 1:
        segs = [(0xC000, prg)]
        notes.append("NROM-128: 16K PRG at $C000 (mirrored at $8000)")
    elif prg_n == 2 and mapper == 0:
        segs = [(0x8000, prg)]
    else:
        last = prg[-16384:]
        segs = [(0xC000, last)]
        if bank is not None:
            if not 0 <= bank < prg_n:
                raise ValueError(f"--bank {bank}: cart has banks 0-{prg_n - 1}")
            segs.insert(0, (0x8000, prg[bank * 16384:(bank + 1) * 16384]))
            notes.append(f"PRG bank {bank} at $8000, last bank {prg_n - 1} fixed at $C000")
        else:
            notes.append(f"last PRG bank ({prg_n - 1}) at $C000; pass --bank N for $8000-$BFFF")
    return {"segments": segs, "mapper": mapper, "prg": prg_n, "chr": chr_n, "notes": notes}


def parse_lynx(data: bytes) -> dict | None:
    """BLL executable (.o/.com: $80 $08, BE load, BE size, 'BS93') or an
    .lnx cartridge (64-byte 'LYNX' header + encrypted cart image)."""
    if len(data) > 10 and data[:2] == b"\x80\x08" and data[6:10] == b"BS93":
        return {"kind": "bll", "load": _be16(data, 2), "data": data[10:]}
    if len(data) > 64 and data[:4] == b"LYNX":
        name = data[10:42].split(b"\x00")[0].decode("ascii", "replace")
        return {"kind": "lnx", "load": None, "data": data[64:], "name": name}
    return None


def parse_bbc_inf(path: str) -> dict | None:
    """BBC sidecar NAME.inf: '$.NAME  LLLLLLLL EEEEEEEE [length]'."""
    for cand in (path + ".inf", os.path.splitext(path)[0] + ".inf"):
        if cand != path and os.path.exists(cand):
            try:
                toks = open(cand, encoding="latin-1").read().split()
            except OSError:
                return None
            nums = [t for t in toks[1:] if re.fullmatch(r"[0-9A-Fa-f]{1,8}", t)]
            if len(nums) >= 2:
                return {"load": int(nums[0], 16) & 0xFFFF, "exec": int(nums[1], 16) & 0xFFFF,
                        "name": toks[0]}
    return None


def bbc_rom_header(data: bytes) -> dict | None:
    """Acorn sideways ROM header at $8000: language JMP, service JMP, type,
    copyright offset -> '\\0(C)', title at $8009."""
    if len(data) not in (8192, 16384) or len(data) < 16:
        return None
    c = data[7]
    if c < 9 or c + 4 > len(data) or data[c] != 0 or data[c + 1:c + 4] != b"(C)":
        return None
    title = data[9:c].split(b"\x00")[0].decode("latin-1", "replace")
    entries = []
    if data[0] == 0x4C:
        entries.append(0x8000)
    if data[3] == 0x4C:
        entries.append(0x8003)
    rtype = data[6]
    kind = "+".join(k for bit, k in ((0x80, "service"), (0x40, "language")) if rtype & bit)
    return {"title": title, "entries": entries, "type": rtype, "kind": kind or "data"}


def machine_rom_signature(data: bytes, org: int) -> tuple[str, str] | None:
    """(machine id, ROM name) for well-known non-Apple OS ROMs."""
    end = org + len(data) - 1

    def at(a):
        return data[a - org] if org <= a <= end else None

    def word(a):
        lo, hi = at(a), at(a + 1)
        return None if lo is None or hi is None else lo | (hi << 8)

    rst = word(0xFFFC)
    if (at(0xFFD2), at(0xFFD3), at(0xFFD4)) == (0x6C, 0x26, 0x03):   # CHROUT = JMP ($0326)
        if rst == 0xFCE2:
            return "c64", "Commodore 64 KERNAL"
        if rst == 0xFD22:
            return "vic20", "VIC-20 KERNAL"
    if rst == 0xFF3D and at(0xFF3D) is not None:
        return "c128", "Commodore 128 KERNAL"
    if (at(0xFFEE), at(0xFFEF), at(0xFFF0)) == (0x6C, 0x0E, 0x02):   # OSWRCH = JMP ($020E)
        return "bbc_b", "Acorn MOS"
    if all(at(0xE450 + 3 * i) == 0x4C for i in range(6)) and rst is not None:
        return ("atari800xl", "Atari XL/XE OS") if org <= 0xC000 else ("atari800", "Atari 400/800 OS")
    if org == 0xFE00 and len(data) == 512 and rst == 0xFF80:
        return "lynx", "Atari Lynx boot ROM"
    return None


def identify_file(path: str, org: int | None = None, raw: bool = False,
                  machine: str | None = None, bank: int | None = None) -> dict:
    """Identify a 6502 program or ROM. Returns a dict describing format,
    segments (org + bytes), entry address(es), machine and ROM hints.
    `machine` (a machines.py id) forces the target machine."""
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
        "entries": [],
        "is_rom": False,
        "rom_name": None,
        "machine": None,
        "machine_id": machine,
        "cpu_hint": None,
        "vectors": None,
        "tables": [],
        "exclude": [],
        "notes": [],
    }

    if not raw:
        multi = _identify_container(data, path, info, machine, bank)
        if multi:
            return _finish(info, org)

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
            d33 = parse_dos33_header(data) if machine in (None, "apple2") else None
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
            info["machine_id"] = info["machine_id"] or "apple2"

    if ptype is not None:
        info["prodos_type"] = ptype
        info["prodos_type_name"] = PRODOS_TYPES.get(ptype, f"${ptype:02X}")
        info["aux_type"] = aux

    sideways = None
    if org is not None:
        if load is not None and load != org:
            info["notes"].append(f"--org ${org:04X} overrides file load address ${load:04X}")
        load = org
    elif load is None:
        guess, why = _guess_raw_org(payload, machine, info)
        if guess is not None:
            load = guess
            info["notes"].append(f"No load address in file; {why} ${load:04X} (override with --org)")
        else:
            load = 0x2000
            info["notes"].append("No load address in file; assuming $2000 (override with --org)")
    if not raw and load == 0x8000 and info["machine_id"] in (None, "bbc_a", "bbc_b", "bbc_bplus",
                                                             "bbc_master"):
        sideways = bbc_rom_header(payload)

    if load + len(payload) > 0x10000:
        info["notes"].append(f"Image exceeds $FFFF from ${load:04X}; truncated")
        payload = payload[:0x10000 - load]

    info["segments"] = [{"org": load, "length": len(payload), "data": payload}]
    info["entry"] = load

    known = KNOWN_ROM_MD5.get(info["md5"])
    apple_ok = info["machine_id"] in (None, "apple2")
    sig = rom_signature(payload, load)
    msig = machine_rom_signature(payload, load) if info["machine_id"] != "apple2" else None
    if msig and info["machine_id"] is None:
        info["machine_id"] = msig[0]
        apple_ok = False
    if apple_ok and sig["machine"]:
        info["machine_id"] = "apple2"
    if apple_ok:
        info.update({k: sig[k] for k in ("is_rom", "rom_name", "machine", "cpu_hint", "vectors",
                                         "tables")})
    else:
        info.update({k: sig[k] for k in ("is_rom", "vectors")})
        if sig["is_rom"]:
            info["rom_name"] = msig[1] if msig else sig["rom_name"]
    if known:
        info["is_rom"] = True
        info["rom_name"] = known[0]
        info["cpu_hint"] = known[2]
    if sideways:
        info["machine_id"] = info["machine_id"] or "bbc_b"
        info["is_rom"] = True
        info["rom_name"] = f"BBC sideways ROM '{sideways['title']}' ({sideways['kind']}, type ${sideways['type']:02X})"
        info["format"] = "bbc_rom"
        if sideways["entries"]:
            info["entry"] = sideways["entries"][0]
            info["entries"] += sideways["entries"][1:]
    if info["is_rom"] and not sideways:
        info["entry"] = sig["vectors"]["RESET"] if sig["vectors"] else load
        if (info["machine_id"] in (None, "apple2")) and load <= 0xC000 and load + len(payload) > 0xC0FF:
            info["exclude"].append((0xC000, 0xC0FF))
            info["notes"].append("$C000-$C0FF is I/O space in this image; treated as data")
    _cart_entries(info, payload, load)
    if ptype == 0xFF:
        info["notes"].append("ProDOS SYS file: loads at $2000, entered at $2000")
    return _finish(info, None)


def _guess_raw_org(payload: bytes, machine: str | None, info: dict):
    """Load address for a headerless file from its size (and signature)."""
    n = len(payload)
    if machine not in (None, "apple2"):
        prof = machines.MACHINES[machine]
        if n in prof["raw_org"]:
            return prof["raw_org"][n], f"{prof['title']} ROM-size guess"
        return None, ""
    if n in (8192, 16384) and bbc_rom_header(payload):
        return 0x8000, "sideways-ROM header found; loading at"
    if n == 8192 and payload[4:9] == b"\xc3\xc2\xcd\x38\x30":
        return 0x8000, "C64 cartridge (CBM80) at"
    if n == 8192 and payload[4:12] == b"CBMBASIC":
        info["machine_id"] = info["machine_id"] or "c64"
        return 0xA000, "C64 BASIC ROM ('CBMBASIC') at"
    if machine is None:
        for size, org_ in ((8192, 0xE000), (10240, 0xD800), (16384, 0xC000), (512, 0xFE00)):
            if n == size and machine_rom_signature(payload, org_):
                return org_, "OS ROM signature; loading at"
        if n == 32768:
            return 0x8000, "32K image (NES NROM-256 PRG / cartridge) at"
    guess = ROM_SIZE_ORG.get(n)
    return (guess, "ROM-size guess") if guess is not None else (None, "")


def _cart_entries(info: dict, payload: bytes, load: int):
    """Cartridge headers that name their own entry points."""
    end = load + len(payload) - 1

    def word(a):
        return payload[a - load] | (payload[a + 1 - load] << 8) if load <= a and a + 1 <= end else None

    mid = info["machine_id"]
    if load == 0x8000 and payload[4:9] == b"\xc3\xc2\xcd\x38\x30" and mid in (None, "c64", "c128"):
        info["machine_id"] = mid or "c64"
        cold, warm = word(0x8000), word(0x8002)
        info["is_rom"] = True
        info["rom_name"] = "C64 cartridge (CBM80)"
        info["entry"] = cold
        info["entries"] += [w for w in (warm,) if w is not None]
        info["tables"].append({"addr": 0x8000, "count": 2, "rts": False, "stride": 2, "hi": None,
                               "name": "CBM80 cold/warm start"})
    if mid and mid.startswith("atari") and end >= 0xBFFF and load <= 0xBFFA and end < 0xFFFA:
        run, init = word(0xBFFA), word(0xBFFE)
        info["is_rom"] = True
        info["rom_name"] = info["rom_name"] or "Atari cartridge"
        info["entry"] = run
        if init is not None and init != run:
            info["entries"].append(init)
        info["notes"].append("Atari cartridge: RUN address $BFFA, INIT address $BFFE, flags $BFFD")


def _identify_container(data: bytes, path: str, info: dict, machine: str | None, bank) -> bool:
    """Non-Apple containers. Fills info and returns True when one matched."""
    nes = parse_ines(data, bank)
    if nes:
        info["format"] = "ines"
        info["machine_id"] = machine if machine in ("nes", "famicom") else "nes"
        info["segments"] = [{"org": o, "length": len(d), "data": d} for o, d in nes["segments"]]
        info["notes"] += nes["notes"]
        info["is_rom"] = True
        info["rom_name"] = f"iNES cartridge, mapper {nes['mapper']}"
        last = nes["segments"][-1][1]
        vec = lambda off: last[off] | (last[off + 1] << 8)   # noqa: E731
        info["vectors"] = {"NMI": vec(0x3FFA), "RESET": vec(0x3FFC), "IRQ": vec(0x3FFE)}
        info["entry"] = info["vectors"]["RESET"]
        return True
    xex = parse_atari_xex(data)
    if xex:
        info["format"] = "atari_xex"
        info["machine_id"] = machine if (machine or "").startswith("atari") else "atari800xl"
        info["segments"] = [{"org": o, "length": len(d), "data": d} for o, d in xex["segments"]]
        info["entry"] = xex["run"] if xex["run"] is not None else \
            (xex["inits"][0] if xex["inits"] else xex["segments"][0][0])
        info["entries"] = [a for a in xex["inits"] if a != info["entry"]]
        if xex["run"] is not None:
            info["notes"].append(f"RUNAD ($02E0) = ${xex['run']:04X}")
        for a in xex["inits"]:
            info["notes"].append(f"INITAD ($02E2) = ${a:04X} (run during load)")
        return True
    car = parse_atari_car(data)
    if car:
        info["format"] = "atari_car"
        info["machine_id"] = machine if (machine or "").startswith("atari") else "atari800xl"
        info["segments"] = [{"org": car["load"], "length": len(car["data"]), "data": car["data"]}]
        info["notes"].append(f"Atari800 .car, cartridge type {car['type']}")
        _cart_entries(info, car["data"], car["load"])
        return True
    lx = parse_lynx(data)
    if lx:
        info["machine_id"] = "lynx"
        if lx["kind"] == "bll":
            info["format"] = "lynx_bll"
            info["segments"] = [{"org": lx["load"], "length": len(lx["data"]), "data": lx["data"]}]
            info["entry"] = lx["load"]
        else:
            info["format"] = "lynx_lnx"
            info["name"] = lx["name"]
            load = 0x0200
            info["segments"] = [{"org": load, "length": min(len(lx["data"]), 0x10000 - load),
                                 "data": lx["data"][:0x10000 - load]}]
            info["entry"] = load
            info["notes"].append("LNX cartridge: the first block is RSA-encrypted and decrypted by "
                                 "the boot ROM to $0200; disassemble a decrypted dump or BLL .o "
                                 "file for real code (use --org to override)")
        return True
    if machine in (None, "bbc_a", "bbc_b", "bbc_bplus", "bbc_master"):
        inf = parse_bbc_inf(path)
        if inf:
            info["format"] = "bbc_inf"
            info["name"] = inf["name"]
            info["machine_id"] = machine or "bbc_b"
            d = data[:0x10000 - inf["load"]]
            info["segments"] = [{"org": inf["load"], "length": len(d), "data": d}]
            info["entry"] = inf["exec"]
            info["notes"].append(f".inf sidecar: load ${inf['load']:04X}, exec ${inf['exec']:04X}")
            return True
    if machine in (None, "c64", "c128", "vic20"):
        prg = parse_cbm_prg(data, path)
        if prg:
            info["format"] = "cbm_prg"
            info["machine_id"] = machine or prg["machine"] or "c64"
            if not (machine or prg["machine"]):
                info["notes"].append(f"PRG loads at ${prg['load']:04X}; machine assumed c64 "
                                     "(pass --machine vic20/c128 otherwise)")
            d = prg["data"][:0x10000 - prg["load"]]
            info["segments"] = [{"org": prg["load"], "length": len(d), "data": d}]
            info["entry"] = prg["load"]
            if prg["sys"] is not None:
                info["entry"] = prg["sys"]
                info["notes"].append(f"BASIC stub: SYS {prg['sys']} (${prg['sys']:04X})")
            elif prg["load"] in CBM_BASIC_STARTS:
                info["notes"].append("BASIC program without a SYS stub: entry is the load address; "
                                     "pass --entry for machine code")
            return True
    return False


def _finish(info: dict, org) -> dict:
    """Common tail: --org relocation of single-segment containers, the
    display machine name and per-machine CPU notes."""
    if org is not None and len(info["segments"]) == 1 and info["segments"][0]["org"] != org \
            and info["format"] not in ("raw", "applesingle", "dos33_bin", "raw+name"):
        s = info["segments"][0]
        delta = org - s["org"]
        info["notes"].append(f"--org ${org:04X} overrides file load address ${s['org']:04X}")
        s["org"] = org
        if info["entry"] is not None:
            info["entry"] = (info["entry"] + delta) & 0xFFFF
    mid = info["machine_id"]
    if mid:
        prof = machines.MACHINES[mid]
        info["machine"] = info["machine"] or prof["title"]
        if info["cpu_hint"] is None and prof["default_cpu"] != "6502":
            info["cpu_hint"] = prof["default_cpu"]
        if prof["cpu_note"]:
            info["notes"].append(prof["cpu_note"])
    return info


def load_image(path: str, org: int | None = None, raw: bool = False,
               machine: str | None = None, bank: int | None = None):
    """Return ([(org, bytes), ...], info) for the disassembler tools."""
    info = identify_file(path, org=org, raw=raw, machine=machine, bank=bank)
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
    if info["machine"] or info["machine_id"]:
        mid = info["machine_id"] or "apple2"
        print(f"Machine:  {info['machine'] or mid}  (--machine {mid})")
    for e in info["entries"]:
        print(f"Entry+:   ${e:04X}")
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
    parser = argparse.ArgumentParser(description="6502 file / ROM analyzer (Apple II, CBM, Atari, BBC, NES, Lynx)")
    parser.add_argument("file", help="File to analyze")
    parser.add_argument("--org", type=lambda x: int(x, 0), default=None,
                        help="Load address override (e.g. 0x2000)")
    parser.add_argument("--raw", action="store_true", help="Skip container detection")
    parser.add_argument("--machine", default=None, help="Force the machine (" + ", ".join(machines.MACHINES) + ")")
    parser.add_argument("--bank", type=int, default=None, help="iNES: 16K PRG bank to map at $8000")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    m = machines.resolve(args.machine) if args.machine and args.machine != "auto" else None
    info = identify_file(args.file, org=args.org, raw=args.raw, machine=m, bank=args.bank)
    if args.json:
        out = dict(info)
        out["segments"] = [{"org": s["org"], "length": s["length"]} for s in info["segments"]]
        print(json.dumps(out, indent=2))
    else:
        print_report(info)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
machines.py — per-machine profiles and reference-table symbol loading

Every 6502 machine the tools know has a profile here (zero page, hardware
window, ROM windows, default CPU, raw-ROM load guesses) and a pair of
markdown reference tables under reference/<machine>/ (memory_map.md,
rom_entry_points.md). The Apple II keeps its historical files in
reference/ and its hand-tuned symbol dicts in dasm6502.py.

Table contract (shared with annotator.py): a row is
    | $XXXX | NAME | Description |      (or $XX for zero page)
    | &XX   | NAME | Description |      (BBC OSBYTE/OSWORD reason codes)
Range rows ($XXXX-$YYYY) and tables whose first column is not an address
are documentation only.

Usage: python3 machines.py [--list] [--check]
"""

import os
import re
import sys
import argparse

REF_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference")


def _p(**kw):
    base = {"zp": (0x00, 0xFF), "hw": [], "rom_windows": [], "default_cpu": "6502",
            "raw_org": {}, "os_vectors": [], "rom_note": None, "family": None,
            "inline_calls": {}, "cpu_note": None}
    base.update(kw)
    return base


_ATARI = dict(family="atari8", hw=[(0xD000, 0xD7FF)], os_vectors=[(0x0200, 0x0247)],
              rom_note="(stores into the OS ROM window hit RAM only when PORTB banks the OS out)")
_BBC = dict(family="bbc", hw=[(0xFC00, 0xFEFF)], rom_windows=[(0x8000, 0xBFFF), (0xC000, 0xFFFF)],
            raw_org={16384: 0xC000}, os_vectors=[(0x0200, 0x0235)],
            rom_note="(FRED/JIM/SHEILA $FC00-$FEFF is I/O, not ROM)")
_NES = dict(family="nes", hw=[(0x2000, 0x2007), (0x4000, 0x4017)], rom_windows=[(0x8000, 0xFFFF)],
            raw_org={16384: 0xC000, 32768: 0x8000},
            rom_note="(stores into $8000-$FFFF are mapper register writes, not code)")

MACHINES = {
    "apple2": _p(title="Apple II", family="apple2", hw=[(0xC000, 0xCFFF)],
                 ref_files=("apple2_memory_map.md", "rom_entry_points.md"), ref_dir=REF_ROOT,
                 rom_windows=[(0xD000, 0xFFFF)], os_vectors=[(0x03D0, 0x03FF)],
                 rom_note="(stores into $D000-$FFFF write language-card RAM, not this ROM)"),
    "atari400": _p(title="Atari 400", rom_windows=[(0xD800, 0xFFFF)], raw_org={10240: 0xD800}, **_ATARI),
    "atari800": _p(title="Atari 800", rom_windows=[(0xD800, 0xFFFF)], raw_org={10240: 0xD800}, **_ATARI),
    "atari600xl": _p(title="Atari 600XL", rom_windows=[(0xC000, 0xFFFF)], raw_org={16384: 0xC000}, **_ATARI),
    "atari800xl": _p(title="Atari 800XL", rom_windows=[(0xC000, 0xFFFF)], raw_org={16384: 0xC000}, **_ATARI),
    "atari1200xl": _p(title="Atari 1200XL", rom_windows=[(0xC000, 0xFFFF)], raw_org={16384: 0xC000}, **_ATARI),
    "c64": _p(title="Commodore 64", family="cbm", hw=[(0xD000, 0xDFFF)],
              rom_windows=[(0xA000, 0xBFFF), (0xE000, 0xFFFF)], raw_org={8192: 0xE000, 16384: 0xC000},
              os_vectors=[(0x0300, 0x0333)],
              rom_note="(stores into $A000-$BFFF/$E000-$FFFF write the RAM under the ROM)",
              cpu_note="C64 software often uses NMOS illegal opcodes: retry with --undocumented "
                       "if code paths are full of .byte"),
    "c128": _p(title="Commodore 128", family="cbm", hw=[(0xD000, 0xDFFF), (0xFF00, 0xFF04)],
               rom_windows=[(0x4000, 0xBFFF), (0xC000, 0xCFFF), (0xE000, 0xFFFF)],
               raw_org={16384: 0xC000, 32768: 0x4000}, os_vectors=[(0x0300, 0x0335)],
               rom_note="(stores into ROM windows write RAM; the MMU at $D500/$FF00 picks the bank)",
               cpu_note="8502 = NMOS 6502 core; use --undocumented for code that needs illegal opcodes"),
    "vic20": _p(title="Commodore VIC-20", family="cbm", hw=[(0x9000, 0x93FF), (0x9400, 0x97FF)],
                rom_windows=[(0xC000, 0xDFFF), (0xE000, 0xFFFF)], raw_org={8192: 0xE000},
                os_vectors=[(0x0300, 0x0333)]),
    "lynx": _p(title="Atari Lynx", family="lynx", hw=[(0xFC00, 0xFDFF), (0xFFF8, 0xFFF9)],
               default_cpu="65sc02", rom_windows=[(0xFE00, 0xFFF7)], raw_org={512: 0xFE00},
               rom_note="(MAPCTL $FFF9 can map RAM over the boot ROM)"),
    "nes": _p(title="NES", **_NES),
    "famicom": _p(title="Famicom", **_NES),
    "bbc_a": _p(title="BBC Micro Model A", **_BBC),
    "bbc_b": _p(title="BBC Micro Model B", **_BBC),
    "bbc_bplus": _p(title="BBC Micro Model B+", **_BBC),
    "bbc_master": _p(title="BBC Master 128", **{**_BBC, "default_cpu": "65c12"}),
}

for _mid, _prof in MACHINES.items():
    _prof["id"] = _mid
    _prof.setdefault("ref_dir", os.path.join(REF_ROOT, _mid))
    _prof.setdefault("ref_files", ("memory_map.md", "rom_entry_points.md"))

ALIASES = {"apple": "apple2", "appleii": "apple2", "a2": "apple2", "atari": "atari800xl",
           "atari8": "atari800xl", "commodore": "c64", "cbm": "c64", "vic": "vic20",
           "bbc": "bbc_b", "beeb": "bbc_b", "master": "bbc_master", "bbcmaster": "bbc_master",
           "fc": "famicom"}


def resolve(name) -> str:
    """Canonical machine id for a user-supplied name ('apple2' when None)."""
    if not name or name == "auto":
        return "apple2"
    key = name.lower().replace("-", "").replace(" ", "")
    key = ALIASES.get(key, key)
    if key not in MACHINES:
        # 'bbcb' / 'atari800' style spellings without underscores
        for mid in MACHINES:
            if mid.replace("_", "") == key:
                return mid
        raise ValueError(f"unknown machine {name!r}; known: {', '.join(MACHINES)}")
    return key


def profile(name) -> dict:
    return MACHINES[resolve(name)]


def machine_choices() -> list:
    return ["auto"] + list(MACHINES)


def in_ranges(addr: int, ranges) -> bool:
    return any(s <= addr <= e for s, e in ranges)


# ---------------------------------------------------------------------------
# Markdown table parsing (shared by the annotator and the disassembler)
# ---------------------------------------------------------------------------

_SKIP_HEADERS = ("| Address", "| Range", "| Code", "| Call", "| Field", "| Offset", "| Mapper",
                 "| Machine", "| File", "| Source")


def parse_table_rows(filepath: str):
    """Yield (first_col, name, description) from markdown table rows."""
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line.startswith("|") or line.startswith("|--") or line.startswith(_SKIP_HEADERS):
                continue
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 3:
                yield parts[0], parts[1], parts[2]


IDENT_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _reserved_names() -> set:
    """Names ca65 can't take as a symbol: every mnemonic of every supported
    CPU, plus register names."""
    try:
        from tools import dasm6502 as d
    except ImportError:
        import dasm6502 as d
    names = {"A", "X", "Y", "S", "Z"}
    for tbl in (d.OPCODES_W65C02, d.OPCODES_UNDOC):
        names.update(m for m, _mode in tbl.values())
    names.update({"NOP", "STP", "WAI", "BRA",
                  # other ca65 6502X spellings of illegal opcodes
                  "JAM", "KIL", "SHA", "SHX", "SHY", "TAS", "ANE", "LXA", "SBX", "DOP", "TOP",
                  "AHX", "XAA", "ISB", "DCM", "INS", "ASO", "LSE", "AXA", "SKB", "SKW"})
    return names


class MachineSymbols:
    """Symbol tables for one machine, sorted by the profile's ranges.

    rom: 16-bit entry points + OS variables outside the hardware window
    hw:  hardware registers inside the profile's hw ranges
    zp:  zero-page locations (2-digit rows, or 4-digit rows below $100)
    codes: {('OSBYTE'|'OSWORD'|'', code): (name, desc)} from &XX rows
    Each table maps addr -> (name, desc). Names are unique across the
    tables (first row wins) so the equate block never redefines a symbol.
    """

    def __init__(self, machine: str, ref_dir: str | None = None):
        self.machine = resolve(machine)
        self.prof = MACHINES[self.machine]
        self.rom: dict[int, tuple] = {}
        self.hw: dict[int, tuple] = {}
        self.zp: dict[int, tuple] = {}
        self.codes: dict[tuple, tuple] = {}
        self.mli: dict[int, tuple] = {}
        self.dropped: list[tuple] = []   # (addr, name, why) — rows not usable as symbols
        self._names: dict[str, int] = {}
        mem_f, rom_f = self.prof["ref_files"]
        for fname in (rom_f, mem_f):
            path = os.path.join(ref_dir or self.prof["ref_dir"], fname)
            if os.path.exists(path):
                self._load(path, is_rom_file=(fname == rom_f))

    def _load(self, path: str, is_rom_file: bool):
        reserved = _reserved_names()
        for key, name, desc in parse_table_rows(path):
            m = re.match(r'^&([0-9A-Fa-f]{2})$', key)
            if m:
                kind = name.split("_")[0] if name.startswith(("OSBYTE_", "OSWORD_")) else ""
                self.codes.setdefault((kind, int(m.group(1), 16)), (name, desc))
                continue
            m = re.match(r'^\$([0-9A-Fa-f]{2}|[0-9A-Fa-f]{4})$', key)
            if not m:
                continue
            addr = int(m.group(1), 16)
            if len(m.group(1)) == 2 and is_rom_file and self.machine == "apple2":
                self.mli[addr] = (name, desc)   # ProDOS MLI command codes
                continue
            if len(m.group(1)) == 2 or addr < 0x100:
                tbl = self.zp
            elif in_ranges(addr, self.prof["hw"]):
                tbl = self.hw
            else:
                tbl = self.rom
            if addr in tbl:
                continue
            base = name.split("+")[0]
            if not IDENT_RE.match(base) or base.upper() in reserved:
                self.dropped.append((addr, name, "not a usable ca65 symbol"))
                tbl[addr] = (None, desc)   # keep the description, no name
                continue
            owner = self._names.get(name)
            if owner is not None and owner != addr:
                # e.g. a KERNAL jump-table entry and its real code address
                # share a name: the second one gets its address appended
                alt = f"{base}_{addr:04X}"
                if "+" in name or alt in self._names:
                    self.dropped.append((addr, name, f"name already used at ${owner:04X}"))
                    tbl[addr] = (None, desc)
                    continue
                name = alt
            self._names[name] = addr
            tbl[addr] = (name, desc)

    # ---- views the disassembler consumes ----

    def labels(self, tbl: dict, allow_offset: bool = False) -> dict:
        out = {}
        for a, (n, _d) in tbl.items():
            if n is None or ("+" in n and not allow_offset):
                continue
            if "+" in n:
                base, off = n.split("+", 1)
                if not off.isdigit() or self._names.get(base) != a - int(off):
                    continue
            out[a] = n
        return out

    @staticmethod
    def descriptions(tbl: dict) -> dict:
        return {a: d for a, (_n, d) in tbl.items() if d}

    def all_addrs(self) -> dict:
        """addr -> (name, desc) over rom + hw + zp (the annotator's view)."""
        out = {}
        for tbl in (self.zp, self.hw, self.rom):
            out.update(tbl)
        return out


_CACHE: dict[str, MachineSymbols] = {}


def load_machine_symbols(machine: str) -> MachineSymbols:
    mid = resolve(machine)
    if mid not in _CACHE:
        _CACHE[mid] = MachineSymbols(mid)
    return _CACHE[mid]


def main():
    ap = argparse.ArgumentParser(description="List machine profiles / check reference tables")
    ap.add_argument("--check", action="store_true", help="Load every machine and print counts")
    args = ap.parse_args()
    for mid, prof in MACHINES.items():
        line = f"{mid:12s} {prof['title']:22s} cpu={prof['default_cpu']:6s} " \
               f"hw={','.join(f'${s:04X}-${e:04X}' for s, e in prof['hw'])}"
        if args.check:
            s = load_machine_symbols(mid)
            line += f"  rom={len(s.rom)} hw={len(s.hw)} zp={len(s.zp)} codes={len(s.codes)}" \
                    f" dropped={len(s.dropped)}"
        print(line)
        if args.check:
            for a, n, why in load_machine_symbols(mid).dropped:
                print(f"    drop ${a:04X} {n}: {why}")


if __name__ == "__main__":
    sys.exit(main())

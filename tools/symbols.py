#!/usr/bin/env python3
"""
symbols.py — user symbol files for the 6502 tools
Usage: python3 symbols.py FILE [FILE ...]      (prints the merged table)

Accepted formats (auto-detected, mix freely with repeated --symbols):

1. JSON schema v1.0 as used by BrentRector/orchard (shared/symbols/*.json):
     {"schema_version": "1.0", "categories": {"<cat>": {
         "0xFDED": {"name": "COUT", "size": 1, "comment": "..."}}}}
   Keys must be "0x"-prefixed addresses (an "_suffix" such as "_dup" is
   ignored); decimal keys (function numbers) and the region categories
   memory_map_regions / memory_model / well_known_constants are skipped.
   size > 1 also names addr+1.. as NAME+1.. (unless those have own names).
2. Flat JSON: {"0xC311": "AUXMOVE", "$C314": {"name": "XFER", "comment": "..."}}
3. ca65 / text equates, one per line:  AUXMOVE = $C311 ; copy main<->aux
   (also "NAME EQU $XXXX", "$XXXX NAME comment" and "#" / ";" comments).

First definition wins (a warning names the conflict), so list the most
specific file first. Names must be valid ca65 identifiers; others are
skipped with a warning.
"""

import json
import re
import sys

SKIP_CATEGORIES = {"memory_map_regions", "memory_model", "well_known_constants"}
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# ca65 reserves register names and mnemonics can't be labels either
RESERVED = {"A", "X", "Y", "S", "P"}


class SymbolTable:
    """addr -> (name, comment) with first-write-wins semantics."""

    def __init__(self):
        self.by_addr: dict[int, tuple[str, str]] = {}
        # NAME+n aliases from size > 1; they only fill gaps and never block
        # a real name defined later (e.g. EXP_ROM size 2048 vs EXPROMOFF $CFFF)
        self.aliases: dict[int, tuple[str, str]] = {}
        self.by_name: dict[str, int] = {}
        self.sources: list[str] = []

    def add(self, addr: int, name: str, comment: str = "", source: str = "") -> bool:
        base = name.split("+")[0]
        if not IDENT_RE.match(base) or base.upper() in RESERVED:
            print(f"warning: {source}: invalid symbol name {name!r} at ${addr:04X}, skipped",
                  file=sys.stderr)
            return False
        if not 0 <= addr <= 0xFFFF:
            return False
        if addr in self.by_addr:
            old = self.by_addr[addr][0]
            if old != name:
                print(f"warning: {source}: ${addr:04X} already named {old!r}, ignoring {name!r}",
                      file=sys.stderr)
            return False
        if "+" not in name and name in self.by_name and self.by_name[name] != addr:
            print(f"warning: {source}: {name!r} already used for ${self.by_name[name]:04X}, "
                  f"ignoring ${addr:04X}", file=sys.stderr)
            return False
        self.by_addr[addr] = (name, comment)
        if "+" not in name:
            self.by_name[name] = addr
        return True

    def get(self, addr: int):
        return self.by_addr.get(addr) or self.aliases.get(addr)

    def name(self, addr: int):
        e = self.get(addr)
        return e[0] if e else None

    def comment(self, addr: int) -> str:
        e = self.by_addr.get(addr)
        return e[1] if e else ""

    def items(self):
        for a in sorted(self.by_addr):
            yield a, self.by_addr[a][0], self.by_addr[a][1]

    def __len__(self):
        return len(self.by_addr)

    def __contains__(self, addr):
        return addr in self.by_addr or addr in self.aliases

    # ---------------- loading ----------------

    def load(self, path: str):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        stripped = text.lstrip()
        if stripped.startswith("{"):
            self._load_json(json.loads(text), path)
        else:
            self._load_text(text, path)
        self.sources.append(path)

    @staticmethod
    def _parse_key(key: str):
        k = key.strip()
        if k.startswith("$"):
            k = "0x" + k[1:]
        if not k.lower().startswith("0x"):
            return None
        try:
            return int(k[2:].split("_")[0], 16)
        except ValueError:
            return None

    def _add_sized(self, addr, name, comment, size, source):
        if self.add(addr, name, comment, source):
            for i in range(1, min(size or 1, 0x10000 - addr)):
                self.aliases.setdefault(addr + i, (f"{name}+{i}", comment))

    def _load_json(self, data: dict, source: str):
        if "categories" in data:
            if data.get("schema_version") not in (None, "1.0"):
                print(f"warning: {source}: schema_version {data.get('schema_version')!r}, trying anyway",
                      file=sys.stderr)
            for cat, entries in data["categories"].items():
                if cat in SKIP_CATEGORIES or not isinstance(entries, dict):
                    continue
                for key, e in entries.items():
                    addr = self._parse_key(key)
                    if addr is None or not isinstance(e, dict) or "name" not in e:
                        continue
                    self._add_sized(addr, e["name"], e.get("comment", ""), e.get("size", 1), source)
            return
        for key, e in data.items():
            addr = self._parse_key(key)
            if addr is None:
                continue
            if isinstance(e, str):
                self.add(addr, e, "", source)
            elif isinstance(e, dict) and "name" in e:
                self._add_sized(addr, e["name"], e.get("comment", ""), e.get("size", 1), source)

    def _load_text(self, text: str, source: str):
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line[0] in ";#":
                continue
            comment = ""
            if ";" in line:
                line, comment = line.split(";", 1)
                line, comment = line.strip(), comment.strip()
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|:=|\bEQU\b)\s*\$([0-9A-Fa-f]{1,4})$", line, re.I)
            if m:
                self.add(int(m.group(2), 16), m.group(1), comment, source)
                continue
            m = re.match(r"^\$?([0-9A-Fa-f]{4})\s+([A-Za-z_][A-Za-z0-9_]*)\s*(.*)$", line)
            if m:
                self.add(int(m.group(1), 16), m.group(2), comment or m.group(3).strip(), source)
                continue
            print(f"warning: {source}: unrecognised line {raw!r}", file=sys.stderr)

    # ---------------- saving ----------------

    def to_json(self, name: str = "user symbols", category: str = "user") -> str:
        """Schema v1.0 JSON (orchard-compatible). NAME+n aliases are folded
        back into the base entry's size."""
        cat = {}
        for a, n, c in self.items():
            cat[f"0x{a:04X}"] = {"name": n, "size": 1, "comment": c}
        for a, (n, _c) in self.aliases.items():
            base = n.split("+")[0]
            ba = self.by_name.get(base)
            if ba is not None and f"0x{ba:04X}" in cat:
                e = cat[f"0x{ba:04X}"]
                e["size"] = max(e["size"], int(n.split("+")[1]) + 1)
        return json.dumps({"schema_version": "1.0", "name": name, "categories": {category: cat}},
                          indent=2)


def load_symbols(paths) -> SymbolTable:
    t = SymbolTable()
    for p in paths:
        t.load(p)
    return t


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    t = load_symbols(sys.argv[1:])
    for a, n, c in t.items():
        print(f"{n:24s} = ${a:04X}" + (f"  ; {c}" if c else ""))
    print(f"; {len(t)} symbols", file=sys.stderr)


if __name__ == "__main__":
    main()

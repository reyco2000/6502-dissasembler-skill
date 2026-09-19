#!/usr/bin/env python3
"""
annotator.py — Split, annotate, and merge tool for chunked 6502 disassembly
Usage:
  Split:    python3 annotator.py --split --asm file.asm --sections sections.json --output-dir chunks/
  Annotate: python3 annotator.py --annotate --manifest chunks/manifest.json --ref-dir reference/
  Merge:    python3 annotator.py --merge --manifest chunks/manifest.json --output annotated.s [--reassemble]

Pipeline: dasm6502.py produces the listing, xref.py --sections the chunk
boundaries, then this tool runs split -> annotate -> merge. Chunk files may
be edited in between (e.g. LLM-added comments); merge only needs the
CODE_MARKER line and everything after it to survive.

Chunk file layout (written by split, relied on by merge):
  header (copied from the listing: .setcpu, macros, equates, memory ranges)
  "; CHUNK n of m ..." context block (subroutines, ROM calls, xrefs)
  CODE_MARKER line
  code body (with a synthesized .org if the chunk didn't start with one)

--reassemble strips the address/hex columns on merge so the annotated file
assembles with ca65 back to the original bytes.

manifest.json lists every chunk and is the only file the driving agent
needs to read.
"""

import sys
import os
import json
import argparse
import re

try:
    from tools.dasm6502 import ROM_LABELS, HW_LABELS, ZP_LABELS
except ImportError:
    from dasm6502 import ROM_LABELS, HW_LABELS, ZP_LABELS

CODE_MARKER = "; --- BEGIN CODE ---"

# Zero-page locations user programs usually reference deliberately
COMMON_SYSTEM_ZP = {0x24, 0x25, 0x28, 0x29, 0x32, 0x33, 0x36, 0x37, 0x38, 0x39,
                    0x3C, 0x3D, 0x3E, 0x3F, 0x42, 0x43, 0x4E, 0x4F, 0x50, 0x51,
                    0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0xB8, 0xB9, 0xE6}

# "  2000  A9 00       LDA     #$00      ; comment"
LINE_RE = re.compile(r'^  ([0-9A-F]{4})  ((?:[0-9A-F]{2}|\.\.\.)(?: (?:[0-9A-F]{2}|\.\.\.))*)\s+(\S.*?)\s*$')
INSTR_RE = re.compile(r'^([A-Z][A-Z0-9]{2,3})\b\s*([^;]*?)\s*(;.*)?$')
LABEL_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*:$')
ORG_RE = re.compile(r'^\s*\.org\s+\$', re.IGNORECASE)

NAME_TO_ADDR = {}
for _tbl in (ZP_LABELS, HW_LABELS, ROM_LABELS):
    for _a, _n in _tbl.items():
        NAME_TO_ADDR[_n] = _a


def extract_header(asm_lines: list[str]) -> tuple[list[str], int]:
    """Header = everything before the first .org directive."""
    for i, line in enumerate(asm_lines):
        if ORG_RE.match(line):
            return asm_lines[:i], i
    return asm_lines, len(asm_lines)


def parse_address_from_line(line: str) -> int | None:
    m = re.match(r'^  ([0-9A-F]{4})  ', line)
    return int(m.group(1), 16) if m else None


def find_line_for_address(asm_lines: list[str], start_idx: int, target_addr: int) -> int | None:
    """Index of the first line at/after target_addr, backed up over the
    label, separator and blank lines that belong to it."""
    for i in range(start_idx, len(asm_lines)):
        addr = parse_address_from_line(asm_lines[i])
        if addr is not None and addr >= target_addr:
            j = i
            while j > start_idx:
                prev = asm_lines[j - 1].strip()
                if prev == "" or prev.startswith(";") or LABEL_RE.match(prev):
                    j -= 1
                else:
                    break
            return j
    return None


def parse_line(line: str):
    """Return (addr, mnemonic, operand, comment) for a listing line, or None."""
    m = LINE_RE.match(line.rstrip("\n"))
    if not m:
        return None
    rest = m.group(3)
    im = INSTR_RE.match(rest)
    if not im:
        return None
    return int(m.group(1), 16), im.group(1), im.group(2).strip(), (im.group(3) or "")


def memory_ranges_from_header(lines: list[str]) -> list[tuple[int, int]]:
    ranges = []
    for line in lines:
        m = re.match(r'^;\s+\$([0-9A-F]{4})-\$([0-9A-F]{4}) \(', line)
        if m:
            ranges.append((int(m.group(1), 16), int(m.group(2), 16)))
        if line.startswith(CODE_MARKER):
            break
    return ranges


# ============================================================
# Pattern Annotator
# ============================================================

class PatternAnnotator:
    """Adds deterministic, pattern-based comments to listing chunks.

    Lookup tables come from the markdown tables in reference/
    (rom_entry_points.md, apple2_memory_map.md), so extending those files
    extends coverage without code changes. annotate_file() rewrites a chunk
    in place and is idempotent.
    """

    def __init__(self, ref_dir: str):
        self.rom_calls = {}   # addr -> (name, desc)
        self.hw_regs = {}     # $C000-$CFFF
        self.zp_vars = {}     # $00-$FF
        self.sys_vars = {}    # everything else (page 2/3 vectors, ProDOS globals)
        self.mli_calls = {}   # command byte -> (name, desc)
        self.file_names = {}  # per-chunk symbol map (see names_from_file)
        self._load_references(ref_dir)

    def _load_references(self, ref_dir: str):
        rom_path = os.path.join(ref_dir, "rom_entry_points.md")
        mem_path = os.path.join(ref_dir, "apple2_memory_map.md")
        if os.path.exists(rom_path):
            self._parse_rom_entry_points(rom_path)
        if os.path.exists(mem_path):
            self._parse_memory_map(mem_path)

    @staticmethod
    def _parse_table_rows(filepath: str):
        """Yield (first_col, name, description) from markdown table rows."""
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if not line.startswith("|") or line.startswith("|--") or line.startswith("| Address") \
                        or line.startswith("| Range") or line.startswith("| Code") or line.startswith("| Call"):
                    continue
                parts = [p.strip() for p in line.strip("|").split("|")]
                if len(parts) >= 3:
                    yield parts[0], parts[1], parts[2]

    def _parse_rom_entry_points(self, filepath: str):
        for key, name, desc in self._parse_table_rows(filepath):
            m = re.match(r'^\$([0-9A-Fa-f]{4})$', key)
            if m:
                self.rom_calls[int(m.group(1), 16)] = (name, desc)
                continue
            m = re.match(r'^\$([0-9A-Fa-f]{2})$', key)
            if m:   # MLI command table uses 2-digit codes
                self.mli_calls[int(m.group(1), 16)] = (name, desc)

    def _parse_memory_map(self, filepath: str):
        for key, name, desc in self._parse_table_rows(filepath):
            m = re.match(r'^\$([0-9A-Fa-f]{2,4})$', key)   # single addresses only, not ranges
            if not m:
                continue
            addr = int(m.group(1), 16)
            if len(m.group(1)) == 2 or addr < 0x100:
                self.zp_vars[addr] = (name, desc)
            elif 0xC000 <= addr <= 0xCFFF:
                self.hw_regs[addr] = (name, desc)
            else:
                self.sys_vars[addr] = (name, desc)

    # ---------------- operand parsing ----------------

    def operand_address(self, operand: str) -> tuple[int | None, str]:
        """Resolve an operand to (address, index) where index is '', 'X',
        'Y', '(X)', '(Y)', '()'. Immediates return (None, '')."""
        op = operand.strip()
        if not op or op.startswith("#") or op == "A":
            return None, ""
        idx = ""
        if op.startswith("("):
            if op.endswith(",X)"):
                idx, op = "(X)", op[1:-3]
            elif op.endswith("),Y"):
                idx, op = "(Y)", op[1:-3]
            elif op.endswith(")"):
                idx, op = "()", op[1:-1]
        elif op.endswith(",X"):
            idx, op = "X", op[:-2]
        elif op.endswith(",Y"):
            idx, op = "Y", op[:-2]
        if op.startswith(("a:", "z:")):
            op = op[2:]
        m = re.match(r'^\$([0-9A-Fa-f]{2,4})$', op)
        if m:
            return int(m.group(1), 16), idx
        m = re.match(r'^(?:L|SUB|D)_([0-9A-F]{4})(?:\+(\d+))?$', op)
        if m:
            return int(m.group(1), 16) + int(m.group(2) or 0), idx
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)(?:\+(\d+))?$', op)
        if m:
            base = self.file_names.get(m.group(1), NAME_TO_ADDR.get(m.group(1)))
            if base is not None:
                return base + int(m.group(2) or 0), idx
        return None, idx

    @staticmethod
    def names_from_file(lines: list[str]) -> dict[str, int]:
        """Symbol -> address from a chunk's own text: header equates
        (NAME = $XXXX, NAME = OTHER+n) and label lines (NAME: followed by
        the next listing line's address). Covers user symbols and renamed
        labels that the built-in tables don't know."""
        names, pending, rel = {}, [], []
        for line in lines:
            m = re.match(r'^([A-Za-z_]\w*)\s+=\s+\$([0-9A-Fa-f]{2,4})\b', line)
            if m:
                names[m.group(1)] = int(m.group(2), 16)
                continue
            m = re.match(r'^([A-Za-z_]\w*)\s+=\s+([A-Za-z_]\w*)\+(\d+)\b', line)
            if m:
                rel.append((m.group(1), m.group(2), int(m.group(3))))
                continue
            m = LABEL_RE.match(line.strip())
            if m:
                pending.append(line.strip()[:-1])
                continue
            a = parse_address_from_line(line)
            if a is not None and pending:
                for n in pending:
                    names[n] = a
                pending = []
        for n, base, off in rel:
            if base in names:
                names[n] = names[base] + off
        return names

    # ---------------- per-file ----------------

    def annotate_file(self, filepath: str) -> int:
        with open(filepath) as f:
            lines = f.readlines()
        self.file_names = self.names_from_file(lines)

        ranges = memory_ranges_from_header(lines)
        is_rom = any(l.startswith("; ROM image:") for l in lines[:40])
        parsed = [parse_line(l) for l in lines]
        instr_idx = [i for i, p in enumerate(parsed) if p and not p[1].startswith(".") and p[1] != "HASC"]
        code_addrs = {parsed[i][0] for i in instr_idx}
        notes: dict[int, str] = {}

        def in_image(addr):
            return any(s <= addr <= e for s, e in ranges)

        for k, i in enumerate(instr_idx):
            addr, mn, op, cm = parsed[i]
            prev = [parsed[j] for j in instr_idx[max(0, k - 4):k]]
            nxt = [parsed[j] for j in instr_idx[k + 1:k + 9]]
            note = self._analyze(addr, mn, op, cm, prev, nxt, set() if is_rom else code_addrs, in_image)
            if note:
                notes[i] = note

        self._display_mode_runs(parsed, instr_idx, notes)

        added = 0
        for i, note in notes.items():
            line = lines[i].rstrip("\n")
            text = note.lstrip("; ").strip()
            if text in line:
                continue   # idempotent: already annotated
            if parsed[i][3]:
                lines[i] = f"{line} | {text}\n"
            else:
                lines[i] = f"{line.ljust(62)}; {text}\n"
            added += 1

        with open(filepath, "w") as f:
            f.writelines(lines)
        return added

    def _desc_for(self, addr: int) -> tuple[str, str] | None:
        for tbl in (self.hw_regs, self.rom_calls, self.sys_vars):
            if addr in tbl:
                return tbl[addr]
        return None

    def _analyze(self, addr, mn, op, cm, prev, nxt, code_addrs, in_image) -> str | None:
        target, idx = self.operand_address(op)
        has_comment = len(cm.lstrip("; ").strip()) > 5

        # ROM / OS calls (dasm --annotate usually covers these already)
        if mn in ("JSR", "JMP") and target is not None and not idx and not in_image(target):
            if target in self.rom_calls and not has_comment:
                name, desc = self.rom_calls[target]
                return f"; {name} - {desc}"

        # JMP through page-3 / ProDOS vectors
        if mn == "JMP" and idx == "()" and target is not None and target in self.sys_vars:
            name, desc = self.sys_vars[target]
            return f"; jump via {name} - {desc}"

        # Keyboard wait loop: LDA KBD / BPL self
        if target == 0xC000 and mn in ("LDA", "BIT") and nxt and nxt[0][1] == "BPL":
            bt, _ = self.operand_address(nxt[0][2])
            if bt is not None and bt <= addr:
                return "; wait for keypress (bit 7 set = key ready)"
        if target == 0xC010 and not has_comment:
            return "; clear keyboard strobe (acknowledge key)"

        # Language card double read
        if target is not None and 0xC080 <= target <= 0xC08F and not idx:
            if prev and prev[-1][1] in ("LDA", "BIT", "LDX", "LDY") and \
                    self.operand_address(prev[-1][2])[0] == target and target & 1:
                return f"; language card: {self.hw_regs.get(target, ('', 'switch'))[1]} (second read enables write)"
            desc = self.hw_regs.get(target)
            if desc and not has_comment:
                return f"; language card: {desc[1]}"

        # Slot-indexed I/O: LDA $C08C,X with X = slot*16
        if target is not None and 0xC080 <= target <= 0xC08F and idx == "X":
            return f"; slot device register {target & 0xF} (X = slot*16), e.g. Disk II {self._disk2_reg(target & 0xF)}"

        # Speaker click / tone loop
        if target == 0xC030 and idx == "":
            if any(n[1] in ("BNE", "BPL", "BCC", "BCS", "BMI", "BEQ") and
                   (self.operand_address(n[2])[0] or 0x10000) <= addr for n in nxt):
                return "; toggle speaker inside loop: tone / click generation"
            return None if has_comment else "; toggle speaker (click)"

        # Paddle read
        if target == 0xC070:
            return "; trigger paddle timers (then poll PADDLx until bit 7 clears)"
        if target is not None and 0xC064 <= target <= 0xC067 and not has_comment:
            return f"; paddle {target - 0xC064} timer: bit 7 set while counting"
        if target is not None and 0xC061 <= target <= 0xC063 and not has_comment:
            return f"; button {target - 0xC061} (bit 7 = pressed)"

        # Other soft switches / I/O
        if target is not None and 0xC000 <= target <= 0xCFFF and not has_comment:
            d = self.hw_regs.get(target)
            if d:
                return f"; {d[0]} - {d[1]}"
            if 0xC090 <= target <= 0xC0FF:
                slot = (target - 0xC080) >> 4
                return f"; slot {slot} I/O register {target & 0xF}"
            if 0xC100 <= target <= 0xC7FF:
                return f"; slot {(target >> 8) & 7} firmware ROM"

        # Page 2/3 system vectors and ProDOS global page
        if target is not None and target in self.sys_vars and mn in ("STA", "STX", "STY", "LDA", "LDX", "LDY"):
            name, desc = self.sys_vars[target]
            return f"; {name} - {desc}"

        # Zero-page system variables. Symbolic operands (ROM listings, or
        # --zp-names) get the description; raw $xx operands only for locations
        # programs commonly touch on purpose, marked "?" since user code
        # often reuses zero page for its own variables.
        if target is not None and target < 0x100 and idx in ("", "X", "Y", "(Y)", "()") \
                and mn not in ("JSR", "JMP") and target in self.zp_vars and not has_comment:
            name, desc = self.zp_vars[target]
            if not re.search(r'\$[0-9A-Fa-f]{2}\b', op):
                return f"; {desc}"
            if target in COMMON_SYSTEM_ZP:
                return f"; {name}? - {desc}"

        # Screen memory
        if target is not None and not in_image(target) and mn in ("STA", "STX", "STY", "STZ", "LDA"):
            if 0x0400 <= target <= 0x07FF:
                return "; text/lo-res page 1 memory"
            if 0x0800 <= target <= 0x0BFF:
                return "; text/lo-res page 2 memory"
            if 0x2000 <= target <= 0x3FFF:
                return "; hi-res page 1 memory"
            if 0x4000 <= target <= 0x5FFF:
                return "; hi-res page 2 memory"

        # Self-modifying code: store into an instruction in this chunk
        if mn in ("STA", "STX", "STY", "STZ", "INC", "DEC") and target is not None and in_image(target):
            for back in range(0, 3):
                if target - back in code_addrs and target - back != addr:
                    what = "opcode" if back == 0 else ("operand" if back == 1 else "operand high byte")
                    return f"; self-modifying code: patches {what} of instruction at ${target - back:04X}"

        # Stack tricks
        if mn == "PLA" and nxt and nxt[0][1] == "PLA" and not (prev and prev[-1][1] == "PLA"):
            return "; PLA/PLA: pop return address (discard caller / get PC)"
        if mn == "TSX" and nxt and "$0100" in nxt[0][2] or (mn == "TSX" and nxt and "$0101" in nxt[0][2]):
            return "; read stack directly (return address / PC-relative data)"
        if mn == "RTS" and prev and prev[-1][1] == "PHA" and len(prev) >= 2 and prev[-2][1] == "PHA":
            return "; PHA/PHA/RTS: computed jump (pushed address + 1)"

        # Pointer loops
        if idx == "(Y)" and mn in ("STA", "LDA") and nxt:
            window = [n[1] for n in nxt[:4]]
            if "INY" in window and ("BNE" in window or "CPY" in window):
                kind = "copy" if mn == "STA" and prev and prev[-1][1] == "LDA" and "(" in prev[-1][2] else \
                       ("fill" if mn == "STA" else "scan")
                return f"; {kind} loop through pointer at ${target:02X}" if target is not None else None

        # Hi-res page select via immediate
        if mn == "LDA" and op in ("#$20", "#$40") and nxt and nxt[0][1] == "STA":
            t2, _ = self.operand_address(nxt[0][2])
            if t2 == 0xE6:
                return f"; hi-res page {1 if op == '#$20' else 2} (HPAG)"

        if mn == "BRK":
            return "; BRK: break to monitor (vector $03F0 on II+/IIe)"
        return None

    @staticmethod
    def _disk2_reg(n: int) -> str:
        return ["PHASE0OFF", "PHASE0ON", "PHASE1OFF", "PHASE1ON", "PHASE2OFF", "PHASE2ON",
                "PHASE3OFF", "PHASE3ON", "MOTOROFF", "MOTORON", "DRV0EN", "DRV1EN",
                "Q6L (read latch)", "Q6H", "Q7L (read mode)", "Q7H (write mode)"][n]

    def _display_mode_runs(self, parsed, instr_idx, notes):
        """Summarize runs of $C050-$C057 / 80-col switch accesses as a mode."""
        names = {0xC050: "GRAPHICS", 0xC051: "TEXT", 0xC052: "FULL", 0xC053: "MIXED",
                 0xC054: "PAGE1", 0xC055: "PAGE2", 0xC056: "LORES", 0xC057: "HIRES",
                 0xC00C: "40COL", 0xC00D: "80COL", 0xC05E: "DHIRES-ON", 0xC05F: "DHIRES-OFF"}
        run = []
        for k, i in enumerate(instr_idx + [None]):
            t = None
            if i is not None:
                t, idx = self.operand_address(parsed[i][2])
                if idx:
                    t = None
            if t in names:
                run.append((i, names[t]))
                continue
            if i is not None and run and parsed[i][1] in ("LDA", "LDX", "LDY") and parsed[i][2].startswith("#"):
                continue   # allow immediate loads between switch writes
            if len(run) >= 2:
                mode = ", ".join(n for _, n in run)
                last = run[-1][0]
                summary = f"display mode: {mode}"
                if {"GRAPHICS", "HIRES"} <= {n for _, n in run}:
                    summary += " (hi-res graphics)"
                notes[last] = (notes.get(last, "") + "; " if last in notes else "") + summary
            run = []


# ============================================================
# Split
# ============================================================

def do_split(args):
    with open(args.asm) as f:
        asm_lines = f.readlines()
    with open(args.sections) as f:
        sections = json.load(f)
    os.makedirs(args.output_dir, exist_ok=True)

    header_lines, first_code_idx = extract_header(asm_lines)
    header_text = "".join(header_lines)

    manifest = {
        "source_asm": os.path.abspath(args.asm),
        "source_sections": os.path.abspath(args.sections),
        "total_chunks": len(sections),
        "chunks": [],
    }

    for n, section in enumerate(sections):
        chunk_id = section["id"]
        start_hex, end_hex = section["start_addr_hex"], section["end_addr_hex"]
        start_addr = int(start_hex, 16)

        chunk_start = find_line_for_address(asm_lines, first_code_idx, start_addr)
        if chunk_start is None:
            print(f"Warning: start {start_hex} not found in listing, skipping chunk {chunk_id}", file=sys.stderr)
            continue
        if n == 0:
            chunk_start = first_code_idx   # keep the leading .org and separators
        if n + 1 < len(sections):
            nxt = int(sections[n + 1]["start_addr_hex"], 16)
            chunk_end = find_line_for_address(asm_lines, chunk_start + 1, nxt) or len(asm_lines)
        else:
            chunk_end = len(asm_lines)
        chunk_lines = asm_lines[chunk_start:chunk_end]

        ctx = ["; =============================================",
               f"; CHUNK {chunk_id} of {len(sections)} -- {start_hex} to {end_hex} ({len(chunk_lines)} lines)",
               "; ============================================="]
        for key, title, limit in (("subroutines", "Subroutines", 40), ("rom_calls", "ROM calls", 40),
                                  ("hw_accesses", "Soft switches", 40), ("self_modifying", "Self-modified", 20),
                                  ("calls_out", "Calls out", 15), ("called_from", "Called from", 10)):
            vals = section.get(key) or []
            if vals:
                ctx.append(f"; {title}: {', '.join(vals[:limit])}")
                if len(vals) > limit:
                    ctx.append(f";   (+{len(vals) - limit} more)")
        ctx += ["; =============================================", ""]

        chunk_filename = f"chunk_{chunk_id:02d}_{start_addr:04X}.asm"
        chunk_path = os.path.join(args.output_dir, chunk_filename)
        with open(chunk_path, "w") as f:
            f.write(header_text)
            f.write("\n")
            f.write("\n".join(ctx) + "\n")
            f.write(CODE_MARKER + "\n")
            if not any(ORG_RE.match(l) for l in chunk_lines[:6]):
                f.write(f"                 .org   ${start_addr:04X}\n\n")
            f.write("".join(chunk_lines))

        manifest["chunks"].append({
            "id": chunk_id,
            "filename": chunk_filename,
            "path": os.path.abspath(chunk_path),
            "start_addr": start_hex,
            "end_addr": end_hex,
            "line_count": len(chunk_lines),
            "subroutines": section.get("subroutines", []),
            "rom_calls": section.get("rom_calls", []),
            "hw_accesses": section.get("hw_accesses", []),
            "self_modifying": section.get("self_modifying", []),
        })

    manifest_path = os.path.join(args.output_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Split into {len(manifest['chunks'])} chunks in {args.output_dir}", file=sys.stderr)
    print(f"Manifest: {manifest_path}", file=sys.stderr)
    for c in manifest["chunks"]:
        print(f"  chunk_{c['id']:02d}: {c['start_addr']}-{c['end_addr']} ({c['line_count']} lines)", file=sys.stderr)


# ============================================================
# Annotate
# ============================================================

def _chunk_path(chunk_info, manifest_path):
    p = chunk_info["path"]
    if not os.path.exists(p):
        p = os.path.join(os.path.dirname(os.path.abspath(manifest_path)), chunk_info["filename"])
    return p


def do_annotate(args):
    with open(args.manifest) as f:
        manifest = json.load(f)
    annotator = PatternAnnotator(args.ref_dir)
    total = 0
    for c in manifest["chunks"]:
        added = annotator.annotate_file(_chunk_path(c, args.manifest))
        total += added
        print(f"  chunk_{c['id']:02d}: +{added} comments", file=sys.stderr)
    print(f"Annotation complete: {total} comments added across {len(manifest['chunks'])} chunks", file=sys.stderr)


# ============================================================
# Merge
# ============================================================

def strip_hex_columns(line: str) -> str:
    """'  2000  A9 00       LDA #$00  ; c' -> '                 LDA #$00  ; c'"""
    m = LINE_RE.match(line.rstrip("\n"))
    if not m:
        return line
    return f"{'':17s}{m.group(3)}\n"


def do_merge(args):
    with open(args.manifest) as f:
        manifest = json.load(f)

    with open(_chunk_path(manifest["chunks"][0], args.manifest)) as f:
        first = f.readlines()
    header = []
    for i, line in enumerate(first):
        if line.strip().startswith("; CHUNK "):
            header = first[:i]
            break

    out = list(header)
    for c in manifest["chunks"]:
        with open(_chunk_path(c, args.manifest)) as f:
            lines = f.readlines()
        body_start = 0
        for i, line in enumerate(lines):
            if line.strip() == CODE_MARKER:
                body_start = i + 1
                break
        else:
            for i, line in enumerate(lines):
                if ORG_RE.match(line):
                    body_start = i
                    break
        out.append(f"\n; ---- Chunk {c['id']}: {c['start_addr']}-{c['end_addr']} ----\n")
        out.extend(lines[body_start:])

    if getattr(args, "reassemble", False):
        out = [strip_hex_columns(l) for l in out]

    text = "".join(out)
    if args.output:
        with open(args.output, "w") as f:
            f.write(text)
        print(f"Merged {len(manifest['chunks'])} chunks to {args.output}", file=sys.stderr)
    else:
        print(text)


# ============================================================
# Apply symbols (rename generated labels in chunk files)
# ============================================================

def do_apply_symbols(args):
    """Rename generated labels (L_XXXX / SUB_XXXX / D_XXXX) to the names in
    a symbol file, across every chunk, keeping all comments. Only labels
    that exist in the chunks are renamed; names that would collide with an
    existing symbol are skipped. Re-running the pipeline with --symbols
    gives the same names, so keep the file."""
    try:
        from tools.symbols import load_symbols
    except ImportError:
        from symbols import load_symbols
    table = load_symbols(args.apply_symbols)
    with open(args.manifest) as f:
        manifest = json.load(f)
    paths = [_chunk_path(c, args.manifest) for c in manifest["chunks"]]
    texts = {p: open(p).read() for p in paths}
    corpus = "\n".join(texts.values())
    existing = set(re.findall(r'^([A-Za-z_]\w*):$', corpus, re.M)) | \
        set(re.findall(r'^([A-Za-z_]\w*)\s+=', corpus, re.M))

    renames = {}
    for addr, name, _c in table.items():
        if "+" in name:
            continue
        for prefix in ("SUB", "L", "D"):
            old = f"{prefix}_{addr:04X}"
            if re.search(rf'\b{old}\b', corpus):
                if name in existing and name != old:
                    print(f"  skip {old} -> {name}: name already defined", file=sys.stderr)
                    break
                renames[old] = name
                existing.add(name)
                break
    if not renames:
        print("No generated labels matched the symbol file", file=sys.stderr)
        return
    pattern = re.compile(r'\b(' + "|".join(map(re.escape, renames)) + r')\b')
    for p, text in texts.items():
        new = pattern.sub(lambda m: renames[m.group(1)], text)
        if new != text:
            with open(p, "w") as f:
                f.write(new)
    for old, new in sorted(renames.items()):
        print(f"  {old} -> {new}", file=sys.stderr)
    print(f"Renamed {len(renames)} labels across {len(paths)} chunks", file=sys.stderr)


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="6502 disassembly splitter / annotator / merger")
    parser.add_argument("--split", action="store_true", help="Split mode")
    parser.add_argument("--annotate", action="store_true", help="Annotate mode")
    parser.add_argument("--merge", action="store_true", help="Merge mode")
    parser.add_argument("--asm", help="Input listing from dasm6502.py (for --split)")
    parser.add_argument("--sections", help="Sections JSON from xref.py --sections (for --split)")
    parser.add_argument("--output-dir", help="Output directory (for --split)")
    parser.add_argument("--manifest", help="Manifest JSON (for --annotate/--merge)")
    parser.add_argument("--ref-dir", help="Reference directory (for --annotate)")
    parser.add_argument("--output", "-o", help="Output file (for --merge)")
    parser.add_argument("--reassemble", action="store_true",
                        help="With --merge: strip address/hex columns so ca65 can assemble the result")
    parser.add_argument("--apply-symbols", nargs="+", metavar="FILE",
                        help="With --manifest: rename generated labels to the names in these "
                             "symbol files (orchard JSON, flat JSON or ca65 equates)")
    args = parser.parse_args()

    if args.apply_symbols:
        if not args.manifest:
            parser.error("--apply-symbols requires --manifest")
        do_apply_symbols(args)
    elif args.split:
        if not (args.asm and args.sections and args.output_dir):
            parser.error("--split requires --asm, --sections and --output-dir")
        do_split(args)
    elif args.annotate:
        if not (args.manifest and args.ref_dir):
            parser.error("--annotate requires --manifest and --ref-dir")
        do_annotate(args)
    elif args.merge:
        if not args.manifest:
            parser.error("--merge requires --manifest")
        do_merge(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

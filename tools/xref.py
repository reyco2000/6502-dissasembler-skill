#!/usr/bin/env python3
"""
xref.py — Cross-reference and call graph builder for 6502/65C02 binaries
Usage: python3 xref.py <file> [--org 0x2000] [--cpu 65c02] [--output xref.txt]
       python3 xref.py <file> --sections --max-chunks 6 --output sections.json
       python3 xref.py <file> --callgraph [--mermaid]

Runs the same recursive-descent analysis as dasm6502.py (same flags ->
same code/data split), then offers three outputs:
  format_report()    human-readable xref (calls, jumps, ROM calls, soft
                     switches, data refs, strings)
  format_sections()  JSON chunk map consumed by annotator.py --split
  format_callgraph() call tree from the entry point (text or Mermaid)
Pass the same --org/--raw/--cpu/--entry flags you gave dasm6502.py, or the
section boundaries will not line up with the listing.
"""

import sys
import json
import argparse
from collections import defaultdict

try:
    from tools.dasm6502 import build_disassembler, add_common_args, BRANCHES, ABS_MODES
except ImportError:
    from dasm6502 import build_disassembler, add_common_args, BRANCHES, ABS_MODES


def is_hw(addr: int) -> bool:
    """Soft switches, slot I/O and the $CFFF expansion-ROM release."""
    return 0xC000 <= addr <= 0xC0FF or addr == 0xCFFF


class CrossReferenceBuilder:
    """Builds call/jump/data-reference maps from a Disassembler6502 analysis.

    "from" maps are keyed by the referencing instruction, "to" maps by the
    target. Only traced + filled instructions contribute; bytes classified
    as data never do.
    """

    def __init__(self, dasm):
        self.dasm = dasm
        self.mem = dasm.mem
        self.exec_addr = dasm.entry_addr
        self.calls_from: dict[int, list[int]] = defaultdict(list)
        self.calls_to: dict[int, list[int]] = defaultdict(list)
        self.jumps_from: dict[int, list[int]] = defaultdict(list)
        self.jumps_to: dict[int, list[int]] = defaultdict(list)
        self.data_refs: dict[int, list[int]] = defaultdict(list)
        self.rom_calls: dict[int, list[int]] = defaultdict(list)
        self.hw_accesses: dict[int, list[int]] = defaultdict(list)
        self.stores_to_code: dict[int, list[int]] = defaultdict(list)
        self.subroutines: set[int] = set()
        self.strings: list[tuple[int, str, bool]] = []

    def analyze(self):
        # Full disassembly so dasm.lines exists for section line counts
        self.dasm.disassemble(show_hex=True, annotate=False)
        self._pass_find_refs()
        self._find_strings()

    def _pass_find_refs(self):
        d = self.dasm
        code_bytes = set(d.owner)
        for pc, ins in sorted(d.instrs.items()):
            m, v = ins.mnemonic, ins.value
            if m == "JSR":
                self.calls_from[pc].append(v)
                self.calls_to[v].append(pc)
                if self.mem.is_populated(v) or self.is_external_named(v):
                    self.subroutines.add(v)
                if self.is_external_named(v):
                    self.rom_calls[v].append(pc)
            elif m == "JMP" or m in BRANCHES:
                if m == "JMP" and ins.mode != "abs":
                    self.data_refs[v].append(pc)   # indirect vector
                    continue
                self.jumps_from[pc].append(v)
                self.jumps_to[v].append(pc)
                if m == "JMP" and self.is_external_named(v):
                    self.rom_calls[v].append(pc)
            elif ins.mode in ABS_MODES:
                self.data_refs[v].append(pc)
                if is_hw(v):
                    self.hw_accesses[v].append(pc)
                if m in ("STA", "STX", "STY", "STZ") and v in code_bytes and not d.rom_name:
                    self.stores_to_code[v].append(pc)
        # MLI parameter-block pointers and other inline references
        for addr, refs in d.data_refs.items():
            for r in refs:
                if r not in self.data_refs[addr]:
                    self.data_refs[addr].append(r)
        # Entry points and vector targets count as subroutines too
        for t in d.call_targets:
            if self.mem.is_populated(t):
                self.subroutines.add(t)

    def _find_strings(self):
        d = self.dasm
        for pc, _hx, mn, op, _cm in d.lines:
            if mn in (".byte", "HASC") and op.startswith('"'):
                self.strings.append((pc, op, mn == "HASC"))

    # ---------------- naming ----------------

    def is_external_named(self, addr: int) -> bool:
        """Outside the image and named (built-in ROM/OS table or user symbol)."""
        return not self.mem.is_populated(addr) and self.dasm.known_name(addr) is not None

    def name(self, addr: int) -> str:
        return self.dasm.addr_label(addr)

    def sub_name(self, addr: int) -> str:
        if addr in self.dasm.labels:
            return self.dasm.labels[addr]
        return self.dasm.known_name(addr) or f"SUB_{addr:04X}"

    # ---------------- report ----------------

    def format_report(self) -> str:
        out = []
        ranges = self.mem.get_contiguous_ranges()
        out.append("=" * 60)
        out.append(f"CROSS-REFERENCE REPORT ({self.dasm.cpu.upper()})")
        out.append("=" * 60)
        for s, e in ranges:
            out.append(f"Range: ${s:04X}-${e:04X} ({e - s + 1} bytes)")
        if self.exec_addr is not None:
            out.append(f"Entry: ${self.exec_addr:04X}")
        d = self.dasm
        out.append(f"Instructions: {len(d.instrs)} (traced {len(d.traced)}, swept {len(d.swept)}, "
                   f"filled {len(d.instrs) - len(d.traced) - len(d.swept)}; fill mode {d.fill})")
        for note in d.auto_found:
            out.append(f"Auto-detected {note}")
        if d.sym.sources:
            out.append(f"Symbols: {', '.join(d.sym.sources)} ({len(d.sym)} entries)")
        out.append("")

        local = sorted(s for s in self.subroutines if self.mem.is_populated(s))
        out.append(f"--- Subroutines ({len(local)}) ---")
        for s in local:
            callers = self.calls_to.get(s, [])
            out.append(f"  {self.sub_name(s):16s} ${s:04X}  called from {len(callers)}: "
                       + ", ".join(f"${c:04X}" for c in sorted(callers)[:10])
                       + (" ..." if len(callers) > 10 else ""))
        out.append("")

        if self.rom_calls:
            out.append(f"--- ROM / OS calls ({len(self.rom_calls)}) ---")
            for a in sorted(self.rom_calls):
                refs = self.rom_calls[a]
                desc = self.dasm.describe(a)
                out.append(f"  {self.name(a):12s} ${a:04X}  x{len(refs):<3d} {desc}")
                out.append("      from: " + ", ".join(f"${r:04X}" for r in sorted(refs)[:12]))
            out.append("")

        if self.hw_accesses:
            out.append(f"--- Soft switches / I/O ({len(self.hw_accesses)}) ---")
            for a in sorted(self.hw_accesses):
                refs = self.hw_accesses[a]
                out.append(f"  {self.name(a):16s} ${a:04X}  x{len(refs):<3d} from: "
                           + ", ".join(f"${r:04X}" for r in sorted(refs)[:10]))
            out.append("")

        if self.stores_to_code:
            out.append("--- Self-modifying code (stores into code) ---")
            for a in sorted(self.stores_to_code):
                out.append(f"  ${a:04X} written from " + ", ".join(f"${r:04X}" for r in self.stores_to_code[a]))
            out.append("")

        internal = {a: r for a, r in self.data_refs.items()
                    if self.mem.is_populated(a) and a not in self.dasm.code_addrs}
        if internal:
            out.append(f"--- Data references into image ({len(internal)}) ---")
            for a in sorted(internal):
                out.append(f"  {self.name(a):16s} ${a:04X}  from: "
                           + ", ".join(f"${r:04X}" for r in sorted(internal[a])[:10]))
            out.append("")

        if self.strings:
            out.append(f"--- Strings ({len(self.strings)}) ---")
            for a, text, hi in self.strings:
                out.append(f"  ${a:04X} {'[hi] ' if hi else ''}{text[:60]}")
            out.append("")
        return "\n".join(out)

    # ---------------- call graph ----------------

    def callees(self, sub: int) -> list[int]:
        """Distinct JSR targets from the body of subroutine `sub` (code up
        to the next subroutine entry)."""
        local = sorted(s for s in self.subroutines if self.mem.is_populated(s))
        nxt = next((s for s in local if s > sub), 0x10000)
        seen = []
        for caller, targets in sorted(self.calls_from.items()):
            if sub <= caller < nxt:
                for t in targets:
                    if t not in seen:
                        seen.append(t)
        return seen

    def format_callgraph(self, mermaid: bool = False, max_depth: int = 12) -> str:
        roots = []
        if self.exec_addr is not None:
            roots.append(self.exec_addr)
        for t in sorted(self.dasm.call_targets):
            if self.mem.is_populated(t) and not self.calls_to.get(t) and t not in roots:
                roots.append(t)   # vectors, --entry points, uncalled routines

        if mermaid:
            out = ["```mermaid", "graph TD"]
            edges = set()
            for s in sorted(self.subroutines):
                if not self.mem.is_populated(s):
                    continue
                for t in self.callees(s):
                    edges.add((self.sub_name(s), self.sub_name(t), self.is_external_named(t)))
            for a, b, rom in sorted(edges):
                out.append(f"    {a} --> {b}" + ("[[" + b + "]]" if rom else ""))
            out.append("```")
            return "\n".join(out)

        out = []

        def walk(sub, prefix, depth, stack):
            for i, t in enumerate(self.callees(sub)):
                last = i == len(self.callees(sub)) - 1
                branch = "└── " if last else "├── "
                tag = ""
                if self.is_external_named(t):
                    tag = f" [ROM] {self.dasm.describe(t)}"
                elif not self.mem.is_populated(t):
                    tag = " [external]"
                elif t in stack:
                    tag = " [recursive]"
                out.append(f"{prefix}{branch}{self.sub_name(t)} (${t:04X}){tag}")
                if self.mem.is_populated(t) and t not in stack and depth < max_depth:
                    walk(t, prefix + ("    " if last else "│   "), depth + 1, stack | {t})

        for r in roots:
            out.append(f"{self.sub_name(r)} (${r:04X})")
            walk(r, "", 1, {r})
            out.append("")
        leaves = [s for s in self.subroutines if self.mem.is_populated(s) and not self.callees(s)]
        out.append(f"Subroutines: {sum(1 for s in self.subroutines if self.mem.is_populated(s))}, "
                   f"leaf: {len(leaves)}, ROM calls: {len(self.rom_calls)}")
        return "\n".join(out)

    # ---------------- sections ----------------

    def format_sections(self, chunk_target: int = 500, max_chunks: int = None) -> str:
        """JSON section map for chunked annotation.

        Sections start at subroutine entries and range starts, so chunks
        never split a subroutine; adjacent sections are merged greedily up to
        ~1.3x chunk_target listing lines. Each chunk carries its
        subroutines, ROM calls, soft-switch accesses and cross-chunk calls.
        """
        ranges = self.mem.get_contiguous_ranges()
        line_starts = sorted(pc for pc, *_r in self.dasm.lines)
        line_set = set(line_starts)

        boundaries = {s for s, _ in ranges}
        for a in self.subroutines:
            if a in line_set:
                boundaries.add(a)
        boundaries = sorted(boundaries)

        def range_end(addr):
            for s, e in ranges:
                if s <= addr <= e:
                    return e
            return addr

        section_lines = []
        for i, b in enumerate(boundaries):
            end = range_end(b)
            if i + 1 < len(boundaries) and boundaries[i + 1] <= end:
                end = boundaries[i + 1] - 1
            count = sum(1 for pc in line_starts if b <= pc <= end)
            if count:
                section_lines.append((b, end, count))

        if max_chunks is not None and section_lines:
            total = sum(c for _, _, c in section_lines)
            chunk_target = max(200, total // max_chunks)

        chunks = []
        cur = None
        for start, end, count in section_lines:
            if cur is None or cur["line_count"] + count > chunk_target * 1.3:
                if cur:
                    chunks.append(cur)
                cur = {"start_addr": start, "end_addr": end, "line_count": count, "subroutines": []}
            else:
                cur["end_addr"] = end
                cur["line_count"] += count
            if start in self.subroutines:
                cur["subroutines"].append(self.sub_name(start))
        if cur:
            chunks.append(cur)

        for i, c in enumerate(chunks):
            lo, hi = c["start_addr"], c["end_addr"]
            c["id"] = i
            c["start_addr_hex"] = f"0x{lo:04X}"
            c["end_addr_hex"] = f"0x{hi:04X}"
            c["rom_calls"] = sorted({self.name(a) for a, refs in self.rom_calls.items()
                                     if any(lo <= r <= hi for r in refs)})
            c["hw_accesses"] = sorted({self.name(a) for a, refs in self.hw_accesses.items()
                                       if any(lo <= r <= hi for r in refs)})
            c["calls_out"] = sorted({self.sub_name(t) for cl, ts in self.calls_from.items()
                                     if lo <= cl <= hi for t in ts if not lo <= t <= hi})
            c["called_from"] = sorted({f"${cl:04X}" for t, cls in self.calls_to.items()
                                       if lo <= t <= hi for cl in cls if not lo <= cl <= hi})
            c["self_modifying"] = sorted({f"${a:04X}" for a, refs in self.stores_to_code.items()
                                          if any(lo <= r <= hi for r in refs)})
            del c["start_addr"], c["end_addr"]
        return json.dumps(chunks, indent=2)


def main():
    parser = argparse.ArgumentParser(description="6502/65C02 cross-reference builder")
    add_common_args(parser)
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument("--sections", action="store_true",
                        help="Output JSON section map for chunked annotation")
    parser.add_argument("--chunk-size", type=int, default=500,
                        help="Target listing lines per chunk for --sections (default: 500)")
    parser.add_argument("--max-chunks", type=int, default=None,
                        help="Maximum number of chunks (overrides --chunk-size)")
    parser.add_argument("--callgraph", action="store_true", help="Output call tree from the entry point")
    parser.add_argument("--mermaid", action="store_true", help="With --callgraph: Mermaid diagram")
    args = parser.parse_args()

    dasm, info = build_disassembler(args)
    xref = CrossReferenceBuilder(dasm)
    xref.analyze()

    if args.sections:
        result = xref.format_sections(chunk_target=args.chunk_size, max_chunks=args.max_chunks)
    elif args.callgraph:
        result = xref.format_callgraph(mermaid=args.mermaid)
    else:
        result = xref.format_report()

    if args.output:
        with open(args.output, "w") as f:
            f.write(result + "\n")
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()

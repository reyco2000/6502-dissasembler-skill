---
name: a2-trace-calls
description: "Use when the user asks for a call graph, call tree, execution flow, or control-flow map of an Apple II 6502/65C02 program or ROM."
---

# Trace Apple II Call Graph

Run from `/home/pi/proyectos/6502-dissasembler/`. Use the same flags as for
disassembly (`--org`, `--cpu`, `--entry`, `--table`, `--symbols`,
`--data-region`, `--raw`; reuse `output/<name>_flags.txt` if it exists). See
the `a2-disassemble` skill, step 1. With `--symbols`, routines show up in the
tree under their real names.

## Steps

1. **Call tree**: `python3 tools/xref.py <file> <flags> --callgraph`
   - Roots are the entry point (load/exec address, or RESET for ROMs) plus
     other vector targets, `--entry` addresses and routines nothing calls.
   - ROM calls are tagged `[ROM]` with a description, targets outside the
     image `[external]`, recursion `[recursive]`.
2. **Mermaid**: `python3 tools/xref.py <file> <flags> --callgraph --mermaid`
   (ROM routines are drawn as `[[subroutine]]` nodes).
3. **Details** as needed: `python3 tools/xref.py <file> <flags>` for callers
   per subroutine, soft switch accesses and self-modifying stores. Read
   specific ranges of `output/<name>.asm` (from the `a2-disassemble` skill)
   for loops and branch structure. Backward branches are marked
   `; loop back` in `--annotate` listings.
4. **Classify subroutines**:
   - **Leaf**: no outgoing JSRs
   - **ROM bridges**: thin wrappers around a Monitor/Applesoft/MLI call
   - **Interrupt handlers**: IRQ/NMI vector targets, or code installed at
     $03FE / $03FB, ending in RTI
   - **Dispatchers**: `JMP (ind)`, `JMP (abs,X)` (65C02), or PHA/PHA/RTS
     computed jumps. The static graph can't follow these, so name them and
     re-run with `--entry` for the targets once they're known.
5. **Explain the flow**: initialization (display mode, text window, hooks),
   main loop (keyboard poll at $C000, game/update routines), exit
   (`JMP $3D0` DOS warm start, MLI QUIT, or `JMP $FF69` Monitor).

## Caveats

- 6502 code often does `JSR` to routines that pop the return address to read
  inline data (strings or parameters after the JSR). The tracer
  already handles `JSR $BF00` (ProDOS MLI). For others, the bytes after the
  JSR may show up as bogus code. Add the routine to `INLINE_ARG_CALLS` in
  `tools/dasm6502.py` or give the real continuation with `--entry`.
- Self-modifying code (reported by xref) can change JSR/JMP targets at run
  time, so treat those edges as best-effort.

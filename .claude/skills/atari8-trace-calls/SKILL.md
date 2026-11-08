---
name: atari8-trace-calls
description: "Use when the user asks for a call graph, call tree, execution flow, or control-flow map of Atari 8-bit 6502 code."
---

# Trace Atari 8-bit (400 / 800 / 600XL / 800XL / 1200XL) Call Graph

Run from the repository root with the same flags as for disassembly
(`--machine`, `--org`, `--cpu`, `--entry`, `--table`, `--bank`, `--symbols`,
`--data-region`; reuse `output/<name>_flags.txt`). See `atari8-disassemble`
step 1.

## Steps

1. **Call tree**: `python3 tools/xref.py <file> <flags> --callgraph`
   - Roots: the entry point, vector targets, cartridge/loader entries,
     `--entry` addresses, installed vector hooks and uncalled routines. OS
     calls are tagged `[ROM]`, targets outside the image `[external]`.
2. **Mermaid**: add `--mermaid`.
3. **Details**: `python3 tools/xref.py <file> <flags>` for callers, hardware
   accesses and self-modifying stores; read ranges of `output/<name>.asm`
   for loops (`; loop back`) and branch structure.
4. **Classify**: leaf routines, OS bridges (thin wrappers around an OS call),
   interrupt handlers (vector targets and hooked handlers, ending in RTI or a
   jump to the previous handler), dispatchers (`JMP (ind)`, PHA/PHA/RTS).
5. **Explain the flow**: initialisation (SDMCTL/SDLSTL display list setup, colour shadows, VBI hook via SETVBV, NMIEN), main loop (wait on RTCLOK $14 or a VBI flag), exit (`JMP (DOSVEC)` $000A, RTS to DOS).

## Caveats

- Handlers installed with computed addresses (not an immediate pair) and code
  copied to RAM before running are invisible to static tracing: add `--entry`.
- Self-modifying code can change JSR/JMP targets at run time; treat those
  edges as best-effort.

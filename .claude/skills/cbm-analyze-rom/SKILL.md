---
name: cbm-analyze-rom
description: "Use when the user asks to analyze, identify, or map the structure of a Commodore 64 / 128 / VIC-20 ROM or cartridge image: vectors, OS entry points, subroutine map, ROM type."
---

# Analyze Commodore 8-bit (C64, C128, VIC-20) ROM

Run from the repository root. Machines: `c64` (Commodore 64), `c128` (Commodore 128 (8502 side)), `vic20` (VIC-20).

## Steps

1. **Identify**: `python3 tools/loader.py <file> --json` (add `--machine <id>`
   and `--org` when the loader can't tell). It reports format, org, machine,
   ROM name, vectors and entries. See step 1 of `cbm-disassemble`.
2. **Read reference data** for the machine:
- `reference/c64/memory_map.md`, `reference/c64/rom_entry_points.md`: C64: zero page, $0200-$03FF vectors, VIC-II/SID/CIA, banking
- `reference/c128/memory_map.md`, `reference/c128/rom_entry_points.md`: C128: MMU, VDC, BASIC 7.0 and KERNAL jumbo table
- `reference/vic20/memory_map.md`, `reference/vic20/rom_entry_points.md`: VIC-20: block map, VIC 6560/6561, VIAs, KERNAL
3. **Map the ROM**:
   - `python3 tools/xref.py <file> <flags>`: subroutines with callers, hardware
     registers used, self-modifying stores, data references, strings.
   - `python3 tools/xref.py <file> <flags> --callgraph`: call tree from RESET /
     the cartridge entries.
   - For the annotated listing, follow `cbm-disassemble`. Inside ROM images
     the machine's ROM and zero-page names are applied automatically.
4. **Classify regions**: code (traced vs swept/filled counts in the header),
   jump and dispatch tables (`--table`), text, vectors, fill.
5. **Report**: for each major routine give address range, entry/exit
   registers and memory, purpose, callers/callees; list the public entry
   points and which RAM vectors they go through.

## Analysis Tips

- KERNAL calls go through the jump table at $FF81-$FFF3. Many entries are
  `JMP (vector)` through $031A-$0333, so a program that patches those vectors
  (a wedge) changes what CHROUT/LOAD do. Duplicate names get the real address
  appended (`PLOT` = jump-table entry $FFF0, `PLOT_E50A` = the code).
- The C64 BASIC ROM ($A000-$BFFF) continues into the KERNAL ($E000-$E4D2):
  disassemble both halves for the whole interpreter. The statement dispatch
  table is address-1 (RTS dispatch): use `--table A00C:35:rts`.
- C128: the MMU ($D500, $FF00 shadow) picks the bank. The jumbo jump table at
  $FF47-$FF80 adds the C128 calls (JSRFAR, PRIMM, SETBNK …).
- VIC-20: VIC chip at $9000, VIAs at $9110/$9120, colour RAM $9400. The screen
  moves with RAM expansion ($1E00 unexpanded, $1000 with 8K+).

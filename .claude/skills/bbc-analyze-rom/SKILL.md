---
name: bbc-analyze-rom
description: "Use when the user asks to analyze, identify, or map the structure of a BBC Micro ROM or cartridge image: vectors, OS entry points, subroutine map, ROM type."
---

# Analyze Acorn BBC Micro (Model A, B, B+, Master 128) ROM

Run from the repository root. Machines: `bbc_a` (Model A), `bbc_b` (Model B (default)), `bbc_bplus` (Model B+), `bbc_master` (Master 128 (65C12: use the default CPU 65c12)).

## Steps

1. **Identify**: `python3 tools/loader.py <file> --json` (add `--machine <id>`
   and `--org` when the loader can't tell). It reports format, org, machine,
   ROM name, vectors and entries. See step 1 of `bbc-disassemble`.
2. **Read reference data** for the machine:
- `reference/bbc_b/memory_map.md`, `reference/bbc_b/rom_entry_points.md`: Model B, MOS 1.20 (the A/B+/Master folders have the same layout with their own notes)
- `reference/bbc_master/memory_map.md`, `reference/bbc_master/rom_entry_points.md`: Master 128: MOS 3.20, ACCCON, extra workspace
3. **Map the ROM**:
   - `python3 tools/xref.py <file> <flags>`: subroutines with callers, hardware
     registers used, self-modifying stores, data references, strings.
   - `python3 tools/xref.py <file> <flags> --callgraph`: call tree from RESET /
     the cartridge entries.
   - For the annotated listing, follow `bbc-disassemble`. Inside ROM images
     the machine's ROM and zero-page names are applied automatically.
4. **Classify regions**: code (traced vs swept/filled counts in the header),
   jump and dispatch tables (`--table`), text, vectors, fill.
5. **Report**: for each major routine give address range, entry/exit
   registers and memory, purpose, callers/callees; list the public entry
   points and which RAM vectors they go through.

## Analysis Tips

- The MOS API lives in the last page: $FFB9-$FFF7 (OSRDRM, OSFIND, OSBYTE …).
  Most entries are `JMP (vector)` through $0200-$0235, so filing systems and
  utilities patch those vectors. The extended vector table at $0D9F lets
  sideways ROMs own a vector.
- Sideways ROM header: $8000 language JMP, $8003 service JMP, $8006 type,
  $8007 copyright offset, $8008 version, $8009 title. Service entry gets A =
  reason code, X = ROM number, Y = parameter.
- Master MOS 3.20 is 65C12 code and pages in extra ROM/RAM through ACCCON
  ($FE34). MOS 1.20 RESET is $D9CD; 2.00 and 3.20 differ (the file says so).

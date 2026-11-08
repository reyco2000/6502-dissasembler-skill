---
name: nes-analyze-rom
description: "Use when the user asks to analyze, identify, or map the structure of an NES / Famicom ROM or cartridge image: vectors, OS entry points, subroutine map, ROM type."
---

# Analyze NES / Famicom ROM

Run from the repository root. Machines: `nes` (NES (default)), `famicom` (Famicom (same core; $4016/$4017 expansion and microphone differences)).

## Steps

1. **Identify**: `python3 tools/loader.py <file> --json` (add `--machine <id>`
   and `--org` when the loader can't tell). It reports format, org, machine,
   ROM name, vectors and entries. See step 1 of `nes-disassemble`.
2. **Read reference data** for the machine:
- `reference/nes/memory_map.md`, `reference/nes/rom_entry_points.md`: CPU/PPU/APU maps, iNES header, mapper registers
- `reference/famicom/memory_map.md`, `reference/famicom/rom_entry_points.md`: Famicom differences: expansion port, microphone, FDS
3. **Map the ROM**:
   - `python3 tools/xref.py <file> <flags>`: subroutines with callers, hardware
     registers used, self-modifying stores, data references, strings.
   - `python3 tools/xref.py <file> <flags> --callgraph`: call tree from RESET /
     the cartridge entries.
   - For the annotated listing, follow `nes-disassemble`. Inside ROM images
     the machine's ROM and zero-page names are applied automatically.
4. **Classify regions**: code (traced vs swept/filled counts in the header),
   jump and dispatch tables (`--table`), text, vectors, fill.
5. **Report**: for each major routine give address range, entry/exit
   registers and memory, purpose, callers/callees; list the public entry
   points and which RAM vectors they go through.

## Analysis Tips

- No firmware: RESET, NMI and IRQ in the fixed bank are the only fixed entries.
  Everything else hangs off them; bank-switched code is reached through
  trampolines in the fixed bank (write bank number, JSR into $8000-$BFFF).
- Stores into $8000-$FFFF are mapper register writes, not self-modifying code
  (the listing header says so for ROM images).
- $2005/$2006 are double-write registers (the w toggle, reset by reading
  $2002); $2007 reads are buffered except for palette RAM.

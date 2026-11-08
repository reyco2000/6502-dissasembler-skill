---
name: lynx-analyze-rom
description: "Use when the user asks to analyze, identify, or map the structure of an Atari Lynx ROM or cartridge image: vectors, OS entry points, subroutine map, ROM type."
---

# Analyze Atari Lynx ROM

Run from the repository root. Machines: `lynx` (Atari Lynx (CPU 65SC02 by default)).

## Steps

1. **Identify**: `python3 tools/loader.py <file> --json` (add `--machine <id>`
   and `--org` when the loader can't tell). It reports format, org, machine,
   ROM name, vectors and entries. See step 1 of `lynx-disassemble`.
2. **Read reference data** for the machine:
- `reference/lynx/memory_map.md`, `reference/lynx/rom_entry_points.md`: Suzy/Mikey registers, MAPCTL, boot ROM entry points, cart header
3. **Map the ROM**:
   - `python3 tools/xref.py <file> <flags>`: subroutines with callers, hardware
     registers used, self-modifying stores, data references, strings.
   - `python3 tools/xref.py <file> <flags> --callgraph`: call tree from RESET /
     the cartridge entries.
   - For the annotated listing, follow `lynx-disassemble`. Inside ROM images
     the machine's ROM and zero-page names are applied automatically.
4. **Classify regions**: code (traced vs swept/filled counts in the header),
   jump and dispatch tables (`--table`), text, vectors, fill.
5. **Report**: for each major routine give address range, entry/exit
   registers and memory, purpose, callers/callees; list the public entry
   points and which RAM vectors they go through.

## Analysis Tips

- The boot ROM ($FE00-$FFF7) decrypts the first cart block into $0200 and jumps
  to it. MAPCTL ($FFF9) bit 3 maps RAM over the vectors, bit 2 over the ROM.
- Hardware sits at $FC00-$FDFF; the vector area $FFFA-$FFFF is ROM or RAM
  depending on MAPCTL.

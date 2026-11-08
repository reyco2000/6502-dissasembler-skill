---
name: atari8-analyze-rom
description: "Use when the user asks to analyze, identify, or map the structure of an Atari 8-bit ROM or cartridge image: vectors, OS entry points, subroutine map, ROM type."
---

# Analyze Atari 8-bit (400 / 800 / 600XL / 800XL / 1200XL) ROM

Run from the repository root. Machines: `atari400` (Atari 400), `atari800` (Atari 800), `atari600xl` (Atari 600XL), `atari800xl` (Atari 800XL (default for .xex)), `atari1200xl` (Atari 1200XL).

## Steps

1. **Identify**: `python3 tools/loader.py <file> --json` (add `--machine <id>`
   and `--org` when the loader can't tell). It reports format, org, machine,
   ROM name, vectors and entries. See step 1 of `atari8-disassemble`.
2. **Read reference data** for the machine:
- `reference/atari800xl/memory_map.md`, `reference/atari800xl/rom_entry_points.md`: 800XL (XL/XE OS); the other models' folders have the same layout
- `reference/atari800/memory_map.md`, `reference/atari800/rom_entry_points.md`: 400/800 OS-A/OS-B
3. **Map the ROM**:
   - `python3 tools/xref.py <file> <flags>`: subroutines with callers, hardware
     registers used, self-modifying stores, data references, strings.
   - `python3 tools/xref.py <file> <flags> --callgraph`: call tree from RESET /
     the cartridge entries.
   - For the annotated listing, follow `atari8-disassemble`. Inside ROM images
     the machine's ROM and zero-page names are applied automatically.
4. **Classify regions**: code (traced vs swept/filled counts in the header),
   jump and dispatch tables (`--table`), text, vectors, fill.
5. **Report**: for each major routine give address range, entry/exit
   registers and memory, purpose, callers/callees; list the public entry
   points and which RAM vectors they go through.

## Analysis Tips

- The OS jump table at $E450-$E48F (DISKIV, CIOV, SIOV, SETVBV, SYSVBV,
  XITVBV, WARMSV, COLDSV …) is the public API; the handler tables at
  $E400-$E44F hold device handler vectors (address-1, RTS dispatch: pass them
  as `--table E400:...:rts` where the layout is known).
- Interrupts go through the RAM vectors on page 2: NMI → VDSLST / VVBLKI,
  IRQ → VIMIRQ and the POKEY vectors. Code that patches them is a handler.
- XL/XE OS: PORTB ($D301) bit 0 banks the OS ROM out (RAM under ROM), bit 7 the
  self-test ROM ($5000-$57FF), bit 1 BASIC. 1200XL uses PORTB bits 2/3 for LEDs.

---
name: a2-analyze-rom
description: "Use when the user asks to analyze, identify, or map the structure of an Apple II ROM image (Monitor, Applesoft, IIe/IIc CD/EF ROMs, Disk II boot ROM, slot card firmware): vectors, subroutine map, ROM type."
---

# Analyze Apple II ROM Image

Run from `/home/pi/proyectos/6502-dissasembler/`.

## Steps

1. **Identify**: `python3 tools/a2loader.py <file> --json`
   - Reports the size-based org, RESET/NMI/IRQ vectors, machine ID ($FBB3 /
     $FBC0 → II, II+, IIe, enhanced IIe, IIc) and a CPU hint.
   - RESET = $FA62 means the Autostart Monitor (II+ and later). RESET = $FF59
     means the original Apple II Monitor.
   - Slot firmware (256 bytes): pass `--org 0xCn00` for slot n. The Disk II
     P5A boot ROM is detected by signature and goes to $C600.
   - Split ROM dumps (e.g. separate CD and EF halves): disassemble each with
     its own `--org` ($C000 / $E000), or concatenate them first.
2. **Read reference data**: `reference/rom_entry_points.md` and
   `reference/apple2_memory_map.md`.
3. **Map the ROM**:
   - `python3 tools/xref.py <file> [--org ...] [--cpu ...]` gives the report:
     subroutines with callers, soft switch usage, self-modifying stores,
     in-image data references and strings.
   - `python3 tools/xref.py <file> ... --callgraph` gives the call tree from
     RESET plus the other vector targets.
   - For the full annotated listing, follow the `a2-disassemble` skill. Monitor
     and Applesoft names are applied inside ROM images automatically
     (zero-page names too).
4. **Classify regions**:
   - Code (traced from vectors plus linearly filled gaps; the listing header
     shows traced vs. filled counts)
   - Dispatch tables: Applesoft keeps statement / function address tables
     (address-1 pushed and entered with RTS), so add them with `--entry` or
     note them as data
   - Text: Applesoft tokens and error messages end with a high-bit character;
     Monitor strings are high-bit ASCII (`HASC`)
   - Vectors: $FFFA-$FFFF, `.word`
5. **Produce report**: for each major subroutine give the address range,
   entry conditions (registers, zero-page inputs such as A1/A2/A4, CH/CV,
   FAC/ARG), exit conditions, purpose, and callers/callees.

## Analysis Tips

- Monitor I/O goes through the CSW ($36) and KSW ($38) hooks. Slot firmware
  and DOS/ProDOS install themselves by patching these.
- Page 3 hooks ($03F0-$03FF) are reached through `JMP ($03xx)` or JMP
  instructions in RAM. The listing marks them and the annotator names them.
- IIe/IIc ROMs bank-switch $C100-$CFFF (SETINTCXROM/SETSLOTCXROM). Code in
  $C300 and $C800 runs in "internal ROM" context.
- The Disk II boot ROM uses slot-relative I/O (`LDA $C08C,X` with X =
  slot*16) and builds its 6-and-2 decode table in page 3. Expect
  timing-critical loops.
- Applesoft math routines use FAC ($9D) and ARG ($A5). The CHRGET routine at
  $B1 modifies its own TXTPTR operand ($B8/$B9).

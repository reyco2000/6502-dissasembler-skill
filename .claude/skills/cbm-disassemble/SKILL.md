---
name: cbm-disassemble
description: "Use when the user asks to disassemble, reverse-engineer, or annotate a Commodore 64, C128 or VIC-20 program or ROM (6502/6510/8502): .prg / .P00 file, BASIC SYS loader, cartridge (CBM80), KERNAL or BASIC ROM dump."
---

# Disassemble Commodore 8-bit (C64, C128, VIC-20) 6502 Code

Produces annotated **ca65** assembly via the same chunked pipeline as
`a2-disassemble`: read only tool stdout and the manifest, never the full
listing or xref output.

Run all commands from the repository root (paths below are relative).
`<name>` = input file basename. `<flags>` = the load/CPU/machine flags from
step 1, **always including `--machine <id>`**. Machines: `c64` (Commodore 64), `c128` (Commodore 128 (8502 side)), `vic20` (VIC-20).
Pass the **same** `<flags>` to steps 2 and 3, or the chunk boundaries won't
match the listing.

**Fast mode**: if the user says "fast" or passes `--fast`, skip step 7.

## Steps

1. **Identify**: `python3 tools/loader.py <file>` (add `--machine <id>` to force one)
   - The `Machine:` line prints the `--machine` value to use. If the file is
     headerless and the guess is wrong, pass `--machine` and `--org` yourself.
   - **.prg / .P00**: the first two bytes are the load address. $0801 → c64,
     $1001/$1201/$0401 → vic20 (unexpanded / +8K / +3K), $1C01 → c128. A
     `SYS nnnn` BASIC stub becomes the entry point (`Note: BASIC stub: SYS …`);
     the stub bytes stay data. Other load addresses default to c64: pass
     `--machine vic20` / `c128` when you know better.
   - **BASIC program without SYS**: the entry is the load address, which is
     tokenized BASIC, not code. Find the machine-code part (often after the
     BASIC end marker `00 00`, or a `SYS` inside the program) and pass `--entry`.
   - **Cartridge** (8K/16K raw with `CBM80` at $8004): org $8000, the cold/warm
     start words at $8000/$8002 are traced.
   - **ROMs** (raw): KERNAL 8K → $E000 (identified by `JMP ($0326)` at $FFD2 plus
     the RESET target: $FCE2 = C64, $FD22 = VIC-20), C64 BASIC 8K → $A000
     (`CBMBASIC` at $A004), C128 KERNAL (RESET $FF3D).
   - **CPU**: 6510/8502 are NMOS 6502. Many C64 programs (demos, games, packers)
     use illegal opcodes: if code paths fill with `.byte`, retry with
     `--undocumented` (ca65 `6502X`).
   - **Extra entry points**: `--entry 0xNNNN` (repeatable) for code only
     reached indirectly (interrupt handlers set up with computed pointers,
     routines called through tables, code copied to RAM and run there).
   - **Dispatch tables**: `--table ADDR:COUNT[:rts][:stride=N][:hi=XX]` (hex
     ADDR) traces every target and emits `.word LABEL` / `.word LABEL-1`.
   - **Automatic detection**: runs of `JMP abs`, pointer tables and OS-vector
     hooks (`LDx #<h / STx VEC / LDx #>h / STx VEC+1`) are traced automatically;
     they appear as `; Auto-detected ...` lines in the listing header.
     `--no-auto-tables` turns tables off.
   - **Symbols**: `--symbols FILE` (repeatable; first wins): orchard JSON, flat
     JSON or ca65 `NAME = $XXXX ; comment`. Reuse `output/<name>_symbols.json`
     when it exists.
   - **Force data**: `--data-region START-END` (hex, inclusive, repeatable).
   - **Fill mode**: default `--fill validated`; `--fill all` only to inspect.

2. **Disassemble**: `python3 tools/dasm6502.py <file> <flags> --annotate --output output/<name>.asm`
   - The listing header has `; Machine: <id>`; equates use the machine's
     ROM/OS, hardware and (for ROM images or `--zp-names`) zero-page names.
   - Check `; Traced instructions: N, swept: S, filled: F`. Large code-looking
     `.byte` areas mean missing entry points: look for `JMP (abs)` dispatch,
     PHA/PHA/RTS, vector hooks and copy-to-RAM loops, then rerun with
     `--entry` / `--table`. Keep the final flags in one variable.

3. **Section map**: `python3 tools/xref.py <file> <flags> --sections --max-chunks N --output output/<name>_sections.json`
   - N ≈ listing lines / 500 (`grep -c . output/<name>.asm`), chunks ≤ ~35KB.

4. **Split**: `python3 tools/annotator.py --split --asm output/<name>.asm --sections output/<name>_sections.json --output-dir output/<name>_chunks/`
   (the manifest records the machine).

5. **Read the manifest**: `output/<name>_chunks/manifest.json`.

6. **Python annotation**: `python3 tools/annotator.py --annotate --manifest output/<name>_chunks/manifest.json --ref-dir reference/`
   - The machine comes from the manifest (`--machine` overrides). Zero LLM
     tokens: KERNAL calls (CHROUT, GETIN, SETLFS/SETNAM/LOAD …) with the real target address, VIC-II / SID / CIA register names, colour RAM, the $0314/$0316/$0318 RAM vectors (IRQ/BRK/NMI wedges), `LDA #<h / STA CINV / LDA #>h / STA CINV+1` hooks (the handler is traced and labelled automatically), $01 banking writes, self-modifying code, stack tricks, pointer loops.

7. **Optional LLM annotation** (skip in fast mode): pick up to 2 chunks with
   the highest subroutines + hw_accesses + rom_calls count and dispatch one
   **foreground** subagent per chunk in parallel (never background). Each
   subagent reads its chunk, adds `;` commentary only (never touches the
   address/hex/instruction columns) and writes it back. Point them at the
   machine techniques worth explaining: raster interrupts (CIA/VIC IRQ setup, $D012 compare), sprite multiplexing, SID register writes (voice/ADSR), $01 memory banking (LORAM/HIRAM/CHAREN), KERNAL vector wedges, decrunchers (self-modifying loops copying to $0801), fast loaders talking to the 1541 on the serial bus ($DD00). Ask each to end with
   confident names as `NAME = $XXXX ; purpose`, verify them, add them to
   `output/<name>_symbols.json` and run
   `python3 tools/annotator.py --manifest output/<name>_chunks/manifest.json --apply-symbols output/<name>_symbols.json`.

8. **Merge**: `python3 tools/annotator.py --merge --manifest output/<name>_chunks/manifest.json --output output/<name>_annotated.asm`
   - Reassemblable copy: add `--reassemble --output output/<name>_annotated.s`
     (`ca65 x.s && ld65 -t none x.o -o x.bin` gives back the original bytes of
     each segment).

9. **Save the flags** to `output/<name>_flags.txt`.

10. **Present findings** from the manifest and tool stdout: format, load
    address(es), machine, CPU, ROM identity, chunks and lines, key
    subroutines, OS calls, hardware registers, vector hooks, self-modifying
    code, output paths.

## References

Read automatically by the annotator; consult them when interpreting results:
- `reference/c64/memory_map.md`, `reference/c64/rom_entry_points.md`: C64: zero page, $0200-$03FF vectors, VIC-II/SID/CIA, banking
- `reference/c128/memory_map.md`, `reference/c128/rom_entry_points.md`: C128: MMU, VDC, BASIC 7.0 and KERNAL jumbo table
- `reference/vic20/memory_map.md`, `reference/vic20/rom_entry_points.md`: VIC-20: block map, VIC 6560/6561, VIAs, KERNAL
- `reference/MACHINES.md`: every supported machine, sources and caveats

## Output

ca65 syntax: `.setcpu`, `NAME = $XXXX` equates for the machine's OS entry
points, hardware registers and zero page (`NAME+1` for the high byte of a
16-bit vector), `.org` per segment, `L_`/`SUB_`/`D_` labels (ROM names inside
ROM images; a repeated name gets its address appended, e.g. `PLOT_E50A`),
`.byte` / `.word` / `.res` data. CMOS reserved opcodes and WDC STP/WAI are
`.byte` with a comment.

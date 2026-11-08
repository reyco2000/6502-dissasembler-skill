---
name: atari8-disassemble
description: "Use when the user asks to disassemble, reverse-engineer, or annotate an Atari 400/800/XL/XE program or ROM: DOS binary load file (.xex/.com/.obj), Atari800 .car cartridge, raw cartridge, OS ROM dump."
---

# Disassemble Atari 8-bit (400 / 800 / 600XL / 800XL / 1200XL) 6502 Code

Produces annotated **ca65** assembly via the same chunked pipeline as
`a2-disassemble`: read only tool stdout and the manifest, never the full
listing or xref output.

Run all commands from the repository root (paths below are relative).
`<name>` = input file basename. `<flags>` = the load/CPU/machine flags from
step 1, **always including `--machine <id>`**. Machines: `atari400` (Atari 400), `atari800` (Atari 800), `atari600xl` (Atari 600XL), `atari800xl` (Atari 800XL (default for .xex)), `atari1200xl` (Atari 1200XL).
Pass the **same** `<flags>` to steps 2 and 3, or the chunk boundaries won't
match the listing.

**Fast mode**: if the user says "fast" or passes `--fast`, skip step 7.

## Steps

1. **Identify**: `python3 tools/loader.py <file>` (add `--machine <id>` to force one)
   - The `Machine:` line prints the `--machine` value to use. If the file is
     headerless and the guess is wrong, pass `--machine` and `--org` yourself.
   - **.xex / .com / .obj** (`$FFFF` header): every segment loads at its own
     address. RUNAD ($02E0) becomes the entry point, every INITAD ($02E2)
     becomes an extra entry (code run during the load); those vector bytes are
     reported in the notes, not loaded. Overlapping segments: the later one wins,
     as on the machine.
   - **.car** (Atari800 emulator) and raw 8K/16K cartridges: 8K at $A000, 16K at
     $8000; RUN address $BFFA and INIT address $BFFE are traced. Raw carts need
     `--machine atari800xl` (or another Atari) so the size guess is right.
   - **OS ROM**: 10K → $D800 (400/800 OS-A/OS-B), 16K → $C000 (XL/XE), recognised
     by the JMP table at $E450. The floating-point package is $D800-$DFFF.
   - Pick the model with `--machine`: the tables differ only in the per-model
     notes (PORTB, 1200XL LEDs); 800XL is the default.
   - **CPU**: NMOS 6502 (SALLY). Some demos use illegal opcodes (`--undocumented`).
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
     tokens: CIO/SIO calls (CIOV $E456, SIOV $E459, SETVBV $E45C …), ANTIC/GTIA/POKEY/PIA register names, OS shadow registers (SDMCTL, SDLSTL, COLOR0-4, PCOLR0-3), stores into page-2 vectors (VDSLST, VVBLKI/VVBLKD, VIMIRQ, VKEYBD …) with automatic tracing of the installed handler, self-modifying code, stack tricks, pointer loops.

7. **Optional LLM annotation** (skip in fast mode): pick up to 2 chunks with
   the highest subroutines + hw_accesses + rom_calls count and dispatch one
   **foreground** subagent per chunk in parallel (never background). Each
   subagent reads its chunk, adds `;` commentary only (never touches the
   address/hex/instruction columns) and writes it back. Point them at the
   machine techniques worth explaining: display lists (ANTIC opcodes, LMS, DLI bits), DLI handlers (WSYNC $D40A timing, colour changes), VBI handlers chained through SETVBV/XITVBV, player/missile graphics (PMBASE, GRACTL, HPOSPx), POKEY sound (AUDF/AUDC, AUDCTL), IOCB setup ($0340 + 16*n: ICCOM, ICBAL, ICBLL) before `JSR CIOV`, PORTB banking on XL/XE. Ask each to end with
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
- `reference/atari800xl/memory_map.md`, `reference/atari800xl/rom_entry_points.md`: 800XL (XL/XE OS); the other models' folders have the same layout
- `reference/atari800/memory_map.md`, `reference/atari800/rom_entry_points.md`: 400/800 OS-A/OS-B
- `reference/MACHINES.md`: every supported machine, sources and caveats

## Output

ca65 syntax: `.setcpu`, `NAME = $XXXX` equates for the machine's OS entry
points, hardware registers and zero page (`NAME+1` for the high byte of a
16-bit vector), `.org` per segment, `L_`/`SUB_`/`D_` labels (ROM names inside
ROM images; a repeated name gets its address appended, e.g. `PLOT_E50A`),
`.byte` / `.word` / `.res` data. CMOS reserved opcodes and WDC STP/WAI are
`.byte` with a comment.

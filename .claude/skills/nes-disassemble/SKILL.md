---
name: nes-disassemble
description: "Use when the user asks to disassemble, reverse-engineer, or annotate an NES or Famicom game or homebrew: iNES / NES 2.0 .nes file, raw PRG ROM or cartridge dump (2A03: NMOS 6502 without decimal mode)."
---

# Disassemble NES / Famicom 6502 Code

Produces annotated **ca65** assembly via the same chunked pipeline as
`a2-disassemble`: read only tool stdout and the manifest, never the full
listing or xref output.

Run all commands from the repository root (paths below are relative).
`<name>` = input file basename. `<flags>` = the load/CPU/machine flags from
step 1, **always including `--machine <id>`**. Machines: `nes` (NES (default)), `famicom` (Famicom (same core; $4016/$4017 expansion and microphone differences)).
Pass the **same** `<flags>` to steps 2 and 3, or the chunk boundaries won't
match the listing.

**Fast mode**: if the user says "fast" or passes `--fast`, skip step 7.

## Steps

1. **Identify**: `python3 tools/loader.py <file>` (add `--machine <id>` to force one)
   - The `Machine:` line prints the `--machine` value to use. If the file is
     headerless and the guess is wrong, pass `--machine` and `--org` yourself.
   - **.nes** (iNES / NES 2.0): the loader reports mapper, PRG/CHR bank counts and
     mirroring. NROM-128 (16K) loads at $C000, NROM-256 (32K) at $8000. Every
     other mapper: the last 16K PRG bank (fixed on UxROM/MMC1/MMC3-style boards)
     at $C000, and `--bank N` puts bank N at $8000. Disassemble bank by bank with
     the same `--bank` in every step; keep one flags file per bank.
   - **Raw PRG**: 16K → $C000, 32K → $8000 (`--machine nes`).
   - Vectors at $FFFA-$FFFF: NMI (vblank handler), RESET, IRQ (mapper / APU
     frame IRQ) are traced automatically.
   - CHR data (graphics) is not code and is not loaded.
   - **CPU**: 2A03 = NMOS 6502, decimal mode ignored. Some homebrew uses illegal
     opcodes (`--undocumented`).
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
     tokens: PPU registers ($2000-$2007: PPUCTRL, PPUMASK, PPUSTATUS, OAMADDR, PPUSCROLL, PPUADDR, PPUDATA), APU/IO registers ($4000-$4017, OAMDMA $4014, JOY1/JOY2), vblank wait loops (`BIT PPUSTATUS / BPL`), mapper register writes (stores into $8000-$FFFF), self-modifying code in RAM, stack tricks, pointer loops.

7. **Optional LLM annotation** (skip in fast mode): pick up to 2 chunks with
   the highest subroutines + hw_accesses + rom_calls count and dispatch one
   **foreground** subagent per chunk in parallel (never background). Each
   subagent reads its chunk, adds `;` commentary only (never touches the
   address/hex/instruction columns) and writes it back. Point them at the
   machine techniques worth explaining: the reset sequence (SEI/CLD, APU frame IRQ off, two vblank waits, RAM clear), NMI handler structure (OAM DMA, PPU updates in vblank, scroll reset via $2005/$2006 pairs), controller reads (strobe $4016, 8 serial reads), mapper bank switching (MMC1 serial writes, MMC3 $8000/$8001 pairs, UxROM bus conflicts), sprite-0 hit splits, music engines writing APU registers. Ask each to end with
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
- `reference/nes/memory_map.md`, `reference/nes/rom_entry_points.md`: CPU/PPU/APU maps, iNES header, mapper registers
- `reference/famicom/memory_map.md`, `reference/famicom/rom_entry_points.md`: Famicom differences: expansion port, microphone, FDS
- `reference/MACHINES.md`: every supported machine, sources and caveats

## Output

ca65 syntax: `.setcpu`, `NAME = $XXXX` equates for the machine's OS entry
points, hardware registers and zero page (`NAME+1` for the high byte of a
16-bit vector), `.org` per segment, `L_`/`SUB_`/`D_` labels (ROM names inside
ROM images; a repeated name gets its address appended, e.g. `PLOT_E50A`),
`.byte` / `.word` / `.res` data. CMOS reserved opcodes and WDC STP/WAI are
`.byte` with a comment.

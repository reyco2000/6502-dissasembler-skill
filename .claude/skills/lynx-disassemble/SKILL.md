---
name: lynx-disassemble
description: "Use when the user asks to disassemble, reverse-engineer, or annotate an Atari Lynx program or ROM (65SC02): BLL .o/.com executable, .lnx cartridge image, boot ROM dump, decrypted cart loader."
---

# Disassemble Atari Lynx 6502 Code

Produces annotated **ca65** assembly via the same chunked pipeline as
`a2-disassemble`: read only tool stdout and the manifest, never the full
listing or xref output.

Run all commands from the repository root (paths below are relative).
`<name>` = input file basename. `<flags>` = the load/CPU/machine flags from
step 1, **always including `--machine <id>`**. Machines: `lynx` (Atari Lynx (CPU 65SC02 by default)).
Pass the **same** `<flags>` to steps 2 and 3, or the chunk boundaries won't
match the listing.

**Fast mode**: if the user says "fast" or passes `--fast`, skip step 7.

## Steps

1. **Identify**: `python3 tools/loader.py <file>` (add `--machine <id>` to force one)
   - The `Machine:` line prints the `--machine` value to use. If the file is
     headerless and the guess is wrong, pass `--machine` and `--org` yourself.
   - **BLL executable** (.o/.com, `$80 $08` + big-endian load address + size +
     `BS93`): loads at its own address (usually $0200 or $0400), entry = load.
   - **.lnx cartridge**: 64-byte `LYNX` header (name, bank sizes) + the cart
     image. The first cart block is RSA-encrypted and is decrypted by the boot
     ROM into $0200, so a plain .lnx disassembly of the start is meaningless:
     use a decrypted dump or the homebrew's BLL file. The loader warns about it.
   - **Boot ROM** (512 bytes): $FE00, RESET $FF80.
   - **CPU**: 65SC02 (65C02 set without BBR/BBS/RMB/SMB): the default CPU for
     `--machine lynx`. CMOS reserved opcodes decode as NOPs of the right width
     and are kept as `.byte`.
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
     tokens: Suzy registers ($FC00-$FCFF: sprite engine, math unit, joystick/switches), Mikey registers ($FD00-$FDFF: timers, audio, interrupts INTRST/INTSET, palette, display address, serial), MAPCTL $FFF9, 65SC02 instructions (STZ, BRA, PHX/PLY, TSB/TRB), self-modifying code, stack tricks, pointer loops.

7. **Optional LLM annotation** (skip in fast mode): pick up to 2 chunks with
   the highest subroutines + hw_accesses + rom_calls count and dispatch one
   **foreground** subagent per chunk in parallel (never background). Each
   subagent reads its chunk, adds `;` commentary only (never touches the
   address/hex/instruction columns) and writes it back. Point them at the
   machine techniques worth explaining: sprite control blocks (SCB linked lists, SPRCTL0/1, SPRCOLL) handed to Suzy via SCBNEXTL/H and SPRGO, math unit multiply/divide (MATHA-MATHP, SPRSYS), Mikey timer chains (timer 0 = HBL, timer 2 = VBL) and their interrupts, audio channels, MAPCTL overlays of Suzy/Mikey/ROM/vectors, cart bank reads through RCART0/1. Ask each to end with
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
- `reference/lynx/memory_map.md`, `reference/lynx/rom_entry_points.md`: Suzy/Mikey registers, MAPCTL, boot ROM entry points, cart header
- `reference/MACHINES.md`: every supported machine, sources and caveats

## Output

ca65 syntax: `.setcpu`, `NAME = $XXXX` equates for the machine's OS entry
points, hardware registers and zero page (`NAME+1` for the high byte of a
16-bit vector), `.org` per segment, `L_`/`SUB_`/`D_` labels (ROM names inside
ROM images; a repeated name gets its address appended, e.g. `PLOT_E50A`),
`.byte` / `.word` / `.res` data. CMOS reserved opcodes and WDC STP/WAI are
`.byte` with a comment.

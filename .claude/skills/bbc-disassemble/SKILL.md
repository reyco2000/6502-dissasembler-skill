---
name: bbc-disassemble
description: "Use when the user asks to disassemble, reverse-engineer, or annotate a BBC Micro (Model A/B/B+) or BBC Master program or ROM: sideways (paged) ROM image, MOS ROM, file with a .inf sidecar, raw *SAVEd memory."
---

# Disassemble Acorn BBC Micro (Model A, B, B+, Master 128) 6502 Code

Produces annotated **ca65** assembly via the same chunked pipeline as
`a2-disassemble`: read only tool stdout and the manifest, never the full
listing or xref output.

Run all commands from the repository root (paths below are relative).
`<name>` = input file basename. `<flags>` = the load/CPU/machine flags from
step 1, **always including `--machine <id>`**. Machines: `bbc_a` (Model A), `bbc_b` (Model B (default)), `bbc_bplus` (Model B+), `bbc_master` (Master 128 (65C12: use the default CPU 65c12)).
Pass the **same** `<flags>` to steps 2 and 3, or the chunk boundaries won't
match the listing.

**Fast mode**: if the user says "fast" or passes `--fast`, skip step 7.

## Steps

1. **Identify**: `python3 tools/loader.py <file>` (add `--machine <id>` to force one)
   - The `Machine:` line prints the `--machine` value to use. If the file is
     headerless and the guess is wrong, pass `--machine` and `--org` yourself.
   - **Sideways ROM** (8K/16K, copyright string `\0(C)` at the offset in byte 7):
     org $8000, the language entry ($8000) and service entry ($8003) are traced.
     The ROM title, type byte and kind (service/language) are in the ROM line.
   - **.inf sidecar** (`NAME.inf` or `NAME` + `.inf`, `$.NAME LLLLLLLL EEEEEEEE`):
     load and exec addresses come from it.
   - **MOS ROM** (16K): $C000, recognised by `JMP ($020E)` at OSWRCH $FFEE.
   - **Raw *SAVE dump**: pass `--org` (common: $1900 PAGE on a disc B, $0E00 on
     tape/Master, $2000, $3000) and `--machine bbc_b`.
   - **CPU**: Model A/B/B+ are NMOS 6502; the Master is a 65C12 (the 65C02 set
     without Rockwell bit ops): `--machine bbc_master` selects it. Code for a
     second processor (6502 Tube) is plain 6502.
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
     tokens: OS calls (OSWRCH, OSBYTE, OSWORD, OSFILE, OSASCI, OSNEWL …), `LDA #&xx / JSR OSBYTE|OSWORD` decoded to the reason-code name, SHEILA register names (CRTC, ULA, System/User VIA, ROMSEL $FE30, ACCCON), stores into page-2 RAM vectors (WRCHV, BYTEV, IRQ1V, BRKV …) with automatic tracing of the installed handler, BRK error blocks, self-modifying code.

7. **Optional LLM annotation** (skip in fast mode): pick up to 2 chunks with
   the highest subroutines + hw_accesses + rom_calls count and dispatch one
   **foreground** subagent per chunk in parallel (never background). Each
   subagent reads its chunk, adds `;` commentary only (never touches the
   address/hex/instruction columns) and writes it back. Point them at the
   machine techniques worth explaining: sideways ROM service-call handling (A = reason: &04 unrecognised *command, &09 *HELP, &12 filing system), the BRK error convention (`BRK` + error number + message + 0), VDU control codes sent through OSWRCH (VDU 22 mode, 23 redefine, 19 palette), CRTC/ULA register programming, paged ROM switching through ROMSEL $FE30 / $F4 copy, Tube communication. Ask each to end with
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
- `reference/bbc_b/memory_map.md`, `reference/bbc_b/rom_entry_points.md`: Model B, MOS 1.20 (the A/B+/Master folders have the same layout with their own notes)
- `reference/bbc_master/memory_map.md`, `reference/bbc_master/rom_entry_points.md`: Master 128: MOS 3.20, ACCCON, extra workspace
- `reference/MACHINES.md`: every supported machine, sources and caveats

## Output

ca65 syntax: `.setcpu`, `NAME = $XXXX` equates for the machine's OS entry
points, hardware registers and zero page (`NAME+1` for the high byte of a
16-bit vector), `.org` per segment, `L_`/`SUB_`/`D_` labels (ROM names inside
ROM images; a repeated name gets its address appended, e.g. `PLOT_E50A`),
`.byte` / `.word` / `.res` data. CMOS reserved opcodes and WDC STP/WAI are
`.byte` with a comment.

---
name: a2-disassemble
description: "Use when the user asks to disassemble, reverse-engineer, or annotate an Apple II / II+ / IIe / IIc binary or ROM (6502 or 65C02): AppleSingle, ProDOS BIN/SYS, DOS 3.3 binary, raw memory dump, or ROM image."
---

# Disassemble Apple II 6502 / 65C02 Binary

Produces annotated **ca65** assembly via a chunked pipeline that keeps
main-agent context small: read only tool stdout and the manifest, never
the full listing or xref output.

Run all commands from `/home/pi/proyectos/6502-dissasembler/` (paths below
are relative). `<name>` = input file basename. `<flags>` = the load/CPU
flags from step 1. Pass the **same** `<flags>` to steps 2 and 3, or the
chunk boundaries won't match the listing.

**Fast mode**: if the user says "fast" or passes `--fast`, skip step 7.

## Steps

1. **Identify**: `python3 tools/a2loader.py <file>`
   - **AppleSingle** (ProDOS export from CiderPress / AppleCommander / cc65):
     load address comes from the aux type (BIN) or $2000 (SYS). No `--org`.
   - **DOS 3.3 binary with 4-byte header**, or a filename like `GAME#062000`:
     load address is automatic.
   - **ROM image**: org is guessed from size (2K→$F800, 12K→$D000,
     16K→$C000, 256B→$C600). RESET/NMI/IRQ vectors are traced
     automatically. `$C000-$C0FF` in 16K IIe/IIc images is I/O space and is
     kept as data.
   - **Raw dump**: pass `--org <addr>`. If the address isn't obvious, ask the
     user. Common values: $0800, $2000, $4000, $6000, $0300.
   - **CPU**: the loader's `CPU hint` comes from the ROM ID bytes. Otherwise
     use `--cpu 6502` for II/II+ software and `--cpu 65c02` for software that
     needs an enhanced IIe/IIc. If a 6502 listing is full of `.byte` in code
     paths (e.g. `$80`, `$64`, `$DA`), retry with `--cpu 65c02`. Use
     `--cpu r65c02` only for Rockwell BBR/BBS/RMB/SMB code (not Apple
     hardware). `--undocumented` enables NMOS illegal opcodes (6502X).
   - **Extra entry points**: add `--entry 0xNNNN` (repeatable) for code that is
     only reached indirectly (`&` / `USR` handlers, documented ROM entries
     reached through hooks such as COUT1 $FDF0, the address after a JSR to a
     print-inline routine).
   - **Dispatch tables**: `--table ADDR:COUNT[:rts][:stride=N][:hi=XX]`
     (hex ADDR) traces every target and emits entries as `.word LABEL-1` /
     `.byte <(LABEL-1)`. `rts` = entries hold address-1 (PHA/PHA/RTS
     dispatch), `hi=XX` = low-byte table with fixed high byte, `stride` for
     interleaved tables. The loader applies presets automatically for the
     Applesoft statement/function/operator tables and the Monitor command
     table (`Table: ... (auto)` lines; disable with `--no-presets`). Split
     lo/hi tables with computed high bytes can't be expressed. Compute the
     targets and pass them as `--entry`.
   - **Automatic tables**: 3 or more consecutive `JMP abs` vectors, and word tables
     whose first 4 entries all point at known routine entries (direct or
     address-1), are detected and traced automatically. They show up as
     `; Auto-detected ...` lines in the listing header. Sanity-check each one;
     `--no-auto-tables` turns this off.
   - **Symbols**: `--symbols FILE` (repeatable; first definition wins)
     names addresses in the listing, xref and call graph. Accepts orchard
     schema-v1.0 JSON (e.g. `shared/symbols/apple2.json` from
     github.com/BrentRector/orchard), flat JSON `{"0xC311": "AUXMOVE"}`, or
     ca65 `NAME = $XXXX ; comment` lines. If `output/<name>_symbols.json`
     exists from an earlier session, always pass it.
   - **Force data**: `--data-region START-END` (hex, inclusive, repeatable)
     for tables or text that tracing or the sweep mistakes for code.
   - **Fill mode**: the default `--fill validated` turns unreached bytes into
     code only when they follow traced code (or are a branch/call target) and
     decode cleanly to RTS/RTI/JMP. Everything else stays `.byte`. Use
     `--fill all` only to see what arbitrary bytes would decode to.

2. **Disassemble**: `python3 tools/dasm6502.py <file> <flags> --annotate --output output/<name>.asm`
   - Check `; Traced instructions: N, swept: S, filled: F` in the listing
     header, plus the size of the `.byte` regions in the xref report. If
     large code-looking areas remain data, entry points are missing. Find them by:
     (a) looking for `PHA / LDA tbl,Y / PHA / RTS` and `JMP (abs)` / `JMP (abs,X)`
     dispatch in traced code, (b) reading protocol bytes (e.g. slot firmware
     $Cn0D-$Cn10 Pascal offsets), (c) the largest runs of untraced code.
     Then rerun with `--table` / `--entry`. Keep the final flags in one
     variable and reuse them in every step.

3. **Section map**: `python3 tools/xref.py <file> <flags> --sections --max-chunks N --output output/<name>_sections.json`
   - Size chunks by listing lines, not bytes: N ≈ listing lines / 500
     (`grep -c . output/<name>.asm`). Chunks for LLM annotation should stay
     around ≤ 35KB each. Dense code such as a 16K ROM gives ~9,500 lines, so N ≈ 20.

4. **Split**: `python3 tools/annotator.py --split --asm output/<name>.asm --sections output/<name>_sections.json --output-dir output/<name>_chunks/`

5. **Read the manifest**: `output/<name>_chunks/manifest.json` (chunk list with
   subroutines, ROM calls, soft switches, self-modifying code per chunk).

6. **Python annotation**: `python3 tools/annotator.py --annotate --manifest output/<name>_chunks/manifest.json --ref-dir reference/`
   - Pattern rules, zero LLM tokens: ROM/MLI calls, soft switches, display
     mode sequences, keyboard wait loops, speaker tone loops, language card
     double reads, slot-indexed Disk II I/O, paddles/buttons, page-3 vectors,
     screen memory writes, pointer fill/copy loops, stack tricks
     (PLA/PLA, PHA/PHA/RTS), self-modifying code.

7. **Optional LLM annotation** (skip in fast mode): pick up to 2 chunks from
   the manifest with the highest subroutines + hw_accesses + rom_calls count.
   Dispatch one **foreground** subagent per chunk, in parallel (never
   background / `run_in_background`, because they must be able to prompt
   for permissions). Each subagent (~30KB context budget):
   - Reads its chunk file (already Python-annotated).
   - Adds inline `;` commentary: subroutine purpose, entry/exit registers,
     block behavior (screen setup, keyboard input, disk I/O, sound), and
     Apple II techniques (self-modifying operands, cycle-counted delays, hi-res
     byte/bit math, nibble encode/decode, bank switching).
   - Must not change the address/hex/instruction columns, only append
     comments or insert `;` lines. Writes the chunk back with the Write tool.
   - Give each subagent the facts you established (dispatch tables, entry
     protocols, screen-hole variables) and tell it to hedge inferences.
   - Ask each subagent to end its report with the routine names it is
     confident about, as `NAME = $XXXX ; one-line purpose` (valid ca65
     identifiers, no guesses).
   - **Name propagation**: verify the proposed names (check them against the
     code or tables yourself), then add them to `output/<name>_symbols.json`
     (schema v1.0, one category) and run
     `python3 tools/annotator.py --manifest output/<name>_chunks/manifest.json --apply-symbols output/<name>_symbols.json`.
     This renames `SUB_xxxx`/`L_xxxx`/`D_xxxx` everywhere in the chunks and
     keeps every comment. Append `--symbols output/<name>_symbols.json` to the
     saved flags so reruns keep the names.
   - Before annotating, copy the Python-annotated chunks (or regenerate them
     with the same flags). After the subagents finish, check that every
     code line is unchanged apart from comments, then merge.

8. **Merge**: `python3 tools/annotator.py --merge --manifest output/<name>_chunks/manifest.json --output output/<name>_annotated.asm`
   - Also produce a reassemblable copy when the user wants to rebuild/patch:
     add `--reassemble --output output/<name>_annotated.s`
     (`ca65 x.s && ld65 -t none x.o -o x.bin` gives back the original bytes).

9. **Save the flags** you used to `output/<name>_flags.txt` so the listing can
   be regenerated exactly.

10. **Present findings** from the manifest and tool stdout only: file format
   and load address, CPU, ROM identity, chunk count and total lines, key
   subroutines, ROM/MLI calls and soft switches used, self-modifying code,
   output paths.

## References

The Python annotator reads these automatically. Consult them yourself only
when interpreting results:
- `reference/apple2_memory_map.md`: zero page, page 3 vectors, soft switches, language card, Disk II, ProDOS global page
- `reference/rom_entry_points.md`: Monitor, Applesoft, DOS 3.3, ProDOS MLI calls, common idioms

## Output

ca65 syntax: `.setcpu`, `NAME = $XXXX` equates for external ROM / soft
switch / zero-page symbols, `.org` per contiguous region, `L_xxxx` /
`SUB_xxxx` / `D_xxxx` labels (Monitor names inside ROM images), `.byte`
strings, a `HASC` macro for high-bit ASCII, `.word` for vectors, jump
pointers and MLI parameter pointers, `.res` for fills, and chunk boundary
markers.

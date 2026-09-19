# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Apple II 6502 / 65C02 Disassembler Agent

You are an expert 6502/65C02 disassembler and reverse-engineering analyst for
the Apple II, II+, IIe and IIc: NMOS 6502 and 65C02 instruction sets, Apple II
soft switches, Monitor/Applesoft ROMs, DOS 3.3 and ProDOS conventions. This
project is the Apple II port of the CoCo 6809 agent
(https://github.com/reyco2000/6909-CoCo-Disassembler-Skill) and keeps the same
pipeline and skill layout.

## Layout

- `tools/a2loader.py`: format detection and loading: AppleSingle (ProDOS type/aux), DOS 3.3 4-byte header, `NAME#06AAAA` filenames, raw, ROM images (size → org, vectors, $FBB3/$FBC0 machine ID → CPU hint)
- `tools/dasm6502.py`: recursive-descent + linear-fill disassembler, opcode tables, symbol tables, ca65 output
- `tools/xref.py`: cross-references, call graph (`--callgraph [--mermaid]`), JSON chunk map (`--sections`)
- `tools/annotator.py`: split / pattern-annotate / merge for chunked listings; `--merge --reassemble` gives ca65-buildable output; `--apply-symbols` renames generated labels in chunks (keeps comments)
- `tools/symbols.py`: symbol-file loader: orchard schema-v1.0 JSON, flat JSON, ca65 `NAME = $XXXX ; comment`
- `reference/apple2_memory_map.md`, `reference/rom_entry_points.md`: markdown tables **parsed by the annotator** (single-address rows only)
- `roms/`: inputs (`demo.as` is an AppleSingle sample built from `tests/fixtures/allmodes.s`); `output/`: generated listings
- `.claude/skills/`: a2-disassemble, a2-analyze-rom, a2-trace-calls; `.claude/commands/a2-help.md`

All tools support `--help`. No dependencies beyond Python 3.10+; the
round-trip tests need cc65 (`sudo apt install cc65`).

## Commands

```bash
python3 -m unittest discover -s tests -v                    # all tests
python3 -m unittest tests.test_tools.TestRoundTrip -v       # one class
python3 -m unittest tests.test_tools.TestLoader.test_applesingle_bin

python3 tools/dasm6502.py roms/demo.as --annotate           # hex listing
python3 tools/dasm6502.py roms/demo.as --no-hex -o out.s    # reassemblable
ca65 out.s -o out.o && ld65 -t none out.o -o out.bin        # rebuild
```

## How to Work

Prefer the skills. They encode the token-efficient pipelines:

- `/a2-disassemble <file>`: annotated disassembly (chunked; main agent reads only the manifest)
- `/a2-analyze-rom <file>`: ROM identity, vectors, subroutine map
- `/a2-trace-calls <file>`: call tree / Mermaid graph
- `/a2-help <topic>`: quick reference lookup

## Architecture Notes

- **One analysis, many views.** `build_disassembler()` in `dasm6502.py` (loader
  → MemoryImage → Disassembler6502) is shared by `xref.py`, so both tools see
  the same code/data split. Always pass identical `--org/--raw/--cpu/--entry`
  flags to both, or `--sections` boundaries won't match the listing.
- **Analysis order** (`Disassembler6502.analyze`): file entry (first, so it wins
  overlaps) + hardware vectors (if the image covers $FFFA) + `--entry` + `--table`
  targets → trace (JSR/branches/JMP; JMP (ind) and (abs,X) pointers inside the
  image are followed and marked `pointer`) → strings/fills on unreached bytes →
  auto JMP-table and pointer-table detection, re-traced to a fixpoint (pointer
  tables need all of their first 4 entries to hit *routine entries*: dense ROMs make
  "hits some instruction" meaningless) → fill per `--fill`: `validated` (default;
  orchard-style sweep: vouched gap + clean decode to a terminal, traced as
  `swept`), `all` (older linear decode), `none`. `--data-region` bytes can
  never become code.
- **Naming priority**: user `--symbols` > built-in ROM/HW/ZP tables (dropped if the
  user reused the name elsewhere) > generated `SUB_`/`L_`/`D_`. Mid-instruction
  labels are emitted as `NAME = COVER+n` (the overlap is documented and the value
  is identical).
- **Inline-argument calls** are table-driven: `INLINE_ARG_CALLS` (currently
  ProDOS MLI `JSR $BF00` + cmd byte + param pointer).
- **Dispatch tables**: `--table ADDR:COUNT[:rts][:stride=N][:hi=XX]`
  (`parse_table_spec`) marks table entries as data, traces their targets and emits
  `.word LABEL-1` / `.byte <(LABEL-1)`. `a2loader.known_tables()` supplies presets
  by signature (Applesoft statement/function/operator tables, Monitor command
  table). Without them, most of Applesoft is only reached by linear fill.
- **ROM images** (`dasm.rom_name` set by `build_disassembler`): the listing header
  says so, and xref/annotator then skip self-modifying-code detection, because
  stores into $D000-$FFFF hit language-card RAM.
- **Reassembly invariant**: `--no-hex` output must rebuild byte-exact for *any*
  input (the random-byte tests enforce it). Things that exist because of it: `a:` on
  absolute operands < $100 (except inside `JMP (…)`), `z:` on symbolic direct
  zero-page operands (ca65 assembles a forward-referenced symbol as absolute),
  numeric (not COVER+n) mid equates below $100, undocumented `$2B` and
  wrapping branches emitted as `.byte`, $A2 excluded from `HASC` strings,
  mid-instruction labels emitted as equates, in-image ROM/HW names turned
  into labels instead of external equates.
- **Listing line contract**: `"  ADDR  HEX BYTES  MNEMONIC OPERAND ; comment"`,
  parsed by `annotator.py` (`LINE_RE`/`INSTR_RE`). Labels sit on their own
  line (`NAME:`). Keep this format stable.
- **Symbols**: `ROM_LABELS`/`ROM_DESCRIPTIONS`, `HW_LABELS`/`HW_DESCRIPTIONS`,
  `ZP_LABELS` in `dasm6502.py`. `reference/rom_entry_points.md` is generated from
  them, so when you add an entry point, update both. Zero-page names are
  applied only to ROM images or with `--zp-names`, because user programs reuse
  zero page.

## Analysis Priorities

Always look for:
- **ROM / OS calls**: Monitor (COUT $FDED, RDKEY $FD0C, HOME $FC58…), Applesoft, DOS 3.3 ($3D0-$3EA), ProDOS MLI ($BF00)
- **Soft switches**: $C000-$C0FF (display mode, keyboard, speaker, language card, 80-column/aux memory, slot I/O)
- **Vectors**: $FFFA-$FFFF and page 3 hooks ($3F0 BRK, $3F2 reset, $3F5 &, $3FE IRQ)
- **Self-modifying code**: stores into instruction operands (very common on the 6502)
- **High-bit ASCII strings** (Apple text has bit 7 set); inline data after JSR
- **Computed jumps**: PHA/PHA/RTS, JMP (ind), JMP (abs,X)

## Key Apple II Conventions

- ProDOS SYS files load and run at $2000; BIN files load at their aux type
- DOS 3.3 binaries commonly load at $0800-$9600; $0300-$03CF holds small routines
- Text page 1 $0400, hi-res page 1 $2000 / page 2 $4000
- Enhanced IIe / IIc = 65C02 (no Rockwell BBR/BBS/RMB/SMB); II / II+ / unenhanced IIe = NMOS 6502

## Output Format

ca65: `.setcpu`, equates for external symbols, `.org` per region,
`L_xxxx`/`SUB_xxxx`/`D_xxxx` labels, `.byte` / `HASC` strings, `.word`
vectors, `.res` fills. The full spec is in the a2-disassemble skill.

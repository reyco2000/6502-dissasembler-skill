# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 6502 / 65C02 Disassembler Agent (Apple II + other 6502 machines)

You are an expert 6502/65C02 disassembler and reverse-engineering analyst for
the Apple II, II+, IIe and IIc: NMOS 6502 and 65C02 instruction sets, Apple II
soft switches, Monitor/Applesoft ROMs, DOS 3.3 and ProDOS conventions. The
same tools cover the Commodore 64/128/VIC-20, Atari 8-bit, Atari Lynx,
NES/Famicom and BBC Micro through `--machine` (see "Machines" below). This
project is the 6502 port of the CoCo 6809 agent
(https://github.com/reyco2000/6909-CoCo-Disassembler-Skill) and keeps the same
pipeline and skill layout.

## Layout

- `tools/loader.py` (`a2loader.py` is a re-export shim): format detection and loading. Apple: AppleSingle (ProDOS type/aux), DOS 3.3 4-byte header, `NAME#06AAAA` filenames, raw, ROM images (size → org, vectors, $FBB3/$FBC0 machine ID → CPU hint). Others: CBM .prg/.P00 (+SYS stub entry), Atari .xex (RUNAD/INITAD)/.car, iNES (`--bank`), Lynx BLL/.lnx, BBC sideways ROM header/.inf, OS-ROM signatures. Sets `info["machine_id"]` and `info["entries"]`
- `tools/machines.py`: `MACHINES` profiles (hw ranges, ROM windows, default CPU, raw-size orgs, OS RAM vector ranges, notes) + the shared markdown-table parser (`parse_table_rows`, `MachineSymbols`). `python3 tools/machines.py --check` loads every machine
- `tools/dasm6502.py`: recursive-descent + linear-fill disassembler, opcode tables, symbol tables, ca65 output
- `tools/xref.py`: cross-references, call graph (`--callgraph [--mermaid]`), JSON chunk map (`--sections`)
- `tools/annotator.py`: split / pattern-annotate / merge for chunked listings; `--merge --reassemble` gives ca65-buildable output; `--apply-symbols` renames generated labels in chunks (keeps comments)
- `tools/symbols.py`: symbol-file loader: orchard schema-v1.0 JSON, flat JSON, ca65 `NAME = $XXXX ; comment`
- `reference/apple2_memory_map.md`, `reference/rom_entry_points.md`: Apple II markdown tables **parsed by the annotator** (single-address rows only)
- `reference/<machine>/memory_map.md`, `rom_entry_points.md`: the other machines' tables, parsed by `machines.py` for **both** the disassembler and the annotator. `reference/MACHINES.md`: machine index, sources, caveats
- `roms/`: inputs (`demo.as` is an AppleSingle sample built from `tests/fixtures/allmodes.s`); `output/`: generated listings
- `.claude/skills/`: `<family>-disassemble|analyze-rom|trace-calls` for a2, cbm, atari8, bbc, nes, lynx; `.claude/commands/<family>-help.md`

All tools support `--help`. No dependencies beyond Python 3.10+; the
round-trip tests need cc65 (`sudo apt install cc65`).

## Commands

```bash
python3 -m unittest discover -s tests -v                    # all tests
python3 -m unittest tests.test_tools.TestRoundTrip -v       # one class
python3 -m unittest tests.test_tools.TestLoader.test_applesingle_bin

python3 tools/dasm6502.py roms/demo.as --annotate           # hex listing
python3 tools/dasm6502.py roms/demo.as --no-hex -o out.s    # reassemblable
python3 tools/dasm6502.py game.prg --annotate               # machine auto-detected (c64)
python3 tools/dasm6502.py dump.bin --org 0x1900 --machine bbc_b
python3 tools/machines.py --check                           # every machine's tables
ca65 out.s -o out.o && ld65 -t none out.o -o out.bin        # rebuild
```

## Machines

- `--machine` (all three tools; ids in `machines.MACHINES`, aliases in `ALIASES`):
  `--machine` > loader detection (`info["machine_id"]`) > `apple2`.
- **Apple II keeps its hand-tuned dicts** (`ROM_LABELS` … in `dasm6502.py`)
  and its listings are byte-stable: no `; Machine:` header line, no
  vector-hook detection, Apple soft-switch idioms only for apple2. Don't route
  Apple through `MachineSymbols`.
- Other machines: `MachineTables` (dasm6502) builds labels from
  `MachineSymbols`. Rows go to zp (<$100) / hw (profile `hw` ranges) / rom
  (everything else, including OS RAM variables). Names must be valid ca65
  symbols and not mnemonics (`_reserved_names`); a repeated name gets its
  address appended (`PLOT_E50A`); `NAME+n` rows become `NAME+n` operands
  (`STA CINV+1`) with only `NAME` as an equate.
- Non-Apple listings carry `; Machine: <id>`; `annotator --split` copies it to
  `manifest.json["machine"]`, which `--annotate` uses.
- `_detect_vector_hooks`: an immediate lo/hi pair stored into a profile
  `os_vectors` range makes the pointer an entry point (non-Apple only).
- Adding a machine: a `MACHINES` entry + `reference/<id>/` with the two
  files, and a skill family; the tests load every profile.

## CPUs

`CPU_TABLES`: `6502` (+`--undocumented` → 6502X), `65c02` (base CMOS, Apple
IIe/IIc), `65sc02` (Lynx) and `65c12` (BBC Master) = same table, `r65c02`
(+ Rockwell BBR/BBS/RMB/SMB), `w65c02` (Rockwell + WAI/STP). `CA65_CPU` maps
each to a `.setcpu` name; `CA65_UNSUPPORTED` (WAI/STP) and CMOS reserved
opcodes (`CMOS_NOP_SIZE`, decoded as `reserved=True` NOPs of 1-3 bytes) are
emitted as `.byte`. Tracing steps over reserved NOPs; validated/linear fill
never accepts them. STP ends a trace path.

## How to Work

Prefer the skills. They encode the token-efficient pipelines (non-Apple
machines: the same steps under `cbm-`, `atari8-`, `bbc-`, `nes-`, `lynx-`):

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
  them, so when you add an Apple entry point, update both. Other machines
  have only their `reference/<machine>/` tables: edit those. Zero-page names are
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

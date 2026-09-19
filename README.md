# Apple II 6502 / 65C02 Disassembler — Code Agent

A Claude Code agent for 6502 and 65C02 disassembly and reverse engineering on
the Apple II, II+, IIe and IIc. It is the Apple II sibling of the
[CoCo 6809 Disassembler Skill](https://github.com/reyco2000/6909-CoCo-Disassembler-Skill).

## Quick Start

```bash
cd 6502-dissasembler
claude

/a2-disassemble roms/demo.as    # annotated ca65 disassembly
/a2-analyze-rom <rom file>      # ROM identity, vectors, subroutine map
/a2-trace-calls <file>          # call tree / Mermaid graph
/a2-help <topic>                # quick reference ("COUT", "language card", "MLI OPEN")
```

To use the skills in any directory, copy `.claude/skills/*` into `~/.claude/skills/`
and `.claude/commands/*` into `~/.claude/commands/`. The skills run the tools
from this project's directory.

Natural-language requests work too:
- *"Disassemble this ProDOS SYS file"*
- *"What soft switches does this game touch?"*
- *"Map the Autostart ROM from the RESET vector"*

## Inputs

| Input | How the load address is found |
|-------|-------------------------------|
| AppleSingle (CiderPress, AppleCommander `-as`, cc65) | ProDOS aux type (BIN), $2000 (SYS) |
| DOS 3.3 binary with its 4-byte header | header |
| `NAME#06AAAA` filenames (CiderPress style) | filename |
| ROM images | size (2K→$F800, 12K→$D000, 16K→$C000, 256B→$C600) + RESET vector |
| Raw dumps | `--org` |

Apple ROMs are copyrighted and not included. Put your own dumps in `roms/`.

## Tools

| Tool | Purpose |
|------|---------|
| `tools/a2loader.py` | Format detection, ROM identification (vectors, machine ID bytes, CPU hint) |
| `tools/dasm6502.py` | Recursive-descent disassembler: 6502, 65C02, Rockwell 65C02, NMOS undocumented |
| `tools/xref.py` | Cross-references, call graph (text / Mermaid), chunk map |
| `tools/annotator.py` | Split / pattern-annotate / merge chunked listings |

## What the Agent Knows

- Full NMOS 6502, 65C02 and Rockwell instruction sets, plus NMOS undocumented opcodes
- Apple II memory map: zero page (Monitor, Applesoft), page 3 vectors, text/hi-res pages
- Every soft switch in $C000-$C0FF, the language card, Disk II slot I/O, and IIe/IIc aux memory
- Monitor, Applesoft, DOS 3.3 and ProDOS MLI entry points (MLI calls decoded inline)
- Idioms: keyboard polling, speaker tones, display mode setup, LC double reads,
  self-modifying code, PHA/PHA/RTS dispatch, pointer fill/copy loops

## Coverage and Naming

- **Recursive descent plus a validated sweep.** Unreached bytes become code only
  when they follow real code and decode cleanly to RTS/JMP. `--fill all` gives the
  old linear decode.
- **Dispatch tables:** Applesoft and Monitor tables are recognized automatically,
  and JMP-vector and pointer tables are detected. Use `--table` for anything else.
- **`--symbols FILE`:** your own names, in [orchard](https://github.com/BrentRector/orchard)
  schema-v1.0 JSON (its `apple2.json` works as-is), flat JSON, or ca65 equates.
  `annotator.py --apply-symbols` applies new names to an annotated project
  without losing comments.
- **`--data-region START-END`:** forces bytes to stay data.

The validated sweep, the pointer-table rules, and the symbol file format follow the
orchard project's `disasm6502` (MIT, Brent Rector).

## Output

ca65 assembly. `--no-hex` output (or `annotator.py --merge --reassemble`)
rebuilds to identical bytes:

```bash
python3 tools/dasm6502.py roms/demo.as --no-hex -o demo.s
ca65 demo.s && ld65 -t none demo.o -o demo.bin
```

## Tests

```bash
sudo apt install cc65                       # for round-trip tests
python3 -m unittest discover -s tests -v
```

## License

MIT, built for the CoCoByte Club
by Reinaldo Torres (Chipshift) https://github.com/reyco2000

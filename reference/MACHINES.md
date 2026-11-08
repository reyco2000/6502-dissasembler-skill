# Additional Machine References (toadd)

Memory maps and ROM/OS entry point tables for 6502-family home computers, in the
same markdown-table format as `reference/apple2_memory_map.md` and
`reference/rom_entry_points.md`, so they can be dropped into `reference/` (or
loaded by a per-machine version of `tools/annotator.py`) without reformatting.

## Files

### Atari 8-bit family

| File | Machine | RAM | OS ROM window |
|------|---------|-----|---------------|
| `atari400_memory_map.md` / `atari400_rom_entry_points.md` | Atari 400 | 16K | $D800-$FFFF (10K) |
| `atari800_memory_map.md` / `atari800_rom_entry_points.md` | Atari 800 | 48K max | $D800-$FFFF (10K) |
| `atari1200xl_memory_map.md` / `atari1200xl_rom_entry_points.md` | Atari 1200XL | 64K | $C000-$FFFF (16K) |
| `atari600xl_memory_map.md` / `atari600xl_rom_entry_points.md` | Atari 600XL | 16K | $C000-$FFFF (16K) |
| `atari800xl_memory_map.md` / `atari800xl_rom_entry_points.md` | Atari 800XL | 64K | $C000-$FFFF (16K) |

### Commodore

| File | Machine |
|------|---------|
| `c64_memory_map.md` / `c64_rom_entry_points.md` | Commodore 64 (full KERNAL jump table with real addresses, BASIC ROM entries) |
| `c128_memory_map.md` / `c128_rom_entry_points.md` | Commodore 128 (MMU register set, jumbo jump table, BASIC 7.0 entries) |
| `vic20_memory_map.md` / `vic20_rom_entry_points.md` | VIC-20 (block map, KERNAL table with real addresses, BASIC 2.0 entries) |

### Consoles and handhelds

| File | Machine |
|------|---------|
| `atari_lynx_memory_map.md` / `atari_lynx_rom_entry_points.md` | Atari Lynx (65SC02, Suzy/Mikey, boot ROM and cart header) |
| `nes_memory_map.md` / `nes_rom_entry_points.md` | NES (CPU/PPU/APU maps, iNES header, mapper registers) |
| `famicom_memory_map.md` / `famicom_rom_entry_points.md` | Famicom (same core plus the $4016/$4017 and expansion differences) |

### Acorn BBC

| File | Machine | RAM | MOS |
|------|---------|-----|-----|
| `bbc_model_a_memory_map.md` / `bbc_model_a_rom_entry_points.md` | BBC Model A | 16K | 1.20 |
| `bbc_model_b_memory_map.md` / `bbc_model_b_rom_entry_points.md` | BBC Model B | 32K | 1.20 |
| `bbc_model_b_plus_memory_map.md` / `bbc_model_b_plus_rom_entry_points.md` | BBC Model B+ | 64K/128K | 2.00 |
| `bbc_master_128_memory_map.md` / `bbc_master_128_rom_entry_points.md` | BBC Master 128 | 128K | 3.20 |

## Format contract

Every file follows the same rules as the Apple II references:

- A table row is `| $XXXX | NAME | Description |` (or `| $XX | ... | ... |` for
  zero-page/command-code rows). Only single-address rows are machine-readable;
  range rows such as `| $D000-$D7FF | ... |` are documentation.
- No document repeats a single address, because the loader stores rows in a
  dict keyed by address and a second row would silently replace the first.
- Tables with a non-address first column (`| Field |`, `| Offset |`, `| Range |`,
  `| Mapper |`) are ignored by the parser by design.

## Parser profile per machine

`tools/annotator.py` has Apple II semantics baked in: 2-digit rows → zero page,
`$C000-$CFFF` → hardware, everything else → system variables. For these machines
a per-machine profile is needed:

| Machine | Zero page | Hardware window | Vectors |
|---------|-----------|-----------------|---------|
| Atari 8-bit | $00-$FF | $D000-$D7FF | $FFFA-$FFFF (+ page-2 shadow vectors) |
| C64 | $00-$FF | $D000-$DFFF | $FFFA-$FFFF |
| C128 | $00-$FF | $D000-$DFFF | $FFFA-$FFFF |
| VIC-20 | $00-$FF | $9000-$93FF (+ colour RAM $9400-$95FF) | $FFFA-$FFFF |
| Atari Lynx | $00-$FF | $FC00-$FDFF (+ $FFF9) | $FFFA-$FFFF |
| NES/Famicom | $00-$FF (no OS) | $2000-$2007, $4000-$4017 | $FFFA-$FFFF (in the cart) |
| BBC Model A/B/B+/Master | $00-$FF | $FC00-$FEFF | $FFFA-$FFFF |

The two-character check also matters: BBC OSBYTE/OSWORD numbers are written with
`&`, not `$`, so they are not mistaken for ProDOS MLI command codes.

## Sources

Every machine file ends with its own `## Sources` block; this is the consolidated
list, with what each page actually supplied. Only pages that were fetched and
used are listed. AtariArchives' "Mapping the Atari" appendix was tried first and
returned 403/404 on this run, so it is not cited and contributes no row — the
Atari map comes from the FAQ and the assembler equates instead.

### Atari 8-bit (all five models)

| Source | Supplied |
|--------|----------|
| https://mcurrent.name/atari-8-bit/faq.txt | RAM steps per model, the $C000-$FFFF detail table (OS vs unused vs floating point package), cartridge-slot rules, the per-model PORTB bit table, XE banking |
| https://atariwiki.org/wiki/Wiki.jsp?page=Memory%20Map | page 0 and page 2 variable names with the OS-A / XL column |
| https://atariwiki.org/wiki/Wiki.jsp?page=PORTB | 400/800 PORTA/PORTB joystick ports vs the XL PORTB memory bits, including the 1200XL LED and self-test bits |
| https://atariwiki.org/wiki/Wiki.jsp?page=Atari%20800%20Assembler%20Equates | cross-check of OS call names |
| https://raw.githubusercontent.com/cc65/cc65/master/asminc/atari.inc | OS jump table $E450-$E48F, floating point package $D800-$DFFF, page-2 vectors, zero page, PORTB/PDVS, the `##1200xl##` / `##rev2##` provenance tags that drive the per-model notes |
| https://raw.githubusercontent.com/cc65/cc65/master/asminc/atari_antic.inc | ANTIC register names and display-list opcodes |
| https://raw.githubusercontent.com/cc65/cc65/master/asminc/atari_gtia.inc | GTIA read/write register names |
| https://raw.githubusercontent.com/cc65/cc65/master/asminc/atari_pokey.inc | POKEY register names |

### Commodore

| Source | Supplied |
|--------|----------|
| https://sta.c64.org/cbm64mem.html | C64 map: zero page, page 2/3, $0288 screen pointer, $0334-$033B unused + cassette buffer at $033C, hardware vectors $FE43/$FCE2/$FF48 |
| https://sta.c64.org/cbm64krnfunc.html | KERNAL jump table with both the $FF81-$FFF3 entry and the real code address for every call |
| https://www.c64-wiki.com/wiki/BASIC-ROM | BASIC ROM labels and vectors ($A000 cold, $A002 warm, $A7AE, $AB1E, $AD9E, $A717) |
| https://codebase.c64.org/doku.php?id=base:asm_include_file_for_basic_routines | BASIC routine addresses and FP helpers ($B1AA, $B391, $BCCC, $BCF3, $BDCD, $BF71...) |
| https://www.c64-wiki.com/wiki/Commodore_128/Memory_Model | C128 MMU register set, CR bit layout, power-up address map, C64-mode entry |
| https://www.zimmers.net/anonftp/pub/cbm/maps/C128rom.txt | C128 ROM layout (BASIC 7.0 $4000-$AFFF, monitor $B000), jumbo jump table with targets, KERNAL entries, vectors $FF05/$FF3D/$FF17 |
| https://www.zimmers.net/anonftp/pub/cbm/maps/C128ram.txt | C128 zero page and page 2/3 (RAM helpers, links, editor tables) |
| https://c128lib.github.io/Reference/E000 | C128 KERNAL entry descriptions and the BOOT_CALL sector layout |
| https://gbppr.net/iirg/vic20-rom.html | VIC-20 ROM map, KERNAL jump table with real addresses, BASIC 2.0 labels, RESET $FD22 / IRQ $FF72 / NMI $FEA9 |
| https://sleepingelephant.com/denial/wiki/index.php/Memory_Map | VIC-20 8K block map, RAM/ROM/I-O placement |
| https://www.cbmitapages.it/vic20/vic20map.html | VIC-20 zero page and page 2 layout, screen page at $0288, BASIC start/top pointers, tape buffer pointer |
| https://raw.githubusercontent.com/cc65/cc65/master/asminc/c64.inc | VIC-II, SID, CIA and $01 banking equates, C64 zero-page names |
| https://raw.githubusercontent.com/cc65/cc65/master/asminc/c128.inc | VIC-IIe, VDC, MMU and CR value equates |
| https://raw.githubusercontent.com/cc65/cc65/master/asminc/vic20.inc | VIC 6560, both 6522 VIAs, colour RAM and zero-page names |

### Acorn BBC (Model A, B, B+, Master 128)

| Source | Supplied |
|--------|----------|
| http://mdfs.net/Docs/Comp/BBC/OS1-20/FC00 | FRED/JIM/SHEILA register map, the OS call table $FFB9-$FFF7 with real targets, extended vector table $FF00-$FF4E, OSBYTE &92/&94/&96 helpers, 6502 vectors $D9CD/$DC1C/$0D00 |
| https://mdfs.net/Docs/Comp/BBC/OS1-20/ | MOS 1.20 disassembly index; the chunk map behind the entry-point descriptions and the "other MOS entry points" table |
| http://mdfs.net/Docs/Comp/BBC/MemAddrs | address translation, workspace RAM overlays, hidden MOS ROM area |
| https://beebwiki.mdfs.net/Paged_ROM | ROM header at $8000/$8003, type byte, socket map, extended vector dispatch, service entry convention |
| https://kieranhj.github.io/llm-beeb-wiki/memory/memory-map | family map, MODE screen bases, per-machine extras (ANDY/HAZEL/LYNNE) |
| https://kieranhj.github.io/llm-beeb-wiki/memory/shadow-ram | ACCCON bit definitions on B+ (single S bit) and Master (D/E/X/Y/ITU/IFJ/TST/IRR) |
| https://kieranhj.github.io/llm-beeb-wiki/memory/os-workspace | page 2 OS vectors/variables, page 3 VDU workspace, extended vector base $0D9F |
| https://kieranhj.github.io/llm-beeb-wiki/memory/zero-page | zero-page allocation and the VDU $D0-$E1 block |
| https://kieranhj.github.io/llm-beeb-wiki/synthesis/model-differences | ROMSEL bit 7 (ANDY 4K vs B+ 12K paged RAM), Master second-32K workspace map, OSHWM shifts |
| https://acorn.huininga.nl/pub/docs/txtfiles/Master%20128.txt | Master sideways ROM list, ROMSEL/ACCCON bit names, Master workspace ranges |

Bare `mdfs.net` paths answer 301; fetch them with `curl -sL`.

### Atari Lynx

| Source | Supplied |
|--------|----------|
| http://monlynx.de/lynx/hardware.html | top-1K layout, MAPCTL bit definitions, Suzy sprite/math registers, Mikey timer/audio/interrupt/serial registers |
| https://gist.github.com/drhelius/30eb03724f510719cd9c51ca059fa727 | annotated boot ROM: code entry points $FE00/$FE19/$FE26/$FE3D/$FEAA/$FF80, the $0200 first stage, vectors NMI $3000 / RESET and IRQ $FF80, public key extent |
| https://forums.atariage.com/topic/191953-annotated-lynx-boot-rom | origin of the annotated boot-ROM listing (the gist copy is what was read) |
| https://atarilynxdeveloper.wordpress.com/2013/08/31/programming-tutorial-part-12memory-mapping | RAM/overlay orientation and the "hardware at $FC00 and up" model |
| https://raw.githubusercontent.com/cc65/cc65/master/asminc/lynx.inc | Suzy/Mikey register names, timer and audio bit definitions, MAPCTL and vector addresses |

### NES / Famicom

| Source | Supplied |
|--------|----------|
| https://www.nesdev.org/wiki/CPU_memory_map | CPU map, RAM mirrors, PPU/APU windows, cartridge space, vector locations |
| https://www.nesdev.org/wiki/PPU_registers | $2000-$2007 register types and bit fields, vblank flag, the $2005/$2006 write-pair reset, PPUDATA buffering and immediate palette reads |
| https://www.nesdev.org/wiki/APU_registers | $4000-$4017 bit fields for both pulses, triangle, noise, DMC and the status/IO registers |
| https://www.nesdev.org/wiki/INES | 16-byte header layout (bytes 0-15), flags 6/7, mapper-number extraction |
| https://www.nesdev.org/wiki/Mapper | iNES mapper grid and numbering (read through the Wayback copy; live page challenges a CLI agent) |
| https://www.nesdev.org/wiki/MMC1 | MMC1 register addresses, serial writes, 16K PRG / 4K CHR banks |
| https://www.nesdev.org/wiki/MMC3 | MMC3 register pairs at $8000/$A000/$C000/$E000 (even/odd), bank select/data, mirroring, IRQ latch/reload/enable |
| https://www.nesdev.org/wiki/UxROM | UxROM bank register |
| https://www.nesdev.org/wiki/CNROM | CNROM CHR bank register |
| https://www.nesdev.org/wiki/Standard_controller | $4016/$4017 bit layout: D0 primary pad, D1 expansion-port pad, D2 microphone ($4016 only); pad 2 on $4017 |
| https://www.nesdev.org/wiki/Controller_reading_code | 2-controller read loop, Famicom expansion-port handling, DPCM-safe reread |
| https://web.archive.org/web/2024/https://www.nesdev.org/wiki/Famicom | Famicom vs NES: hard-wired pads and microphone, 15-pin expansion port, cartridge audio path, 60-pin connector, no CIC (Wayback copy) |
| https://www.nesdev.org/wiki/FDS | Famicom Disk System register area and PRG RAM range |
| https://raw.githubusercontent.com/cc65/cc65/master/asminc/nes.inc | PPU/APU names cross-check |

## Verification performed

- `python3 -m unittest`-independent format check with the annotator's own table
  parser: 30 files, no duplicate single address, no short rows.
- Loaded each pair through the repo's real `tools.annotator.PatternAnnotator` in
  a temporary `reference/` directory: 15/15 machines load. Counts observed:
  c64 65 zp / 137 ROM, c128 47 / 172, vic20 49 / 86, atari* 103 / 51,
  bbc_* 37 / 68, atari_lynx 0 / 14, nes 1 / 5. `hw_regs = 0` everywhere outside
  the Apple II map is expected and is why the Tooling Profile exists.
- `6502-machine-reference-maps/scripts/validate_ref_tables.py --annotator
  <repo> toadd` reports "30 files, duplicate/short-row free: True" and
  "annotator loaded 15 machines".
- Every cited URL was re-requested with `curl -skL`: 35 answer 200 and 16 answer
  403/502 to a command-line agent — the twelve live nesdev pages, three
  atariwiki pages and the AtariAge thread. Eleven of the nesdev pages and all
  three atariwiki pages were read through the page extractor, the Mapper page
  through its Wayback copy, and the AtariAge row is labelled as the origin of
  the gist that was actually read. No citation is a guess: pages that could not
  be read are named in the caveats (AtariArchives' Mapping the Atari appendix,
  403/404) instead of being cited.

## Coverage and caveats

- Entry-point addresses come from the sources above. Where a value is model- or
  revision-dependent (for example the BBC 6502 vectors, which differ between
  MOS 1.20 and MOS 3.20, or the C128 BASIC warm-start link, which moved by three
  bytes between ROM revisions) the file says so instead of inventing a number.
- ROM binaries are not included. Load addresses for disassembly come from the
  machine profile tables and the ROM window column above.
- Atari 400/800 OS-A and OS-B share the $E400-$E48F region: handler vector
  tables at $E400-$E44F and the call table at $E450-$E48F. The entries marked
  "rev 2" exist only in the XL/XE OS.
- The C128's zero page is relocatable through MMU P0; the table documents the
  power-up layout.
- The c64-wiki and llm-beeb-wiki pages are secondary sources. Where they
  disagree with a listing (BBC page-2 vector spacing, C128 link targets), the
  listing wins and the file records the listing value.

# Nintendo Entertainment System (NES) Memory Map Reference

Tables with a single `$XX` / `$XXXX` in the first column are the rows a tool
like `tools/annotator.py` can parse: 2-digit rows are zero page, 4-digit rows are
either hardware registers or system vectors/variables. Range rows (`$XXXX-$YYYY`)
are documentation only. Keep one row per address — a second row for the same
address silently overwrites the first when the tables are loaded.

## Machine Profile

| Field | Value |
|-------|-------|
| CPU | Ricoh 2A03 (6502 core without decimal mode), 1.79 MHz (NTSC) / 1.66 MHz (PAL) |
| RAM | 2K internal at $0000-$07FF, mirrored to $1FFF |
| Video | Ricoh 2C02 PPU with 2K nametable RAM and 8K CHR (ROM or RAM) |
| Audio | 2 pulse, 1 triangle, 1 noise, 1 DMC channel |
| Cartridge | 72-pin NES cartridge with CIC lockout, PRG ROM mapped at $8000-$FFFF |

## CPU Address Map

| Range | Description |
|-------|-------------|
| $0000-$07FF | 2K internal RAM (mirrored every $0800 up to $1FFF) |
| $0000-$00FF | Zero page |
| $0100-$01FF | 6502 hardware stack |
| $0200-$02FF | Conventional OAM buffer (copied to the PPU by $4014 DMA) |
| $0300-$07FF | Free RAM |
| $0800-$1FFF | Mirrors of $0000-$07FF |
| $2000-$2007 | PPU registers |
| $2008-$3FFF | Mirrors of $2000-$2007, repeating every 8 bytes |
| $4000-$4013 | APU registers (detailed table below) |
| $4014-$4017 | OAMDMA, APU status, controller 1 and controller 2 (detailed table below) |
| $4018-$401F | Disabled APU/test registers (enable with the CPU test mode) |
| $4020-$5FFF | Cartridge expansion space (usually mapper registers) |
| $6000-$7FFF | Cartridge WRAM (battery-backed save RAM when present) |
| $8000-$FFFF | Cartridge PRG ROM (banked by the mapper) |

## PPU Address Space

| Range | Description |
|-------|-------------|
| $0000-$0FFF | Pattern table 0 (4K CHR) |
| $1000-$1FFF | Pattern table 1 (4K CHR) |
| $2000-$23BF | Nametable 0 (960 bytes + 64 bytes attribute at $23C0) |
| $2400-$27BF | Nametable 1 |
| $2800-$2BBF | Nametable 2 |
| $2C00-$2FBF | Nametable 3 |
| $3000-$3EFF | Mirrors of $2000-$2EFF depending on the mirroring mode |
| $3F00-$3F0F | Background palette (16 entries) |
| $3F10-$3F1F | Sprite palette (16 entries) |
| $3F20-$3FFF | Mirrors of the palette RAM |

## PPU Registers ($2000-$2007)

| Address | Name | Description |
|---------|------|-------------|
| $2000 | PPUCTRL | NMI enable, sprite size, background pattern base, increment, nametable |
| $2001 | PPUMASK | Rendering enables, left-column masks, greyscale, emphasis |
| $2002 | PPUSTATUS | Vblank, sprite 0 hit, sprite overflow (reading clears vblank) |
| $2003 | OAMADDR | OAM address for CPU access through $2004 |
| $2004 | OAMDATA | OAM data (read/write, increments OAMADDR) |
| $2005 | PPUSCROLL | Scroll X then Y (two writes) |
| $2006 | PPUADDR | VRAM address high then low (two writes) |
| $2007 | PPUDATA | VRAM data (buffered read; palette reads return immediately on 2C02G/H and PAL PPUs) |

Register 0 bit 7 enables NMI; bit 2 selects the VRAM increment (0 = +1,
1 = +32) and bits 0-1 select the base nametable. Register 2 bit 7 is the vblank
flag every NMI handler polls or relies on.

## APU and I/O Registers ($4000-$4017)

| Address | Name | Description |
|---------|------|-------------|
| $4000 | SQ1_VOL | Pulse 1 duty, envelope loop, constant volume, volume |
| $4001 | SQ1_SWEEP | Pulse 1 sweep enable, period, negate, shift |
| $4002 | SQ1_LO | Pulse 1 timer low |
| $4003 | SQ1_HI | Pulse 1 length counter load and timer high |
| $4004 | SQ2_VOL | Pulse 2 duty and volume |
| $4005 | SQ2_SWEEP | Pulse 2 sweep |
| $4006 | SQ2_LO | Pulse 2 timer low |
| $4007 | SQ2_HI | Pulse 2 length counter load and timer high |
| $4008 | TRI_LINEAR | Triangle linear counter control |
| $400A | TRI_LO | Triangle timer low |
| $400B | TRI_HI | Triangle length counter load and timer high |
| $400C | NOISE_VOL | Noise envelope and volume |
| $400E | NOISE_LO | Noise period |
| $400F | NOISE_HI | Noise length counter load |
| $4010 | DMC_FREQ | DMC IRQ enable, loop, rate index |
| $4011 | DMC_RAW | DMC direct 7-bit DAC load |
| $4012 | DMC_ADDR | DMC sample address ($C000 + A * 64) |
| $4013 | DMC_LEN | DMC sample length |
| $4014 | OAMDMA | Write page number: DMA 256 bytes from $XX00 to PPU OAM |
| $4015 | APU_STATUS | Read channel status / write channel enables |
| $4016 | JOY1 | Controller 1 read; write 1 then 0 to strobe both controllers |
| $4017 | JOY2 | Controller 2 read; write = APU frame counter |

## Zero Page and RAM Conventions

There is no operating system: the 2K at $0000-$07FF belongs to the program. The
6502 forces two page usages, one convention is worth keeping:

| Address | Name | Description |
|---------|------|-------------|
| $0000 | ZP_BASE | Free zero page, 256 bytes |
| $0100 | STACK | Hardware stack (descends from $01FF) |
| $0200 | OAMBUF | Conventional shadow OAM, 256 bytes ($0200-$02FF) |
| $0300 | RAM_FREE | Free RAM ($0300-$07FF) |

Nintendo's own example code and most tutorials keep $00-$0F for NMI scratch,
$10-$1F for general variables and $20-$2F for sprite/scroll state, but nothing
in the hardware requires it. `$0200` is the usual OAM shadow because `$4014`
needs a page-aligned source.

## 6502 Hardware Vectors

| Address | Name | Description |
|---------|------|-------------|
| $FFFA | NMI | NMI vector — points at the vblank handler in the fixed bank |
| $FFFC | RESET | RESET vector — points at the initialisation code |
| $FFFE | IRQ | IRQ/BRK vector — points at the mapper or APU interrupt handler |

## Cartridge Space and Mappers

| Range | Description |
|-------|-------------|
| $4020-$5FFF | Expansion area — mapper registers, expansion audio, FDS |
| $6000-$7FFF | Cartridge WRAM / battery save RAM |
| $8000-$BFFF | Switchable PRG bank (mapper-dependent) |
| $C000-$FFFF | Fixed or switchable PRG bank containing the vectors |

The vectors at $FFFA-$FFFF must be present in whichever bank is mapped at
$C000-$FFFF, so most mappers fix the last 16K or 32K bank there.

| Mapper | Name | Description |
|--------|------|-------------|
| 0 | NROM | No banking: 16K or 32K PRG, 8K CHR |
| 1 | MMC1 | Serial-port banking, 16K PRG banks, CHR banking, WRAM |
| 2 | UxROM | 16K switchable low bank, fixed high bank, CHR RAM |
| 3 | CNROM | Fixed PRG, switchable 8K CHR |
| 4 | MMC3 | 8K PRG banking, CHR banking, scanline IRQ |
| 5 | MMC5 | 8K PRG banking, expansion audio, extra nametables |
| 7 | AxROM | 32K PRG banks, single-screen mirroring |

## Tooling Profile

| Field | Value |
|-------|-------|
| CPU | Ricoh 2A03 (NMOS 6502 core, decimal mode disabled), 1.79 MHz NTSC |
| zero_page | $0000-$00FF (no OS convention) |
| hardware | $2000-$2007 PPU, $4000-$4017 APU/IO |
| vectors | $FFFA-$FFFF in the cartridge's fixed bank |
| ROM window | $8000-$FFFF PRG (mapped by the cartridge) |

## Notes

- Writes to $2000-$2007 go to the PPU; reads of $2002/$2004/$2007 come back on
  the CPU data bus and also have side effects (vblank clear, OAM increment,
  VRAM buffer fill).
- The PPU has its own address space: CPU code reaches it only through
  PPUDATA/PPUADDR, and character/nametable memory is invisible to the 6502.
- Sprite DMA ($4014) copies 256 bytes from a page in CPU RAM to OAM during the
  next CPU cycle stretch and is the normal way to update sprites.
- Controller reads are serial: write 1 then 0 to $4016, then read 8 bits from
  $4016 (pad 1) or $4017 (pad 2), bit 0 first.
- Decimal mode is disabled on the 2A03; `SED` has no effect.

## Sources

- https://www.nesdev.org/wiki/CPU_memory_map
- https://www.nesdev.org/wiki/PPU_registers
- https://www.nesdev.org/wiki/APU_registers
- https://www.nesdev.org/wiki/INES
- https://www.nesdev.org/wiki/Mapper
- cc65 `asminc/nes.inc`

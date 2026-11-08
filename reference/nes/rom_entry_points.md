# Nintendo Entertainment System (NES) ROM / Cartridge Entry Points Reference

There is no firmware to call: the cartridge contains all code, and the CPU
vector table in its fixed bank is the only fixed entry contract.

## Machine Profile

| Field | Value |
|-------|-------|
| Machine | Nintendo Entertainment System |
| Cartridge | 72-pin, CIC lockout, PRG ROM at $8000-$FFFF |
| Controllers | Two ports, read through $4016 and $4017 |
| Expansion audio | None — cartridges cannot add sound channels |

## Reset, NMI and IRQ Entry Points

| Address | Name | Description |
|---------|------|-------------|
| $FFFA | NMI_VECTOR | NMI vector — vblank handler, the main per-frame entry |
| $FFFC | RESET_VECTOR | RESET vector — first code executed at power-up/reset |
| $FFFE | IRQ_VECTOR | IRQ/BRK vector — mapper IRQ (MMC3 scanline, FDS, VRC) or APU |
| $8000 | PRG_BASE | Base of the switchable PRG window (every mapper, every bank) |
| $C000 | PRG_FIXED | Base of the fixed bank that holds the vectors on 16K-bank mappers |

The vectors live in the PRG bank mapped at $FFFA-$FFFF, so a mapper must keep a
bank with valid vectors fixed at $C000-$FFFF (or copy a stub into every bank).

Typical reset code, in order: disable NMI and rendering (`$2000 = 0`,
`$2001 = 0`), disable DMC IRQ and APU channels, wait two vblanks by polling
`$2002` bit 7, clear $0000-$07FF and the palette, load the palette and nametables
during vblank, then enable NMI and rendering. The first NMI is the earliest
point at which PPU writes are safe.

## iNES File Header (16 bytes)

| Offset | Name | Description |
|--------|------|-------------|
| 0-3 | MAGIC | "NES" followed by $1A |
| 4 | PRG_BANKS | PRG ROM size in 16K units |
| 5 | CHR_BANKS | CHR ROM size in 8K units (0 = CHR RAM) |
| 6 | FLAGS6 | Mirroring (bit 0), battery (1), trainer (2), four-screen (3), mapper low nybble (4-7) |
| 7 | FLAGS7 | Console type (0-1), NES 2.0 marker (2), mapper high nybble (4-7) |
| 8 | PRG_RAM | Flags 8 — PRG RAM size in 8K units (rarely used extension) |
| 9 | TV_SYSTEM | Flags 9 — TV system (rarely used extension) |
| 10 | FLAGS10 | Flags 10 — TV system / PRG-RAM presence (unofficial, rarely used) |
| 11-15 | PADDING | Unused; some rippers put their name here |

Mapper number = (FLAGS7 & $F0) | (FLAGS6 >> 4).

## Mapper Register Entry Points

| Range | Name | Description |
|-------|------|-------------|
| $8000-$FFFF | UxROM_BANK | UxROM: write a 16K bank number to switch $8000-$BFFF |
| $8000-$FFFF | CNROM_BANK | CNROM: write an 8K CHR bank number |
| $8000-$FFFF | MMC1_SERIAL | MMC1: five serial writes (bit 0 data, bit 7 reset) |
| $8000-$9FFF | MMC3_SELECT | MMC3: bank select (bits 0-2 slot, bit 6 PRG mode, bit 7 CHR mode) |
| $A000-$BFFF | MMC3_BANKDATA | MMC3: bank data for the selected slot |
| $A000-$BFFF | MMC1_CHR0 | MMC1: CHR bank 0 |
| $C000-$DFFF | MMC1_CHR1 | MMC1: CHR bank 1 |
| $C000-$DFFF | MMC3_MIRROR | MMC3: mirroring and PRG RAM protect |
| $C000-$DFFF | MMC3_IRQLATCH | MMC3: IRQ counter reload value |
| $E000-$FFFF | MMC1_PRG | MMC1: PRG bank |
| $E000-$FFFF | MMC3_IRQRELOAD | MMC3: reload the IRQ counter |
| $E000-$FFFF | MMC3_IRQDISABLE | MMC3: enable/disable the scanline IRQ |

NROM has no registers — the whole 16K/32K PRG ROM is mapped permanently.
Exact bit layouts differ per mapper; these are the addresses a disassembler
will see written from initialisation code.

## APU / PPU Initialisation Order

1. `$4015 = $00` — silence all channels.
2. `$4010 = $00` — stop DMC IRQ.
3. Wait two vblanks (`BIT $2002` until bit 7 sets, twice) so the PPU warm-up is
   complete.
4. `$2000 = $00`, `$2001 = $00` — NMI and rendering off while loading.
5. Load palette via `$2006/$2007`, then nametables, then CHR if CHR RAM.
6. `$4014 = $02` — copy the OAM shadow at $0200.
7. `$2000 = $80`, `$2001 = $1E` — NMI on, background and sprites visible.
8. `$4015 = $0F` — enable the four APU channels when sound is wanted.

## Calling Conventions Worth Knowing

- **NMI ($FFFA)**: set PPUCTRL bit 7. The handler must not exceed vblank or
  writes land during rendering; keep the hot path to OAM DMA, scroll writes and
  a music tick.
- **PPUDATA ($2007)**: after setting PPUADDR, reads are buffered by one byte
  (the first read returns stale data). Palette reads bypass the buffer.
- **OAMDMA ($4014)**: source must be a page-aligned address; the CPU stalls for
  513/514 cycles.
- **PPUSCROLL ($2005)**: two writes, X then Y; the write toggle is shared with
  PPUADDR, so a stray write desynchronises both.
- **Controller strobe ($4016)**: write 1 then 0, then read 8 times; reads return
  bit 0 = A, then B, Select, Start, Up, Down, Left, Right.

## Common NES Idioms

### Wait for vblank without NMI
```
WAIT    BIT $2002        ; PPUSTATUS
        BPL WAIT         ; loop while bit 7 clear
```

### Copy the OAM shadow
```
        LDA #$02
        STA $4014        ; DMA $0200-$02FF to OAM
```

### Read controller 1
```
        LDA #1
        STA $4016
        LDA #0
        STA $4016        ; strobe
        LDX #8
READ    LDA $4016
        LSR A
        ROL BUTTONS
        DEX
        BNE READ
```

### Set the VRAM address
```
        LDA #$3F
        STA $2006
        LDA #$00
        STA $2006        ; PPUADDR = $3F00 (palette)
```

### Enable NMI and rendering
```
        LDA #$80
        STA $2000        ; NMI on, background pattern table 0
        LDA #$1E
        STA $2001        ; show background and sprites
```

## Sources

- https://www.nesdev.org/wiki/CPU_memory_map
- https://www.nesdev.org/wiki/PPU_registers
- https://www.nesdev.org/wiki/APU_registers
- https://www.nesdev.org/wiki/INES
- https://www.nesdev.org/wiki/MMC1
- https://www.nesdev.org/wiki/MMC3
- https://www.nesdev.org/wiki/UxROM
- https://www.nesdev.org/wiki/CNROM
- cc65 `asminc/nes.inc`



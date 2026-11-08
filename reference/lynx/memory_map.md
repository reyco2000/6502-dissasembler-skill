# Atari Lynx Memory Map Reference

Tables with a single `$XX` / `$XXXX` in the first column are the rows a tool
like `tools/annotator.py` can parse: 2-digit rows are zero page, 4-digit rows are
either hardware registers or system vectors/variables. Range rows (`$XXXX-$YYYY`)
are documentation only. Keep one row per address — a second row for the same
address silently overwrites the first when the tables are loaded.

The Lynx is a 65SC02 (65C02 without the Rockwell bit instructions) at up to
4 MHz with 64K of DRAM. All 64K is RAM physically; the top 1K is overlaid by
Suzy, Mikey, the cartridge ROM window and the vector block, and the overlay is
controlled by MAPCTL at $FFF9.

## Overview

| Range | Description |
|-------|-------------|
| $0000-$00FF | Zero page (free for the program) |
| $0100-$01FF | 6502 hardware stack |
| $0200-$FBFF | 64K RAM (minus the top 1K overlay); boot RAM at $0200 |
| $FC00-$FCFF | Suzy (sprite engine, math, cartridge I/O, switches) |
| $FD00-$FDFF | Mikey (timers, audio, interrupts, video, serial) |
| $FE00-$FFF7 | Cartridge ROM window (sequential access, 504 bytes) |
| $FFF8 | Reserved RAM |
| $FFF9 | MAPCTL — memory map control register |
| $FFFA-$FFFF | NMI, RESET and IRQ vectors (RAM or boot ROM) |

The boot ROM lives at $FE00-$FFF7 with its vectors at $FFFA-$FFFF. On power-up
MAPCTL is 0, so $FC00-$FFF7 is hardware/ROM and the vectors come from the boot
ROM; the boot ROM then maps RAM under Mikey/ROM and under the vectors.

## MAPCTL ($FFF9)

| Address | Name | Description |
|---------|------|-------------|
| $FFF9 | MAPCTL | Memory map control: bit 0 Suzy, bit 1 Mikey, bit 2 ROM, bit 3 vectors; 1 = RAM instead of hardware/ROM |

Bit 7 (sequential disable) forces full 5-tick cycles; bits 6-4 are reserved.
Bits 3-0 are zero at reset.

## Suzy ($FC00-$FCFF)

| Address | Name | Description |
|---------|------|-------------|
| $FC00 | TMPADRL | Sprite temporary address lo |
| $FC02 | TILTACUML | Tilt accumulator lo |
| $FC04 | HOFFL | Horizontal screen offset lo |
| $FC06 | VOFFL | Vertical screen offset lo |
| $FC08 | VIDBASL | Video build buffer base lo |
| $FC0A | COLLBASL | Collision build buffer base lo |
| $FC0C | VIDADRL | Current video build address lo |
| $FC0E | COLLADRL | Current collision build address lo |
| $FC10 | SCBNEXTL | Address of next sprite control block lo |
| $FC12 | SPRDLINEL | Start of sprite data line lo |
| $FC14 | HPOSSTRTL | Sprite start X lo |
| $FC16 | VPOSSTRTL | Sprite start Y lo |
| $FC18 | SPRHSIZL | Sprite horizontal size lo |
| $FC1A | SPRVSIZL | Sprite vertical size lo |
| $FC1C | STRETCHL | Horizontal size adder lo |
| $FC1E | TILTL | Horizontal position adder lo |
| $FC20 | SPRDOFFL | Offset to next sprite data line lo |
| $FC22 | SPRVPOSL | Current sprite Y lo |
| $FC24 | COLLOFFL | Collision depository offset lo |
| $FC26 | VSIZACUML | Vertical size accumulator lo |
| $FC28 | HSIZOFFL | Horizontal size offset lo |
| $FC2A | VSIZOFFL | Vertical size offset lo |
| $FC2C | SCBADRL | Address of current sprite control block lo |
| $FC2E | PROCADRL | Current sprite data processing address lo |
| $FC52 | MATHD | Math result D |
| $FC53 | MATHC | Math result C |
| $FC54 | MATHB | Math operand B |
| $FC55 | MATHA | Math operand A |
| $FC56 | MATHP | Math result P (multiply/divide) |
| $FC57 | MATHN | Math result N |
| $FC60 | MATHH | Math result H |
| $FC61 | MATHG | Math result G |
| $FC62 | MATHF | Math result F |
| $FC63 | MATHE | Math result E |
| $FC6C | MATHM | Math result M |
| $FC6D | MATHL | Math result L |
| $FC6E | MATHK | Math result K |
| $FC6F | MATHJ | Math result J |
| $FC80 | SPRCTL0 | Sprite control 0: bits/pixel, flips, sprite type |
| $FC81 | SPRCTL1 | Sprite control 1: literal, reload, palette, direction |
| $FC82 | SPRCOLL | Sprite collision number |
| $FC83 | SPRINIT | Sprite initialisation (set to $F3 after 100 ms) |
| $FC88 | SUZYHREV | Suzy hardware revision (reads $01) |
| $FC89 | SUZYSREV | Suzy software revision |
| $FC90 | SUZYBUSEN | Suzy bus enable (bit 0) |
| $FC91 | SPRGO | Sprite process start (bit 0), everon detect (bit 2) |
| $FC92 | SPRSYS | System control / status (signed math, accumulate, collisions) |
| $FCB0 | JOYSTICK | Joystick and option buttons (read) |
| $FCB1 | SWITCHES | Pause, cartridge I/O inactive flags (read) |
| $FCB2 | RCART0 | Read/write cart byte, CART0 strobe |
| $FCB3 | RCART1 | Read/write cart byte, CART1 strobe |
| $FCC0 | LEDS | LED control, 0 = on |
| $FCC2 | PARSTATUS | Parallel port status |
| $FCC3 | PARDATA | Parallel port data |
| $FCC4 | HOWIE | Howie register |

Suzy's sprite control block registers $FC00-$FC2F are also accessible as a
32-byte DMA/SCB block; the sprite engine reads them from a control block in RAM.

## Mikey ($FD00-$FDFF)

| Address | Name | Description |
|---------|------|-------------|
| $FD00 | TIM0BKUP | Timer 0 (horizontal line) backup value |
| $FD01 | TIM0CTLA | Timer 0 control A (interrupt, reload, count, clock) |
| $FD02 | TIM0CNT | Timer 0 counter (read) |
| $FD03 | TIM0CTLB | Timer 0 control B (borrow/last clock) |
| $FD04 | TIM1BKUP | Timer 1 backup value |
| $FD05 | TIM1CTLA | Timer 1 control A |
| $FD08 | TIM2BKUP | Timer 2 (vertical blank) backup value |
| $FD09 | TIM2CTLA | Timer 2 control A |
| $FD0C | TIM3BKUP | Timer 3 backup value |
| $FD0D | TIM3CTLA | Timer 3 control A |
| $FD10 | TIM4BKUP | Timer 4 (serial) backup value |
| $FD11 | TIM4CTLA | Timer 4 control A |
| $FD14 | TIM5BKUP | Timer 5 backup value |
| $FD15 | TIM5CTLA | Timer 5 control A |
| $FD18 | TIM6BKUP | Timer 6 backup value |
| $FD19 | TIM6CTLA | Timer 6 control A |
| $FD1C | TIM7BKUP | Timer 7 (audio) backup value |
| $FD1D | TIM7CTLA | Timer 7 control A |
| $FD20 | AUD0VOL | Audio channel 0 volume |
| $FD21 | AUD0FEED | Audio channel 0 feedback taps |
| $FD22 | AUD0OUT | Audio channel 0 output (read) |
| $FD23 | AUD0SHIFT | Audio channel 0 shift register |
| $FD24 | AUD0BKUP | Audio channel 0 backup |
| $FD25 | AUD0CTLA | Audio channel 0 control A |
| $FD26 | AUD0CNT | Audio channel 0 counter |
| $FD27 | AUD0CTLB | Audio channel 0 control B |
| $FD28 | AUD1VOL | Audio channel 1 volume |
| $FD30 | AUD2VOL | Audio channel 2 volume |
| $FD38 | AUD3VOL | Audio channel 3 volume |
| $FD40 | ATTENREG0 | Stereo attenuation channel 0 (if fitted) |
| $FD44 | MPAN | Stereo panning |
| $FD50 | MSTEREO | Stereo master enable |
| $FD80 | INTRST | Interrupt reset (write 1 to clear, read mask) |
| $FD81 | INTSET | Interrupt set (write 1 to enable) |
| $FD84 | MAGRDY0 | Magnetic/eeprom ready 0 |
| $FD85 | MAGRDY1 | Magnetic/eeprom ready 1 |
| $FD86 | AUDIN | Audio input from cartridge (read) |
| $FD87 | SYSCTL1 | System control: cartridge address strobe, power |
| $FD88 | MIKEYHREV | Mikey hardware revision |
| $FD89 | MIKEYSREV | Mikey software revision |
| $FD8A | IODIR | I/O direction |
| $FD8B | IODAT | I/O data (cart address data, power, no-expansion) |
| $FD8C | SERCTL | Serial control/status |
| $FD8D | SERDAT | Serial data |
| $FD90 | SDONEACK | Suzy done acknowledge |
| $FD91 | CPUSLEEP | CPU bus request / sleep |
| $FD92 | DISPCTL | Display control (colour, 4-bit, flip, DMA enable) |
| $FD93 | PBKUP | Palette backup |
| $FD94 | DISPADRL | Display address lo |
| $FD95 | DISPADRH | Display address hi |
| $FDA0 | PALETTE | 16-entry 12-bit palette (green nibbles) |
| $FDB0 | PALETTE_RB | 16-entry palette (red/blue nibbles) |

## 65SC02 Hardware Vectors

| Address | Name | Description |
|---------|------|-------------|
| $FFFA | NMIVEC | NMI vector — boot ROM value $3000 |
| $FFFC | RESETVEC | RESET vector — boot ROM value $FF80 |
| $FFFE | IRQVEC | IRQ/BRK vector — boot ROM value $FF80 |

## Cartridge Access and the Top 1K

- The cartridge is not mapped into the address space as a whole. The CPU reads
  it one byte at a time through Suzy ($FCB2/$FCB3 with the CART0/CART1 strobe)
  or through the ROM window at $FE00-$FFF7; an internal address counter advances
  on every read. MIKEY SYSCTL1 bit 0 strokes the counter and IODAT bit 1 feeds
  address data for banked (>512K) carts.
- The boot ROM reads the first block, RSA-decrypts it and writes the plaintext
  to $0200, then `JMP $0200`. So cart image offset 0 is the byte that ends up at
  $0200, and the decrypted block begins with the 64-byte "LYNX" header:
  offset 0 = "LYNX", offset 4 = version, offset 8 = cart name (32 bytes),
  offset 40 = manufacturer (16 bytes).
- The boot ROM's very first cart byte is the two's complement of the number of
  encrypted blocks in the first frame (0 = one block of 51 bytes).
- Everything above the first stage is loaded by the program itself (usually via
  Suzy sprite/DMA or a hand-written loader), because there is no full-cart
  window.

## Tooling Profile

| Field | Value |
|-------|-------|
| CPU | 65SC02 (65C02 core, no BBR/BBS/RMB/SMB), 2-4 MHz |
| zero_page | $0000-$00FF |
| hardware | $FC00-$FDFF, MAPCTL $FFF9 |
| vectors | $FFFA-$FFFF (RAM once MAPCTL bit 3 = 1) |
| ROM window | $FE00-$FFF7 (cartridge, sequential) |

## Sources

- http://monlynx.de/lynx/hardware.html (address ranges, MAPCTL, Suzy/Mikey registers)
- https://gist.github.com/drhelius/30eb03724f510719cd9c51ca059fa727 (annotated boot ROM)
- cc65 `asminc/lynx.inc`
- https://atarilynxdeveloper.wordpress.com/2013/08/31/programming-tutorial-part-12memory-mapping

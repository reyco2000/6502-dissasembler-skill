# Commodore 128 Memory Map Reference

Tables with a single `$XX` / `$XXXX` in the first column are the rows a tool
like `tools/annotator.py` can parse: 2-digit rows are zero page, 4-digit rows are
either hardware registers or system vectors/variables. Range rows (`$XXXX-$YYYY`)
are documentation only. Keep one row per address — a second row for the same
address silently overwrites the first when the tables are loaded.

The C128 exposes 128K of RAM to a 6510-class 8502 through a MOS 8722 MMU. Only
64K is visible at a time; the MMU rewrites address lines A16-A19 on the fly. The
machine boots on its Z80, which checks the cartridge lines and then hands the bus
to the 8502 in C128 mode (or C64 mode for legacy cartridges).

## Overview — C128 mode, power-up configuration

| Range | Description |
|-------|-------------|
| $0000-$03FF | Common RAM, always bank 0 (zero page, stack, page 2/3) |
| $0400-$3FFF | RAM, selected bank (bank 0 at power-up) |
| $4000-$7FFF | BASIC 7.0 low ROM (16K, U33) |
| $8000-$AFFF | BASIC 7.0 high ROM (12K, U34) |
| $B000-$BFFF | Machine language monitor ROM |
| $C000-$CFFF | Editor ROM (4K, U35) — CINT, KEY, PLOT, 40/80 swap |
| $D000-$DFFF | I/O (VIC-IIe, SID, MMU, VDC, colour RAM, CIAs) |
| $E000-$FFFF | KERNAL ROM (8K, U35) — includes $FF00-$FF04 MMU shadow |

The four 16K windows ($0000, $4000, $8000, $C000) are each independently
mapped to system ROM, internal function ROM, external function ROM or RAM by
the CR bits. $D000-$DFFF is I/O or character ROM depending on CR bit 0.

## Zero Page — BASIC 7.0 and KERNAL

| Address | Name | Description |
|---------|------|-------------|
| $00 | D6510 | 8502 data direction register |
| $01 | R6510 | 8502 port (same banking bits as C64) |
| $02 | BANK | Bank number for the next SYS/JMP FAR |
| $03 | SYSADDR | SYS target address hi |
| $04 | SYSADDR+1 | SYS target address lo |
| $05 | SR_TEMP | Saved status register for SYS |
| $06 | AC_TEMP | Saved A for SYS |
| $07 | XR_TEMP | Saved X for SYS |
| $08 | YR_TEMP | Saved Y for SYS |
| $09 | SP_TEMP | Saved stack pointer for SYS |
| $2D | TXTTAB | Start of BASIC text lo (bank 0) |
| $2E | TXTTAB+1 | Start of BASIC text hi |
| $2F | VARTAB | Start of BASIC variables lo (bank 1) |
| $30 | VARTAB+1 | Start of BASIC variables hi |
| $39 | MEMSIZ | Limit of BASIC memory lo (bank 1) |
| $3A | MEMSIZ+1 | Limit of BASIC memory hi |
| $3D | TXTPTR | BASIC work pointer / CHRGET operand |
| $3E | TXTPTR+1 | BASIC work pointer hi |
| $56 | FUNJVEC | Jump vector for functions |
| $60 | MLM0 | Monitor MLM address 0 (3 bytes) |
| $63 | MLM1 | Monitor MLM address 1 (3 bytes) |
| $66 | MLM2 | Monitor MLM address 2 (3 bytes) |
| $90 | STATUS | KERNAL I/O status (ST) |
| $A0 | TIME | Jiffy clock lo (60 Hz) |
| $A1 | TIME+1 | Jiffy clock mid |
| $A2 | TIME+2 | Jiffy clock hi |
| $B7 | FNLEN | Filename length |
| $B9 | SECADR | Secondary address |
| $BA | DEVNUM | Device number |
| $BB | FNADR | Filename pointer lo |
| $BC | FNADR+1 | Filename pointer hi |
| $C7 | FNADR_BANK | Bank holding the filename |
| $D0 | KEY_COUNT | Characters in the keyboard buffer |
| $D1 | FKEY_COUNT | Characters queued for a function key |
| $D7 | MODE | 40/80 column mode (bit 7 = 80 columns) |
| $D8 | GRAPHM | Graphics mode flags (bits 5-7) |
| $D9 | CHARDIS | Shadow of the $01 character-set bit |
| $E0 | SCREEN_PTR | Pointer to current screen line lo |
| $E1 | SCREEN_PTR+1 | Pointer hi |
| $E2 | CRAM_PTR | Pointer to colour memory lo |
| $E3 | CRAM_PTR+1 | Pointer hi |
| $EB | CURS_Y | Cursor row |
| $EC | CURS_X | Cursor column |
| $F1 | CHARCOLOR | Current character colour |
| $F3 | RVS | Reverse output flag |
| $F8 | SCROLL | Scrolling disabled flag |
| $FF | BASIC_SCRATCH | BASIC scratch byte |

## Page 2/3 — RAM Helpers, Vectors, Tables

| Address | Name | Description |
|---------|------|-------------|
| $0200 | BUF | BASIC/monitor input buffer ($0200-$02A1) |
| $02A2 | PEPEEK | Bank peek subroutine (RAM) |
| $02AF | PEPOKE | Bank poke subroutine (RAM) |
| $02BE | PECMP | Bank compare subroutine (RAM) |
| $02CD | JSRFAR | JSR to another bank (RAM) |
| $02E3 | JMPFAR | JMP to another bank (RAM) |
| $02FC | FEXEC | Function execute hook |
| $0300 | IERROR | BASIC error message link (JMP) |
| $0302 | IMAIN | BASIC warm start link (JMP) |
| $0304 | ICRNCH | Tokenise link (JMP) |
| $0306 | IQPLOP | Print tokens link (JMP) |
| $0308 | IGONE | Start new BASIC code link (JMP) |
| $030A | IEVAL | Get arithmetic element link (JMP) |
| $030C | ICRNCH_FE | Crunch $FE prefix hook (JMP) |
| $030E | IQPLOP_FE | List $FE prefix hook (JMP) |
| $0310 | IGONE_FE | Execute $FE prefix hook (JMP) |
| $0314 | CINV | IRQ vector lo (default $FA65) |
| $0315 | CINV+1 | IRQ vector hi |
| $0316 | CBINV | BRK vector lo (default $B003) |
| $0317 | CBINV+1 | BRK vector hi |
| $0318 | NMINV | NMI vector lo (default $FA40) |
| $031A | IOPEN | OPEN vector lo ($EFBD) |
| $031C | ICLOSE | CLOSE vector lo ($F188) |
| $031E | ICHKIN | CHKIN vector lo ($F106) |
| $0320 | ICHKOUT | CHKOUT vector lo ($F14C) |
| $0322 | ICLRCH | CLRCHN vector lo ($F226) |
| $0324 | IBASIN | CHRIN vector lo ($EF06) |
| $0326 | IBSOUT | CHROUT vector lo ($EF79) |
| $0328 | ISTOP | STOP vector lo ($F66E) |
| $032A | IGETIN | GETIN vector lo ($EEEB) |
| $032C | ICLALL | CLALL vector lo ($F222) |
| $032E | MLMLINK | Machine language monitor link ($B006) |
| $0330 | ILOAD | LOAD link ($F26C) |
| $0332 | ISAVE | SAVE link ($F54E) |
| $0334 | IPRINT_CTRL | Print control-code link ($C7B9) |
| $0336 | IPRINT_HI | Print high-ASCII link ($C805) |
| $0338 | IPRINT_ESC | Print ESC-sequence link ($C9C1) |
| $033A | IKEYSCAN | Keyscan link ($C5E1) |
| $033C | ISTOREKEY | Store key link ($C6AD) |
| $033E | KBDTAB | Unshifted keyboard table pointer ($FA80) |
| $0340 | KBDTAB_SHIFT | Shifted keyboard table pointer ($FAD9) |
| $0342 | KBDTAB_CBM | Commodore keyboard table pointer ($FB32) |
| $0344 | KBDTAB_CTRL | Control keyboard table pointer ($FB8B) |
| $0346 | KBDTAB_ALT | Alt keyboard table pointer ($FA80) |
| $034A | KEYBUF | IRQ keyboard buffer (10 bytes) |
| $0354 | TABMAP | Tab stop bitmap (10 bytes) |
| $035E | LINEMAP | Line-wrap bitmap |
| $0362 | LFTAB | Logical file number table |
| $036C | DEVTAB | Device number table |
| $0376 | SATAB | Secondary address table |
| $0380 | CHRGET | CHRGET routine |
| $0386 | CHRGOT | CHRGOT entry |
| $039F | FETCH0 | Fetch from bank 0 |
| $03AB | FETCH1 | Fetch from bank 1 |
| $03B7 | FETCH1I | Indexed-indirect fetch from bank 1 |
| $03C0 | FETCH0I | Indexed-indirect fetch from bank 0 |
| $03C9 | TXTPTR0 | TXTPTR fetch from bank 0 |
| $03D5 | CURBANK | Current bank for SYS/PEEK/POKE |
| $03F0 | DMALINK | DMA link code |

## MMU ($D500-$D50B, mirrored at $FF00-$FF04)

| Address | Name | Description |
|---------|------|-------------|
| $D500 | MMU_CR | Configuration register (also at $FF00) |
| $D501 | MMU_PCRA | Preconfiguration register A |
| $D502 | MMU_PCRB | Preconfiguration register B |
| $D503 | MMU_PCRC | Preconfiguration register C |
| $D504 | MMU_PCRD | Preconfiguration register D |
| $D505 | MMU_MCR | Mode configuration (C64 mode, Z80/8502 select) |
| $D506 | MMU_RCR | RAM configuration (common area, VIC bank) |
| $D507 | MMU_P0L | Zero-page pointer lo |
| $D508 | MMU_P0H | Zero-page pointer hi (bank) |
| $D509 | MMU_P1L | Stack-page pointer lo |
| $D50A | MMU_P1H | Stack-page pointer hi (bank) |
| $D50B | MMU_VR | MMU version register (read only) |
| $FF01 | MMU_LCRA | Load configuration A (write = activate PCRA) |
| $FF02 | MMU_LCRB | Load configuration B |
| $FF03 | MMU_LCRC | Load configuration C |
| $FF04 | MMU_LCRD | Load configuration D |

CR bit layout: bits 7-6 = RAM bank, bits 5-4 = $C000-$FFFF source
(00 system ROM, 01 internal function ROM, 10 external function ROM, 11 RAM),
bits 3-2 = $8000-$BFFF source (same encoding), bit 1 = $4000-$7FFF
(0 = BASIC low ROM, 1 = RAM), bit 0 = $D000-$DFFF (0 = I/O, 1 = char ROM/RAM).

Useful CR values:

| Value | Meaning |
|-------|---------|
| $00 | Power-up: system ROMs, I/O, bank 0 |
| $0E | Bank 0, KERNAL only ($4000-$BFFF and $D000 RAM) |
| $0F | As $0E but character ROM at $D000, no I/O |
| $3F | Bank 0, full RAM |
| $7F | Bank 1, full RAM |
| $BF | Bank 2, full RAM |
| $FF | Bank 3, full RAM |

## I/O Map ($D000-$DFFF)

| Address | Name | Description |
|---------|------|-------------|
| $D000 | VIC_SPR0_X | VIC-IIe sprite 0 X (through $D02E as on C64) |
| $D011 | VIC_CTRL1 | VIC-IIe control 1 |
| $D012 | VIC_RASTER | VIC-IIe raster line |
| $D018 | VIC_VIDEO | VIC-IIe video matrix / character base |
| $D020 | VIC_BORDER | VIC-IIe border colour |
| $D021 | VIC_BG0 | VIC-IIe background colour 0 |
| $D02F | VIC_KBD_128 | Extended keyboard bits (visible in C64 mode too) |
| $D030 | VIC_CLK_128 | 1/2 MHz clock rate register |
| $D400 | SID_FREQ1 | SID voice 1 frequency lo |
| $D404 | SID_CTRL1 | SID voice 1 control |
| $D418 | SID_VOL | SID filter mode and volume |
| $D600 | VDC_INDEX | 8563 VDC register address port |
| $D601 | VDC_DATA | 8563 VDC register data port |
| $D800 | COLOR_RAM | Colour RAM (1K nybbles) |
| $DC00 | CIA1_PRA | CIA1 port A (keyboard/joystick) |
| $DC01 | CIA1_PRB | CIA1 port B |
| $DC0D | CIA1_ICR | CIA1 interrupt control |
| $DD00 | CIA2_PRA | CIA2 port A (serial, VIC bank) |
| $DD0D | CIA2_ICR | CIA2 interrupt control |
| $DE00 | EXPANSION | Cartridge I/O area ($DE00-$DFFF) |

## 6502 Hardware Vectors

| Address | Name | Description |
|---------|------|-------------|
| $FFFA | NMIVEC | NMI transfer entry ($FF05) |
| $FFFC | RESETVEC | RESET transfer entry ($FF3D) |
| $FFFE | IRQVEC | IRQ transfer entry ($FF17) |

## Memory Banking Notes

- The Z80 boots first. It reads the 8502 reset vector through $FFFC and checks
  GAME/EXROM; with no cartridge it hands over to the 8502 in C128 mode.
- The 8502's `$01` port still controls $4000-$BFFF/$D000/$E000 visibility, but
  in C128 mode the MMU CR has the final say; writes to ROM fall through to RAM.
- Zero page and stack can be relocated anywhere by P0/P1 (256-byte granularity,
  bank in the high byte). $0000/$0001 always stay on the 8502's own port.
- The common area (RCR bits 3-0) is always bank 0 RAM; by default 1K at $0000.
- C64 mode is entered by `JMP $FF4D` (or `SYS 65229`); it switches the MMU to a
  fixed C64-compatible configuration and is not reversible without a reset.
- 40/80 column output is selected by $D7 bit 7 and $D030; the VDC has its own
  16K/64K video RAM, separate from the VIC-IIe's 16K window.

## Tooling Profile

| Field | Value |
|-------|-------|
| CPU | MOS 8502 (6510-compatible) + Z80A, 8722 MMU |
| zero_page | $0000-$00FF (relocatable via P0) |
| hardware | $D000-$DFFF |
| vectors | $FFFA-$FFFF |
| ROM windows | $4000-$AFFF BASIC 7.0, $B000-$BFFF monitor, $C000-$CFFF editor, $E000-$FFFF KERNAL |

## Sources

- https://www.c64-wiki.com/wiki/Commodore_128/Memory_Model (MMU register set)
- https://www.zimmers.net/anonftp/pub/cbm/maps/C128rom.txt (ROM map, KERNAL jump table)
- https://www.zimmers.net/anonftp/pub/cbm/maps/C128ram.txt (zero page and page 2/3)
- https://c128lib.github.io/Reference/E000 (KERNAL entries)
- cc65 `asminc/c128.inc`

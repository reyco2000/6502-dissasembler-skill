# Commodore VIC-20 Memory Map Reference

Tables with a single `$XX` / `$XXXX` in the first column are the rows a tool
like `tools/annotator.py` can parse: 2-digit rows are zero page, 4-digit rows are
either hardware registers or system vectors/variables. Range rows (`$XXXX-$YYYY`)
are documentation only. Keep one row per address — a second row for the same
address silently overwrites the first when the tables are loaded.

## Overview

The VIC-20 splits its 64K into eight 8K "blocks". A stock machine has 5K RAM
(1K at $0000-$03FF plus 4K at $1000-$1FFF), 20K ROM and 4K of I/O.

| Range | Block | Description |
|-------|-------|-------------|
| $0000-$03FF | 0 | 1K RAM: zero page, stack, KERNAL work area |
| $0400-$0FFF | 0 | 3K open area (RAM only with a 3K expansion) |
| $1000-$1FFF | 0 | 4K RAM; default screen at $1E00 (22x23 characters) |
| $2000-$3FFF | 1 | 8K expansion RAM |
| $4000-$5FFF | 2 | 8K expansion RAM |
| $6000-$7FFF | 3 | 8K expansion RAM |
| $8000-$8FFF | 4 | Character ROM (4K) |
| $9000-$93FF | 4 | I/O: VIC $9000, VIA1 $9110, VIA2 $9120 |
| $9400-$95FF | 4 | Colour RAM (1K x 4 bits at $9400) |
| $9600-$9FFF | 4 | Open |
| $A000-$BFFF | 5 | Cartridge ROM (8K) |
| $C000-$DFFF | 6 | BASIC ROM (8K) |
| $E000-$FFFF | 7 | KERNAL ROM (8K) |

With 8K or more expansion the BASIC start moves up (memory is contiguous from
$1201 or $2001), and the screen can be relocated to any 512-byte boundary inside
the 4K at $1000-$1FFF (and into expansion RAM) by changing $0288.

## Zero Page — BASIC and KERNAL

| Address | Name | Description |
|---------|------|-------------|
| $00 | D6510 | 6510 data direction register (default $2F) |
| $01 | R6510 | 6510 port: RAM/ROM/IO banking, cassette (default $37) |
| $2B | TXTTAB | Start of BASIC text lo (default $01) |
| $2C | TXTTAB+1 | Start of BASIC text hi (default $12 with 8K+ expansion) |
| $2D | VARTAB | Start of BASIC variables lo |
| $2E | VARTAB+1 | Start of BASIC variables hi |
| $2F | ARYTAB | Start of BASIC arrays lo |
| $30 | ARYTAB+1 | Start of BASIC arrays hi |
| $31 | STREND | End of BASIC arrays lo |
| $32 | STREND+1 | End of BASIC arrays hi |
| $33 | FRETOP | Bottom of string storage lo |
| $34 | FRETOP+1 | Bottom of string storage hi |
| $37 | MEMSIZ | Highest BASIC RAM address + 1 lo |
| $38 | MEMSIZ+1 | Highest BASIC RAM address + 1 hi |
| $39 | CURLIN | Current BASIC line number lo |
| $3A | CURLIN+1 | Current BASIC line number hi |
| $3D | TXTPTR | Pointer to next BASIC byte for CHRGET |
| $3E | TXTPTR+1 | Pointer hi |
| $61 | FAC1 | Floating point accumulator 1 (5 bytes $61-$65) |
| $69 | FAC2 | Floating point accumulator 2 (5 bytes $69-$6D) |
| $7A | TXTPTR2 | Operand pointer inside CHRGET |
| $90 | STATUS | KERNAL I/O status word (ST) |
| $91 | STKEY | STOP key flag |
| $98 | NFNUM | Number of open files |
| $99 | LA | Current input device (0 = keyboard) |
| $9A | FA | Current output device (3 = screen) |
| $9D | MSGFLG | KERNAL message switch |
| $A0 | TIME | Jiffy clock lo (60 Hz, $A0-$A2) |
| $A3 | RVS | Reverse output flag |
| $B7 | FNLEN | Length of current filename |
| $B9 | SECADR | Current secondary address |
| $BA | DEVNUM | Current device number |
| $BB | FNADR | Pointer to current filename lo |
| $BC | FNADR+1 | Pointer hi |
| $C5 | KEYLOG | Last key pressed |
| $C6 | KEY_COUNT | Characters in the keyboard buffer |
| $C7 | RVSFLG | Reverse video flag |
| $CC | CURS_FLAG | Cursor enable |
| $CD | CURS_BLINK | Cursor blink counter |
| $CE | CURS_CHAR | Character under the cursor |
| $D1 | SCREEN_PTR | Pointer to current screen line lo |
| $D2 | SCREEN_PTR+1 | Pointer hi |
| $D3 | CURS_X | Cursor column |
| $D6 | CURS_Y | Cursor row |
| $F3 | CRAM_PTR | Pointer to colour RAM under the cursor lo |
| $F4 | CRAM_PTR+1 | Pointer hi |
| $F7 | KEYPTR | Keyboard decode pointer lo |
| $F8 | KEYPTR+1 | Keyboard decode pointer hi |
| $FB | FREKZP | Free zero page (4 bytes $FB-$FE) |

## Page 2/3 — Buffers and Vectors

| Address | Name | Description |
|---------|------|-------------|
| $0200 | BUF | BASIC input line buffer (89 bytes) |
| $0259 | LAT | Logical file number table (10 bytes) |
| $0263 | FAT | Device number table (10 bytes) |
| $026D | SAT | Secondary address table (10 bytes) |
| $0277 | KEYD | Keyboard buffer (10 bytes) |
| $0281 | MEMSTART | Pointer to start of BASIC memory lo |
| $0282 | MEMSTART+1 | Pointer hi |
| $0283 | MEMTOP2 | Pointer to top of BASIC memory lo |
| $0284 | MEMTOP2+1 | Pointer hi |
| $0286 | COLOR | Current character colour |
| $0288 | SCREEN_PAGE | Screen memory page (default $1E) |
| $028A | KBDREPEAT | Key repeat delay |
| $028B | KBDREPEATRATE | Key repeat speed |
| $028C | KBDREPEATDELAY | Key repeat delay counter |
| $028D | SHFLAG | Shift/control key flags |
| $028E | LASTSHIFT | Last keyboard shift pattern |
| $028F | DECODE_PTR | Keyboard decode logic pointer lo |
| $0290 | DECODE_PTR+1 | Pointer hi |
| $0291 | SHMODE | Shift mode switch (0 = enabled) |
| $0292 | AUTODN | Auto-scroll-down flag |
| $0297 | RSSTAT | RS-232 status |
| $0300 | IERROR | BASIC error vector lo |
| $0302 | IMAIN | BASIC warm start vector lo |
| $0304 | ICRNCH | Tokenise vector lo |
| $0306 | IQPLOP | LIST vector lo |
| $0308 | IGONE | Execute statement vector lo |
| $030A | IEVAL | Evaluate expression vector lo |
| $0314 | CINV | IRQ vector lo |
| $0315 | CINV+1 | IRQ vector hi |
| $0316 | CBINV | BRK vector lo |
| $0318 | NMINV | NMI vector lo |
| $031A | IOPEN | OPEN vector lo |
| $031C | ICLOSE | CLOSE vector lo |
| $031E | ICHKIN | CHKIN vector lo |
| $0320 | ICHKOUT | CHKOUT vector lo |
| $0322 | ICLRCH | CLRCHN vector lo |
| $0324 | IBASIN | CHRIN vector lo |
| $0326 | IBSOUT | CHROUT vector lo |
| $0328 | ISTOP | STOP vector lo |
| $032A | IGETIN | GETIN vector lo |
| $032C | ICLALL | CLALL vector lo |
| $033C | TBUFFR | Cassette buffer (192 bytes, $033C-$03FB) |

## VIC 6560/6561 ($9000-$900F)

| Address | Name | Description |
|---------|------|-------------|
| $9000 | VIC_CR0 | Horizontal origin / interlace |
| $9001 | VIC_CR1 | Vertical origin / columns |
| $9002 | VIC_CR2 | Screen columns and rows |
| $9003 | VIC_CR3 | Character cell height / video address bits |
| $9004 | VIC_CR4 | Raster line (read) |
| $9005 | VIC_CR5 | Sprite 0-3 positions |
| $9006 | VIC_CR6 | Sprite 0-3 X MSBs / light pen X |
| $9007 | VIC_CR7 | Light pen Y |
| $9008 | VIC_CR8 | Paddle 0/1 (read) |
| $9009 | VIC_CR9 | Paddle 2/3 (read) |
| $900A | VIC_CRA | Voice 1 frequency |
| $900B | VIC_CRB | Voice 2 frequency |
| $900C | VIC_CRC | Voice 3 frequency |
| $900D | VIC_CRD | Noise frequency |
| $900E | VIC_CRE | Auxiliary colour / volume |
| $900F | VIC_CRF | Border and background colour |

## VIA 6522 and Colour RAM

| Address | Name | Description |
|---------|------|-------------|
| $9110 | VIA1_PB | VIA1 port B (joystick, cassette, IRQ) |
| $9111 | VIA1_PA1 | VIA1 port A without handshake |
| $9112 | VIA1_DDRB | VIA1 data direction B |
| $9113 | VIA1_DDRA | VIA1 data direction A |
| $9114 | VIA1_T1CL | VIA1 timer 1 counter lo |
| $9115 | VIA1_T1CH | VIA1 timer 1 counter hi |
| $9116 | VIA1_T1LL | VIA1 timer 1 latch lo |
| $9117 | VIA1_T1LH | VIA1 timer 1 latch hi |
| $9118 | VIA1_T2CL | VIA1 timer 2 counter lo |
| $9119 | VIA1_T2CH | VIA1 timer 2 counter hi |
| $911A | VIA1_SR | VIA1 shift register |
| $911B | VIA1_ACR | VIA1 auxiliary control |
| $911C | VIA1_PCR | VIA1 peripheral control |
| $911D | VIA1_IFR | VIA1 interrupt flags |
| $911E | VIA1_IER | VIA1 interrupt enable |
| $9120 | VIA2_PB | VIA2 port B (keyboard rows, joystick) |
| $9121 | VIA2_PA1 | VIA2 port A without handshake |
| $9122 | VIA2_DDRB | VIA2 data direction B |
| $9123 | VIA2_DDRA | VIA2 data direction A |
| $9124 | VIA2_T1CL | VIA2 timer 1 counter lo |
| $912B | VIA2_ACR | VIA2 auxiliary control |
| $912C | VIA2_PCR | VIA2 peripheral control |
| $912D | VIA2_IFR | VIA2 interrupt flags |
| $912E | VIA2_IER | VIA2 interrupt enable |
| $9400 | COLOR_RAM | Colour RAM start (1K x 4 bits, $9400-$95FF) |

## 6502 Hardware Vectors

| Address | Name | Description |
|---------|------|-------------|
| $FFFA | NMIVEC | NMI vector ($FEA9, NMI transfer entry) |
| $FFFC | RESETVEC | RESET vector ($FD22, power-up entry) |
| $FFFE | IRQVEC | IRQ/BRK vector ($FF72, IRQ transfer entry) |

## Memory Banking Notes

- `$01` bits 0-2 select BASIC at $C000, I/O at $9000-$97FF and KERNAL at $E000
  exactly as on the C64 (%x11 = ROMs + I/O).
- Character ROM is at $8000-$8FFF. It is not visible to the VIC as character
  data — the VIC always reads character glyphs from its own internal ROM.
- The 4K at $1000-$1FFF is the only RAM the VIC can use for the screen without
  expansion; $0288 holds the screen page and can be changed per frame.
- On a 3K/8K+ expanded machine the RAM blocks are banked in hardware (no
  software switch); BASIC moves its start pointer to the bottom of contiguous
  RAM.

## Tooling Profile

| Field | Value |
|-------|-------|
| CPU | MOS 6502 (NMOS), 6560/6561 VIC, two 6522 VIAs |
| zero_page | $0000-$00FF |
| hardware | $9000-$93FF (VIC/VIA), colour RAM $9400-$95FF |
| vectors | $FFFA-$FFFF |
| ROM windows | $8000-$8FFF character, $C000-$DFFF BASIC, $E000-$FFFF KERNAL |

## Sources

- https://sleepingelephant.com/denial/wiki/index.php/Memory_Map (block map)
- https://gbppr.net/iirg/vic20-rom.html (VIC-20 ROM addresses and jump table)
- cc65 `asminc/vic20.inc`
- Compute!'s Mapping the VIC (zero page and page 2/3 tables)

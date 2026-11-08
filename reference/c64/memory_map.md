# Commodore 64 Memory Map Reference

Tables with a single `$XX` / `$XXXX` in the first column are the rows a tool
like `tools/annotator.py` can parse: 2-digit rows are zero page, 4-digit rows are
either hardware registers or system vectors/variables. Range rows (`$XXXX-$YYYY`)
are documentation only. Keep one row per address — a second row for the same
address silently overwrites the first when the tables are loaded.

## Overview

| Range | Description |
|-------|-------------|
| $0000-$00FF | Zero page (BASIC, KERNAL, FP package; $FB-$FE free) |
| $0100-$01FF | 6502 hardware stack |
| $0200-$03FF | BASIC input buffer, KERNAL/BASIC vectors, tables, tape buffer |
| $0400-$07FF | Default screen RAM (1000 bytes at $0400, 40x25) |
| $0800-$9FFF | BASIC program area (TXTTAB = $0801, 38911 bytes free) |
| $A000-$BFFF | BASIC ROM (8K) — RAM visible when $01 bits 0-1 = %x00 |
| $C000-$CFFF | Free RAM (4K), popular for ML routines and sprite data |
| $D000-$DFFF | I/O: VIC-IIe, SID, colour RAM, CIA1, CIA2 (see $01 bits 0-1) |
| $E000-$FFFF | KERNAL ROM (8K) — RAM visible when $01 bits 0-1 = %x00 |

The three ROM/I/O windows are controlled by the 6510 on-chip port at $0001:
bits 0-2 select the $A000-$BFFF, $D000-$DFFF and $E000-$FFFF mappings
(%x11 = BASIC + KERNAL + I/O, %xxx with bit 2 clear = character ROM at $D000).

## Zero Page — BASIC and KERNAL

| Address | Name | Description |
|---------|------|-------------|
| $00 | D6510 | 6510 data direction register (default $2F) |
| $01 | R6510 | 6510 port: LORAM/HIRAM/CHAREN/cassette (default $37) |
| $2B | TXTTAB | Start of BASIC program text lo (default $01) |
| $2C | TXTTAB+1 | Start of BASIC program text hi (default $08) |
| $2D | VARTAB | Start of BASIC variables lo |
| $2E | VARTAB+1 | Start of BASIC variables hi |
| $2F | ARYTAB | Start of BASIC arrays lo |
| $30 | ARYTAB+1 | Start of BASIC arrays hi |
| $31 | STREND | End of BASIC arrays lo |
| $32 | STREND+1 | End of BASIC arrays hi |
| $33 | FRETOP | Bottom of string storage lo |
| $34 | FRETOP+1 | Bottom of string storage hi |
| $35 | FRESPC | Current string pointer lo |
| $36 | FRESPC+1 | Current string pointer hi |
| $37 | MEMSIZ | Highest BASIC RAM address + 1 lo (default $00) |
| $38 | MEMSIZ+1 | Highest BASIC RAM address + 1 hi (default $A0) |
| $39 | CURLIN | Current BASIC line number lo |
| $3A | CURLIN+1 | Current BASIC line number hi |
| $3D | TXTPTR | Pointer to next BASIC byte for CHRGET (self-modified) |
| $3E | TXTPTR+1 | Pointer to next BASIC byte, hi |
| $45 | VARNAM | Current variable name, first character |
| $47 | VARPNT | Pointer to current variable value lo |
| $49 | FORPNT | Pointer to FOR variable lo |
| $57 | FAC3 | Arithmetic register 3 (5 bytes $57-$5B) |
| $5C | FAC4 | Arithmetic register 4 (5 bytes $5C-$60) |
| $61 | FAC1 | Floating point accumulator 1 (5 bytes $61-$65) |
| $66 | FAC1SGN | Sign of FAC1 (bit 7 = negative) |
| $69 | FAC2 | Floating point accumulator 2 (5 bytes $69-$6D) |
| $6E | FAC2SGN | Sign of FAC2 |
| $73 | CHRGET | Get next BASIC character (24-byte self-modifying routine) |
| $79 | CHRGOT | Re-read current BASIC character |
| $7A | TXTPTR2 | Pointer to current BASIC byte (operand inside CHRGET) |
| $7B | TXTPTR2+1 | Pointer hi |
| $8B | RNDX | Previous RND() result (5 bytes $8B-$8F) |
| $90 | STATUS | KERNAL I/O status word (ST) |
| $91 | STKEY | STOP key flag ($7F pressed, $FF not pressed) |
| $93 | VERIFY | LOAD/VERIFY switch ($00 load) |
| $98 | NFNUM | Number of open files |
| $99 | LA | Current input device (default 0 = keyboard) |
| $9A | FA | Current output device (default 3 = screen) |
| $9D | MSGFLG | KERNAL message switch (bit 7 errors, bit 6 control msgs) |
| $A0 | TIME | Jiffy clock lo (60 Hz, $A0-$A2) |
| $A1 | TIME+1 | Jiffy clock mid |
| $A2 | TIME+2 | Jiffy clock hi |
| $A3 | RVS | PETSCII reverse flag |
| $B7 | FNLEN | Length of current filename |
| $B9 | SECADR | Current secondary address |
| $BA | DEVNUM | Current device number |
| $BB | FNADR | Pointer to current filename lo |
| $BC | FNADR+1 | Pointer to current filename hi |
| $C5 | KEYLOG | Last key pressed (matrix code) |
| $C6 | KEY_COUNT | Number of characters in keyboard buffer |
| $C7 | RVSFLG | Reverse video flag |
| $CB | LSTX | Matrix code of last key |
| $CC | CURS_FLAG | Cursor enable (0 = blink enabled) |
| $CD | CURS_BLINK | Cursor blink counter |
| $CE | CURS_CHAR | Character under the cursor |
| $CF | CURS_STATE | Cursor blink phase |
| $D1 | SCREEN_PTR | Pointer to current screen line lo |
| $D2 | SCREEN_PTR+1 | Pointer to current screen line hi |
| $D3 | CURS_X | Cursor column (0-39) |
| $D6 | CURS_Y | Cursor row (0-24) |
| $F3 | CRAM_PTR | Pointer to colour RAM under cursor lo |
| $F4 | CRAM_PTR+1 | Pointer hi |
| $FB | FREKZP | Free zero page (5 bytes $FB-$FF) |

## Page 2/3 — Buffers, Vectors, Tables

| Address | Name | Description |
|---------|------|-------------|
| $0200 | BUF | BASIC input line buffer (89 bytes) |
| $0259 | LAT | Logical file number table (10 bytes) |
| $0263 | FAT | Device number table (10 bytes) |
| $026D | SAT | Secondary address table (10 bytes) |
| $0277 | KEYD | Keyboard buffer (10 bytes) |
| $0281 | MEMSTART | Pointer to start of BASIC memory lo |
| $0283 | MEMTOP2 | Pointer to top of BASIC memory lo |
| $0286 | COLOR | Current character colour |
| $0288 | SCREEN_PAGE | High byte of the pointer to screen memory (default $04) |
| $028A | KBDREPEAT | Key repeat delay (128 = repeat all) |
| $028B | KBDREPEATRATE | Key repeat speed |
| $028C | KBDREPEATDELAY | Key repeat delay counter |
| $028D | SHFLAG | Shift/C= /ctrl key flags |
| $0291 | SHMODE | Shift mode switch (0 = enabled) |
| $0292 | AUTODN | Auto-scroll-down flag |
| $0300 | IERROR | BASIC error message vector lo |
| $0301 | IERROR+1 | BASIC error message vector hi |
| $0302 | IMAIN | BASIC warm start vector lo |
| $0303 | IMAIN+1 | BASIC warm start vector hi |
| $0304 | ICRNCH | Tokenise vector lo |
| $0306 | IQPLOP | LIST vector lo |
| $0308 | IGONE | Execute statement vector lo |
| $030A | IEVAL | Evaluate expression vector lo |
| $0314 | CINV | IRQ vector lo (default $31, i.e. $EA31) |
| $0315 | CINV+1 | IRQ vector hi |
| $0316 | CBINV | BRK vector lo |
| $0317 | CBINV+1 | BRK vector hi |
| $0318 | NMINV | NMI vector lo (default $47, i.e. $FE47) |
| $0319 | NMINV+1 | NMI vector hi |
| $031A | IOPEN | OPEN vector lo ($F34A) |
| $031C | ICLOSE | CLOSE vector lo ($F291) |
| $031E | ICHKIN | CHKIN vector lo ($F20E) |
| $0320 | ICHKOUT | CHKOUT vector lo ($F250) |
| $0322 | ICLRCH | CLRCHN vector lo ($F333) |
| $0324 | IBASIN | CHRIN vector lo ($F157) |
| $0326 | IBSOUT | CHROUT vector lo ($F1CA) |
| $0328 | ISTOP | STOP vector lo ($F6ED) |
| $032A | IGETIN | GETIN vector lo ($F13E) |
| $032C | ICLALL | CLALL vector lo ($F32F) |
| $0334 | FREE8 | Unused (8 bytes $0334-$033B) |
| $033C | TBUFFR | Cassette buffer (192 bytes, $033C-$03FB) |

## VIC-IIe ($D000-$D02E)

| Address | Name | Description |
|---------|------|-------------|
| $D000 | SP0X | Sprite 0 X position |
| $D001 | SP0Y | Sprite 0 Y position |
| $D002 | SP1X | Sprite 1 X position |
| $D003 | SP1Y | Sprite 1 Y position |
| $D004 | SP2X | Sprite 2 X position |
| $D005 | SP2Y | Sprite 2 Y position |
| $D006 | SP3X | Sprite 3 X position |
| $D007 | SP3Y | Sprite 3 Y position |
| $D008 | SP4X | Sprite 4 X position |
| $D009 | SP4Y | Sprite 4 Y position |
| $D00A | SP5X | Sprite 5 X position |
| $D00B | SP5Y | Sprite 5 Y position |
| $D00C | SP6X | Sprite 6 X position |
| $D00D | SP6Y | Sprite 6 Y position |
| $D00E | SP7X | Sprite 7 X position |
| $D00F | SP7Y | Sprite 7 Y position |
| $D010 | MSB_X | Sprite X MSBs (bit n = sprite n) |
| $D011 | CR1 | Screen control 1: raster hi, blank, rows, y-scroll, mode |
| $D012 | RASTER | Raster line (read) / raster compare low (write) |
| $D013 | LPENX | Light pen X |
| $D014 | LPENY | Light pen Y |
| $D015 | SPENA | Sprite enable mask |
| $D016 | CR2 | Screen control 2: x-scroll, columns, multicolour |
| $D017 | SPYEX | Sprite Y expansion mask |
| $D018 | VMCSB | Video matrix base ($0400) and character base ($D000) |
| $D019 | VICIRQ | IRQ status (write 1 to acknowledge) |
| $D01A | IRQMSK | IRQ mask (raster, sprite-background, sprite-sprite, light pen) |
| $D01B | SPPRIO | Sprite-to-background priority |
| $D01C | SPMC | Sprite multicolour mask |
| $D01D | SPXEX | Sprite X expansion mask |
| $D01E | SPSPCL | Sprite-sprite collision (write to clear) |
| $D01F | SPBGCL | Sprite-background collision (write to clear) |
| $D020 | EXTCOL | Border colour |
| $D021 | BGCOL0 | Background colour 0 |
| $D022 | BGCOL1 | Background colour 1 (multicolour) |
| $D023 | BGCOL2 | Background colour 2 (multicolour) |
| $D024 | BGCOL3 | Background colour 3 (multicolour) |
| $D025 | SPMC0 | Sprite multicolour 0 |
| $D026 | SPMC1 | Sprite multicolour 1 |
| $D027 | SP0COL | Sprite 0 colour |
| $D02E | SP7COL | Sprite 7 colour |

## SID, Colour RAM, CIAs

| Address | Name | Description |
|---------|------|-------------|
| $D400 | SID_FREQ1 | Voice 1 frequency lo |
| $D401 | SID_FREQ1H | Voice 1 frequency hi |
| $D402 | SID_PW1 | Voice 1 pulse width lo |
| $D403 | SID_PW1H | Voice 1 pulse width hi |
| $D404 | SID_CTRL1 | Voice 1 control (waveform, gate, ring, sync, test) |
| $D405 | SID_ATK1 | Voice 1 attack/decay |
| $D406 | SID_SUS1 | Voice 1 sustain/release |
| $D407 | SID_FREQ2 | Voice 2 frequency lo |
| $D40B | SID_CTRL2 | Voice 2 control |
| $D40E | SID_FREQ3 | Voice 3 frequency lo |
| $D412 | SID_CTRL3 | Voice 3 control |
| $D415 | SID_FC_LO | Filter cutoff lo (3 bits) |
| $D416 | SID_FC_HI | Filter cutoff hi |
| $D417 | SID_RES_FILT | Filter resonance and voice routing |
| $D418 | SID_MODE_VOL | Filter mode and master volume |
| $D419 | SID_POT_X | Paddle X (read) |
| $D41A | SID_POT_Y | Paddle Y (read) |
| $D41B | SID_OSC3 | Voice 3 oscillator (read, noise) |
| $D41C | SID_ENV3 | Voice 3 envelope (read) |
| $D800 | COLOR_RAM | Colour RAM, 1000 nybbles (mirrored $D800-$DBFF) |
| $DC00 | CIA1_PRA | CIA1 port A: keyboard columns / joystick 2 |
| $DC01 | CIA1_PRB | CIA1 port B: keyboard rows / joystick 1 |
| $DC02 | CIA1_DDRA | CIA1 data direction A |
| $DC03 | CIA1_DDRB | CIA1 data direction B |
| $DC04 | CIA1_TA | CIA1 timer A (16-bit) |
| $DC05 | CIA1_TA_HI | CIA1 timer A hi |
| $DC06 | CIA1_TB | CIA1 timer B (16-bit) |
| $DC08 | CIA1_TOD | CIA1 time of day (10ths) |
| $DC0D | CIA1_ICR | CIA1 interrupt control |
| $DC0E | CIA1_CRA | CIA1 control register A |
| $DC0F | CIA1_CRB | CIA1 control register B |
| $DD00 | CIA2_PRA | CIA2 port A: VIC bank, serial bus, RS-232 |
| $DD01 | CIA2_PRB | CIA2 port B: RS-232 / user port |
| $DD02 | CIA2_DDRA | CIA2 data direction A |
| $DD0D | CIA2_ICR | CIA2 interrupt control |
| $DD0E | CIA2_CRA | CIA2 control register A |
| $DD0F | CIA2_CRB | CIA2 control register B |

## 6502 Hardware Vectors

| Address | Name | Description |
|---------|------|-------------|
| $FFFA | NMIVEC | NMI vector ($FE43, RESTORE key / RS-232) |
| $FFFC | RESETVEC | RESET vector ($FCE2) |
| $FFFE | IRQVEC | IRQ/BRK vector ($FF48, KERNAL IRQ entry) |

## Memory Banking Notes

- `$01` bits 0-2: %x11 → BASIC at $A000, I/O at $D000, KERNAL at $E000;
  %x10 → RAM at $A000, KERNAL at $E000; %x00 → RAM everywhere.
  Bit 2 set = I/O at $D000-$DFFF, clear = character ROM at $D000-$DFFF.
- Writing to ROM addresses writes the RAM underneath; that is how "copying the
  character ROM to RAM" works (read $D000-$DFFF with bit 2 clear, write with
  bit 2 set and BASIC/KERNAL banked out).
- The VIC-IIe sees only 16K at a time: CIA2 port A bits 0-1 select the 16K
  bank, and VIC $D018 selects the 1K matrix and 2K character set inside it.
- The KERNAL's software vectors at $0314-$0333 are what code should patch;
  $FFFA-$FFFF are read-only ROM vectors.

## Tooling Profile

| Field | Value |
|-------|-------|
| CPU | MOS 6510 (NMOS 6502 + I/O port), no undocumented opcodes required |
| zero_page | $0000-$00FF |
| hardware | $D000-$DFFF |
| vectors | $FFFA-$FFFF |
| ROM windows | $A000-$BFFF BASIC, $D000-$DFFF character, $E000-$FFFF KERNAL |

## Sources

- https://sta.c64.org/cbm64mem.html (full C64 memory map)
- https://sta.c64.org/cbm64krnfunc.html (KERNAL jump table, real addresses)
- https://www.c64-wiki.com/wiki/BASIC-ROM (BASIC ROM entry points)
- https://codebase.c64.org/doku.php?id=base:asm_include_file_for_basic_routines
- cc65 `asminc/c64.inc`

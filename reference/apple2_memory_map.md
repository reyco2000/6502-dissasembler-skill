# Apple II / II+ / IIe / IIc Memory Map Reference

Tables with a single `$XX` / `$XXXX` in the first column are parsed by
`tools/annotator.py`: 2-digit rows → zero page, `$C000-$CFFF` → soft
switches / I/O, anything else → system vectors and variables. Range rows are
documentation only.

## Overview

| Range | Description |
|-------|-------------|
| $0000-$00FF | Zero page (Monitor, Applesoft, DOS/ProDOS use much of it) |
| $0100-$01FF | 6502 hardware stack |
| $0200-$02FF | Keyboard input buffer (GETLN) |
| $0300-$03CF | Free (popular spot for small ML routines) |
| $03D0-$03FF | DOS 3.3 / ProDOS vectors and system hooks |
| $0400-$07FF | Text / lo-res page 1 (IIe 80-col: aux bank interleaved) |
| $0800-$0BFF | Text / lo-res page 2; Applesoft program default start $0801 |
| $0C00-$1FFF | Free RAM |
| $2000-$3FFF | Hi-res page 1 (ProDOS SYS files load at $2000) |
| $4000-$5FFF | Hi-res page 2 |
| $6000-$95FF | Free RAM (DOS 3.3 HIMEM $9600 with 3 buffers) |
| $9600-$BFFF | DOS 3.3 (48K) / ProDOS BASIC.SYSTEM + global page $BF00 |
| $C000-$C0FF | Soft switches and slot I/O ($C080+$n0 for slot n) |
| $C100-$C7FF | Slot firmware ROM ($Cn00 for slot n) |
| $C800-$CFFF | Shared expansion ROM (release with any access to $CFFF) |
| $D000-$F7FF | Applesoft BASIC ROM (or language card RAM) |
| $F800-$FFFF | Monitor ROM (or language card RAM) |

## Zero Page — Monitor

| Address | Name | Description |
|---------|------|-------------|
| $20 | WNDLFT | Text window left edge |
| $21 | WNDWDTH | Text window width |
| $22 | WNDTOP | Text window top line |
| $23 | WNDBTM | Text window bottom line + 1 |
| $24 | CH | Cursor horizontal position |
| $25 | CV | Cursor vertical position |
| $26 | GBASL | Lo-res graphics base address lo |
| $27 | GBASH | Lo-res graphics base address hi |
| $28 | BASL | Text line base address lo |
| $29 | BASH | Text line base address hi |
| $2A | BAS2L | Scroll destination base lo |
| $2B | BAS2H | Scroll destination base hi |
| $2C | H2 | Lo-res line end horizontal |
| $2D | V2 | Lo-res line end vertical |
| $2E | MASK | Lo-res color mask |
| $30 | COLOR | Lo-res color |
| $31 | MODE | Monitor command mode |
| $32 | INVFLG | Text inverse mask ($FF normal, $3F inverse, $7F flash) |
| $33 | PROMPT | GETLN prompt character |
| $34 | YSAV | Monitor Y save |
| $35 | YSAV1 | Monitor Y save (COUT) |
| $36 | CSWL | Character output hook lo (PR#) |
| $37 | CSWH | Character output hook hi |
| $38 | KSWL | Character input hook lo (IN#) |
| $39 | KSWH | Character input hook hi |
| $3A | PCL | Monitor program counter lo |
| $3B | PCH | Monitor program counter hi |
| $3C | A1L | Monitor A1 lo (MOVE/VERIFY source start) |
| $3D | A1H | Monitor A1 hi |
| $3E | A2L | Monitor A2 lo (source end) |
| $3F | A2H | Monitor A2 hi |
| $40 | A3L | Monitor A3 lo |
| $41 | A3H | Monitor A3 hi |
| $42 | A4L | Monitor A4 lo (destination) |
| $43 | A4H | Monitor A4 hi |
| $44 | A5L | Monitor A5 lo |
| $45 | A5H | Monitor A5 hi / A register save |
| $46 | XREG | Monitor X save |
| $47 | YREG | Monitor Y save |
| $48 | STATUS | Monitor P save |
| $49 | SPNT | Monitor S save |
| $4E | RNDL | Random seed lo (incremented while waiting for a key) |
| $4F | RNDH | Random seed hi |

## Zero Page — Applesoft

| Address | Name | Description |
|---------|------|-------------|
| $50 | LINNUM | Line number / integer result lo (GETADR) |
| $51 | LINNUM+1 | Line number / integer result hi |
| $67 | TXTTAB | Start of program text lo |
| $68 | TXTTAB+1 | Start of program text hi |
| $69 | VARTAB | Start of simple variables lo |
| $6A | VARTAB+1 | Start of simple variables hi |
| $6B | ARYTAB | Start of arrays lo |
| $6C | ARYTAB+1 | Start of arrays hi |
| $6D | STREND | End of arrays lo |
| $6E | STREND+1 | End of arrays hi |
| $6F | FRETOP | Bottom of string storage lo |
| $70 | FRETOP+1 | Bottom of string storage hi |
| $73 | MEMSIZ | HIMEM lo |
| $74 | MEMSIZ+1 | HIMEM hi |
| $75 | CURLIN | Current line number lo |
| $76 | CURLIN+1 | Current line number hi |
| $9D | FAC | Floating point accumulator (6 bytes $9D-$A2) |
| $A5 | ARG | Floating point argument (6 bytes $A5-$AA) |
| $B1 | CHRGET | Get next program character (self-modifying routine) |
| $B7 | CHRGOT | Re-read current character |
| $B8 | TXTPTR | CHRGET text pointer lo (operand of LDA inside CHRGET) |
| $B9 | TXTPTR+1 | CHRGET text pointer hi |
| $D8 | ERRFLG | ONERR active flag (bit 7) |
| $DE | ERRNUM | Last error number |
| $E0 | HORIZ | Hi-res cursor X lo |
| $E1 | HORIZ+1 | Hi-res cursor X hi |
| $E2 | VERT | Hi-res cursor Y |
| $E4 | HCOLOR1 | Hi-res color byte |
| $E6 | HPAG | Hi-res page for plotting ($20 page 1, $40 page 2) |
| $E7 | SCALE | Shape scale |
| $E8 | SHAPEL | Shape table address lo |
| $E9 | SHAPEH | Shape table address hi |
| $F9 | ROT | Shape rotation |

Free for ML programs under Applesoft: $06-$09, $19-$1F, $CE-$CF, $EB-$EF, $FA-$FF.

## Page 2/3 System Vectors

| Address | Name | Description |
|---------|------|-------------|
| $03D0 | DOSWARM | DOS 3.3 warm start (JMP) |
| $03D3 | DOSCOLD | DOS 3.3 cold start (JMP) |
| $03D6 | FILEMGR | DOS 3.3 file manager entry (JMP) |
| $03D9 | RWTS | DOS 3.3 RWTS entry (JMP) |
| $03DC | FMPARMS | Locate file manager parameter list (Y/A) |
| $03E3 | RWTSPARMS | Locate RWTS IOB (Y/A) |
| $03EA | DOSHOOK | Reconnect DOS I/O hooks |
| $03F0 | BRKV | BRK handler vector (II+ autostart and later) |
| $03F2 | SOFTEV | Reset vector (valid when PWREDUP = SOFTEV hi EOR $A5) |
| $03F4 | PWREDUP | Power-up byte (checksum of SOFTEV hi) |
| $03F5 | AMPERV | Applesoft & handler (JMP) |
| $03F8 | USRADR | Ctrl-Y monitor command (JMP) |
| $03FB | NMIVEC | NMI handler (JMP) |
| $03FE | IRQLOC | IRQ handler vector (autostart ROM) |

## ProDOS Global Page ($BF00)

| Address | Name | Description |
|---------|------|-------------|
| $BF00 | MLI | ProDOS Machine Language Interface entry (JSR; cmd byte + param ptr follow) |
| $BF03 | QUIT_VEC | Quit vector |
| $BF06 | DATETIME | Clock driver entry |
| $BF09 | SYSERR | System error handler |
| $BF0C | SYSDEATH | System death handler |
| $BF0F | SERR | Last MLI error code |
| $BF10 | DEVADR01 | Device driver vector table start |
| $BF30 | DEVNUM | Last device accessed (DSSS0000) |
| $BF31 | DEVCNT | Number of devices - 1 |
| $BF32 | DEVLST | Device list |
| $BF58 | BITMAP | Memory bit map (24 bytes, 1 bit per page) |
| $BF90 | DATE | ProDOS date (2 bytes) |
| $BF92 | TIME | ProDOS time (2 bytes) |
| $BF94 | LEVEL | Current file level |
| $BF98 | MACHID | Machine ID byte |
| $BF99 | SLTBYT | Slots with ROM bitmap |
| $BF9A | PFIXPTR | Prefix active flag |
| $BFFC | IBAKVER | Minimum interpreter version |
| $BFFD | IVERSION | Interpreter version |
| $BFFE | KBAKVER | Minimum kernel version |
| $BFFF | KVERSION | Kernel version |

## Soft Switches — Keyboard, 80-Column, Memory ($C000-$C01F)

Writes to $C000-$C00F set IIe/IIc switches; reads of $C011-$C01F return
the state in bit 7.

| Address | Name | Description |
|---------|------|-------------|
| $C000 | KBD | Keyboard data, bit 7 = key ready (W: 80STORE off) |
| $C001 | SET80STORE | W: 80STORE on (PAGE2 selects aux display memory) |
| $C002 | RDMAINRAM | W: read main 48K |
| $C003 | RDCARDRAM | W: read aux 48K |
| $C004 | WRMAINRAM | W: write main 48K |
| $C005 | WRCARDRAM | W: write aux 48K |
| $C006 | SETSLOTCXROM | W: slot ROMs at $C100-$CFFF |
| $C007 | SETINTCXROM | W: internal ROM at $C100-$CFFF |
| $C008 | SETSTDZP | W: main zero page, stack and LC |
| $C009 | SETALTZP | W: aux zero page, stack and LC |
| $C00A | SETINTC3ROM | W: internal slot 3 ROM |
| $C00B | SETSLOTC3ROM | W: slot 3 card ROM |
| $C00C | CLR80VID | W: 40-column display |
| $C00D | SET80VID | W: 80-column display |
| $C00E | CLRALTCHAR | W: primary character set |
| $C00F | SETALTCHAR | W: alternate character set (MouseText) |
| $C010 | KBDSTRB | Clear keyboard strobe; R: bit 7 = any key down (IIe) |
| $C011 | RDLCBNK2 | R: bit 7 = LC bank 2 selected |
| $C012 | RDLCRAM | R: bit 7 = LC RAM read enabled |
| $C013 | RDRAMRD | R: bit 7 = reading aux 48K |
| $C014 | RDRAMWRT | R: bit 7 = writing aux 48K |
| $C015 | RDCXROM | R: bit 7 = internal CX ROM |
| $C016 | RDALTZP | R: bit 7 = aux zero page |
| $C017 | RDC3ROM | R: bit 7 = slot 3 ROM |
| $C018 | RD80STORE | R: bit 7 = 80STORE on |
| $C019 | RDVBL | R: vertical blank (IIe: bit 7 clear during VBL) |
| $C01A | RDTEXT | R: bit 7 = text mode |
| $C01B | RDMIXED | R: bit 7 = mixed mode |
| $C01C | RDPAGE2 | R: bit 7 = page 2 |
| $C01D | RDHIRES | R: bit 7 = hi-res |
| $C01E | RDALTCHAR | R: bit 7 = alternate charset |
| $C01F | RD80VID | R: bit 7 = 80-column |

## Soft Switches — Sound, Video, Game I/O ($C020-$C07F)

Any access (read or write) toggles/selects; reads are normally used.
Writes to these addresses on the 6502 perform a dummy read first, so
`STA $C030` clicks the speaker twice.

| Address | Name | Description |
|---------|------|-------------|
| $C020 | TAPEOUT | Toggle cassette output |
| $C030 | SPKR | Toggle speaker |
| $C040 | STROBE | Game I/O strobe output |
| $C050 | TXTCLR | Graphics mode |
| $C051 | TXTSET | Text mode |
| $C052 | MIXCLR | Full-screen graphics |
| $C053 | MIXSET | Mixed graphics + 4 lines text |
| $C054 | TXTPAGE1 | Display page 1 (80STORE: main memory) |
| $C055 | TXTPAGE2 | Display page 2 (80STORE: aux memory) |
| $C056 | LORES | Lo-res graphics |
| $C057 | HIRES | Hi-res graphics |
| $C058 | SETAN0 | Annunciator 0 off |
| $C059 | CLRAN0 | Annunciator 0 on |
| $C05A | SETAN1 | Annunciator 1 off |
| $C05B | CLRAN1 | Annunciator 1 on |
| $C05C | SETAN2 | Annunciator 2 off |
| $C05D | CLRAN2 | Annunciator 2 on |
| $C05E | SETAN3 | Annunciator 3 off = double hi-res on (IIe/IIc) |
| $C05F | CLRAN3 | Annunciator 3 on = double hi-res off |
| $C060 | TAPEIN | Cassette input (bit 7) |
| $C061 | BUTN0 | Button 0 / Open-Apple (bit 7) |
| $C062 | BUTN1 | Button 1 / Closed-Apple (bit 7) |
| $C063 | BUTN2 | Button 2 / shift-key mod (bit 7) |
| $C064 | PADDL0 | Paddle 0 timer (bit 7 set while counting) |
| $C065 | PADDL1 | Paddle 1 timer |
| $C066 | PADDL2 | Paddle 2 timer |
| $C067 | PADDL3 | Paddle 3 timer |
| $C070 | PTRIG | Trigger paddle timers |
| $C07E | IOUDIS | IIc: W IOU disable on / R: bit 7 IOUDIS state |
| $C07F | RDDHIRES | R: bit 7 = double hi-res |

## Language Card ($C080-$C08F)

The write-enabling switches ($C081, $C083, $C089, $C08B) must be read
twice in a row. $C084-$C087 and $C08C-$C08F mirror these.

| Address | Name | Description |
|---------|------|-------------|
| $C080 | LCBANK2_RD | Read RAM bank 2, write protected |
| $C081 | LCBANK2_ROM_WR | Read ROM, write RAM bank 2 (read twice) |
| $C082 | LCROM_RD | Read ROM, write protected |
| $C083 | LCBANK2_RW | Read/write RAM bank 2 (read twice) |
| $C088 | LCBANK1_RD | Read RAM bank 1, write protected |
| $C089 | LCBANK1_ROM_WR | Read ROM, write RAM bank 1 (read twice) |
| $C08A | LCROM_RD2 | Read ROM, write protected |
| $C08B | LCBANK1_RW | Read/write RAM bank 1 (read twice) |

## Slot I/O ($C090-$C0FF) — Disk II in Slot 6

Slot n registers are at $C080 + n*$10. Drivers usually index with X =
slot*16 (`LDA $C08C,X`). Offsets for a Disk II controller:

| Address | Name | Description |
|---------|------|-------------|
| $C0E0 | PHASE0OFF | Stepper phase 0 off |
| $C0E1 | PHASE0ON | Stepper phase 0 on |
| $C0E2 | PHASE1OFF | Stepper phase 1 off |
| $C0E3 | PHASE1ON | Stepper phase 1 on |
| $C0E4 | PHASE2OFF | Stepper phase 2 off |
| $C0E5 | PHASE2ON | Stepper phase 2 on |
| $C0E6 | PHASE3OFF | Stepper phase 3 off |
| $C0E7 | PHASE3ON | Stepper phase 3 on |
| $C0E8 | MOTOROFF | Drive motor off |
| $C0E9 | MOTORON | Drive motor on |
| $C0EA | DRV0EN | Select drive 1 |
| $C0EB | DRV1EN | Select drive 2 |
| $C0EC | Q6L | Shift data register / read data latch |
| $C0ED | Q6H | Load data register / sense write protect |
| $C0EE | Q7L | Read mode |
| $C0EF | Q7H | Write mode |
| $CFFF | CLRROM | Release $C800-$CFFF expansion ROM |

## 6502 Hardware Vectors

| Address | Name | Description |
|---------|------|-------------|
| $FFFA | NMI_VECTOR | NMI vector (Monitor: JMP ($03FB)) |
| $FFFC | RESET_VECTOR | RESET vector ($FA62 Autostart, $FF59 original Monitor) |
| $FFFE | IRQ_VECTOR | IRQ/BRK vector ($FA40 Autostart → $03FE / $03F0) |

## Machine Identification (Tech Note #7)

| Machine | $FBB3 | $FBC0 | CPU |
|---------|-------|-------|-----|
| Apple II | $38 | — | 6502 |
| Apple II+ | $EA | — | 6502 |
| Apple IIe | $06 | $EA | 6502 |
| Apple IIe enhanced | $06 | $E0 | 65C02 |
| Apple IIc | $06 | $00 | 65C02 |

## Screen Memory Layout

Text/lo-res rows are interleaved: row r base = $0400 + $80*(r mod 8) +
$28*(r div 8). Monitor BASCALC ($FBC1) computes BASL/BASH. Hi-res rows:
base = $2000 + $400*(y mod 8) + $80*((y div 8) mod 8) + $28*(y div 64).
Each hi-res byte holds 7 pixels (bits 0-6, LSB leftmost); bit 7 selects
the color palette (violet/green vs blue/orange).

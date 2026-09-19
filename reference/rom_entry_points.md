# Apple II ROM / OS Entry Points Reference

Generated from `ROM_LABELS` / `ROM_DESCRIPTIONS` in `tools/dasm6502.py`, plus
hand-written sections. `tools/annotator.py` parses every `| $XXXX | NAME | Description |`
row as a callable entry point and `| $XX |` rows as ProDOS MLI command codes.
When you add an entry, add it to `tools/dasm6502.py` as well so the listing uses the name.

## Monitor ROM ($F800-$FFFF)

| Address | Name | Description |
|---------|------|-------------|
| $F800 | PLOT | Plot lo-res point (A=row, Y=col) |
| $F819 | HLINE | Lo-res horizontal line |
| $F828 | VLINE | Lo-res vertical line |
| $F832 | CLRSCR | Clear lo-res screen |
| $F836 | CLRTOP | Clear top 40 lo-res lines |
| $F847 | GBASCALC | Compute GBASL/H from row in A |
| $F85F | NXTCOL | Next lo-res color |
| $F864 | SETCOL | Set lo-res color (A) |
| $F871 | SCRN | Read lo-res point |
| $F88E | INSDS2 | Disassembler: decode opcode |
| $F8D0 | INSTDSP | Disassembler: display instruction |
| $F940 | PRNTYX | Print Y,X as hex |
| $F941 | PRNTAX | Print A,X as hex |
| $F944 | PRNTX | Print X as hex |
| $F948 | PRBLNK | Print 3 blanks |
| $F94A | PRBL2 | Print X blanks |
| $FA62 | RESET | RESET handler |
| $FAA6 | PWRUP | Power-up: init DOS/boot |
| $FAD7 | REGDSP | Display registers |
| $FB1E | PREAD | Read paddle X (result in Y) |
| $FB2F | INIT | Init text screen/window |
| $FB39 | SETTXT | Set text mode |
| $FB40 | SETGR | Set lo-res graphics mode |
| $FB4B | SETWND | Set normal text window |
| $FB5B | TABV | Vertical tab to A |
| $FBC1 | BASCALC | Compute BASL/H for row |
| $FBDD | BELL1 | Ring bell |
| $FBF4 | ADVANCE | Advance cursor |
| $FC10 | BS | Backspace |
| $FC1A | UP | Cursor up |
| $FC22 | VTAB | Vertical tab (CV) |
| $FC24 | VTABZ | Vertical tab to A |
| $FC42 | CLREOP | Clear to end of page |
| $FC58 | HOME | Clear screen, home cursor |
| $FC62 | CR | Carriage return |
| $FC66 | LF | Line feed |
| $FC70 | SCROLL | Scroll text window |
| $FC9C | CLREOL | Clear to end of line |
| $FC9E | CLEOLZ | Clear EOL from Y |
| $FCA8 | WAIT | Delay (26+27A+5A^2)/2 cycles |
| $FCB4 | NXTA4 | Increment A4L/H |
| $FCBA | NXTA1 | Increment A1L/H, compare A2 |
| $FCC9 | HEADR | Write cassette header |
| $FD0C | RDKEY | Read key (via KSW) |
| $FD1B | KEYIN | Keyboard input with blink |
| $FD35 | RDCHAR | Read char, handle ESC |
| $FD67 | GETLNZ | CR then get line |
| $FD6A | GETLN | Get line with prompt |
| $FD6F | GETLN1 | Get line, no prompt |
| $FD8B | CROUT1 | CR after clearing EOL |
| $FD8E | CROUT | Print CR |
| $FD96 | PRA1 | Print CR, A1 and dash |
| $FDDA | PRBYTE | Print A as 2 hex digits |
| $FDE3 | PRHEX | Print low nibble hex |
| $FDED | COUT | Output char in A (via CSW) |
| $FDF0 | COUT1 | Output char to screen |
| $FE1F | IDROUTINE | ID routine (IIgs returns machine info) |
| $FE2C | MOVE | Move memory A1..A2 -> A4 |
| $FE36 | VERIFY | Verify memory |
| $FE5E | LIST | Disassemble 20 instructions |
| $FE80 | SETINV | Inverse video |
| $FE84 | SETNORM | Normal video |
| $FE89 | SETKBD | Reset KSW to keyboard |
| $FE93 | SETVID | Reset CSW to screen |
| $FEB0 | XBASIC | Jump to BASIC |
| $FECD | WRITE | Write cassette |
| $FEFD | READ | Read cassette |
| $FF2D | PRERR | Print ERR, bell |
| $FF3A | BELL | Bell |
| $FF3F | RESTORE | Restore registers |
| $FF4A | SAVE | Save registers |
| $FF58 | IORTS | Known RTS (slot detection) |
| $FF59 | OLDRST | Old monitor reset |
| $FF65 | MON | Monitor (bell) |
| $FF69 | MONZ | Monitor entry (no bell) |

## Applesoft BASIC ROM ($D000-$F7FF)

| Address | Name | Description |
|---------|------|-------------|
| $D412 | ERROR | Applesoft error (X=code) |
| $D43C | RESTART | Applesoft warm restart |
| $D61A | FNDLIN | Find line number in LINNUM |
| $D7D2 | NEWSTT | Execute next statement |
| $D858 | ISCNTC | Check ctrl-C |
| $DB3A | STROUT | Print string at A(lo)/Y(hi) |
| $DB3D | STRPRT | Print string (FAC) |
| $DB5C | OUTDO | Output char (Applesoft) |
| $DD67 | FRMNUM | Evaluate numeric expression |
| $DD7B | FRMEVL | Evaluate expression |
| $DEBE | CHKCOM | Check for comma |
| $DEC0 | SYNCHR | Check for char in A |
| $DEC9 | SYNERR | Syntax error |
| $E000 | COLDSTART | Applesoft cold start |
| $E003 | WARMSTART | Applesoft warm start |
| $E10C | AYINT | FAC to signed integer |
| $E2F2 | GIVAYF | A,Y int to FAC |
| $E6F8 | GETBYT | Get byte param in X |
| $E752 | GETADR | Get address param in LINNUM |
| $E7A7 | FSUB | FAC = (A,Y) - FAC |
| $E7AA | FSUBT | FAC = ARG - FAC |
| $E7BE | FADD | FAC = (A,Y) + FAC |
| $E7C1 | FADDT | FAC = ARG + FAC |
| $E97F | FMULT | FAC = (A,Y) * FAC |
| $E982 | FMULTT | FAC = ARG * FAC |
| $EA66 | FDIV | FAC = (A,Y) / FAC |
| $EA69 | FDIVT | FAC = ARG / FAC |
| $EAF9 | MOVFM | Load FAC from (A,Y) |
| $EB2B | MOVMF | Store FAC at (X,Y) |
| $EBF2 | QINT | Quick FAC to int |
| $EC23 | INT | INT function |
| $EC4A | FIN | String to FAC |
| $ED24 | LINPRT | Print A,X as decimal |
| $ED34 | FOUT | FAC to string |
| $EE8D | SQR | SQR |
| $EE97 | FPWRT | FAC = ARG ^ FAC |
| $EF09 | EXP | EXP |
| $EFAE | RND | RND |
| $EFEA | COS | COS |
| $EFF1 | SIN | SIN |
| $F03A | TAN | TAN |
| $F09E | ATN | ATN |
| $F1D5 | CALL | CALL statement |
| $F1DE | IN | IN# statement |
| $F1E5 | PR | PR# statement |
| $F3D8 | HGR2 | HGR2 |
| $F3E2 | HGR | HGR |
| $F3F2 | HCLR | Clear hires screen |
| $F3F6 | BKGND | Fill hires with color |
| $F411 | HPOSN | Position hires cursor (X,Y / A) |
| $F457 | HPLOT | Plot hires point |
| $F53A | HGLIN | Hires line to |
| $F5CB | HFIND | Find hires point |
| $F601 | DRAW | DRAW shape |
| $F65D | XDRAW | XDRAW shape |
| $F6EC | SETHCOL | Set hires color from X |
| $F721 | ROT | ROT= |
| $F727 | SCALE | SCALE= |

## ProDOS Global Page

| Address | Name | Description |
|---------|------|-------------|
| $BF00 | MLI | ProDOS MLI call |
| $BF06 | DATETIME | ProDOS date/time routine |

## DOS 3.3 Page-3 Vectors

| Address | Name | Description |
|---------|------|-------------|
| $03D0 | DOSWARM | DOS warm start |
| $03D3 | DOSCOLD | DOS cold start |
| $03D6 | FILEMGR | DOS file manager |
| $03D9 | RWTS | RWTS entry |
| $03DC | FMPARMS | Locate FM parameter list |
| $03E3 | RWTSPARMS | Locate RWTS parameter list |
| $03EA | DOSHOOK | Reconnect DOS I/O hooks |

## Applesoft Zero-Page Routines

| Address | Name | Description |
|---------|------|-------------|
| $00B1 | CHRGET | Get next Applesoft char |
| $00B7 | CHRGOT | Get current char |

## ProDOS MLI Commands

Calling convention: `JSR $BF00` followed by one command byte and a 2-byte
pointer to the parameter block; execution resumes after those 3 bytes.
Carry set on return = error, code in A. The disassembler emits the inline
bytes as `.byte`/`.word` and names the call.

| Code | Name | Description |
|------|------|-------------|
| $40 | ALLOC_INTERRUPT | Install interrupt handler |
| $41 | DEALLOC_INTERRUPT | Remove interrupt handler |
| $65 | QUIT | Quit to selector / next SYS program |
| $80 | READ_BLOCK | Read 512-byte block |
| $81 | WRITE_BLOCK | Write 512-byte block |
| $82 | GET_TIME | Read clock into $BF90 |
| $C0 | CREATE | Create file |
| $C1 | DESTROY | Delete file |
| $C2 | RENAME | Rename file |
| $C3 | SET_FILE_INFO | Set file info |
| $C4 | GET_FILE_INFO | Get file info |
| $C5 | ONLINE | List online volumes |
| $C6 | SET_PREFIX | Set prefix |
| $C7 | GET_PREFIX | Get prefix |
| $C8 | OPEN | Open file (1K I/O buffer) |
| $C9 | NEWLINE | Set newline mode |
| $CA | READ | Read from file |
| $CB | WRITE | Write to file |
| $CC | CLOSE | Close file |
| $CD | FLUSH | Flush file buffer |
| $CE | SET_MARK | Set file position |
| $CF | GET_MARK | Get file position |
| $D0 | SET_EOF | Set end of file |
| $D1 | GET_EOF | Get end of file |
| $D2 | SET_BUF | Move I/O buffer |
| $D3 | GET_BUF | Get I/O buffer address |
## Calling Conventions Worth Knowing

- **COUT ($FDED)**: character in A with the **high bit set** for normal text
  (`ORA #$80`). Output goes through CSW ($36/$37), so DOS/ProDOS/80-col
  firmware can intercept it.
- **RDKEY ($FD0C)**: returns the key in A with the high bit set; goes through
  KSW ($38/$39).
- **PRBYTE ($FDDA) / PRHEX ($FDE3)**: print A as hex. Clobbers A.
- **WAIT ($FCA8)**: delay of about (26 + 27A + 5A²)/2 cycles for A.
- **MOVE ($FE2C)**: copy A1..A2 to A4 with Y = 0 on entry.
- **STROUT ($DB3A)**: prints a zero-terminated string at A (lo) / Y (hi).
- **HPOSN ($F411)**: X/Y = horizontal lo/hi, A = vertical; sets up for HPLOT.

## Common Apple II Idioms

### Keyboard wait
```
WAIT    LDA $C000      ; KBD: bit 7 set when a key is ready
        BPL WAIT
        STA $C010      ; KBDSTRB: acknowledge
```

### Speaker tone
```
TONE    LDA $C030      ; toggle speaker
        LDX #PITCH
DLY     DEX
        BNE DLY
        DEY
        BNE TONE
```

### Enter hi-res page 1 full screen
```
        LDA $C050      ; TXTCLR: graphics
        LDA $C052      ; MIXCLR: full screen
        LDA $C054      ; TXTPAGE1
        LDA $C057      ; HIRES
```

### Enable language card RAM bank 2 read/write
```
        LDA $C083      ; must be read twice
        LDA $C083
```

### ProDOS MLI call
```
        JSR $BF00
        .byte $C8      ; OPEN
        .word PARMS
        BCS ERROR
```

### Slot-relative Disk II I/O
```
        LDX #$60       ; slot 6 * 16
        LDA $C089,X    ; motor on
        LDA $C08E,X    ; read mode
READ    LDA $C08C,X    ; data latch
        BPL READ       ; wait for a full nibble
```

### PC-relative data via the stack
```
        JSR PRINT      ; inline string follows the JSR
        .byte "HELLO",0
PRINT   PLA            ; return address - 1 is the string start - 1
        STA PTR
        PLA
        STA PTR+1
```
These inline-argument routines confuse any disassembler: bytes after the
JSR get traced as code. Add the routine to `INLINE_ARG_CALLS` in
`tools/dasm6502.py`, or re-run with `--entry` for the real continuation
address.

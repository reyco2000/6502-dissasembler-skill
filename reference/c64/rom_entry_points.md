# Commodore 64 ROM / KERNAL Entry Points Reference

Every KERNAL entry in the table below is a 3-byte `JMP` in ROM at $FF81-$FFF3.
The "Real" address is where the code actually lives; patching the jump table is
a common way to wedge the KERNAL. BASIC entry points live in the BASIC ROM at
$A000-$BFFF plus a small block at $E37B-$E4D2 inside the KERNAL ROM.

## KERNAL Jump Table ($FF81-$FFF3)

| Address | Name | Description |
|---------|------|-------------|
| $FF81 | CINT | Initialise VIC and screen editor (real $FF5B) |
| $FF84 | IOINIT | Initialise CIAs, SID volume, memory config (real $FDA3) |
| $FF87 | RAMTAS | RAM test, set screen $0400 and tape buffer $033C (real $FD50) |
| $FF8A | RESTOR | Restore default I/O vectors $0314-$0333 (real $FD15) |
| $FF8D | VECTOR | Copy vector table to/from user table (X/Y pointer) (real $FD1A) |
| $FF90 | SETMSG | Set KERNAL message switch $9D (real $FE18) |
| $FF93 | SECOND | Send secondary address after LISTEN (real $EDB9) |
| $FF96 | TKSA | Send secondary address after TALK (real $EDC7) |
| $FF99 | MEMTOP | Read/set top of BASIC memory (real $FE25) |
| $FF9C | MEMBOT | Read/set bottom of BASIC memory (real $FE34) |
| $FF9F | SCNKEY | Scan keyboard into buffer (real $EA87) |
| $FFA2 | SETTMO | Set IEEE/serial timeout (real $FE21) |
| $FFA5 | ACPTR | Read byte from serial bus (real $EE13) |
| $FFA8 | CIOUT | Write byte to serial bus (real $EDDD) |
| $FFAB | UNTLK | Send UNTALK (real $EDEF) |
| $FFAE | UNLSN | Send UNLISTEN (real $EDFE) |
| $FFB1 | LISTEN | Send LISTEN, A = device (real $ED0C) |
| $FFB4 | TALK | Send TALK, A = device (real $ED09) |
| $FFB7 | READST | Read I/O status word into A (real $FE07) |
| $FFBA | SETLFS | Set logical file, device, secondary address (real $FE00) |
| $FFBD | SETNAM | Set filename length and pointer (real $FDF9) |
| $FFC0 | OPEN | Open file (real $F34A via $031A) |
| $FFC3 | CLOSE | Close file, A = logical number (real $F291 via $031C) |
| $FFC6 | CHKIN | Set input channel, X = logical number (real $F20E via $031E) |
| $FFC9 | CHKOUT | Set output channel (real $F250 via $0320) |
| $FFCC | CLRCHN | Restore default input/output (real $F333 via $0322) |
| $FFCF | CHRIN | Read byte from current input (real $F157 via $0324) |
| $FFD2 | CHROUT | Write byte in A to current output (real $F1CA via $0326) |
| $FFD5 | LOAD | Load/verify, A = 0 load (real $F49E) |
| $FFD8 | SAVE | Save memory block (real $F5DD) |
| $FFDB | SETTIM | Set jiffy clock $A0-$A2 from A/X/Y (real $F6E4) |
| $FFDE | RDTIM | Read jiffy clock into A/X/Y (real $F6DD) |
| $FFE1 | STOP | Test STOP key, Z/C set if pressed (real $F6ED via $0328) |
| $FFE4 | GETIN | Get one byte from input (real $F13E via $032A) |
| $FFE7 | CLALL | Close all files, restore I/O (real $F32F via $032C) |
| $FFEA | UDTIM | Update jiffy clock and STOP flag (real $F69B) |
| $FFED | SCREEN | Return X = columns (40), Y = rows (25) (real $E505) |
| $FFF0 | PLOT | Get/set cursor position (real $E50A via $0334) |
| $FFF3 | IOBASE | Return CIA1 base address $DC00 in X/Y (real $E500) |

## BASIC ROM Entry Points ($A000-$BFFF)

| Address | Name | Description |
|---------|------|-------------|
| $A000 | COLD_VEC | Cold start vector: word points at $E394 |
| $A002 | WARM_VEC | Warm start vector: word points at $E37B |
| $A00C | STMDSP | Statement dispatch table, 35 words minus 1 |
| $A052 | FUNDSP | Function dispatch table, 23 words minus 1 |
| $A080 | OPTAB | Operator precedence and dispatch table |
| $A09E | RESLST | BASIC keyword list (PETSCII, bit 7 ends each) |
| $A19E | ERRMSG | BASIC error message table |
| $A328 | ERRPTR | Pointers to error messages |
| $A38A | FNDFOR | Find FOR/GOSUB entry on the stack |
| $A3B8 | BLTU | Open space in memory for a line |
| $A435 | OMERR | Print ?OUT OF MEMORY |
| $A437 | ERROR | Print error message, X = error number |
| $A480 | READY | Main input loop / READY prompt |
| $A49C | MAIN1 | Get line number, tokenise and insert line |
| $A533 | LINKPRG | Re-link BASIC program lines |
| $A560 | INLIN | Input a line from the keyboard |
| $A579 | CRUNCH | Tokenise the input buffer |
| $A613 | FNDLIN | Find a BASIC line by number |
| $A642 | SCRTCH | Perform NEW |
| $A65E | CLEAR | Perform CLR |
| $A69C | LIST | Perform LIST |
| $A717 | QPLOP | Detokenise a BASIC line (print token) |
| $A742 | FOR | Perform FOR |
| $A7AE | NEWSTT | Set up next statement for execution |
| $A7C4 | CKEOL | Check for end of program |
| $A7E1 | GONE | Execute a BASIC statement |
| $A81D | RESTORE | Perform RESTORE |
| $A82C | STOP | Perform STOP/END/break |
| $A857 | CONT | Perform CONT |
| $A871 | RUN | Perform RUN |
| $A883 | GOSUB | Perform GOSUB |
| $A8A0 | GOTO | Perform GOTO |
| $A8D2 | RETURN | Perform RETURN |
| $A8F8 | DATA | Perform DATA |
| $A928 | IF | Perform IF |
| $A93B | REM | Perform REM |
| $A94B | ON | Perform ON |
| $A96B | LINGET | Get a line number into $14/$15 |
| $A9A5 | LET | Perform LET |
| $AA80 | PRINT_HASH | Perform PRINT# |
| $AAA0 | PRINT | Perform PRINT |
| $AB1E | STROUT | Print NUL-terminated string at A (lo) / Y (hi) |
| $AB7B | GET | Perform GET |
| $ABA5 | INPUT_HASH | Perform INPUT# |
| $ABBF | INPUT | Perform INPUT |
| $AC06 | READ | Shared READ/GET/INPUT dispatcher |
| $AD1D | NEXT | Perform NEXT |
| $AD9E | FRMEVL | Evaluate expression into FAC1 |
| $AE83 | EVAL | Get next element of an expression |
| $AEF1 | PARCHK | Evaluate expression in brackets |
| $AEFA | CHKOPN | Check for "(" |
| $AEFD | CHKCOM | Check for "," |
| $AF08 | SYNERR | Print ?SYNTAX ERROR |
| $AF14 | RESVAR | Check for TI/TI$/ST |
| $AF28 | GETVAR | Find a variable by name |
| $AFA7 | CALCFUN | Evaluate a function |
| $AFE6 | ANDOR | Perform AND/OR |
| $B016 | DOREL | Perform comparison |
| $B1AA | FAC1YA | FAC1 to signed int16 in A/Y |
| $B391 | GIVAYF | Int16 in A/Y to FAC1 |
| $B7F7 | GETADR | FAC1 to unsigned int16 in $14/$15 |
| $B849 | FADDH | FAC1 += 0.5 |
| $BA8C | CONUPK | FAC2 from 4-byte memory at A/Y |
| $BBFC | MOVFA | FAC1 = FAC2 |
| $BC0C | MOVAF | Copy FAC2 = FAC1 with rounding |
| $BC1B | ROUND | Round FAC1 |
| $BC2B | SIGN | A = sign of FAC1 |
| $BC39 | SGN | FAC1 = SGN(FAC1) |
| $BC58 | ABS | FAC1 = ABS(FAC1) |
| $BC9B | QINT | FAC1 to int32 in $62-$65 |
| $BCCC | INT | FAC1 = INT(FAC1) |
| $BCF3 | FIN | Convert string to FAC1 |
| $BDCD | LINPRT | Print A/X as unsigned decimal |
| $BDDD | FOUT | FAC1 to string at $0100 |
| $BF71 | SQR | FAC1 = SQR(FAC1) |
| $BF7B | FPWRT | FAC1 = FAC2 ^ FAC1 |
| $BFED | EXP | FAC1 = EXP(FAC1) |
| $B9C1 | LOG | FAC1 = LN(FAC1) |
| $E0BE | RNDNEXT | Next random number |
| $E264 | COS | FAC1 = COS(FAC1) |
| $E268 | SIN | FAC1 = SIN(FAC1) |
| $E2B4 | TAN | FAC1 = TAN(FAC1) |
| $E20E | ATN | FAC1 = ATN(FAC1) |
| $E37B | BASIC_WARM | BASIC warm start code |
| $E394 | BASIC_COLD | BASIC cold start code |
| $E3A2 | INITAT | Reset CHRGET to the start of the program |

## KERNAL Entry Points Outside the Jump Table

| Address | Name | Description |
|---------|------|-------------|
| $E500 | IOBASE | Return CIA1 base in X/Y |
| $E505 | SCREEN | Return screen size in X/Y |
| $E50A | PLOT | Get/set cursor position |
| $EA31 | IRQ | Default IRQ handler (jiffy clock, keyboard, RS-232) |
| $EA87 | SCNKEY | Scan the keyboard matrix |
| $FCE2 | RESET | KERNAL RESET entry, initialises everything |
| $FD15 | RESTOR | Copy default vectors into $0314-$0333 |
| $FD1A | VECTOR | Copy vectors to/from user table |
| $FD50 | RAMTAS | RAM test and memory sizing |
| $FDA3 | IOINIT | CIA/SID/memory initialisation |
| $FE43 | NMI | NMI handler (RESTORE key, RS-232) |
| $FF48 | IRQ_ENTRY | IRQ/BRK entry used by the $FFFE vector |

## Calling Conventions Worth Knowing

- **CHROUT ($FFD2)**: character in A, PETSCII. Goes through the vector at
  $0326, so a wedge only has to patch $0326/$0327.
- **CHRIN ($FFCF)**: returns the next character in A; for the keyboard it waits
  for a whole line and returns it from the screen editor.
- **GETIN ($FFE4)**: returns 0 immediately if no key is waiting — this is the
  non-blocking keyboard read.
- **SETLFS/SETNAM/OPEN/CHKIN/CHROUT/CLOSE**: the canonical file output sequence.
- **LOAD ($FFD5)**: A = 0 load, non-zero verify; X/Y = load address when the
  secondary address has bit 0 clear.
- **$0314/$0315**: the IRQ vector every program should chain through; the ROM
  vector at $FFFE only points at $FF48, which is a JMP ($0314).

## Common C64 Idioms

### Wait for a key and echo it
```
WAIT    JSR $FFE4        ; GETIN
        BEQ WAIT
        JSR $FFD2        ; CHROUT
```

### Print a zero-terminated string
```
        LDA #<TEXT
        LDY #>TEXT
        JSR $AB1E        ; STROUT
TEXT    .byte "HELLO",0
```

### Chain the IRQ
```
        SEI
        LDA #<IRQ
        STA $0314
        LDA #>IRQ
        STA $0315
        CLI
IRQ     ; ... do work ...
        JMP $EA31        ; continue KERNAL IRQ work
```

### Bank out BASIC and KERNAL
```
        LDA $01
        AND #$FE         ; RAM at $A000-$BFFF
        STA $01
```

### Copy the character ROM into RAM
```
        LDA $01
        AND #$FB         ; char ROM at $D000
        STA $01
        LDX #0
COPY    LDA $D000,X
        STA $3000,X
        ...
```

## Sources

- https://sta.c64.org/cbm64krnfunc.html
- https://www.c64-wiki.com/wiki/BASIC-ROM
- https://codebase.c64.org/doku.php?id=base:asm_include_file_for_basic_routines

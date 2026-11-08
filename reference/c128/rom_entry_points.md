# Commodore 128 ROM / KERNAL Entry Points Reference

C128 mode keeps the classic Commodore jump-table addresses at $FF81-$FFF3, so
C64-era calls such as CHROUT ($FFD2) and GETIN ($FFE4) still work — but they
point at different code and run through a differently organised KERNAL. The
C128-specific calls occupy $FF47-$FF7D ("jumbo jump table").

## C128 Jumbo Jump Table ($FF47-$FF7D)

| Address | Name | Description |
|---------|------|-------------|
| $FF47 | SPINSPOUT | Set up the serial bus for fast serial, C = direction (real $E5FB) |
| $FF4A | CLOSE_ALL | Close all files on the device in A (real $F23D) |
| $FF4D | C64MODE | Switch immediately to C64 mode (real $E24B) |
| $FF50 | DMACALL | Perform a DMA call (real $F7A5) |
| $FF53 | BOOTCALL | Boot from disk: X = device, A = drive (real $F890) |
| $FF56 | FOENIX | Fast serial / FOENIX entry (real $F867) |
| $FF59 | LKUPLA | Convert logical to physical address (real $F79D) |
| $FF5C | LKUPSA | Convert secondary address (real $F786) |
| $FF5F | SWAPPER | Swap 40/80 column display (real $C02A) |
| $FF62 | DLCHR | Initialise 80-column character RAM (real $C027) |
| $FF65 | PFKEY | Program a function key (real $C021) |
| $FF68 | SETBNK | Set bank for load/save and filename (real $F73F) |
| $FF6B | SETCFG | Set MMU configuration from a table (real $F7EC) |
| $FF6E | JSRFAR | JSR to a routine in another bank (real $02CD) |
| $FF71 | JMPFAR | JMP to a routine in another bank (real $02E3) |
| $FF74 | INDFET | Banked LDA (fetchvec),Y (real $F7D0) |
| $FF77 | INDSTA | Banked STA (stavec),Y (real $F7DA) |
| $FF7A | INDCMP | Banked CMP (cmpvec),Y (real $F7E3) |
| $FF7D | PRIMM | Print the inline string following the JSR (real $FA17) |

## Standard Jump Table ($FF81-$FFF3)

| Address | Name | Description |
|---------|------|-------------|
| $FF81 | CINT | Init editor and video chips (real $C000) |
| $FF84 | IOINIT | Init I/O devices, ports, timers (real $E109) |
| $FF87 | RAMTAS | Init RAM and buffers (real $E093) |
| $FF8A | RESTOR | Restore vectors at $0314 (real $E056) |
| $FF8D | VECTOR | Change vectors for user (real $E05B) |
| $FF90 | SETMSG | Control OS messages (real $F75C) |
| $FF93 | SECOND | Send SA after LISTEN (real $E4D2) |
| $FF96 | TKSA | Send SA after TALK (real $E4E0) |
| $FF99 | MEMTOP | Set/read system RAM top (real $F763) |
| $FF9C | MEMBOT | Set/read system RAM bottom (real $F772) |
| $FF9F | KEY | Scan keyboard (real $C012) |
| $FFA2 | SETTMO | Set IEEE timeout (real $F75F) |
| $FFA5 | ACPTR | Handshake serial byte in (real $E43E) |
| $FFA8 | CIOUT | Handshake serial byte out (real $E503) |
| $FFAB | UNTLK | Serial bus UNTALK (real $E515) |
| $FFAE | UNLSN | Serial bus UNLISTEN (real $E526) |
| $FFB1 | LISTEN | Serial bus LISTEN (real $E33E) |
| $FFB4 | TALK | Serial bus TALK (real $E33B) |
| $FFB7 | READST | Read I/O status word (real $F744) |
| $FFBA | SETLFS | Set logical file parameters (real $F738) |
| $FFBD | SETNAM | Set filename (real $F731) |
| $FFC0 | OPEN | Open file (real $EFBD via $031A) |
| $FFC3 | CLOSE | Close file (real $F188 via $031C) |
| $FFC6 | CHKIN | Set input channel (real $F106 via $031E) |
| $FFC9 | CHKOUT | Set output channel (real $F14C via $0320) |
| $FFCC | CLRCHN | Restore default I/O (real $F226 via $0322) |
| $FFCF | CHRIN | Input vector (real $EF06 via $0324) |
| $FFD2 | CHROUT | Output vector (real $EF79 via $0326) |
| $FFD5 | LOAD | Load RAM from device (real $F265) |
| $FFD8 | SAVE | Save RAM to device (real $F53E) |
| $FFDB | SETTIM | Set real-time clock (real $F665) |
| $FFDE | RDTIM | Read real-time clock (real $F65E) |
| $FFE1 | STOP | Test STOP key (real $F66E via $0328) |
| $FFE4 | GETIN | Get input vector (real $EEEB via $032A) |
| $FFE7 | CLALL | Close all channels and files (real $F222 via $032C) |
| $FFEA | UDTIM | Increment real-time clock (real $F5F8) |
| $FFED | SCRORG | Return screen organisation (real $C00F) |
| $FFF0 | PLOT | Read/set cursor X/Y (real $C018) |
| $FFF3 | IOBASE | Return I/O base address (real $F781) |

## KERNAL Entry Points Outside the Jump Table

| Address | Name | Description |
|---------|------|-------------|
| $E000 | RESET | KERNAL reset code |
| $E056 | RESTOR | Restore vectors at $0314 |
| $E05B | VECTOR | Copy vectors to/from a user table |
| $E093 | RAMTAS | RAM test and buffer init |
| $E109 | IOINIT | Init I/O devices and timers |
| $E24B | C64MODE | Switch to 64 mode |
| $E5FB | SPINSPOUT | Fast serial setup |
| $E4D2 | SECOND | Send SA after LISTEN |
| $E4E0 | TKSA | Send SA after TALK |
| $EEEB | GETIN | Get a byte from the input vector |
| $EF06 | CHRIN | Read from the current input |
| $EF79 | CHROUT | Write to the current output |
| $F23D | CLOSE_ALL | Close all files on a device |
| $F265 | LOAD | Load from device |
| $F53E | SAVE | Save to device |
| $F73F | SETBNK | Set banks for load/save |
| $F781 | IOBASE | Return I/O base |
| $F7A5 | DMACALL | DMA call |
| $F7EC | SETCFG | Set MMU configuration |
| $F890 | BOOTCALL | Auto-boot from disk |
| $FA17 | PRIMM | Print inline string |
| $FA40 | NMI | NMI handler (default $0318 target) |
| $FA65 | IRQ | IRQ handler (default $0314 target) |
| $FF05 | NMI_ENTRY | NMI transfer entry |
| $FF17 | IRQ_ENTRY | IRQ transfer entry |
| $FF3D | RESET_ENTRY | RESET transfer entry |

## BASIC 7.0 ROM Entry Points ($4000-$AFFF)

| Address | Name | Description |
|---------|------|-------------|
| $4000 | BASIC_COLD | Cold entry jump |
| $4003 | BASIC_WARM | Warm entry jump |
| $4006 | BASIC_IRQ | IRQ entry jump |
| $4009 | BASIC_RESTART | BASIC restart |
| $4023 | BASIC_COLD2 | Cold start initialisation |
| $4045 | SET_CONST | Set up BASIC constants |
| $417A | SET_PCR | Set preconfiguration registers |
| $419B | STARTUP_MSG | Print the startup message |
| $4251 | SET_LINKS | Set BASIC links at $0300 |
| $4267 | LINKS_0300 | Link table for $0300 |
| $4279 | CHRGET_RAM | CHRGET code copied to $0380 |
| $430A | CRUNCH | Crunch tokens |
| $46FC | ACTION_VEC | Action vectors |
| $47D8 | FUNC_VEC | Function vectors |
| $4A82 | FIND_MSG | Find an error message |
| $4A9F | NEW_CODE | Start new BASIC code |
| $4B3F | EXEC_STMT | Execute/trace a statement |
| $4BCB | PERFORM_STOP | Perform STOP |
| $4BF7 | SETUP_FN | Set up an FN reference |
| $4D2A | PRINT_READY | Print READY |
| $4D37 | ERR_OR_READY | Error or ready |
| $4D3C | ERROR | Print an error message |
| $4DDB | BREAK_ENTRY | Break entry |
| $4DC3 | READY_BASIC | Ready for BASIC |
| $4F4F | RECHAIN | Re-chain lines |
| $4F93 | GET_INPUT | Receive an input line |
| $5064 | FIND_LINE | Find a BASIC line |
| $50E2 | PERFORM_LIST | Perform LIST |
| $51D6 | PERFORM_NEW | Perform NEW |
| $51F8 | PERFORM_CLR | Perform CLR |
| $5262 | PERFORM_RETURN | Perform RETURN |
| $52C5 | PERFORM_IF | Perform IF |
| $53A3 | PERFORM_ON | Perform ON |
| $53C6 | PERFORM_LET | Perform LET |
| $553A | PERFORM_PRINT_HASH | Perform PRINT# |
| $555A | PERFORM_PRINT | Perform PRINT |
| $5612 | PERFORM_GET | Perform GET |
| $5635 | GETKEY | Get a key |
| $5662 | PERFORM_INPUT | Perform INPUT |
| $56A9 | PERFORM_READ | Perform READ |
| $57F4 | PERFORM_NEXT | Perform NEXT |
| $587B | PERFORM_DIM | Perform DIM |
| $5885 | PERFORM_SYS | Perform SYS |
| $5901 | ASSIGN_MID | Assign MID$ |
| $59CF | PERFORM_GOSUB | Perform GOSUB |
| $59DB | PERFORM_GOTO | Perform GOTO |
| $5A3D | PERFORM_GO | Perform GO |
| $5A60 | PERFORM_CONT | Perform CONT |
| $5A9B | PERFORM_RUN | Perform RUN |
| $5ACA | PERFORM_RESTORE | Perform RESTORE |
| $5AF8 | PERFORM_RENUMBER | Perform RENUMBER |
| $5DF9 | PERFORM_FOR | Perform FOR |
| $5E87 | PERFORM_DELETE | Perform DELETE |
| $5F4D | PERFORM_TRAP | Perform TRAP |
| $5F62 | PERFORM_RESUME | Perform RESUME |
| $5FE0 | PERFORM_DO | Perform DO |
| $6039 | PERFORM_EXIT | Perform EXIT |
| $608A | PERFORM_LOOP | Perform LOOP |
| $60E1 | DEFINE_KEY | Define a programmed key |
| $610A | PERFORM_KEY | Perform KEY |
| $61A8 | PERFORM_PAINT | Perform PAINT |
| $62B7 | PERFORM_BOX | Perform BOX |
| $642B | PERFORM_SSHAPE | Perform SSHAPE |
| $658D | PERFORM_GSHAPE | Perform GSHAPE |
| $668E | PERFORM_CIRCLE | Perform CIRCLE |
| $6797 | PERFORM_DRAW | Perform DRAW |
| $67D7 | PERFORM_CHAR | Perform CHAR |
| $6955 | PERFORM_LOCATE | Perform LOCATE |
| $6960 | PERFORM_SCALE | Perform SCALE |
| $69E2 | PERFORM_COLOR | Perform COLOR |
| $6A79 | PERFORM_SCNCLR | Perform SCNCLR |
| $6B5A | PERFORM_GRAPHIC | Perform GRAPHIC |
| $6BC9 | PERFORM_BANK | Perform BANK |
| $6BD7 | PERFORM_SLEEP | Perform SLEEP |
| $6C2D | PERFORM_WAIT | Perform WAIT |
| $6C4F | PERFORM_SPRITE | Perform SPRITE |
| $6CC6 | PERFORM_MOVSPR | Perform MOVSPR |
| $6DE1 | PERFORM_PLAY | Perform PLAY |

## Monitor and Editor ROM Entry Points

| Address | Name | Description |
|---------|------|-------------|
| $B000 | MONITOR | Machine language monitor entry |
| $B003 | BRK_ENTRY | Monitor BRK entry (default $0316 target) |
| $B006 | MLM | Monitor link used by $032E |
| $C000 | CINT | Initialise editor and video chips |
| $C00F | SCRORG | Return screen organisation |
| $C012 | KEY | Scan the keyboard |
| $C018 | PLOT | Read/set cursor X/Y |
| $C021 | PFKEY | Program a function key |
| $C027 | DLCHR | Initialise 80-column character RAM |
| $C02A | SWAPPER | Swap 40/80 column display |

## Calling Conventions Worth Knowing

- **CHROUT ($FFD2)**: same call as the C64, but the code is at $EF79 and the
  editor is 40/80-column aware.
- **PRIMM ($FF7D)**: prints the bytes that follow the JSR until a 0 byte; the
  return address is adjusted. This is the canonical "inline string" call.
- **JSRFAR ($FF6E)**: $02 = bank, $03/$04 = target address (hi/lo order is
  reversed from the usual convention: $03 hi, $04 lo).
- **SETBNK ($FF68)**: A = bank for data, X = bank for the filename.
- **C64MODE ($FF4D)**: no return; the machine comes back up in C64 mode.
- **$0314/$0315**: the IRQ vector (default $FA65), chainable as on the C64.

## Common C128 Idioms

### Print an inline string
```
        JSR $FF7D        ; PRIMM
        .byte "HELLO",$0D,0
```

### Call a routine in another bank
```
        LDA #1           ; bank
        STA $02
        LDA #<$2000
        STA $04
        LDA #>$2000
        STA $03
        JSR $FF6E        ; JSRFAR
```

### Switch to full RAM in bank 1
```
        LDA #$7F
        STA $FF00        ; MMU CR: bank 1, all RAM
```

### Go to C64 mode
```
        JMP $FF4D
```

## Sources

- https://www.zimmers.net/anonftp/pub/cbm/maps/C128rom.txt
- https://c128lib.github.io/Reference/E000
- https://www.c64-wiki.com/wiki/Commodore_128/Memory_Model
- cc65 `asminc/c128.inc`

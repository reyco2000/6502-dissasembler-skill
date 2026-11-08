# Commodore VIC-20 ROM / KERNAL Entry Points Reference

The VIC-20 KERNAL jump table sits at $FF8A-$FFF3 and — unlike the C64 — has no
$FF81/$FF84/$FF87 entries: CINT, IOINIT and RAMTAS are only reachable through
their real addresses or through the RESET entry at $FD22. The routine addresses
also differ from the C64 (for example SCNKEY is $EB1E, not $EA87).

## KERNAL Jump Table ($FF8A-$FFF3)

| Address | Name | Description |
|---------|------|-------------|
| $FF8A | RESTOR | Restore default vectors at $0314 (real $FD52) |
| $FF8D | VECTOR | Change vectors for user (real $FD57) |
| $FF90 | SETMSG | Control KERNAL messages (real $FE66) |
| $FF93 | SECOND | Send secondary address after LISTEN (real $EEC0) |
| $FF96 | TKSA | Send secondary address after TALK (real $EECE) |
| $FF99 | MEMTOP | Set/read top of BASIC memory (real $FE73) |
| $FF9C | MEMBOT | Set/read bottom of BASIC memory (real $FE82) |
| $FF9F | SCNKEY | Scan keyboard (real $EB1E) |
| $FFA2 | SETTMO | Set IEEE/serial timeout (real $FE6F) |
| $FFA5 | ACPTR | Handshake serial byte in (real $EF19) |
| $FFA8 | CIOUT | Handshake serial byte out (real $EEE4) |
| $FFAB | UNTALK | Serial bus UNTALK (real $EEF6) |
| $FFAE | UNLSN | Serial bus UNLISTEN (real $EF04) |
| $FFB1 | LISTEN | Serial bus LISTEN, A = device (real $EE17) |
| $FFB4 | TALK | Serial bus TALK, A = device (real $EE14) |
| $FFB7 | READST | Read I/O status word (real $FE57) |
| $FFBA | SETLFS | Set logical file parameters (real $FE50) |
| $FFBD | SETNAM | Set filename (real $FE49) |
| $FFC0 | OPEN | Open file (real $F40A via $031A) |
| $FFC3 | CLOSE | Close file (real $F34A via $031C) |
| $FFC6 | CHKIN | Set input channel (real $F2C7 via $031E) |
| $FFC9 | CHKOUT | Set output channel (real $F309 via $0320) |
| $FFCC | CLRCHN | Restore default I/O (real $F353 via $0322) |
| $FFCF | CHRIN | Input vector, read a byte (real $F20E via $0324) |
| $FFD2 | CHROUT | Output vector, write A (real $F27A via $0326) |
| $FFD5 | LOAD | Load RAM from device (real $F542) |
| $FFD8 | SAVE | Save RAM to device (real $F675) |
| $FFDB | SETTIM | Set real-time clock (real $F767) |
| $FFDE | RDTIM | Read real-time clock (real $F760) |
| $FFE1 | STOP | Test STOP key (real $F770 via $0328) |
| $FFE4 | GETIN | Get key from keyboard (real $F1F5 via $032A) |
| $FFE7 | CLALL | Close all channels and files (real $F3EF via $032C) |
| $FFEA | UDTIM | Increment real-time clock (real $F734) |
| $FFED | SCREEN | Return screen organisation (real $E505) |
| $FFF0 | PLOT | Read/set cursor X/Y position (real $E50A) |
| $FFF3 | IOBASE | Return I/O base address (real $E500) |

## KERNAL Entry Points Outside the Jump Table

| Address | Name | Description |
|---------|------|-------------|
| $E500 | IOBASE | Return VIA base address |
| $E505 | SCREEN | Return screen size in X/Y |
| $E50A | PLOT | Get/set cursor position |
| $FD22 | RESET | Power-up RESET entry (vector target) |
| $FD3F | CHKA0 | Check for the A-ROM signature |
| $FD52 | RESTOR | Restore KERNAL vectors at $0314 |
| $FD57 | VECTOR | Copy vectors to/from a user table |
| $FD8D | RAMTAS | Initialise system constants |
| $FDF9 | IOINIT | Initialise I/O devices and timers |
| $FE49 | SETNAM | Set filename |
| $FE50 | SETLFS | Set logical file parameters |
| $FE57 | READST | Read I/O status word |
| $FE66 | SETMSG | Control OS messages |
| $FE6F | SETTMO | Set IEEE timeout |
| $FE73 | MEMTOP | Set/read top of memory |
| $FE82 | MEMBOT | Set/read bottom of memory |
| $FEA9 | NMI_ENTRY | NMI transfer entry (vector target) |
| $FED2 | BRK_ENTRY | Warm start BASIC via the BRK vector |
| $FF72 | IRQ_ENTRY | IRQ transfer entry (vector target) |

## BASIC ROM Entry Points ($C000-$DFFF)

The VIC-20 BASIC is Microsoft BASIC 2.0, nearly identical to the C64's but
relocated: add $2000 to a C64 BASIC address to get the VIC-20 address for most
routines (for example C64 $A7AE → VIC-20 $C7AE).

| Address | Name | Description |
|---------|------|-------------|
| $C000 | RESTART_VEC | BASIC restart vectors |
| $C00C | STMDSP | Statement dispatch table |
| $C052 | FUNDSP | Function dispatch table |
| $C080 | OPTAB | Operator dispatch table |
| $C09E | RESLST | BASIC keyword list |
| $C19E | ERRMSG | Error message table |
| $C328 | ERRPTR | Error message pointers |
| $C437 | ERROR | Error routine, X = error number |
| $C469 | ERRFIN | Break entry |
| $C474 | READY | Restart BASIC / READY prompt |
| $C480 | MAIN | Input and identify a BASIC line |
| $C49C | MAIN1 | Get line number and tokenise |
| $C533 | LINKPRG | Re-chain BASIC lines |
| $C560 | INLIN | Input a line into the buffer |
| $C579 | CRUNCH | Tokenise the input buffer |
| $C613 | FNDLIN | Search for a line number |
| $C642 | SCRTCH | Perform NEW |
| $C65E | CLEAR | Perform CLR |
| $C69C | LIST | Perform LIST |
| $C742 | FOR | Perform FOR |
| $C7AE | NEWSTT | BASIC warm start / next statement |
| $C7E1 | GONE | Prepare to execute a statement |
| $C81D | RESTOR | Perform RESTORE |
| $C82C | STOP | Perform STOP/END |
| $C857 | CONT | Perform CONT |
| $C871 | RUN | Perform RUN |
| $C883 | GOSUB | Perform GOSUB |
| $C8A0 | GOTO | Perform GOTO |
| $C8D2 | RETURN | Perform RETURN |
| $C8F8 | DATA | Perform DATA |
| $C906 | DATAN | Search for the next statement |

## Calling Conventions Worth Knowing

- **CHROUT ($FFD2)**: character in A, PETSCII, through $0326.
- **GETIN ($FFE4)**: non-blocking key read, returns 0 when no key is waiting.
- **SETLFS/SETNAM/OPEN/CHKIN/CHROUT/CLOSE**: same sequence as the C64, with
  different real addresses (OPEN is $F40A, not $F34A).
- **LOAD ($FFD5)**: A = 0 loads, non-zero verifies; X/Y = address when the
  secondary address has bit 0 clear.
- **$0314/$0315**: the IRQ vector to chain; the ROM vector at $FFFE only points
  at the IRQ transfer entry at $FF72.

## Common VIC-20 Idioms

### Non-blocking key read
```
WAIT    JSR $FFE4        ; GETIN
        BEQ WAIT
        JSR $FFD2        ; CHROUT
```

### Print a zero-terminated string via BASIC
```
        LDA #<TEXT
        LDY #>TEXT
        JSR $CB1E        ; VIC-20 STROUT ($C000 + $1B1E)
TEXT    .byte "HELLO",0
```

### Screen colour
```
        LDA #$1B         ; light blue border, white background
        STA $900F
```

## Sources

- https://gbppr.net/iirg/vic20-rom.html (jump table, real addresses, BASIC entries)
- https://sleepingelephant.com/denial/wiki/index.php/Memory_Map
- cc65 `asminc/vic20.inc`

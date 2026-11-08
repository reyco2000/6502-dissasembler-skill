# Atari 400 ROM / OS Entry Points Reference

The Atari OS exposes one fixed call table at $E400-$E48F. It is identical in
OS-B and the XL/XE OS; OS-A lacks some of the later entries marked "rev 2".
Handlers are also callable directly through per-device vector tables at
$E400-$E44F, and the floating point package is at $D800.

## Machine Profile

| Field | Value |
|-------|-------|
| Model | Atari 400 |
| OS ROM | OS-A (1979) or OS-B (rev B, 1981), 10K at $D800-$FFFF |
| OS window | 10K at $D800-$FFFF |
| BASIC | No built-in BASIC — BASIC is a cartridge at $A000-$BFFF |

## OS Jump Table ($E450-$E48F)

| Address | Name | Description |
|---------|------|-------------|
| $E450 | DISKIV | Initialise the disk interface |
| $E453 | DSKINV | Disk interface entry |
| $E456 | CIOV | Central I/O: X = IOCB offset (0-$70) |
| $E459 | SIOV | Serial I/O bus |
| $E45C | SETVBV | Set vertical blank parameters (X = immediate/deferred) |
| $E45F | SYSVBV | Immediate vertical blank handler |
| $E462 | XITVBV | Deferred vertical blank exit |
| $E465 | SIOINV | Initialise SIO |
| $E468 | SENDEV | Enable the SEND interrupt |
| $E46B | INTINV | Initialise the interrupt handler |
| $E46E | CIOINV | Initialise CIO |
| $E471 | BLKBDV | Power-up display ("Memo Pad") |
| $E474 | WARMSV | Warm start |
| $E477 | COLDSV | Cold start (RESET vector target) |
| $E47A | RBLOKV | Read a cassette block |
| $E47D | CSOPIV | Open cassette for input |
| $E480 | PUPDIV | Power-up display vector (rev 2) |
| $E483 | SLFTSV | Self-test entry (rev 2) |
| $E486 | PHENTV | Enter peripheral handler (rev 2) |
| $E489 | PHUNLV | Unlink peripheral handler (rev 2) |
| $E48C | PHINIV | Initialise peripheral handler (rev 2) |
| $E48F | GPDVV | Generic parallel device handler vector (rev 2) |

## Floating Point Package ($D800-$DFFF)

| Address | Name | Description |
|---------|------|-------------|
| $D800 | AFP | Convert ASCII to floating point |
| $D8E6 | FASC | Convert floating point to ASCII |
| $D9AA | IFP | Convert integer to floating point |
| $D9D2 | FPI | Convert floating point to integer |
| $DA44 | ZFR0 | Zero FR0 |
| $DA46 | ZF1 | Zero floating point number 1 |
| $DA60 | FSUB | Subtract floating point numbers |
| $DA66 | FADD | Add floating point numbers |
| $DADB | FMUL | Multiply floating point numbers |
| $DB28 | FDIV | Divide floating point numbers |
| $DD40 | PLYEVL | Evaluate a floating point polynomial |
| $DD89 | FLD0R | Load FR0 from memory |
| $DD8D | FLD0P | Load FR0 from a pointer |
| $DD98 | FLD1R | Load FR1 from memory |
| $DD9C | PLD1P | Load FR1 from a pointer |
| $DDA7 | FST0R | Store FR0 to memory |
| $DDAB | FST0P | Store FR0 through a pointer |
| $DDB6 | FMOVE | Move a floating point number |
| $DDC0 | EXP | Floating point exponential |
| $DDCC | EXP10 | Base-10 exponential |
| $DECD | LOG | Natural logarithm |
| $DED1 | LOG10 | Base-10 logarithm |

## Device Handler Vector Tables ($E400-$E44F)

Each handler vector table is six words in the fixed order OPEN, CLOSE, GET,
PUT, STATUS, SPECIAL. The addresses below are the table bases; read the word at
the slot to reach the routine.

| Address | Name | Description |
|---------|------|-------------|
| $E400 | EDITRV | Editor handler vectors: +0 OPEN, +2 CLOSE, +4 GET, +6 PUT, +8 STATUS, +A SPECIAL |
| $E410 | SCRENV | Screen handler vectors: same six-word layout |
| $E420 | KEYBDV | Keyboard handler vectors: same six-word layout |
| $E430 | PRINTV | Printer handler vectors: same six-word layout |
| $E440 | CASETV | Cassette handler vectors: same six-word layout |

## Character Set and International Support (XL/XE)

| Address | Name | Description |
|---------|------|-------------|
| $CC00 | ICSORG | International character set (inside the XL OS ROM) |
| $E000 | DCSORG | Domestic character set origin |

## Call Conventions Worth Knowing

- **CIOV ($E456)**: X = IOCB offset ($00, $10, ... $70). Fill ICCOM, ICBAL/H,
  ICBLL/H and ICAX1/2 in the IOCB first. Returns status in ICSTA and Y.
- **SIOV ($E459)**: DCB at $0300-ish; X = $00 for immediate, $40 read, $80 write
  frame. Returns Y = status ($01 = success).
- **SETVBV ($E45C)**: X = 7 for the immediate VBLANK vector, 6 for the deferred
  one, Y/A = address lo/hi.
- **COLDSV ($E477)**: full cold start; WARMSV ($E474) keeps DOS and files.
- **BLKBDV ($E471)**: the built-in "Memo Pad" (not available on the 1200XL,
  which has no such mode).
- The floating point package uses FR0 ($D4) and FR1 ($E0) in zero page; load
  with FLD0R/FLD1R and call FADD/FSUB/FMUL/FDIV directly.

## Common Atari 8-bit Idioms

### Write a character to the screen editor
```
        LDA #'A'
        LDX #$00         ; IOCB 0 = editor
        STA $0342,X      ; ICCOM = PUTCHR
        LDA #$00
        STA $0348,X      ; ICBLL
        ...
        JSR $E456        ; CIOV
```

### Wait for vertical blank
```
WAIT    LDA $D40B        ; VCOUNT
        CMP #$7D
        BNE WAIT
```

### Set up a deferred VBLANK
```
        LDA #<VBL
        LDY #>VBL
        LDX #7
        JSR $E45C        ; SETVBV
```

### Bank out the OS and BASIC (XL/XE)
```
        LDA $D301
        AND #$FE         ; bit 0 = 0: RAM at $C000-$FFFF
        STA $D301
```

## Sources

- https://atariwiki.org/wiki/Wiki.jsp?page=Atari%20800%20Assembler%20Equates
- cc65 `asminc/atari.inc` (OS vector and floating point equates)
- https://atariwiki.org/wiki/Wiki.jsp?page=PORTB
- Mapping the Atari, revised edition (OS entry points appendix)

# BBC Micro Model B ROM / OS Entry Points Reference

The BBC MOS exposes its API at fixed addresses in the last 256 bytes of the MOS
ROM. MOS 1.20, 2.00 and 3.20 keep the same entry addresses, so code written for
a Model B runs on a Master; only the code behind the jumps changes. The tables
below are from the MOS 1.20 disassembly (Model A/B); the "real" targets are
MOS 1.20 addresses.

## OS Call Table ($FFB9-$FFF7)

| Address | Name | Description |
|---------|------|-------------|
| $FFB9 | OSRDRM | Read a byte from a sideways ROM (real $DC0B) |
| $FFBC | VDUCHR | Send a character to the VDU driver (real $C4C0) |
| $FFBF | OSEVEN | Generate an event (real $E494) |
| $FFC2 | GSINIT | Initialise an OS string (real $EA1E) |
| $FFC5 | GSREAD | Read a character from an OS string (real $EA2F) |
| $FFC8 | NVRDCH | Non-vectored OSRDCH (real $DEC5) |
| $FFCB | NVWRCH | Non-vectored OSWRCH (real $E0A4) |
| $FFCE | OSFIND | Open or close a file (JMP ($021C)) |
| $FFD1 | OSGBPB | Transfer a block to/from a file (JMP ($021A)) |
| $FFD4 | OSBPUT | Write a byte to a file (JMP ($0218)) |
| $FFD7 | OSBGET | Read a byte from a file (JMP ($0216)) |
| $FFDA | OSARGS | Read/write file arguments (JMP ($0214)) |
| $FFDD | OSFILE | Read/write a whole file (JMP ($0212)) |
| $FFE0 | OSRDCH | Read a byte from the current input (JMP ($0210)) |
| $FFE3 | OSASCI | Output A, expanding CR to LF/CR |
| $FFE7 | OSNEWL | Output a CR/LF |
| $FFEC | OSWRCR | Output a CR |
| $FFEE | OSWRCH | Write a character to the VDU stream (JMP ($020E)) |
| $FFF1 | OSWORD | Perform an OSWORD operation (JMP ($020C)) |
| $FFF4 | OSBYTE | Perform an OSBYTE operation (JMP ($020A)) |
| $FFF7 | OSCLI | Pass a string to the command line interpreter (JMP ($0208)) |

## Other MOS ROM Entry Points

| Address | Name | Description |
|---------|------|-------------|
| $FF00 | XUSERV | Extended vector: user |
| $FF03 | XBRKV | Extended vector: BRK |
| $FF06 | XIRQ1V | Extended vector: IRQ1 |
| $FF09 | XIRQ2V | Extended vector: IRQ2 |
| $FF0C | XCLIV | Extended vector: OSCLI |
| $FF0F | XBYTEV | Extended vector: OSBYTE |
| $FF12 | XWORDV | Extended vector: OSWORD |
| $FF15 | XWRCHV | Extended vector: OSWRCH |
| $FF18 | XRDCHV | Extended vector: OSRDCH |
| $FF1B | XFILEV | Extended vector: OSFILE |
| $FF1E | XARGSV | Extended vector: OSARGS |
| $FF21 | XBGETV | Extended vector: OSBGET |
| $FF24 | XBPUTV | Extended vector: OSBPUT |
| $FF27 | XGBPBV | Extended vector: OSGBPB |
| $FF2A | XFINDV | Extended vector: OSFIND |
| $FF2D | XFSCV | Extended vector: filing system control |
| $FF30 | XEVENTV | Extended vector: event |
| $FF33 | XUPTV | Extended vector: up-call |
| $FF36 | XNETV | Extended vector: Econet |
| $FF39 | XVDUV | Extended vector: VDU |
| $FF3C | XKEYV | Extended vector: keyboard |
| $FF3F | XINSV | Extended vector: insert character |
| $FF42 | XREMV | Extended vector: remove character |
| $FF45 | XCNPV | Extended vector: count/purge |
| $FF48 | XIND1V | Extended vector: spare 1 |
| $FF4B | XIND2V | Extended vector: spare 2 |
| $FF4E | XIND3V | Extended vector: spare 3 |
| $FF51 | XVECTOR | Common extended-vector dispatcher (JSR target of $FF00-$FF4E) |
| $FF89 | XVECTOR_RET | Return path from a ROM-routed extended vector |
| $FFA7 | FASTBPUT | OSBYTE &9D fast BPUT |
| $FFAA | FRED_READ | OSBYTE &92 read a byte from FRED |
| $FFAE | JIM_READ | OSBYTE &94 read a byte from JIM |
| $FFB2 | SHEILA_READ | OSBYTE &96 read a byte from SHEILA |
| $FFB6 | VECTAB | Default vector table descriptor (length 36, address $D928) |
| $D9CD | RESET | System startup: default vectors, find ROMs, enter a language |
| $DC1C | IRQ_MAIN | Main IRQ routines, timed INKEY, OSRDCH dispatch |
| $DF0C | OSCLI_WRCH | OSCLI and OSWRCH dispatch |
| $E6B0 | OSBYTE_DISP | OSBYTE/OSWORD dispatch table and handlers |
| $E887 | SOUND | Sound system, SOUND, ENVELOPE, BELL |
| $EEDA | KEYBOARD | Keyboard scanning |
| $F135 | CFS | ROM/cassette filing system: ARGS, FSC, FILE, RUN, CAT |

## How a Sideways ROM Is Entered

| Address | Name | Description |
|---------|------|-------------|
| $8000 | ROM_LANG | Language entry point: normally a 3-byte JMP |
| $8003 | ROM_SERVICE | Service entry point: normally a 3-byte JMP |
| $8006 | ROM_TYPE | Type byte: b7 service entry, b6 language entry, b5 Tube address, b3-b0 CPU type |
| $8007 | ROM_COPYOFF | Offset from $8000 to the copyright string |
| $8008 | ROM_VERSION | Binary version number |
| $8009 | ROM_TITLE | Title string, NUL terminated |

On reset the MOS scans all 16 banks, disables sockets without a valid header and
then calls each ROM's service entry with A = service number, X = ROM number,
Y = remaining bytes on the stack. Well-known service calls: &00 reset, &01
absolute workspace claim, &02 private workspace claim, &03 auto-boot, &04
unrecognised *command, &05 *HELP, &06 BRK, &08 OSWORD, &09 *HELP with a keyword.
Further calls are listed in the New Advanced User Guide and on the beebwiki.

## OSBYTE / OSWORD Numbers Worth Knowing

| Code | Name | Description |
|------|------|-------------|
| &00 | OSBYTE_VERSION | Read the OS version |
| &83 | OSBYTE_OSHWM | Read OSHWM (start of user memory) |
| &84 | OSBYTE_HIMEM | Read HIMEM (top of user memory) |
| &87 | OSBYTE_EXPLODE | Explode character definitions into RAM |
| &88 | OSBYTE_IMPLODE | Implode character definitions back into ROM |
| &A0 | OSBYTE_VDUVAR | Read a VDU variable, X = variable number |
| &A8 | OSBYTE_XVEC | Return the extended vector table base ($0D9F) in X/Y |

| Code | Name | Description |
|------|------|-------------|
| &00 | OSWORD_TIME | Read the soft clock (5 bytes) |
| &01 | OSWORD_RTC | Read/write the CMOS real-time clock (Master) |
| &05 | OSWORD_READIO | Read I/O processor memory |
| &06 | OSWORD_WRITEIO | Write I/O processor memory |
| &0A | OSWORD_READFONT | Read a font definition |
| &0B | OSWORD_WRITEFONT | Write a font definition |

## Calling Conventions Worth Knowing

- **OSWRCH ($FFEE)**: character in A. Routing goes through WRCHV ($020E/$020F),
  so a VDU driver or filter patches that vector.
- **OSBYTE ($FFF4)**: A = reason, X/Y = parameters; returns X/Y and often the
  carry flag. The MOS saves A/X/Y in $EF-$F1 during the call.
- **OSWORD ($FFF1)**: A = reason, X/Y = parameter block address.
- **OSCLI ($FFF7)**: X/Y = address of a NUL-terminated command string, or the
  carry flag set to pass an inline string.
- **OSFILE ($FFDD)**: X/Y = control block; A = reason (0 save, 1-4 load/info,
  5 read catalogue, 6 delete, 7 create, 255 load and run).
- **OSARGS ($FFDA)**: A = reason, X = file handle, Y = 0; zero page $00-$0F is
  the argument block.
- **Service entry**: entered with A = service number, X = ROM number, Y = stack
  offset to the remaining parameters. Return with A preserved and RTS.
- **$F4** always holds the currently selected ROM number; write $FE30 to change
  banks, and never write $FE30 while running from sideways ROM unless the code
  is copied to RAM first.

## Common BBC Micro Idioms

### Print a character
```
        LDA #'A'
        JSR $FFEE        ; OSWRCH
```

### Read a line of input
```
        LDX #0
READ    JSR $FFE0        ; OSRDCH
        CMP #$0D
        BEQ DONE
        STA BUFFER,X
        INX
        BNE READ
DONE    ...
```

### Call an OSBYTE
```
        LDA #$83         ; read OSHWM
        LDX #0
        LDY #$FF
        JSR $FFF4        ; OSBYTE
        STX OSHWM_LO
        STY OSHWM_HI
```

### Claim the WRCHV vector
```
        SEI
        LDA $020E
        STA OLDWRCH
        LDA $020F
        STA OLDWRCH+1
        LDA #<MYWRCH
        STA $020E
        LDA #>MYWRCH
        STA $020F
        CLI
```

### Select a sideways ROM bank
```
        LDA #15
        STA $FE30        ; ROMSEL: bank 15
```

## Sources

- http://mdfs.net/Docs/Comp/BBC/OS1-20/FC00 (MOS 1.20 OS calls, extended vectors, hardware)
- https://mdfs.net/Docs/Comp/BBC/OS1-20/ (MOS 1.20 disassembly index)
- https://beebwiki.mdfs.net/Paged_ROM (ROM headers, service entry, language entry)
- https://kieranhj.github.io/llm-beeb-wiki/memory/os-workspace (page 2/3 layout)
- https://kieranhj.github.io/llm-beeb-wiki/memory/zero-page
- https://acorn.huininga.nl/pub/docs/txtfiles/Master%20128.txt

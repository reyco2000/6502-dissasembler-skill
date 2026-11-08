# BBC Master 128 Memory Map Reference

Tables with a single `$XX` / `$XXXX` in the first column are the rows a tool
like `tools/annotator.py` can parse: 2-digit rows are zero page, 4-digit rows are
either hardware registers or system vectors/variables. Range rows (`$XXXX-$YYYY`)
are documentation only. Keep one row per address — a second row for the same
address silently overwrites the first when the tables are loaded.

## Machine Profile

| Field | Value |
|-------|-------|
| Model | BBC Master 128 |
| RAM | 128K: 32K main + 20K LYNNE shadow + 4K ANDY + 8K HAZEL + second 32K workspace |
| MOS / BASIC | MOS 3.20 with BASIC IV, ADFS, EDIT, VIEW, ViewSheet, DFS and ANFS in the 128K ROM |
| Notable | 65C12 CPU, 4 x 16K sideways RAM, HAZEL/ANDY overlays, CMOS RTC, 4K private MOS workspace |
| CPU | 65C12 (65C02 + extra 65C02 instructions) |

## Address Map

| Range | Description |
|-------|-------------|
| $0000-$2FFF | 12K main RAM: zero page, stack, OS workspace, language |
| $3000-$7FFF | 20K LYNNE shadow display RAM (or main RAM) |
| $8000-$8FFF | ANDY: 4K private MOS RAM when ROMSEL bit 7 = 1, otherwise sideways ROM |
| $C000-$DFFF | HAZEL: 8K filing-system RAM overlaid on the MOS ROM when ACCCON bit 3 = 1 |
| $DC00-$DCFF | MOS CLI buffer (in the second 32K) |
| $DD00-$DEFF | Transient utility workspace (*MOVE) |
| $DF00-$DFFF | MOS private workspace |
| $8000-$BFFF | Paged (sideways) ROM/RAM — one of 16 banks, selected by ROMSEL |
| $C000-$FBFF | MOS ROM (15K of the 16K part; the I/O hole follows) |
| $FC00-$FCFF | FRED — 1 MHz bus memory-mapped I/O |
| $FD00-$FDFF | JIM — 1 MHz bus memory expansion page |
| $FE00-$FEFF | SHEILA — MOS memory-mapped I/O |
| $FF00-$FFFF | MOS ROM tail: extended vectors $FF00-$FF4E, OS calls $FFB9-$FFF7, 6502 vectors |

ACCCON ($FE34) bits: 7 IRR, 6 TST, 5 IFJ, 4 ITU, 3 Y (HAZEL), 2 X (unconditional
shadow), 1 E (auto-shadow), 0 D (display from shadow).

Two rows can describe the same range at different times: with ACCCON bit 3 set
the CPU sees HAZEL RAM at $C000-$DFFF, with it clear it sees the MOS 3.20 ROM
there. Likewise ROMSEL bit 7 swaps ANDY RAM over $8000-$8FFF.

## Zero Page

| Address | Name | Description |
|---------|------|-------------|
| $00 | LANGWS | Language workspace base ($00-$6F belongs to the current language) |
| $70 | USERZP | User zero page, 32 bytes ($70-$8F), free for machine code |
| $90 | ECONET_ZP | Econet workspace ($90-$9F) |
| $A0 | NMI_ZP | Filing system NMI workspace ($A0-$A7) |
| $A8 | OS_SCRATCH | OS temporary scratch ($A8-$AF) |
| $B0 | FS_SCRATCH | Filing system scratch ($B0-$BF) |
| $C0 | FS_WORK | Filing system workspace ($C0-$CF) |
| $D0 | STATS | VDU status byte (same as OSBYTE &75) |
| $D1 | ZMASK | Current graphics-point bit mask |
| $D2 | ZORA | Text colour OR mask |
| $D3 | ZEOR | Text colour EOR mask |
| $D4 | GORA | Graphics colour OR mask |
| $D5 | GEOR | Graphics colour EOR mask |
| $D6 | GCELL | Graphics character cell lo |
| $D7 | GCELL+1 | Graphics character cell hi |
| $D8 | SCANTOP | Top scan line lo |
| $D9 | SCANTOP+1 | Top scan line hi |
| $E7 | REPEAT | Auto-repeat countdown |
| $EA | SERTIME | Serial timeout counter |
| $EC | KEYLAST | Last key press (internal key number) |
| $ED | KEYPREV | Penultimate key press |
| $EE | JIM_PAGE | 1 MHz bus paging register copy |
| $EF | OSBYTE_A | OSBYTE/OSWORD A value during a call |
| $F0 | OSBYTE_X | OSBYTE/OSWORD X value during a call |
| $F1 | OSBYTE_Y | OSBYTE/OSWORD Y value during a call |
| $F2 | GSPTR | GSINIT/GSREAD string pointer lo |
| $F3 | GSPTR+1 | GSINIT/GSREAD string pointer hi |
| $F4 | ROMSEL_COPY | Copy of the ROM select register |
| $F5 | PHROM | Speech PHROM / RFS ROM number |
| $F6 | OSRDSC | OSRDSC address lo |
| $F7 | OSRDSC+1 | OSRDSC address hi |
| $FA | OSTMP | General OS workspace used by interrupts |
| $FB | OSTMP+1 | General OS workspace hi |
| $FC | IRQ_A | A saved during IRQ |
| $FD | ERRPTR | Error message pointer lo |
| $FE | ERRPTR+1 | Error message pointer hi |
| $FF | ESCFLAG | ESCAPE flag (bit 7) |

## Page 2 — OS Vectors

| Address | Name | Description |
|---------|------|-------------|
| $0200 | USERV | User vector (JMP instruction) |
| $0202 | BRKV | BRK vector (JMP instruction) |
| $0204 | IRQ1V | IRQ1 vector (JMP instruction) |
| $0206 | IRQ2V | IRQ2 vector (JMP instruction) |
| $0208 | CLIV | OSCLI vector (JMP instruction) |
| $020A | BYTEV | OSBYTE vector (JMP instruction) |
| $020C | WORDV | OSWORD vector (JMP instruction) |
| $020E | WRCHV | OSWRCH vector (JMP instruction) |
| $0210 | RDCHV | OSRDCH vector (JMP instruction) |
| $0212 | FILEV | OSFILE vector (JMP instruction) |
| $0214 | ARGSV | OSARGS vector (JMP instruction) |
| $0216 | BGETV | OSBGET vector (JMP instruction) |
| $0218 | BPUTV | OSBPUT vector (JMP instruction) |
| $021A | GBPBV | OSGBPB vector (JMP instruction) |
| $021C | FINDV | OSFIND vector (JMP instruction) |
| $021E | FSCV | Filing system control vector (JMP instruction) |
| $0220 | EVENTV | Event vector (JMP instruction) |
| $0222 | UPTV | Up-call vector (JMP instruction) |
| $0224 | NETV | Econet transmit vector (JMP instruction) |
| $0226 | VDUV | VDU vector (JMP instruction) |
| $0228 | KEYV | Keyboard vector (JMP instruction) |
| $022A | INSV | Insert-character vector (JMP instruction) |
| $022C | REMV | Remove-character vector (JMP instruction) |
| $022E | CNPV | Count/purge vector (JMP instruction) |
| $0230 | IND1V | Spare indirect vector 1 (JMP instruction) |
| $0232 | IND2V | Spare indirect vector 2 (JMP instruction) |
| $0234 | IND3V | Spare indirect vector 3 (JMP instruction) |
| $0D9F | EVTBASE | Extended vector table base (OSBYTE &A8 returns this) |

## Page 3 — VDU Workspace

| Address | Name | Description |
|---------|------|-------------|
| $0300 | GWMIN | Graphics window left column |
| $0302 | GWWIDTH | Graphics window width |
| $0304 | GWMINY | Graphics window bottom row |
| $0306 | GWHEIGHT | Graphics window height |
| $0308 | TWL | Text window left |
| $0309 | TWR | Text window right |
| $030A | TWT | Text window top |
| $030B | TWB | Text window bottom |
| $030C | GORIGX | Graphics origin X |
| $030E | GORIGY | Graphics origin Y |
| $0310 | GCURX | Graphics cursor X |
| $0312 | GCURY | Graphics cursor Y |
| $0318 | TEXTX | Text cursor X |
| $0319 | TEXTY | Text cursor Y |
| $031F | VDUQ | VDU queue (5 bytes) |
| $034A | CURADDR | Text cursor address for the 6845 |
| $034C | TEXTWIDTH | Text window width in bytes |
| $034E | HIMEMSH | HIMEM high byte (ignoring shadow) |
| $034F | BYTESPERCHAR | Bytes per character in the current mode |
| $0350 | SCREENSTART | Top-left screen address (hardware scroll mirror) |
| $0352 | BYTESPERROW | Bytes per character row |
| $0354 | SCREENPAGES | Screen mode size in pages |
| $0355 | SCREENMODE | Current screen mode (ignoring shadow bit) |
| $0356 | SCREENSIZE | Screen size code: 0=20K, 1=16K, 2=10K, 3=8K, 4=1K |
| $0360 | LOGCOLS | Logical colours - 1 |
| $0361 | PIXPERBYTE | Pixels per byte - 1 (0 for text) |
| $0380 | PALETTE | Colour palette copy, 1 byte per logical colour |
| $0400 | LANGMEM | Start of the current language's workspace |

## Page 2/3 Notes

Page 2 holds the OS vector table — 27 two-byte vectors at $0200-$0235, followed
by OS variables from $0236. Patching the vector (for example WRCHV at
$020E) is the supported way to intercept an OS call; the MOS keeps the real
routine address in its own table.

Page 3 is VDU workspace. The screen-start mirror at $0350/$0351 matters if you
scroll by reprogramming the 6845 directly: the OS uses it to decide where the
next character goes.

## SHEILA, FRED and JIM

## SHEILA — I/O ($FE00-$FEFF)

| Address | Name | Description |
|---------|------|-------------|
| $FE00 | CRTC_ADDR | 6845 CRTC address register (write) |
| $FE01 | CRTC_DATA | 6845 CRTC data register (write) |
| $FE02 | ULA_BORDER | Border colour (write) / border colour read |
| $FE08 | ACIA_CTRL | 6850 ACIA control (write) / status (read) |
| $FE09 | ACIA_DATA | 6850 ACIA transmit (write) / receive (read) |
| $FE10 | SERIAL_ULA | Serial ULA control register |
| $FE18 | ECONET_ID | Econet station ID (read) / ADLC disable interrupts (write) |
| $FE20 | VIDEO_ULA | Video ULA control register |
| $FE21 | VIDEO_PAL | Video ULA palette register (read/write) |
| $FE24 | FDC_CONTROL | Floppy disc control register (Master/Compact) |
| $FE28 | FDC_1770 | WD1770 FDC registers (B+/Master, $FE28-$FE2F) |
| $FE30 | ROMSEL | Paged ROM/RAM latch: bits 3-0 = bank, bit 7 = RAM select |
| $FE31 | ALTAIR | ALTAIR RAM protect |
| $FE34 | ACCCON | Access control: shadow RAM, HAZEL, Tube, FRED/JIM routing |
| $FE38 | INTOFF | Econet NMI disable (B+/Master) |
| $FE3C | INTON | Econet NMI enable (B+/Master) |
| $FE40 | SYSVIA_ORB | System 6522 output register B |
| $FE41 | SYSVIA_ORA | System 6522 output register A |
| $FE42 | SYSVIA_DDRB | System 6522 data direction B |
| $FE43 | SYSVIA_DDRA | System 6522 data direction A |
| $FE44 | SYSVIA_T1CL | System 6522 timer 1 counter lo |
| $FE45 | SYSVIA_T1CH | System 6522 timer 1 counter hi |
| $FE46 | SYSVIA_T1LL | System 6522 timer 1 latch lo |
| $FE47 | SYSVIA_T1LH | System 6522 timer 1 latch hi |
| $FE48 | SYSVIA_T2CL | System 6522 timer 2 counter lo |
| $FE49 | SYSVIA_T2CH | System 6522 timer 2 counter hi |
| $FE4A | SYSVIA_SR | System 6522 shift register |
| $FE4B | SYSVIA_ACR | System 6522 auxiliary control |
| $FE4C | SYSVIA_PCR | System 6522 peripheral control |
| $FE4D | SYSVIA_IFR | System 6522 interrupt flags |
| $FE4E | SYSVIA_IER | System 6522 interrupt enable |
| $FE4F | SYSVIA_ORB_NH | System 6522 ORB without handshake |
| $FE60 | USERVIA_ORB | User 6522 output register B |
| $FE61 | USERVIA_ORA | User 6522 output register A |
| $FE62 | USERVIA_DDRB | User 6522 data direction B |
| $FE63 | USERVIA_DDRA | User 6522 data direction A |
| $FE64 | USERVIA_T1CL | User 6522 timer 1 counter lo |
| $FE65 | USERVIA_T1CH | User 6522 timer 1 counter hi |
| $FE66 | USERVIA_T1LL | User 6522 timer 1 latch lo |
| $FE67 | USERVIA_T1LH | User 6522 timer 1 latch hi |
| $FE68 | USERVIA_T2CL | User 6522 timer 2 counter lo |
| $FE69 | USERVIA_T2CH | User 6522 timer 2 counter hi |
| $FE6A | USERVIA_SR | User 6522 shift register |
| $FE6B | USERVIA_ACR | User 6522 auxiliary control |
| $FE6C | USERVIA_PCR | User 6522 peripheral control |
| $FE6D | USERVIA_IFR | User 6522 interrupt flags |
| $FE6E | USERVIA_IER | User 6522 interrupt enable |
| $FE6F | USERVIA_ORB_NH | User 6522 ORB without handshake |
| $FE80 | FDC_CMD | 8271 FDC command (write) / status (read) |
| $FE81 | FDC_PARAM | 8271 FDC parameter (write) / result (read) |
| $FE82 | FDC_RESET | 8271 FDC reset |
| $FE84 | FDC_DATA | 8271 FDC data register |
| $FEA0 | ADLC_CR1 | 68B54 Econet ADLC control 1 / status 1 |
| $FEA1 | ADLC_CR2 | 68B54 ADLC control 2/3 / status 2/3 |
| $FEA2 | ADLC_TX1 | ADLC transmit FIFO (frame continue) / receive FIFO |
| $FEA3 | ADLC_TX2 | ADLC transmit FIFO (frame terminate) / receive FIFO |
| $FEC0 | ADC_LATCH | 7002 ADC data latch and start / status |
| $FEC1 | ADC_HI | 7002 ADC high data byte |
| $FEC2 | ADC_LO | 7002 ADC low data byte |
| $FEE0 | TUBE_FIFO1 | Tube ULA FIFO 1 status |
| $FEE1 | TUBE_FIFO1_D | Tube ULA FIFO 1 data |
| $FEE2 | TUBE_FIFO2 | Tube ULA FIFO 2 status |
| $FEE3 | TUBE_FIFO2_D | Tube ULA FIFO 2 data |
| $FEE4 | TUBE_FIFO3 | Tube ULA FIFO 3 status |
| $FEE5 | TUBE_FIFO3_D | Tube ULA FIFO 3 data |
| $FEE6 | TUBE_FIFO4 | Tube ULA FIFO 4 status |
| $FEE7 | TUBE_FIFO4_D | Tube ULA FIFO 4 data |

FRED ($FC00-$FCFF) is the 1 MHz bus I/O page: $FC00 test hardware, $FC10-$FC13
teletext, $FC14-$FC1F Prestel, $FC20-$FC27 IEEE, $FC40-$FC47 Winchester. JIM
($FD00-$FDFF) is the 1 MHz bus memory-expansion page; $FCFF is its paging
register.

## Memory Banking

- ROMSEL ($FE30): bits 3-0 select the sideways bank; bit 7 = 1 maps the 4K
  ANDY RAM at $8000-$8FFF (MOS private workspace).
- ACCCON ($FE34): bit 0 = D (6845 displays from LYNNE), bit 1 = E (auto-shadow
  when executing from $C000-$DFFF), bit 2 = X (unconditional LYNNE access),
  bit 3 = Y (HAZEL at $C000-$DFFF), bit 4 = ITU, bit 5 = IFJ, bit 6 = TST,
  bit 7 = IRR (force IRQ).
- The Master's 128K ROM is banked in 16K slices: MOS 3.20 occupies $C000-$FFFF
  and the utility ROMs (ADFS, BASIC IV, EDIT, VIEW, ViewSheet, DFS, ANFS,
  Terminal) occupy banks 8-15 of the sideways window.
- Sideways banks 4-7 are RAM on a standard Master (64K of sideways RAM), which
  is why ROM images can be soft-loaded.
- OSHWM is $0E00 with HAZEL enabled (DFS workspace moves into HAZEL).

## 6502 Hardware Vectors

| Address | Name | Description |
|---------|------|-------------|
| $FFFA | NMI | NMI vector — MOS 1.20: $0D00 (NMI handler page) |
| $FFFC | RESET | RESET vector — MOS 1.20: $D9CD (system startup) |
| $FFFE | IRQ | IRQ vector — MOS 1.20: $DC1C (main IRQ handler) |

The vector values are MOS-version specific; the addresses $FFFA-$FFFF never
change. On the Master (MOS 3.20) they point at the equivalent routines in the
$C000-$FFFF MOS ROM.

## Tooling Profile

| Field | Value |
|-------|-------|
| CPU | 65C12 |
| zero_page | $0000-$00FF (user block $70-$8F) |
| hardware | $FC00-$FEFF |
| vectors | $FFFA-$FFFF plus the RAM vectors at $0200-$0235 |
| ROM windows | $8000-$BFFF sideways, $C000-$FFFF MOS |

## Sources

- http://mdfs.net/Docs/Comp/BBC/OS1-20/FC00 (FRED/JIM/SHEILA, OS calls, vectors)
- http://mdfs.net/Docs/Comp/BBC/MemAddrs (address translation and workspace)
- https://beebwiki.mdfs.net/Paged_ROM (ROM sockets, headers, service entry)
- https://kieranhj.github.io/llm-beeb-wiki/memory/memory-map (family map)
- https://kieranhj.github.io/llm-beeb-wiki/memory/shadow-ram (ACCCON)
- https://kieranhj.github.io/llm-beeb-wiki/synthesis/model-differences
- https://acorn.huininga.nl/pub/docs/txtfiles/Master%20128.txt (Master map, ROMSEL/ACCCON)

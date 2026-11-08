# Atari 400 Memory Map Reference

Tables with a single `$XX` / `$XXXX` in the first column are the rows a tool
like `tools/annotator.py` can parse: 2-digit rows are zero page, 4-digit rows are
either hardware registers or system vectors/variables. Range rows (`$XXXX-$YYYY`)
are documentation only. Keep one row per address — a second row for the same
address silently overwrites the first when the tables are loaded.

## Machine Profile

| Field | Value |
|-------|-------|
| Model | Atari 400 |
| RAM | 16K (early units 8K): $0000-$3FFF |
| OS ROM | OS-A (1979) or OS-B (rev B, 1981), 10K at $D800-$FFFF |
| Cartridge | One 8K cartridge slot at $A000-$BFFF (left slot) |
| Controller ports | Four controller ports via PIA PORTA/PORTB |
| Notable | No built-in BASIC (BASIC shipped on cartridge), no PBI/ECI, membrane keyboard, no monitor port |

## Address Map

| Range | Description |
|-------|-------------|
| $0000-$00FF | Zero page |
| $0100-$01FF | 6502 hardware stack |
| $0200-$02FF | OS interrupt vectors, countdown timers |
| $0300-$03FF | OS variables, handler table ($031A), IOCBs ($0340) |
| $0400-$3FFF | User RAM (16K) |
| $4000-$9FFF | Nothing fitted — open bus |
| $A000-$BFFF | Cartridge ROM (left slot, 8K) |
| $C000-$CFFF | Unused (no ROM, no RAM on a 16K machine) |
| $D000-$D7FF | GTIA, POKEY, PIA, ANTIC |
| $D800-$DFFF | Floating point package (inside the OS ROM) |
| $E000-$FFFF | OS ROM (6502 vectors at $FFFA-$FFFF) |

## Hardware Registers ($D000-$D7FF)

| Address | Name | Description |
|---------|------|-------------|
| $D000 | M0PF | GTIA: missile 0 / playfield collision (read) |
| $D001 | M1PF | GTIA: missile 1 / playfield collision (read) |
| $D002 | M2PF | GTIA: missile 2 / playfield collision (read) |
| $D003 | M3PF | GTIA: missile 3 / playfield collision (read) |
| $D004 | P0PF | GTIA: player 0 / playfield collision (read) |
| $D005 | P1PF | GTIA: player 1 / playfield collision (read) |
| $D006 | P2PF | GTIA: player 2 / playfield collision (read) |
| $D007 | P3PF | GTIA: player 3 / playfield collision (read) |
| $D008 | M0PL | GTIA: missile 0 / player collision (read) |
| $D00C | P0PL | GTIA: player 0 / player collision (read) |
| $D010 | TRIG0 | GTIA: joystick 0 trigger (read) |
| $D011 | TRIG1 | GTIA: joystick 1 trigger (read) |
| $D012 | TRIG2 | GTIA: cartridge interlock (read) |
| $D013 | TRIG3 | GTIA: module interlock (read) |
| $D014 | PAL | GTIA: PAL/NTSC indicator (bit 1 = PAL) |
| $D01F | CONSOL | GTIA: console switches and speaker (write) |
| $D200 | POT0 | POKEY: paddle 0 (read) / audio frequency 1 (write) |
| $D201 | POT1 | POKEY: paddle 1 (read) / audio frequency 2 (write) |
| $D202 | POT2 | POKEY: paddle 2 (read) / audio frequency 3 (write) |
| $D203 | POT3 | POKEY: paddle 3 (read) / audio frequency 4 (write) |
| $D204 | POT4 | POKEY: paddle 4 (read) / audio control 1 (write) |
| $D205 | POT5 | POKEY: paddle 5 (read) / audio control 2 (write) |
| $D206 | POT6 | POKEY: paddle 6 (read) / audio control 3 (write) |
| $D207 | POT7 | POKEY: paddle 7 (read) / audio control 4 (write) |
| $D208 | ALLPOT | POKEY: all paddle triggers (read) / AUDCTL (write) |
| $D209 | KBCODE | POKEY: keyboard code (read) / STIMER (write) |
| $D20A | RANDOM | POKEY: random number generator (read) / SKREST (write) |
| $D20B | POTGO | POKEY: start paddle scan (write) |
| $D20D | SERIN | POKEY: serial input (read) / SEROUT (write) |
| $D20E | IRQST | POKEY: IRQ status (read) / IRQEN (write) |
| $D20F | SKSTAT | POKEY: serial/keyboard status (read) / SKCTL (write) |
| $D300 | PORTA | PIA: port A — controller ports 3/4 (400/800) or joystick 1 |
| $D301 | PORTB | PIA: port B — controller ports 1/2 (400/800) or XL memory control |
| $D302 | PACTL | PIA: port A control |
| $D303 | PBCTL | PIA: port B control |
| $D400 | DMACTL | ANTIC: DMA control (playfield width, players, missiles) |
| $D401 | CHACTL | ANTIC: character control (vertical reflect, blink) |
| $D402 | DLISTL | ANTIC: display list address lo |
| $D403 | DLISTH | ANTIC: display list address hi |
| $D404 | HSCROL | ANTIC: horizontal scroll |
| $D405 | VSCROL | ANTIC: vertical scroll |
| $D407 | PMBASE | ANTIC: player/missile base address |
| $D409 | CHBASE | ANTIC: character set base address |
| $D40A | WSYNC | ANTIC: wait for horizontal blank |
| $D40B | VCOUNT | ANTIC: vertical line counter (read) |
| $D40C | PENH | ANTIC: light pen horizontal (read) |
| $D40D | PENV | ANTIC: light pen vertical (read) |
| $D40E | NMIEN | ANTIC: NMI enable (DLI, VBI, reset) |
| $D40F | NMIST | ANTIC: NMI status (read) / NMIRES (write) |
| $D600 | PBI_RAM | XL/XE: parallel bus interface RAM window ($D600-$D61F) |

The GTIA write registers overlap the collision reads: $D000-$D00F are
HPOSP0-3/HPOSM0-3 on write, $D00D-$D011 GRAFP0-3/GRAFM, $D012-$D019
COLPM0-3/COLPF0-3, $D01A COLBK, $D01B PRIOR, $D01C VDELAY, $D01D GRACTL,
$D01E HITCLR. POKEY's $D200-$D207 are AUDF1-4/AUDC1-4 on write. ANTIC's
reads at $D40B-$D40F are VCOUNT/PENH/PENV/NMIST.

## Zero Page

| Address | Name | Description |
|---------|------|-------------|
| $00 | LNFLG | LNBUG flag / LINBUG RAM |
| $01 | NGFLAG | Memory status (0 = failure) |
| $02 | CASINI | Cassette initialisation vector lo |
| $03 | CASINI+1 | Cassette initialisation vector hi |
| $04 | RAMLO | RAM pointer used by the memory test |
| $06 | TRAMSZ | Temporary RAM size register |
| $07 | CMCMD | Command communications byte |
| $08 | WARMST | Warm start flag |
| $09 | BOOTQ | Successful boot flag |
| $0A | DOSVEC | Disk software start vector lo |
| $0B | DOSVEC+1 | Disk software start vector hi |
| $0C | DOSINI | Disk software init address lo |
| $0D | DOSINI+1 | Disk software init address hi |
| $0E | APPMHI | Application memory high limit lo |
| $0F | APPMHI+1 | Application memory high limit hi |
| $10 | POKMSK | Shadow of POKEY IRQEN |
| $11 | BRKKEY | BREAK key flag |
| $12 | RTCLOK | Real-time clock, 16 ms units (3 bytes $12-$14) |
| $15 | BUFADR | Indirect buffer address lo |
| $17 | ICCOMT | Command for the vector |
| $18 | DSKFMS | Disk file manager pointer lo |
| $1A | DSKUTL | Disk utilities pointer lo |
| $1C | ABUFPT | ACMI buffer pointer area (4 bytes) |
| $20 | ZIOCB | Zero-page IOCB ($20-$2F); ICHIDZ handler index ($FF = free) |
| $21 | ICDNOZ | IOCB device number |
| $22 | ICCOMZ | IOCB command code |
| $23 | ICSTAZ | IOCB status |
| $24 | ICBALZ | IOCB buffer address lo |
| $26 | ICPTLZ | IOCB put-byte routine address - 1 |
| $28 | ICBLLZ | IOCB buffer length lo |
| $2A | ICAX1Z | IOCB auxiliary byte 1 |
| $2E | ICIDNO | IOCB number x 16 |
| $2F | CIOCHR | Character for the current CIO operation |
| $30 | STATUS | Internal status storage |
| $31 | CHKSUM | Checksum |
| $32 | BUFRLO | Data buffer pointer lo |
| $34 | BFENLO | Next byte past the buffer lo |
| $36 | LTEMP | Loader temporary (2 bytes) |
| $38 | BUFRFL | Data buffer full flag |
| $39 | RECVDN | Receive done flag |
| $3A | XMTDON | Transmission done flag |
| $3B | CHKSNT | Checksum sent flag |
| $3C | NOCKSM | No checksum follows flag |
| $3D | BPTR | Cassette buffer pointer |
| $3E | FTYPE | Cassette IRG type |
| $3F | FEOF | Cassette EOF flag |
| $40 | FREQ | Cassette beep counter |
| $41 | SOUNDR | Noisy I/O flag |
| $42 | CRITIC | Critical section flag |
| $43 | FMSZPG | Disk file manager system zero page |
| $4A | ZCHAIN | Handler linkage chain pointer (2 bytes) |
| $4C | DSTAT | Display status |
| $4D | ATRACT | Attract mode flag |
| $4E | DRKMSK | Attract dark mask |
| $4F | COLRSH | Attract colour shifter |
| $50 | TMPCHR | Temporary character |
| $51 | HOLD1 | Temporary byte |
| $52 | LMARGN | Left margin (normally 2) |
| $53 | RMARGN | Right margin (normally 39) |
| $54 | ROWCRS | Cursor row |
| $55 | COLCRS | Cursor column (2 bytes) |
| $57 | DINDEX | Display mode |
| $58 | SAVMSC | Saved memory scan counter lo |
| $59 | SAVMSC+1 | Saved memory scan counter hi |
| $5A | OLDROW | Prior row |
| $5B | OLDCOL | Prior column (2 bytes) |
| $5D | OLDCHR | Character under the cursor |
| $5E | OLDADR | Saved cursor address |
| $60 | FKDEF | Function key definition table |
| $62 | PALNTS | PAL/NTSC indicator (0 = NTSC) |
| $63 | LOGCOL | Logical line column |
| $64 | ADRESS | Temporary address |
| $66 | MLTTMP | Temporary / open work |
| $68 | SAVADR | Saved address |
| $6A | RAMTOP | RAM size defined by the power-on logic |
| $6B | BUFCNT | Buffer count |
| $6C | BUFSTR | Editor get-character pointer |
| $6E | BITMSK | Bit mask |
| $6F | SHFAMT | Pixel shift amount |
| $70 | ROWAC | Draw working row (2 bytes) |
| $72 | COLAC | Draw working column (2 bytes) |
| $74 | ENDPT | Draw end point |
| $76 | DELTAR | Row difference |
| $77 | DELTAC | Column difference |
| $79 | KEYDEF | Key definition table address |
| $7B | SWPFLG | Text/RAM swap flag |
| $7C | HOLDCH | Held character |
| $7D | INSDAT | Insert data temporary |
| $7E | COUNTR | Draw iteration count |
| $D4 | FR0 | Floating point register 0 (6 bytes) |
| $DA | FRE | Floating point register E (6 bytes) |
| $E0 | FR1 | Floating point register 1 (6 bytes) |
| $E6 | FR2 | Floating point register 2 (6 bytes) |
| $EC | FRX | Floating point temporary |
| $ED | EEXP | Value of E |
| $EE | FRSIGN | Floating point sign |
| $F2 | CIX | Current input index |
| $F3 | INBUFF | Pointer to the user's line buffer |
| $F5 | ZTEMP1 | Temporary (2 bytes) |
| $F7 | ZTEMP4 | Temporary (2 bytes) |
| $F9 | ZTEMP3 | Temporary (2 bytes) |
| $FC | FLPTR | Floating point number pointer |
| $FE | FPTR2 | Second floating point pointer |

## Page 2 — Interrupt Vectors and Timers

| Address | Name | Description |
|---------|------|-------------|
| $0200 | VDSLST | Display list interrupt (NMI) vector lo |
| $0201 | VDSLST+1 | Display list interrupt vector hi |
| $0202 | VPRCED | Proceed line IRQ vector |
| $0204 | VINTER | Interrupt line IRQ vector |
| $0206 | VBREAK | BRK instruction IRQ vector |
| $0208 | VKEYBD | POKEY keyboard IRQ vector |
| $020A | VSERIN | POKEY serial input ready IRQ vector |
| $020C | VSEROR | POKEY serial output ready IRQ vector |
| $020E | VSEROC | POKEY serial output complete IRQ vector |
| $0210 | VTIMR1 | POKEY timer 1 IRQ vector |
| $0212 | VTIMR2 | POKEY timer 2 IRQ vector |
| $0214 | VTIMR4 | POKEY timer 4 IRQ vector |
| $0216 | VIMIRQ | Immediate IRQ vector |
| $0218 | CDTMV1 | Countdown timer 1 (2 bytes) |
| $021A | CDTMV2 | Countdown timer 2 |
| $021C | CDTMV3 | Countdown timer 3 |
| $021E | CDTMV4 | Countdown timer 4 |
| $0220 | CDTMV5 | Countdown timer 5 |
| $0222 | VVBLKI | Immediate vertical blank NMI vector |
| $0224 | VVBLKD | Deferred vertical blank NMI vector |
| $0226 | CDTMA1 | Countdown timer 1 JSR address |
| $0228 | CDTMA2 | Countdown timer 2 JSR address |
| $022A | CDTMF3 | Countdown timer 3 flag |
| $022B | SRTIMR | Software repeat timer |
| $022C | CDTMF4 | Countdown timer 4 flag |
| $022E | CDTMF5 | Countdown timer 5 flag |
| $022F | SDMCTL | Shadow of DMACTL |
| $0230 | SDLSTL | Shadow display list pointer lo |
| $0231 | SDLSTH | Shadow display list pointer hi |
| $0232 | SSKCTL | Shadow of SKCTL |
| $0233 | LCOUNT | Relocating loader record (XL) |
| $0234 | LPENH | Light pen horizontal |
| $0235 | LPENV | Light pen vertical |
| $0236 | BRKKY | BREAK key vector |
| $0238 | VPIRQ | Parallel device IRQ vector (XL/XE) |
| $023A | CDEVIC | Command frame device buffer |
| $0290 | TXTROW | Text cursor row |
| $0291 | TXTCOL | Text cursor column |
| $02C0 | PCOLR0 | Shadow of COLPM0 (player/missile 0 colour) |
| $02C1 | PCOLR1 | Shadow of COLPM1 |
| $02C2 | PCOLR2 | Shadow of COLPM2 |
| $02C3 | PCOLR3 | Shadow of COLPM3 |
| $02C4 | COLOR0 | Shadow of COLPF0 (playfield 0 colour) |
| $02C5 | COLOR1 | Shadow of COLPF1 (text luminance in GR.0) |
| $02C6 | COLOR2 | Shadow of COLPF2 (background in GR.0) |
| $02C7 | COLOR3 | Shadow of COLPF3 |
| $02C8 | COLOR4 | Shadow of COLBK (border/background) |
| $02E0 | RUNAD | Binary-load run address (DOS jumps here after loading) |
| $02E2 | INITAD | Binary-load init address (called after each segment) |
| $02E4 | RAMSIZ | RAM size (high byte only) |
| $02E5 | MEMTOP | Top of available user memory |
| $02E7 | MEMLO | Bottom of available user memory |
| $02F0 | CRSINH | Cursor inhibit (non-zero = no cursor) |
| $02F4 | CHBAS | Shadow of CHBASE (character set page) |
| $02FC | CH | Last key pressed (internal code, $FF = none) |

## Page 3 — Handler Table and IOCBs

| Address | Name | Description |
|---------|------|-------------|
| $031A | HATABS | Handler address table, 35 bytes (device letter + vector) |
| $0340 | IOCB0 | I/O control block 0 (16 bytes); ICHID handler index ($FF = free) |
| $0341 | ICDNO | IOCB device number |
| $0342 | ICCOM | IOCB command code |
| $0343 | ICSTA | IOCB status |
| $0344 | ICBAL | IOCB buffer address lo |
| $0345 | ICBAH | IOCB buffer address hi |
| $0346 | ICPTL | IOCB put-byte routine address - 1 lo |
| $0347 | ICPTH | IOCB put-byte routine address hi |
| $0348 | ICBLL | IOCB buffer length lo |
| $0349 | ICBLH | IOCB buffer length hi |
| $034A | ICAX1 | IOCB auxiliary byte 1 |
| $034B | ICAX2 | IOCB auxiliary byte 2 |
| $034C | ICAX3 | IOCB auxiliary byte 3 (screen IOCB) |
| $034D | ICAX4 | IOCB auxiliary byte 4 (screen IOCB) |
| $034E | ICAX5 | IOCB auxiliary byte 5 (screen IOCB) |
| $0350 | IOCB1 | I/O control block 1 ($0340 + $10) |
| $0360 | IOCB2 | I/O control block 2 |
| $0370 | IOCB3 | I/O control block 3 |
| $0380 | IOCB4 | I/O control block 4 |
| $0390 | IOCB5 | I/O control block 5 |
| $03A0 | IOCB6 | I/O control block 6 |
| $03B0 | IOCB7 | I/O control block 7 |

## OS ROM Layout and Banking

The OS ROM is 10K at $D800-$FFFF and contains the floating point package
at $D800-$DFFF plus the OS at $E000-$FFFF. There is no $C000-$CFFF OS window
and no PORTB memory banking: on the 400/800 PORTB at $D301 is the second
joystick port, not a bank switch. RAM size is read from $02E4 and the top of
usable memory from $02E5/$02E6.

## Memory Banking

- RAM is populated in 8K/16K steps; a 16K machine has $0000-$3FFF only.
- The cartridge at $A000-$BFFF overlays nothing (there is no RAM there).
- $C000-$FFFF is not RAM on a stock 400, so code cannot hide under the OS.
- The floating point package is callable directly at $D800 and is also
  reachable through the OS entry points.

## 6502 Hardware Vectors

| Address | Name | Description |
|---------|------|-------------|
| $FFFA | NMIVEC | NMI vector — points into the OS ROM (ANTIC/display list NMI) |
| $FFFC | RESETVEC | RESET vector — points at the OS cold start (COLDSV) |
| $FFFE | IRQVEC | IRQ/BRK vector — points at the OS IRQ dispatcher |

Programs rarely touch $FFFA-$FFFF directly: the OS routes NMI through VVBLKI/
VVBLKD ($0222/$0224) and VDSLST ($0200), and IRQ through VIMIRQ ($0216) and the
per-source vectors at $0202-$0214.

## Tooling Profile

| Field | Value |
|-------|-------|
| CPU | MOS 6502 (NMOS) at 1.79 MHz (NTSC) / 1.77 MHz (PAL) |
| zero_page | $0000-$00FF |
| hardware | $D000-$D7FF |
| vectors | $FFFA-$FFFF (page-2 shadow vectors are what code patches) |
| ROM window | 10K at $D800-$FFFF |

## Sources

- https://mcurrent.name/atari-8-bit/faq.txt (memory map, PORTB, per-model RAM)
- https://atariwiki.org/wiki/Wiki.jsp?page=Memory%20Map
- https://atariwiki.org/wiki/Wiki.jsp?page=PORTB
- cc65 `asminc/atari.inc`, `atari_antic.inc`, `atari_gtia.inc`, `atari_pokey.inc`
- Mapping the Atari, revised edition (Ian Chadwick)

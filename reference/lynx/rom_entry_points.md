# Atari Lynx ROM / Boot Entry Points Reference

The Lynx has no operating system: a 504-byte boot ROM at $FE00-$FFF7 performs
cartridge authentication, decrypts the first stage and jumps to $0200. Everything
else — screen setup, sprite engine, timers — is done by the cartridge code.

## Boot ROM ($FE00-$FFF7)

| Address | Name | Description |
|---------|------|-------------|
| $FE00 | CART_SHIFT | Shift the byte in A into the cartridge address register |
| $FE19 | CLEAR_MEM | Clear all RAM from $0003 to $FFFF |
| $FE26 | INIT_MIKEY | Write the Mikey initialisation table ($FFD8/$FFCC) |
| $FE34 | COPY_DECRYPT | Copy the 256-byte RSA routine from $FEC1 to $5000 |
| $FE3D | DECRYPT_FRAME | Read and decrypt one frame of 51-byte blocks |
| $FE9D | RETRY | Bump the retry counters and retry the frame |
| $FEAA | INIT_SUZY | Write the Suzy initialisation table ($FFEF/$FFE6) |
| $FEB8 | CLEAR_BUSREQ | Reset the CPU bus request flip-flop |
| $FEC1 | RSA_ROUTINE | RSA decryption routine (copied to $5000 and run there) |
| $FF80 | BOOT | Boot entry: check Suzy revision, power the cart, map RAM, run |
| $FF9A | PUBLIC_KEY | 49-byte public key used by the RSA sanity checks ($FF9A-$FFCA) |

## Boot Sequence

1. RESET vector ($FFFC) points at $FF80. The boot code verifies Suzy is present
   (`LDA $FC88`, must be non-zero), powers the cartridge and sets MAPCTL to map
   RAM over Mikey and the ROM window.
2. RAM is cleared from $0003 to $FFFF, then the Mikey and Suzy tables are
   written (timers, display control, palette, sprite engine idle state).
3. The first frame of cartridge data is read through Suzy and RSA-decrypted by
   the routine at $5000; the plaintext is written to $0200 onward.
4. `JMP $0200` starts the cartridge's first stage. The decrypted block starts
   with the 64-byte "LYNX" header, so the code entry used by the cartridge
   loader is normally $0200 + $40.

## Vectors

| Address | Name | Description |
|---------|------|-------------|
| $FFFA | NMI | Boot ROM NMI vector ($3000) |
| $FFFC | RESET | Boot ROM reset vector ($FF80) |
| $FFFE | IRQ | Boot ROM IRQ/BRK vector ($FF80) |

Once a cartridge sets MAPCTL bit 3, $FFFA-$FFFF become RAM and the program owns
the vectors; install the IRQ handler there before enabling timer interrupts.

## Cartridge Layout

| Offset | Name | Description |
|--------|------|-------------|
| $00-$03 | LYNX | Magic "LYNX" (the boot ROM's block count sits in the first encrypted byte) |
| $04-$05 | VERSION | Header version |
| $08-$27 | CARTNAME | Cart name, 32 bytes, NUL padded |
| $28-$37 | MANUFACTURER | Manufacturer name, 16 bytes, NUL padded |
| $38-$3F | RESERVED | Zero in practice; not used by the boot ROM |

The boot ROM never parses these fields — it only reads the block count in the
first byte and decrypts. The header is what tools and emulators use to identify
a cart.

## Hardware Initialisation Values

Timers: timer 0 (horizontal line), timer 2 (vertical blank), timer 4 (serial to
cartridge) and timer 7 (audio) are set up by the boot ROM. Display starts with
DISPCTL = $0D (4-bit colour, video DMA enabled) and display address $2000, which
is why a first-stage loader usually copies itself out of the way before enabling
the display.

## Calling Conventions Worth Knowing

- **MAPCTL ($FFF9)**: write bit 3 to take over the vectors, bit 2 to map RAM
  over the ROM window, bit 1 over Mikey and bit 0 over Suzy. Most programs run
  with the cartridge window mapped as RAM after loading.
- **Suzy sprite start ($FC91)**: write 1 to bit 0 to start the sprite engine;
  poll bit 0 until it clears.
- **SDONEACK ($FD90)** and **CPUSLEEP ($FD91)**: acknowledge sprite completion
  and release the CPU bus.
- **INTRST/INTSET ($FD80/$FD81)**: write 1 bits to clear/set timer interrupts;
  timer n uses bit n.
- **Timer control A** bit 7 enables the interrupt, bit 6 resets the done flag,
  bit 4 enables reload, bit 3 enables counting, bits 2-0 select the clock.

## Common Lynx Idioms

### Map RAM over the ROM window and vectors
```
        LDA #$0C         ; RAM at $FE00-$FFFF (ROM + vectors)
        STA $FFF9
```

### Set up timer 0 for horizontal interrupts
```
        LDA #$9E         ; 158 backup value
        STA $FD00
        LDA #$18         ; enable interrupt + count, 2 us clock
        STA $FD01
        LDA #$01         ; enable timer 0 interrupt
        STA $FD81
```

### Wait for the sprite engine
```
        LDA #$01
        STA $FC91        ; SPRGO: start
WAIT    LDA $FC91
        AND #$01
        BNE WAIT
```

## Sources

- https://gist.github.com/drhelius/30eb03724f510719cd9c51ca059fa727
- http://monlynx.de/lynx/hardware.html
- https://forums.atariage.com/topic/191953-annotated-lynx-boot-rom
- cc65 `asminc/lynx.inc`

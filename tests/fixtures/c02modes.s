; Round-trip fixture: 65C02-only instructions and modes.
        .setcpu "65C02"
        .org $0800

start:  stz $12
        stz $12,x
        stz $1234
        stz $1234,x
        lda ($12)
        sta ($12)
        ora ($12)
        and ($12)
        eor ($12)
        adc ($12)
        cmp ($12)
        sbc ($12)
        bit #$80
        bit $12,x
        bit $1234,x
        tsb $12
        tsb $1234
        trb $12
        trb $1234
        inc a
        dec a
        phx
        phy
        plx
        ply
        bra skip
        nop
skip:   jmp (table,x)
table:  .word start, skip
        .byte "65C02 TEST", 0

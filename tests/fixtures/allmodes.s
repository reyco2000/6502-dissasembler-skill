; Round-trip fixture: every 6502 addressing mode, soft switches, ROM calls,
; MLI inline args, strings, fills and a pointer table.
        .setcpu "6502"
        .org $2000

COUT    = $FDED
HOME    = $FC58
MLI     = $BF00
KBD     = $C000
KBDSTRB = $C010
SPKR    = $C030

start:  cld
        jsr HOME
        lda #$00
        sta KBDSTRB
        ldx #$00
print:  lda msg,x
        beq wait
        ora #$80
        jsr COUT
        inx
        bne print
wait:   lda KBD
        bpl wait
        sta KBDSTRB
        jsr modes
        jsr tone
        jsr MLI
        .byte $C8
        .word openparm
        bcs err
        jmp (vector)
err:    brk

modes:  lda $12
        lda $12,x
        ldx $12,y
        lda $1234
        lda $1234,x
        lda $1234,y
        lda ($12,x)
        lda ($12),y
        lda a:$0012
        sta a:$0012,x
        asl a
        lsr a
        rol $12
        ror $1234,x
        bit $C061
        inc $0300
        dec $12,x
        adc #$10
        sbc $12
        cmp ($20),y
        cpx #$05
        cpy $1234
        and #$0F
        eor $12
        php
        plp
        pha
        pla
        tax
        tay
        txa
        tya
        tsx
        txs
        sec
        clc
        sei
        cli
        clv
        sed
        cld
        nop
        bvc :+
        bvs :+
        bcc :+
        bcs :+
:       rts

tone:   ldy #$40
@loop:  lda SPKR
        ldx #$20
@dly:   dex
        bne @dly
        dey
        bne @loop
        rti

vector: .word start
openparm:
        .byte 3
        .word fname
        .word $0C00
        .byte 0
fname:  .byte 5, "HELLO"
msg:    .byte "PRESS A KEY", 0
        .res 16, $00
        .byte $01, $02, $03

#!/usr/bin/env python3
"""
dasm6502.py — 6502 / 65C02 disassembler engine for Apple II analysis
Usage: python3 dasm6502.py <file> [--org 0x2000] [--cpu 65c02] [--entry 0x2000]
                           [--annotate] [--no-hex] [--output file.s]

Strategy: recursive descent from the entry points (file load/exec address,
--entry addresses, and the NMI/RESET/IRQ vectors when the image covers
$FFFA), then a linear fill of whatever was not reached: string / zero / $FF
runs become data, the rest is decoded linearly and falls back to .byte on
undefined opcodes. Traced code always wins over filled code.

Output is ca65 syntax. --no-hex produces a listing that reassembles
byte-exact (ca65 out.s && ld65 -t none out.o -o out.bin); the default
hex-dump format is what annotator.py --split expects:
    "  ADDR  HEX BYTES  MNEMONIC OPERAND ; comment"
Keep that line format stable — annotator.py parses it.
"""

import sys
import argparse
from dataclasses import dataclass
from typing import Optional

try:
    from tools.a2loader import load_image
    from tools.symbols import SymbolTable, load_symbols
except ImportError:
    from a2loader import load_image
    from symbols import SymbolTable, load_symbols

# ===========================================================================
# ADDRESSING MODES
# ===========================================================================

IMP = "imp"          # implied
ACC = "acc"          # accumulator
IMM = "imm"          # #$nn
ZP = "zp"            # $nn
ZPX = "zpx"          # $nn,X
ZPY = "zpy"          # $nn,Y
ABS = "abs"          # $nnnn
ABSX = "absx"        # $nnnn,X
ABSY = "absy"        # $nnnn,Y
IND = "ind"          # ($nnnn)
INDX = "indx"        # ($nn,X)
INDY = "indy"        # ($nn),Y
REL = "rel"          # branch
ZPIND = "zpind"      # ($nn)        65C02
ABSINDX = "absindx"  # ($nnnn,X)    65C02
ZPREL = "zprel"      # $nn,label    Rockwell BBR/BBS

MODE_SIZE = {IMP: 0, ACC: 0, IMM: 1, ZP: 1, ZPX: 1, ZPY: 1, ABS: 2, ABSX: 2,
             ABSY: 2, IND: 2, INDX: 1, INDY: 1, REL: 1, ZPIND: 1, ABSINDX: 2,
             ZPREL: 2}

# Modes whose operand is a 16-bit memory address
ABS_MODES = (ABS, ABSX, ABSY, IND, ABSINDX)
ZP_MODES = (ZP, ZPX, ZPY, INDX, INDY, ZPIND)

# ===========================================================================
# OPCODE TABLES: opcode -> (mnemonic, mode)
# ===========================================================================

OPCODES_6502 = {
    0x00: ("BRK", IMP),  0x01: ("ORA", INDX), 0x05: ("ORA", ZP),   0x06: ("ASL", ZP),
    0x08: ("PHP", IMP),  0x09: ("ORA", IMM),  0x0A: ("ASL", ACC),  0x0D: ("ORA", ABS),
    0x0E: ("ASL", ABS),  0x10: ("BPL", REL),  0x11: ("ORA", INDY), 0x15: ("ORA", ZPX),
    0x16: ("ASL", ZPX),  0x18: ("CLC", IMP),  0x19: ("ORA", ABSY), 0x1D: ("ORA", ABSX),
    0x1E: ("ASL", ABSX), 0x20: ("JSR", ABS),  0x21: ("AND", INDX), 0x24: ("BIT", ZP),
    0x25: ("AND", ZP),   0x26: ("ROL", ZP),   0x28: ("PLP", IMP),  0x29: ("AND", IMM),
    0x2A: ("ROL", ACC),  0x2C: ("BIT", ABS),  0x2D: ("AND", ABS),  0x2E: ("ROL", ABS),
    0x30: ("BMI", REL),  0x31: ("AND", INDY), 0x35: ("AND", ZPX),  0x36: ("ROL", ZPX),
    0x38: ("SEC", IMP),  0x39: ("AND", ABSY), 0x3D: ("AND", ABSX), 0x3E: ("ROL", ABSX),
    0x40: ("RTI", IMP),  0x41: ("EOR", INDX), 0x45: ("EOR", ZP),   0x46: ("LSR", ZP),
    0x48: ("PHA", IMP),  0x49: ("EOR", IMM),  0x4A: ("LSR", ACC),  0x4C: ("JMP", ABS),
    0x4D: ("EOR", ABS),  0x4E: ("LSR", ABS),  0x50: ("BVC", REL),  0x51: ("EOR", INDY),
    0x55: ("EOR", ZPX),  0x56: ("LSR", ZPX),  0x58: ("CLI", IMP),  0x59: ("EOR", ABSY),
    0x5D: ("EOR", ABSX), 0x5E: ("LSR", ABSX), 0x60: ("RTS", IMP),  0x61: ("ADC", INDX),
    0x65: ("ADC", ZP),   0x66: ("ROR", ZP),   0x68: ("PLA", IMP),  0x69: ("ADC", IMM),
    0x6A: ("ROR", ACC),  0x6C: ("JMP", IND),  0x6D: ("ADC", ABS),  0x6E: ("ROR", ABS),
    0x70: ("BVS", REL),  0x71: ("ADC", INDY), 0x75: ("ADC", ZPX),  0x76: ("ROR", ZPX),
    0x78: ("SEI", IMP),  0x79: ("ADC", ABSY), 0x7D: ("ADC", ABSX), 0x7E: ("ROR", ABSX),
    0x81: ("STA", INDX), 0x84: ("STY", ZP),   0x85: ("STA", ZP),   0x86: ("STX", ZP),
    0x88: ("DEY", IMP),  0x8A: ("TXA", IMP),  0x8C: ("STY", ABS),  0x8D: ("STA", ABS),
    0x8E: ("STX", ABS),  0x90: ("BCC", REL),  0x91: ("STA", INDY), 0x94: ("STY", ZPX),
    0x95: ("STA", ZPX),  0x96: ("STX", ZPY),  0x98: ("TYA", IMP),  0x99: ("STA", ABSY),
    0x9A: ("TXS", IMP),  0x9D: ("STA", ABSX), 0xA0: ("LDY", IMM),  0xA1: ("LDA", INDX),
    0xA2: ("LDX", IMM),  0xA4: ("LDY", ZP),   0xA5: ("LDA", ZP),   0xA6: ("LDX", ZP),
    0xA8: ("TAY", IMP),  0xA9: ("LDA", IMM),  0xAA: ("TAX", IMP),  0xAC: ("LDY", ABS),
    0xAD: ("LDA", ABS),  0xAE: ("LDX", ABS),  0xB0: ("BCS", REL),  0xB1: ("LDA", INDY),
    0xB4: ("LDY", ZPX),  0xB5: ("LDA", ZPX),  0xB6: ("LDX", ZPY),  0xB8: ("CLV", IMP),
    0xB9: ("LDA", ABSY), 0xBA: ("TSX", IMP),  0xBC: ("LDY", ABSX), 0xBD: ("LDA", ABSX),
    0xBE: ("LDX", ABSY), 0xC0: ("CPY", IMM),  0xC1: ("CMP", INDX), 0xC4: ("CPY", ZP),
    0xC5: ("CMP", ZP),   0xC6: ("DEC", ZP),   0xC8: ("INY", IMP),  0xC9: ("CMP", IMM),
    0xCA: ("DEX", IMP),  0xCC: ("CPY", ABS),  0xCD: ("CMP", ABS),  0xCE: ("DEC", ABS),
    0xD0: ("BNE", REL),  0xD1: ("CMP", INDY), 0xD5: ("CMP", ZPX),  0xD6: ("DEC", ZPX),
    0xD8: ("CLD", IMP),  0xD9: ("CMP", ABSY), 0xDD: ("CMP", ABSX), 0xDE: ("DEC", ABSX),
    0xE0: ("CPX", IMM),  0xE1: ("SBC", INDX), 0xE4: ("CPX", ZP),   0xE5: ("SBC", ZP),
    0xE6: ("INC", ZP),   0xE8: ("INX", IMP),  0xE9: ("SBC", IMM),  0xEA: ("NOP", IMP),
    0xEC: ("CPX", ABS),  0xED: ("SBC", ABS),  0xEE: ("INC", ABS),  0xF0: ("BEQ", REL),
    0xF1: ("SBC", INDY), 0xF5: ("SBC", ZPX),  0xF6: ("INC", ZPX),  0xF8: ("SED", IMP),
    0xF9: ("SBC", ABSY), 0xFD: ("SBC", ABSX), 0xFE: ("INC", ABSX),
}

# 65C02 additions (NCR/GTE core used in the enhanced IIe and IIc)
OPCODES_65C02_EXTRA = {
    0x04: ("TSB", ZP),   0x0C: ("TSB", ABS),  0x12: ("ORA", ZPIND), 0x14: ("TRB", ZP),
    0x1A: ("INC", ACC),  0x1C: ("TRB", ABS),  0x32: ("AND", ZPIND), 0x34: ("BIT", ZPX),
    0x3A: ("DEC", ACC),  0x3C: ("BIT", ABSX), 0x52: ("EOR", ZPIND), 0x5A: ("PHY", IMP),
    0x64: ("STZ", ZP),   0x72: ("ADC", ZPIND), 0x74: ("STZ", ZPX),  0x7A: ("PLY", IMP),
    0x7C: ("JMP", ABSINDX), 0x80: ("BRA", REL), 0x89: ("BIT", IMM), 0x92: ("STA", ZPIND),
    0x9C: ("STZ", ABS),  0x9E: ("STZ", ABSX), 0xB2: ("LDA", ZPIND), 0xD2: ("CMP", ZPIND),
    0xDA: ("PHX", IMP),  0xF2: ("SBC", ZPIND), 0xFA: ("PLX", IMP),
}
OPCODES_65C02 = {**OPCODES_6502, **OPCODES_65C02_EXTRA}

# Rockwell / WDC bit instructions (not present on the Apple IIe/IIc 65C02)
OPCODES_ROCKWELL = {}
for _n in range(8):
    OPCODES_ROCKWELL[0x07 + _n * 0x10] = (f"RMB{_n}", ZP)
    OPCODES_ROCKWELL[0x87 + _n * 0x10] = (f"SMB{_n}", ZP)
    OPCODES_ROCKWELL[0x0F + _n * 0x10] = (f"BBR{_n}", ZPREL)
    OPCODES_ROCKWELL[0x8F + _n * 0x10] = (f"BBS{_n}", ZPREL)
OPCODES_R65C02 = {**OPCODES_65C02, **OPCODES_ROCKWELL}

# NMOS undocumented opcodes that ca65 accepts with .setcpu "6502X"
OPCODES_UNDOC = {
    0x07: ("SLO", ZP), 0x17: ("SLO", ZPX), 0x0F: ("SLO", ABS), 0x1F: ("SLO", ABSX),
    0x1B: ("SLO", ABSY), 0x03: ("SLO", INDX), 0x13: ("SLO", INDY),
    0x27: ("RLA", ZP), 0x37: ("RLA", ZPX), 0x2F: ("RLA", ABS), 0x3F: ("RLA", ABSX),
    0x3B: ("RLA", ABSY), 0x23: ("RLA", INDX), 0x33: ("RLA", INDY),
    0x47: ("SRE", ZP), 0x57: ("SRE", ZPX), 0x4F: ("SRE", ABS), 0x5F: ("SRE", ABSX),
    0x5B: ("SRE", ABSY), 0x43: ("SRE", INDX), 0x53: ("SRE", INDY),
    0x67: ("RRA", ZP), 0x77: ("RRA", ZPX), 0x6F: ("RRA", ABS), 0x7F: ("RRA", ABSX),
    0x7B: ("RRA", ABSY), 0x63: ("RRA", INDX), 0x73: ("RRA", INDY),
    0x87: ("SAX", ZP), 0x97: ("SAX", ZPY), 0x8F: ("SAX", ABS), 0x83: ("SAX", INDX),
    0xA7: ("LAX", ZP), 0xB7: ("LAX", ZPY), 0xAF: ("LAX", ABS), 0xBF: ("LAX", ABSY),
    0xA3: ("LAX", INDX), 0xB3: ("LAX", INDY),
    0xC7: ("DCP", ZP), 0xD7: ("DCP", ZPX), 0xCF: ("DCP", ABS), 0xDF: ("DCP", ABSX),
    0xDB: ("DCP", ABSY), 0xC3: ("DCP", INDX), 0xD3: ("DCP", INDY),
    0xE7: ("ISC", ZP), 0xF7: ("ISC", ZPX), 0xEF: ("ISC", ABS), 0xFF: ("ISC", ABSX),
    0xFB: ("ISC", ABSY), 0xE3: ("ISC", INDX), 0xF3: ("ISC", INDY),
    # $2B is a second ANC encoding; ca65 always emits $0B, so $2B stays .byte
    0x0B: ("ANC", IMM), 0x4B: ("ALR", IMM), 0x6B: ("ARR", IMM),
    0xCB: ("AXS", IMM), 0xBB: ("LAS", ABSY),
}

CPU_TABLES = {"6502": OPCODES_6502, "65c02": OPCODES_65C02, "r65c02": OPCODES_R65C02}

BRANCHES = {"BPL", "BMI", "BVC", "BVS", "BCC", "BCS", "BNE", "BEQ", "BRA"} | \
           {f"BBR{n}" for n in range(8)} | {f"BBS{n}" for n in range(8)}
FLOW_END = {"RTS", "RTI", "BRK", "BRA", "JMP"}
TERMINALS = {"RTS", "RTI", "JMP", "BRA", "BRK"}
LOADS_STORES = {"LDA", "LDX", "LDY", "STA", "STX", "STY", "STZ", "BIT", "CMP", "CPX",
                "CPY", "INC", "DEC", "ASL", "LSR", "ROL", "ROR", "ADC", "SBC", "AND",
                "ORA", "EOR", "TSB", "TRB", "LAX", "SAX", "DCP", "ISC", "SLO", "RLA",
                "SRE", "RRA"}
STORES = {"STA", "STX", "STY", "STZ", "SAX"}

# JSR targets followed by inline argument bytes: addr -> (kind, byte count)
INLINE_ARG_CALLS = {
    0xBF00: ("mli", 3),   # ProDOS MLI: command byte + parameter block pointer
}

# ===========================================================================
# SYMBOLS
# ===========================================================================

ROM_LABELS = {
    # Monitor ($F800-$FFFF)
    0xF800: "PLOT", 0xF819: "HLINE", 0xF828: "VLINE", 0xF832: "CLRSCR",
    0xF836: "CLRTOP", 0xF847: "GBASCALC", 0xF85F: "NXTCOL", 0xF864: "SETCOL", 0xF871: "SCRN",
    0xF88E: "INSDS2", 0xF8D0: "INSTDSP", 0xF940: "PRNTYX", 0xF941: "PRNTAX",
    0xF944: "PRNTX", 0xF948: "PRBLNK", 0xF94A: "PRBL2", 0xFA62: "RESET",
    0xFAA6: "PWRUP", 0xFAD7: "REGDSP", 0xFB1E: "PREAD", 0xFB2F: "INIT",
    0xFB39: "SETTXT", 0xFB40: "SETGR", 0xFB4B: "SETWND", 0xFB5B: "TABV",
    0xFBC1: "BASCALC", 0xFBDD: "BELL1", 0xFBF4: "ADVANCE", 0xFC10: "BS",
    0xFC1A: "UP", 0xFC22: "VTAB", 0xFC24: "VTABZ", 0xFC42: "CLREOP",
    0xFC58: "HOME", 0xFC62: "CR", 0xFC66: "LF", 0xFC70: "SCROLL", 0xFC9C: "CLREOL",
    0xFC9E: "CLEOLZ", 0xFCA8: "WAIT", 0xFCB4: "NXTA4", 0xFCBA: "NXTA1",
    0xFCC9: "HEADR", 0xFD0C: "RDKEY", 0xFD1B: "KEYIN", 0xFD35: "RDCHAR",
    0xFD67: "GETLNZ", 0xFD6A: "GETLN", 0xFD6F: "GETLN1", 0xFD8B: "CROUT1",
    0xFD8E: "CROUT", 0xFD96: "PRA1", 0xFDDA: "PRBYTE", 0xFDE3: "PRHEX",
    0xFDED: "COUT", 0xFDF0: "COUT1", 0xFE1F: "IDROUTINE", 0xFE2C: "MOVE", 0xFE36: "VERIFY",
    0xFE5E: "LIST", 0xFE80: "SETINV", 0xFE84: "SETNORM", 0xFE89: "SETKBD",
    0xFE93: "SETVID", 0xFEB0: "XBASIC", 0xFECD: "WRITE", 0xFEFD: "READ", 0xFF2D: "PRERR",
    0xFF3A: "BELL", 0xFF3F: "RESTORE", 0xFF4A: "SAVE", 0xFF58: "IORTS",
    0xFF59: "OLDRST", 0xFF65: "MON", 0xFF69: "MONZ",
    # Applesoft ($D000-$F7FF)
    0xD412: "ERROR", 0xD43C: "RESTART",
    0xD61A: "FNDLIN", 0xD7D2: "NEWSTT",
    0xD858: "ISCNTC", 0xDB3A: "STROUT", 0xDB3D: "STRPRT", 0xDB5C: "OUTDO",
    0xDD67: "FRMNUM", 0xDD7B: "FRMEVL", 0xDEBE: "CHKCOM", 0xDEC0: "SYNCHR",
    0xDEC9: "SYNERR", 0xE10C: "AYINT", 0xE2F2: "GIVAYF", 0xE6F8: "GETBYT",
    0xE752: "GETADR", 0xE7A7: "FSUB", 0xE7AA: "FSUBT", 0xE7BE: "FADD",
    0xE7C1: "FADDT", 0xE97F: "FMULT", 0xE982: "FMULTT", 0xEA66: "FDIV", 0xEA69: "FDIVT",
    0xEAF9: "MOVFM", 0xEB2B: "MOVMF", 0xEBF2: "QINT",
    0xEC23: "INT", 0xEC4A: "FIN", 0xED24: "LINPRT", 0xED34: "FOUT", 0xEE8D: "SQR",
    0xEE97: "FPWRT", 0xEF09: "EXP", 0xEFAE: "RND", 0xEFEA: "COS", 0xEFF1: "SIN",
    0xF03A: "TAN", 0xF09E: "ATN", 0xF1D5: "CALL", 0xF1DE: "IN", 0xF1E5: "PR",
    0xF3D8: "HGR2", 0xF3E2: "HGR", 0xF3F2: "HCLR", 0xF3F6: "BKGND",
    0xF411: "HPOSN", 0xF457: "HPLOT", 0xF53A: "HGLIN", 0xF5CB: "HFIND",
    0xF601: "DRAW", 0xF65D: "XDRAW", 0xF6EC: "SETHCOL", 0xF721: "ROT", 0xF727: "SCALE",
    0xE000: "COLDSTART", 0xE003: "WARMSTART",
    # ProDOS global page
    0xBF00: "MLI", 0xBF06: "DATETIME",
    # DOS 3.3 page-3 vectors
    0x03D0: "DOSWARM", 0x03D3: "DOSCOLD", 0x03D6: "FILEMGR", 0x03D9: "RWTS",
    0x03DC: "FMPARMS", 0x03E3: "RWTSPARMS", 0x03EA: "DOSHOOK",
    # Applesoft zero-page entry
    0x00B1: "CHRGET", 0x00B7: "CHRGOT",
}

ROM_DESCRIPTIONS = {
    0xF800: "Plot lo-res point (A=row, Y=col)", 0xF819: "Lo-res horizontal line",
    0xF828: "Lo-res vertical line", 0xF832: "Clear lo-res screen",
    0xF836: "Clear top 40 lo-res lines", 0xF847: "Compute GBASL/H from row in A",
    0xF85F: "Next lo-res color", 0xF864: "Set lo-res color (A)", 0xF871: "Read lo-res point",
    0xF88E: "Disassembler: decode opcode", 0xF8D0: "Disassembler: display instruction",
    0xF940: "Print Y,X as hex", 0xF941: "Print A,X as hex", 0xF944: "Print X as hex",
    0xF948: "Print 3 blanks", 0xF94A: "Print X blanks", 0xFA62: "RESET handler",
    0xFAA6: "Power-up: init DOS/boot", 0xFAD7: "Display registers",
    0xFB1E: "Read paddle X (result in Y)", 0xFB2F: "Init text screen/window",
    0xFB39: "Set text mode", 0xFB40: "Set lo-res graphics mode",
    0xFB4B: "Set normal text window", 0xFB5B: "Vertical tab to A", 0xFBC1: "Compute BASL/H for row",
    0xFBDD: "Ring bell", 0xFBF4: "Advance cursor", 0xFC10: "Backspace", 0xFC1A: "Cursor up",
    0xFC22: "Vertical tab (CV)", 0xFC24: "Vertical tab to A", 0xFC42: "Clear to end of page",
    0xFC58: "Clear screen, home cursor", 0xFC62: "Carriage return", 0xFC66: "Line feed",
    0xFC70: "Scroll text window", 0xFC9C: "Clear to end of line", 0xFC9E: "Clear EOL from Y",
    0xFCA8: "Delay (26+27A+5A^2)/2 cycles", 0xFCB4: "Increment A4L/H",
    0xFCBA: "Increment A1L/H, compare A2", 0xFCC9: "Write cassette header",
    0xFD0C: "Read key (via KSW)", 0xFD1B: "Keyboard input with blink",
    0xFD35: "Read char, handle ESC", 0xFD67: "CR then get line", 0xFD6A: "Get line with prompt",
    0xFD6F: "Get line, no prompt", 0xFD8B: "CR after clearing EOL", 0xFD8E: "Print CR",
    0xFD96: "Print CR, A1 and dash", 0xFDDA: "Print A as 2 hex digits", 0xFDE3: "Print low nibble hex",
    0xFDED: "Output char in A (via CSW)", 0xFDF0: "Output char to screen",
    0xFE1F: "ID routine (IIgs returns machine info)", 0xFE2C: "Move memory A1..A2 -> A4",
    0xFE36: "Verify memory", 0xFE5E: "Disassemble 20 instructions", 0xFE80: "Inverse video",
    0xFE84: "Normal video", 0xFE89: "Reset KSW to keyboard", 0xFE93: "Reset CSW to screen",
    0xFEB0: "Jump to BASIC", 0xFECD: "Write cassette", 0xFEFD: "Read cassette", 0xFF2D: "Print ERR, bell",
    0xFF3A: "Bell", 0xFF3F: "Restore registers", 0xFF4A: "Save registers",
    0xFF58: "Known RTS (slot detection)", 0xFF59: "Old monitor reset", 0xFF65: "Monitor (bell)",
    0xFF69: "Monitor entry (no bell)",
    0xD412: "Applesoft error (X=code)", 0xD43C: "Applesoft warm restart",
    0xD61A: "Find line number in LINNUM", 0xD7D2: "Execute next statement", 0xD858: "Check ctrl-C",
    0xDB3A: "Print string at A(lo)/Y(hi)", 0xDB3D: "Print string (FAC)",
    0xDB5C: "Output char (Applesoft)", 0xDD67: "Evaluate numeric expression",
    0xDD7B: "Evaluate expression", 0xDEBE: "Check for comma", 0xDEC0: "Check for char in A",
    0xDEC9: "Syntax error", 0xE10C: "FAC to signed integer", 0xE2F2: "A,Y int to FAC",
    0xE6F8: "Get byte param in X", 0xE752: "Get address param in LINNUM",
    0xE7A7: "FAC = (A,Y) - FAC", 0xE7AA: "FAC = ARG - FAC", 0xE7BE: "FAC = (A,Y) + FAC",
    0xE7C1: "FAC = ARG + FAC", 0xE97F: "FAC = (A,Y) * FAC", 0xE982: "FAC = ARG * FAC",
    0xEA66: "FAC = (A,Y) / FAC", 0xEA69: "FAC = ARG / FAC", 0xEAF9: "Load FAC from (A,Y)",
    0xEB2B: "Store FAC at (X,Y)", 0xEBF2: "Quick FAC to int", 0xEC23: "INT function", 0xEC4A: "String to FAC",
    0xED24: "Print A,X as decimal", 0xED34: "FAC to string", 0xEE8D: "SQR", 0xEE97: "FAC = ARG ^ FAC",
    0xEF09: "EXP", 0xEFAE: "RND", 0xEFEA: "COS", 0xEFF1: "SIN", 0xF03A: "TAN", 0xF09E: "ATN",
    0xF1D5: "CALL statement", 0xF1DE: "IN# statement", 0xF1E5: "PR# statement",
    0xF3D8: "HGR2", 0xF3E2: "HGR", 0xF3F2: "Clear hires screen", 0xF3F6: "Fill hires with color",
    0xF411: "Position hires cursor (X,Y / A)", 0xF457: "Plot hires point", 0xF53A: "Hires line to",
    0xF5CB: "Find hires point", 0xF601: "DRAW shape", 0xF65D: "XDRAW shape", 0xF6EC: "Set hires color from X",
    0xF721: "ROT=", 0xF727: "SCALE=", 0xE000: "Applesoft cold start", 0xE003: "Applesoft warm start",
    0xBF00: "ProDOS MLI call", 0xBF06: "ProDOS date/time routine",
    0x03D0: "DOS warm start", 0x03D3: "DOS cold start", 0x03D6: "DOS file manager",
    0x03D9: "RWTS entry", 0x03DC: "Locate FM parameter list", 0x03E3: "Locate RWTS parameter list",
    0x03EA: "Reconnect DOS I/O hooks", 0x00B1: "Get next Applesoft char", 0x00B7: "Get current char",
}

HW_LABELS = {
    0xC000: "KBD", 0xC001: "SET80STORE", 0xC002: "RDMAINRAM", 0xC003: "RDCARDRAM",
    0xC004: "WRMAINRAM", 0xC005: "WRCARDRAM", 0xC006: "SETSLOTCXROM", 0xC007: "SETINTCXROM",
    0xC008: "SETSTDZP", 0xC009: "SETALTZP", 0xC00A: "SETINTC3ROM", 0xC00B: "SETSLOTC3ROM",
    0xC00C: "CLR80VID", 0xC00D: "SET80VID", 0xC00E: "CLRALTCHAR", 0xC00F: "SETALTCHAR",
    0xC010: "KBDSTRB", 0xC011: "RDLCBNK2", 0xC012: "RDLCRAM", 0xC013: "RDRAMRD",
    0xC014: "RDRAMWRT", 0xC015: "RDCXROM", 0xC016: "RDALTZP", 0xC017: "RDC3ROM",
    0xC018: "RD80STORE", 0xC019: "RDVBL", 0xC01A: "RDTEXT", 0xC01B: "RDMIXED",
    0xC01C: "RDPAGE2", 0xC01D: "RDHIRES", 0xC01E: "RDALTCHAR", 0xC01F: "RD80VID",
    0xC020: "TAPEOUT", 0xC030: "SPKR", 0xC040: "STROBE",
    0xC050: "TXTCLR", 0xC051: "TXTSET", 0xC052: "MIXCLR", 0xC053: "MIXSET",
    0xC054: "TXTPAGE1", 0xC055: "TXTPAGE2", 0xC056: "LORES", 0xC057: "HIRES",
    0xC058: "SETAN0", 0xC059: "CLRAN0", 0xC05A: "SETAN1", 0xC05B: "CLRAN1",
    0xC05C: "SETAN2", 0xC05D: "CLRAN2", 0xC05E: "SETAN3", 0xC05F: "CLRAN3",
    0xC060: "TAPEIN", 0xC061: "BUTN0", 0xC062: "BUTN1", 0xC063: "BUTN2",
    0xC064: "PADDL0", 0xC065: "PADDL1", 0xC066: "PADDL2", 0xC067: "PADDL3",
    0xC070: "PTRIG", 0xC07E: "IOUDIS", 0xC07F: "RDDHIRES",
    0xC080: "LCBANK2_RD", 0xC081: "LCBANK2_ROM_WR", 0xC082: "LCROM_RD", 0xC083: "LCBANK2_RW",
    0xC088: "LCBANK1_RD", 0xC089: "LCBANK1_ROM_WR", 0xC08A: "LCROM_RD2", 0xC08B: "LCBANK1_RW",
    0xC0E0: "PHASE0OFF", 0xC0E1: "PHASE0ON", 0xC0E2: "PHASE1OFF", 0xC0E3: "PHASE1ON",
    0xC0E4: "PHASE2OFF", 0xC0E5: "PHASE2ON", 0xC0E6: "PHASE3OFF", 0xC0E7: "PHASE3ON",
    0xC0E8: "MOTOROFF", 0xC0E9: "MOTORON", 0xC0EA: "DRV0EN", 0xC0EB: "DRV1EN",
    0xC0EC: "Q6L", 0xC0ED: "Q6H", 0xC0EE: "Q7L", 0xC0EF: "Q7H",
    0xCFFF: "CLRROM",
}

HW_DESCRIPTIONS = {
    0xC000: "keyboard data (bit 7 = key ready) / W: 80STORE off", 0xC001: "W: 80STORE on",
    0xC002: "W: read main RAM", 0xC003: "W: read aux RAM", 0xC004: "W: write main RAM",
    0xC005: "W: write aux RAM", 0xC006: "W: slot ROM at $C100-$CFFF", 0xC007: "W: internal ROM at $C100-$CFFF",
    0xC008: "W: main zero page/stack", 0xC009: "W: aux zero page/stack",
    0xC00A: "W: internal slot 3 ROM", 0xC00B: "W: slot 3 card ROM",
    0xC00C: "W: 40-column video", 0xC00D: "W: 80-column video",
    0xC00E: "W: primary charset", 0xC00F: "W: alternate charset (mousetext)",
    0xC010: "clear keyboard strobe (R: any-key-down)", 0xC011: "R: LC bank 2 selected",
    0xC012: "R: LC RAM read enabled", 0xC013: "R: aux RAM read", 0xC014: "R: aux RAM write",
    0xC015: "R: internal CX ROM", 0xC016: "R: aux zero page", 0xC017: "R: slot 3 ROM",
    0xC018: "R: 80STORE state", 0xC019: "R: vertical blanking", 0xC01A: "R: text mode",
    0xC01B: "R: mixed mode", 0xC01C: "R: page 2", 0xC01D: "R: hires mode",
    0xC01E: "R: alt charset", 0xC01F: "R: 80-column", 0xC020: "cassette output toggle",
    0xC030: "speaker toggle", 0xC040: "game I/O strobe",
    0xC050: "graphics mode", 0xC051: "text mode", 0xC052: "full screen", 0xC053: "mixed text/graphics",
    0xC054: "page 1", 0xC055: "page 2", 0xC056: "lo-res", 0xC057: "hi-res",
    0xC058: "annunciator 0 off", 0xC059: "annunciator 0 on", 0xC05A: "annunciator 1 off",
    0xC05B: "annunciator 1 on", 0xC05C: "annunciator 2 off", 0xC05D: "annunciator 2 on",
    0xC05E: "annunciator 3 off (double hires on, IIe)", 0xC05F: "annunciator 3 on (double hires off)",
    0xC060: "cassette input", 0xC061: "open-apple / button 0", 0xC062: "closed-apple / button 1",
    0xC063: "button 2 / shift key mod", 0xC064: "paddle 0 timer", 0xC065: "paddle 1 timer",
    0xC066: "paddle 2 timer", 0xC067: "paddle 3 timer", 0xC070: "paddle trigger",
    0xC07E: "IOU disable (IIc)", 0xC07F: "R: double hires state",
    0xC080: "LC: read RAM bank 2, no write", 0xC081: "LC: read ROM, write RAM bank 2 (2 reads)",
    0xC082: "LC: read ROM, no write", 0xC083: "LC: read/write RAM bank 2 (2 reads)",
    0xC088: "LC: read RAM bank 1, no write", 0xC089: "LC: read ROM, write RAM bank 1 (2 reads)",
    0xC08A: "LC: read ROM, no write", 0xC08B: "LC: read/write RAM bank 1 (2 reads)",
    0xC0E0: "Disk II slot 6: phase 0 off", 0xC0E1: "Disk II slot 6: phase 0 on",
    0xC0E2: "Disk II slot 6: phase 1 off", 0xC0E3: "Disk II slot 6: phase 1 on",
    0xC0E4: "Disk II slot 6: phase 2 off", 0xC0E5: "Disk II slot 6: phase 2 on",
    0xC0E6: "Disk II slot 6: phase 3 off", 0xC0E7: "Disk II slot 6: phase 3 on",
    0xC0E8: "Disk II slot 6: motor off", 0xC0E9: "Disk II slot 6: motor on",
    0xC0EA: "Disk II slot 6: drive 1", 0xC0EB: "Disk II slot 6: drive 2",
    0xC0EC: "Disk II slot 6: Q6L read data latch", 0xC0ED: "Disk II slot 6: Q6H sense write protect",
    0xC0EE: "Disk II slot 6: Q7L read mode", 0xC0EF: "Disk II slot 6: Q7H write mode",
    0xCFFF: "turn off expansion ROM ($C800)",
}

ZP_LABELS = {
    0x20: "WNDLFT", 0x21: "WNDWDTH", 0x22: "WNDTOP", 0x23: "WNDBTM", 0x24: "CH",
    0x25: "CV", 0x26: "GBASL", 0x27: "GBASH", 0x28: "BASL", 0x29: "BASH",
    0x2A: "BAS2L", 0x2B: "BAS2H", 0x2C: "H2", 0x2D: "V2", 0x2E: "MASK",
    0x30: "COLOR", 0x31: "MODE", 0x32: "INVFLG", 0x33: "PROMPT", 0x34: "YSAV",
    0x35: "YSAV1", 0x36: "CSWL", 0x37: "CSWH", 0x38: "KSWL", 0x39: "KSWH",
    0x3A: "PCL", 0x3B: "PCH", 0x3C: "A1L", 0x3D: "A1H", 0x3E: "A2L", 0x3F: "A2H",
    0x40: "A3L", 0x41: "A3H", 0x42: "A4L", 0x43: "A4H", 0x44: "A5L", 0x45: "A5H",
    0x46: "XREG", 0x47: "YREG", 0x48: "STATUS", 0x49: "SPNT", 0x4E: "RNDL", 0x4F: "RNDH",
    0x50: "LINNUM", 0x51: "LINNUM+1", 0x67: "TXTTAB", 0x68: "TXTTAB+1", 0x69: "VARTAB",
    0x6A: "VARTAB+1", 0x6B: "ARYTAB", 0x6C: "ARYTAB+1", 0x6D: "STREND", 0x6E: "STREND+1",
    0x6F: "FRETOP", 0x70: "FRETOP+1", 0x73: "MEMSIZ", 0x74: "MEMSIZ+1", 0x75: "CURLIN",
    0x76: "CURLIN+1", 0x9D: "FAC", 0xA5: "ARG", 0xB8: "TXTPTR", 0xB9: "TXTPTR+1",
    0xE0: "HORIZ", 0xE1: "HORIZ+1", 0xE2: "VERT", 0xE4: "HCOLOR1", 0xE6: "HPAG",
    0xE7: "SCALE_", 0xE8: "SHAPEL", 0xE9: "SHAPEH", 0xF9: "ROT_",
}

ZP_DESCRIPTIONS = {
    0x20: "text window left", 0x21: "text window width", 0x22: "text window top",
    0x23: "text window bottom", 0x24: "cursor horizontal", 0x25: "cursor vertical",
    0x26: "lo-res base lo", 0x27: "lo-res base hi", 0x28: "text base lo", 0x29: "text base hi",
    0x2A: "scroll base lo", 0x2B: "scroll base hi", 0x2C: "line end H", 0x2D: "line end V",
    0x2E: "lo-res mask", 0x30: "lo-res color", 0x31: "monitor mode", 0x32: "inverse flag ($FF normal, $3F inverse)",
    0x33: "prompt char", 0x34: "Y save", 0x35: "Y save", 0x36: "char out vector lo", 0x37: "char out vector hi",
    0x38: "key in vector lo", 0x39: "key in vector hi", 0x3A: "PC lo", 0x3B: "PC hi",
    0x3C: "A1 lo", 0x3D: "A1 hi", 0x3E: "A2 lo", 0x3F: "A2 hi", 0x40: "A3 lo", 0x41: "A3 hi",
    0x42: "A4 lo", 0x43: "A4 hi", 0x44: "A5 lo", 0x45: "A5 hi / ACC", 0x46: "X save",
    0x47: "Y save", 0x48: "P save", 0x49: "S save", 0x4E: "random seed lo", 0x4F: "random seed hi",
    0x50: "Applesoft LINNUM lo", 0x51: "Applesoft LINNUM hi", 0x67: "program start lo",
    0x68: "program start hi", 0x69: "simple vars lo", 0x6A: "simple vars hi", 0x6B: "arrays lo",
    0x6C: "arrays hi", 0x6D: "end of arrays lo", 0x6E: "end of arrays hi", 0x6F: "string space lo",
    0x70: "string space hi", 0x73: "HIMEM lo", 0x74: "HIMEM hi", 0x75: "current line lo",
    0x76: "current line hi", 0x9D: "floating accumulator", 0xA5: "floating argument",
    0xB8: "text pointer lo", 0xB9: "text pointer hi", 0xE0: "hires X lo", 0xE1: "hires X hi",
    0xE2: "hires Y", 0xE4: "hires color mask", 0xE6: "hires page ($20/$40)", 0xE7: "shape scale",
    0xE8: "shape table lo", 0xE9: "shape table hi", 0xF9: "shape rotation",
}

MLI_CALLS = {
    0x40: "ALLOC_INTERRUPT", 0x41: "DEALLOC_INTERRUPT", 0x65: "QUIT", 0x80: "READ_BLOCK",
    0x81: "WRITE_BLOCK", 0x82: "GET_TIME", 0xC0: "CREATE", 0xC1: "DESTROY", 0xC2: "RENAME",
    0xC3: "SET_FILE_INFO", 0xC4: "GET_FILE_INFO", 0xC5: "ONLINE", 0xC6: "SET_PREFIX",
    0xC7: "GET_PREFIX", 0xC8: "OPEN", 0xC9: "NEWLINE", 0xCA: "READ", 0xCB: "WRITE",
    0xCC: "CLOSE", 0xCD: "FLUSH", 0xCE: "SET_MARK", 0xCF: "GET_MARK", 0xD0: "SET_EOF",
    0xD1: "GET_EOF", 0xD2: "SET_BUF", 0xD3: "GET_BUF",
}

VECTOR_NAMES = {0xFFFA: "NMI", 0xFFFC: "RESET", 0xFFFE: "IRQ/BRK"}


def rom_comment(addr: int) -> str:
    if addr in ROM_DESCRIPTIONS:
        return f"; {ROM_DESCRIPTIONS[addr]}"
    return ""


def hw_comment(addr: int) -> str:
    if addr in HW_DESCRIPTIONS:
        return f"; {HW_DESCRIPTIONS[addr]}"
    if 0xC090 <= addr <= 0xC0FF:
        return f"; slot {(addr - 0xC080) >> 4} I/O"
    if 0xC100 <= addr <= 0xC7FF:
        return f"; slot {(addr >> 8) & 7} ROM"
    if 0xC800 <= addr <= 0xCFFE:
        return "; expansion ROM"
    return ""


# ===========================================================================
# MEMORY IMAGE
# ===========================================================================

class MemoryImage:
    """Sparse 64K memory image built from one or more load segments."""

    def __init__(self):
        self.data = bytearray(0x10000)
        self.populated = bytearray(0x10000)
        self.segments = []
        self._ranges = None

    def load_segment(self, addr: int, seg_data: bytes):
        self._ranges = None
        for i, b in enumerate(seg_data):
            if addr + i > 0xFFFF:
                break
            self.data[addr + i] = b
            self.populated[addr + i] = 1
        self.segments.append((addr, min(addr + len(seg_data) - 1, 0xFFFF)))

    def is_populated(self, addr: int) -> bool:
        return 0 <= addr < 0x10000 and bool(self.populated[addr])

    def byte_at(self, addr: int) -> int:
        if 0 <= addr < 0x10000:
            return self.data[addr]
        return 0

    def word_at(self, addr: int) -> int:
        return self.byte_at(addr) | (self.byte_at(addr + 1) << 8)

    def get_contiguous_ranges(self) -> list:
        if self._ranges is not None:
            return list(self._ranges)
        ranges = []
        in_range = False
        start = 0
        for i in range(0x10000):
            if self.populated[i]:
                if not in_range:
                    start = i
                    in_range = True
            elif in_range:
                ranges.append((start, i - 1))
                in_range = False
        if in_range:
            ranges.append((start, 0xFFFF))
        self._ranges = ranges
        return list(ranges)


# ===========================================================================
# DECODER
# ===========================================================================

@dataclass
class Instr:
    pc: int
    opcode: int
    mnemonic: Optional[str]
    mode: str
    size: int
    value: Optional[int] = None   # operand; for REL/ZPREL the resolved target
    zp: Optional[int] = None      # ZPREL zero-page operand
    valid: bool = True


def is_printable(b: int) -> bool:
    return 32 <= b <= 126


def is_hi_printable(b: int) -> bool:
    # $A2 (high-bit quote) is excluded: it cannot appear inside a HASC macro argument
    return 160 <= b <= 254 and b != 0xA2


def detect_data_regions(mem: MemoryImage, free: set) -> dict:
    """Classify unreached bytes: 'string' (ASCII), 'hstring' (high-bit
    ASCII), 'zero', 'ff'. Only addresses in `free` are considered."""
    regions = {}
    for addr in sorted(free):
        if addr in regions:
            continue
        b = mem.byte_at(addr)
        for kind, pred, minlen in (("string", is_printable, 4), ("hstring", is_hi_printable, 4),
                                   ("zero", lambda x: x == 0, 8), ("ff", lambda x: x == 0xFF, 8)):
            if pred(b):
                a = addr
                while a in free and a not in regions and pred(mem.byte_at(a)):
                    a += 1
                # Strings need at least two distinct characters, so NOP
                # padding ($EA = 'j' with the high bit) is not a string
                distinct = len({mem.byte_at(i) for i in range(addr, a)})
                if a - addr >= minlen and (kind in ("zero", "ff") or distinct >= 2):
                    for i in range(addr, a):
                        regions[i] = kind
                break
    return regions


# ===========================================================================
# DISASSEMBLER
# ===========================================================================

class Disassembler6502:
    """Recursive-descent + linear-fill disassembler over a MemoryImage."""

    def __init__(self, mem: MemoryImage, entry_addr: int = None, cpu: str = "6502",
                 undocumented: bool = False, entries: list = None, fill="validated",
                 exclude: list = None, zp_names: bool = False, tables: list = None,
                 symbols: "SymbolTable" = None, data_regions: list = None,
                 auto_tables: bool = True):
        self.mem = mem
        self.entry_addr = entry_addr
        self.cpu = cpu
        self.undocumented = undocumented
        self.table = dict(CPU_TABLES[cpu])
        if undocumented and cpu == "6502":
            self.table.update(OPCODES_UNDOC)
        self.entries = list(entries or [])
        # fill mode for bytes tracing never reached:
        #   "validated" - code only if vouched + decodes cleanly to a terminal
        #   "all"       - decode everything decodable (older behaviour)
        #   "none"      - leave as data
        if fill is True:
            fill = "validated"
        elif fill is False:
            fill = "none"
        self.fill = fill
        self.sym = symbols if symbols is not None else SymbolTable()
        self.auto_tables = auto_tables
        self.forced_data: set[int] = set()
        for s_, e_ in (data_regions or []):
            self.forced_data.update(range(s_, e_ + 1))
        self.swept: set[int] = set()          # instruction starts added by validated fill
        self.auto_found: list[str] = []       # human-readable notes on auto-detected tables
        self.zp_names = zp_names
        self.tables = list(tables or [])
        self.rom_name = None   # set for ROM images: stores into the image hit LC RAM, not code
        self.table_entries: dict[int, tuple] = {}   # addr -> (size, target, rts)
        self.exclude = set()
        for s, e in (exclude or []):
            self.exclude.update(range(s, e + 1))

        self.labels: dict[int, str] = {}
        self.instrs: dict[int, Instr] = {}
        self.owner: dict[int, int] = {}      # byte addr -> instruction start
        self.code_addrs: set[int] = set()
        self.traced: set[int] = set()        # instruction starts reached by tracing
        self.call_targets: set[int] = set()
        self.jump_targets: set[int] = set()
        self.data_refs: dict[int, list[int]] = {}
        self.indirect_vectors: set[int] = set()
        self.inline_data: dict[int, tuple] = {}
        self.data_kind: dict[int, str] = {}
        self.backward_branches: set[int] = set()
        self.lines: list[tuple] = []
        self.used_rom: set[int] = set()
        self.used_hw: set[int] = set()
        self.used_zp: set[int] = set()
        self.used_user: set[int] = set()
        self.used_hasc = False
        self._analyzed = False

    # ---------------- decoding ----------------

    def decode(self, pc: int) -> Optional[Instr]:
        """Decode one instruction at pc. None if unpopulated; valid=False
        for undefined opcodes (size 1)."""
        if not self.mem.is_populated(pc):
            return None
        op = self.mem.byte_at(pc)
        entry = self.table.get(op)
        if entry is None:
            return Instr(pc, op, None, IMP, 1, valid=False)
        mnemonic, mode = entry
        size = 1 + MODE_SIZE[mode]
        for i in range(1, size):
            if not self.mem.is_populated(pc + i):
                return Instr(pc, op, None, IMP, 1, valid=False)
        value = None
        zp = None
        if mode in (REL, ZPREL):
            off = self.mem.byte_at(pc + size - 1)
            value = pc + size + (off - 256 if off > 127 else off)
            if not 0 <= value <= 0xFFFF:
                # wraps around the address space: not expressible in ca65
                return Instr(pc, op, None, IMP, 1, valid=False)
            if mode == ZPREL:
                zp = self.mem.byte_at(pc + 1)
        elif MODE_SIZE[mode] == 1:
            value = self.mem.byte_at(pc + 1)
        elif MODE_SIZE[mode] == 2:
            value = self.mem.word_at(pc + 1)
        return Instr(pc, op, mnemonic, mode, size, value, zp)

    def instr_bytes(self, ins: Instr) -> str:
        return " ".join(f"{self.mem.byte_at(ins.pc + i):02X}" for i in range(ins.size))

    # ---------------- labels ----------------

    def _builtin_ok(self, name: str, addr: int) -> bool:
        """A built-in name is usable unless a user symbol claims it elsewhere."""
        other = self.sym.by_name.get(name)
        return other is None or other == addr

    def known_name(self, addr: int):
        """User symbol or built-in ROM/HW name for addr (no generated names)."""
        n = self.sym.name(addr)
        if n and "+" not in n:
            return n
        for tbl in (ROM_LABELS, HW_LABELS):
            if addr in tbl and self._builtin_ok(tbl[addr], addr):
                return tbl[addr]
        return None

    def describe(self, addr: int) -> str:
        """One-line description: user symbol comment, else built-in tables."""
        c = self.sym.comment(addr)
        if c:
            return c
        return ROM_DESCRIPTIONS.get(addr) or HW_DESCRIPTIONS.get(addr) or ""

    def addr_label(self, addr: int) -> str:
        if addr in self.labels:
            return self.labels[addr]
        return self.known_name(addr) or f"${addr:04X}"

    def add_target_label(self, addr: int, is_call: bool = False):
        """Register a branch/call target inside the image."""
        if is_call:
            self.call_targets.add(addr)
        else:
            self.jump_targets.add(addr)
        if not self.mem.is_populated(addr):
            return
        known = self.known_name(addr)
        if known:
            self.labels.setdefault(addr, known)
        elif is_call:
            self.labels.setdefault(addr, f"SUB_{addr:04X}")
        else:
            self.labels.setdefault(addr, f"L_{addr:04X}")

    def add_data_ref(self, addr: int, from_pc: int):
        self.data_refs.setdefault(addr, []).append(from_pc)

    # ---------------- pass 1: trace + fill ----------------

    def _can_place(self, ins: Instr) -> bool:
        for i in range(ins.size):
            a = ins.pc + i
            if a in self.owner or a in self.exclude or a in self.data_kind or a in self.forced_data:
                return False
        return True

    def _place(self, ins: Instr, traced: bool):
        self.instrs[ins.pc] = ins
        self.code_addrs.add(ins.pc)
        if traced:
            self.traced.add(ins.pc)
        for i in range(ins.size):
            self.owner[ins.pc + i] = ins.pc

    def _record_refs(self, ins: Instr):
        m = ins.mnemonic
        if m == "JSR":
            self.add_target_label(ins.value, is_call=True)
        elif m == "JMP":
            if ins.mode == ABS:
                self.add_target_label(ins.value)
            else:
                self.indirect_vectors.add(ins.value)
                self.add_data_ref(ins.value, ins.pc)
        elif m in BRANCHES:
            self.add_target_label(ins.value)
            if ins.value < ins.pc:
                self.backward_branches.add(ins.pc)
        elif ins.mode in ABS_MODES:
            self.add_data_ref(ins.value, ins.pc)

    def _trace(self, entries: list, core: bool = True):
        """Recursive descent from entries. core=False marks instructions as
        swept (validated fill) rather than traced."""
        work = list(entries)
        while work:
            pc = work.pop()
            while True:
                if not self.mem.is_populated(pc) or pc in self.owner or pc in self.exclude:
                    break
                ins = self.decode(pc)
                if ins is None or not ins.valid or not self._can_place(ins):
                    break
                self._place(ins, traced=core)
                if not core:
                    self.swept.add(ins.pc)
                self._record_refs(ins)
                m = ins.mnemonic
                if m == "JSR":
                    work.append(ins.value)
                    inline = INLINE_ARG_CALLS.get(ins.value)
                    if inline:
                        kind, n = inline
                        start = pc + ins.size
                        if all(self.mem.is_populated(start + i) and (start + i) not in self.owner
                               for i in range(n)):
                            self.inline_data[start] = inline
                            for i in range(n):
                                self.data_kind[start + i] = "inline"
                            if kind == "mli":
                                self.add_data_ref(self.mem.word_at(start + 1), pc)
                            pc = start + n
                            continue
                elif m == "JMP":
                    if ins.mode == ABS:
                        work.append(ins.value)
                    elif ins.mode == IND:
                        self._mark_pointer(ins.value, work)
                    elif ins.mode == ABSINDX:
                        # jump table: follow consecutive pointers into the image
                        a = ins.value
                        while self._mark_pointer(a, work) and a - ins.value < 64:
                            a += 2
                    break
                elif m in BRANCHES:
                    work.append(ins.value)
                    if m == "BRA":
                        break
                elif m in ("RTS", "RTI", "BRK"):
                    break
                pc += ins.size

    def _mark_tables(self) -> list:
        """Mark dispatch tables (see parse_table_spec) as data and return
        their in-image targets as entry points."""
        found = []
        for t in self.tables:
            size = 1 if t["hi"] is not None else 2
            for i in range(t["count"]):
                a = t["addr"] + i * t["stride"]
                if not all(self.mem.is_populated(a + k) for k in range(size)):
                    break
                raw = self.mem.byte_at(a) | ((t["hi"] << 8) if size == 1 else (self.mem.byte_at(a + 1) << 8))
                target = (raw + 1) & 0xFFFF if t["rts"] else raw
                for k in range(size):
                    self.data_kind[a + k] = "table"
                self.table_entries[a] = (size, target, t["rts"])
                if self.mem.is_populated(target):
                    found.append(target)
                    self.add_target_label(target, is_call=True)
        return found

    def _mark_pointer(self, addr: int, work: list) -> bool:
        """Mark a 2-byte code pointer at addr and queue its target."""
        if not (self.mem.is_populated(addr) and self.mem.is_populated(addr + 1)):
            return False
        if addr in self.owner or addr + 1 in self.owner or addr in self.data_kind:
            return False
        target = self.mem.word_at(addr)
        if not self.mem.is_populated(target):
            return False
        self.data_kind[addr] = "pointer"
        self.data_kind[addr + 1] = "pointer"
        self.add_target_label(target)
        work.append(target)
        return True

    def _free(self, a: int) -> bool:
        return (self.mem.is_populated(a) and a not in self.owner and a not in self.data_kind
                and a not in self.exclude)

    def _detect_jump_tables(self) -> list:
        """>=3 consecutive JMP abs in unreached bytes whose targets are in the
        image or named: these are jump vectors (e.g. $C311/$C314, DOS $3D0).
        Returns the JMP addresses as new entry points."""
        found = []
        for s, e in self.mem.get_contiguous_ranges():
            a = s
            while a <= e:
                n = 0
                while True:
                    b = a + 3 * n
                    if not all(self._free(b + k) and b + k not in self.forced_data for k in range(3)):
                        break
                    if self.mem.byte_at(b) != 0x4C:
                        break
                    t = self.mem.word_at(b + 1)
                    if not (self.mem.is_populated(t) or self.known_name(t)):
                        break
                    n += 1
                if n >= 3:
                    found += [a + 3 * i for i in range(n)]
                    self.auto_found.append(f"jump table ${a:04X} x{n}")
                    a += 3 * n
                else:
                    a += 1
        return found

    def _detect_pointer_tables(self) -> list:
        """>=4 consecutive words in unreached bytes whose first 4 entries all
        point at routine entries (traced code that something already calls or
        branches to, or a known name), directly or as address-1 for RTS
        dispatch; later entries keep a >=75% hit rate and the rest must point
        into the image. Merely landing on *some* instruction start is not
        enough: in a dense 16K ROM that happens ~40% of the time by chance.
        Strings and fills are classified first and never scanned. Marks the
        entries as table data; returns their untraced in-image targets."""
        found = []
        starts = self.traced | self.swept
        entries_ = self.call_targets | self.jump_targets

        def strong(w, rts):
            t = (w + 1) & 0xFFFF if rts else w
            if self.mem.is_populated(t):
                return t in starts and (t in entries_ or t in self.sym)
            return self.known_name(t) is not None

        def plausible(w, rts):
            """Weak entry: a named address, or in-image bytes that are code
            already or decode cleanly to a terminal (so they can be traced)."""
            t = (w + 1) & 0xFFFF if rts else w
            if not self.mem.is_populated(t):
                return self.known_name(t) is not None
            if t in starts:
                return True
            return t not in self.owner and t not in self.data_kind and self._block_ok(t, min(t + 255, 0xFFFF))

        for s, e in self.mem.get_contiguous_ranges():
            a = s
            while a < e:
                if not all(self._free(a + k) for k in range(8)) or a + 7 > e:
                    a += 1
                    continue
                probe = [self.mem.word_at(a + 2 * i) for i in range(4)]
                if not any(all(strong(w, r) for w in probe) for r in (False, True)):
                    a += 1
                    continue
                words = []
                b = a
                while b + 1 <= e and self._free(b) and self._free(b + 1):
                    words.append(self.mem.word_at(b))
                    b += 2
                best = None
                if len(words) >= 4:
                    for rts in (False, True):
                        if not all(strong(w, rts) for w in words[:4]):
                            continue
                        n, hits = 0, 0
                        for w in words:
                            if not plausible(w, rts):
                                break
                            hits += strong(w, rts)
                            n += 1
                            if n >= 4 and hits < 0.75 * n:
                                n -= 1
                                hits -= strong(w, rts)
                                break

                        if n >= 4 and (best is None or n > best[0]):
                            best = (n, rts)
                if best:
                    n, rts = best
                    for i in range(n):
                        p = a + 2 * i
                        w = words[i]
                        t = (w + 1) & 0xFFFF if rts else w
                        self.data_kind[p] = self.data_kind[p + 1] = "table"
                        self.table_entries[p] = (2, t, rts)
                        if self.mem.is_populated(t):
                            self.add_target_label(t, is_call=True)
                            if t not in self.owner:
                                found.append(t)
                    self.auto_found.append(f"pointer table ${a:04X} x{n}{' (address-1)' if rts else ''}")
                    a += 2 * n
                else:
                    a += 1
        return found

    def _fill_validated(self):
        """Sweep unreached gaps: accept a gap as code only if it is vouched
        (a branch/call target, or directly after a terminal traced
        instruction) and decodes cleanly to RTS/RTI/JMP/BRA/BRK inside the gap
        in >= 2 instructions. Accepted gaps are traced (so their branches are
        followed) as swept code. Iterates to a fixpoint. Idea from the
        orchard project's --auto-coverage pass (github.com/BrentRector/orchard).
        """
        for _ in range(25):
            changed = False
            for s, e in self.mem.get_contiguous_ranges():
                a = s
                while a <= e:
                    if not self._free(a) or a in self.forced_data:
                        a += 1
                        continue
                    gap = a
                    while a <= e and self._free(a) and a not in self.forced_data:
                        a += 1
                    if self._vouched(gap) and self._block_ok(gap, a - 1):
                        before = len(self.instrs)
                        self._trace([gap], core=False)
                        changed |= len(self.instrs) > before
            if not changed:
                break

    def _vouched(self, a: int) -> bool:
        if a in self.jump_targets or a in self.call_targets:
            return True
        for back in range(1, 4):
            p = a - back
            ins = self.instrs.get(p)
            if ins is not None and p in self.traced and p + ins.size == a \
                    and ins.mnemonic in TERMINALS:
                return True
        return False

    def _block_ok(self, start: int, end: int) -> bool:
        pc, n = start, 0
        while pc <= end:
            ins = self.decode(pc)
            if ins is None or not ins.valid or pc + ins.size - 1 > end:
                return False
            n += 1
            if ins.mnemonic in TERMINALS:
                return n >= 2
            pc += ins.size
        return False

    def _fill_linear(self, start: int, end: int):
        """Linear decode of an unreached gap; undefined opcodes become bytes."""
        pc = start
        while pc <= end:
            if pc in self.owner or pc in self.data_kind or pc in self.exclude:
                pc += 1
                continue
            if pc in self.forced_data:
                self.data_kind[pc] = "byte"
                pc += 1
                continue
            if pc in self.data_refs and pc not in self.jump_targets and pc not in self.call_targets:
                a = pc
                while a <= end and a not in self.owner and a not in self.exclude \
                        and (a == pc or (a not in self.jump_targets and a not in self.call_targets)):
                    self.data_kind.setdefault(a, "byte")
                    a += 1
                pc = a
                continue
            ins = self.decode(pc)
            if ins is None or not ins.valid or ins.pc + ins.size - 1 > end or not self._can_place(ins):
                self.data_kind[pc] = "byte"
                pc += 1
                continue
            self._place(ins, traced=False)
            self._record_refs(ins)
            pc += ins.size

    def analyze(self):
        """Pass 1: trace from entry points, classify the rest."""
        if self._analyzed:
            return
        self._analyzed = True
        ranges = self.mem.get_contiguous_ranges()

        for a in self.exclude:
            if self.mem.is_populated(a):
                self.data_kind[a] = "io"

        # Primary entry first: _trace pops from the end of a reversed list,
        # so earlier entries win when two entries overlap
        entries = []
        if self.entry_addr is not None:
            entries.append(self.entry_addr)
            self.add_target_label(self.entry_addr, is_call=True)
        if self.mem.is_populated(0xFFFA) and self.mem.is_populated(0xFFFF):
            for vec in (0xFFFA, 0xFFFC, 0xFFFE):
                target = self.mem.word_at(vec)
                for i in range(2):
                    self.data_kind[vec + i] = "vector"
                if self.mem.is_populated(target):
                    entries.append(target)
                    self.add_target_label(target, is_call=True)
        for e in self.entries:
            entries.append(e)
            self.add_target_label(e, is_call=True)
        entries += self._mark_tables()
        if not entries and ranges:
            entries.append(ranges[0][0])

        # (User-named addresses are not entry points by themselves: naming
        # alone doesn't make bytes code.)
        self._trace(list(reversed(entries)))

        # Strings / fills first so table detection never scans text
        self.data_kind.update(detect_data_regions(
            self.mem, {a for s_, e_ in ranges for a in range(s_, e_ + 1) if self._free(a)}))

        # Auto-detect jump / pointer tables, growing coverage to a fixpoint
        if self.auto_tables:
            for _ in range(10):
                new = self._detect_jump_tables()
                self._trace(new)
                ptr = self._detect_pointer_tables()
                self._trace(ptr)
                if not new and not ptr:
                    break

        # Unreached bytes: strings / fills first, then fill per mode
        free = set()
        for s, e in ranges:
            for a in range(s, e + 1):
                if a not in self.owner and a not in self.data_kind:
                    free.add(a)
        self.data_kind.update(detect_data_regions(self.mem, free))
        if self.fill == "all":
            for s, e in ranges:
                self._fill_linear(s, e)
        elif self.fill == "validated":
            self._fill_validated()
        for s, e in ranges:
            for a in range(s, e + 1):
                if a not in self.owner:
                    self.data_kind.setdefault(a, "byte")

        # Labels for data references inside the image
        for addr in list(self.data_refs):
            if not self.mem.is_populated(addr) or addr in self.labels:
                continue
            # Known names inside the image become real labels (or equates
            # when mid-instruction), never external equates
            known = self.known_name(addr)
            if known:
                self.labels[addr] = known
                continue
            if addr in self.code_addrs:
                self.labels[addr] = f"L_{addr:04X}"
            elif addr in self.owner:
                self.labels[addr] = f"L_{addr:04X}"   # mid-instruction: becomes an equate
            else:
                self.labels[addr] = f"D_{addr:04X}"
        # Branch/jump targets that landed mid-instruction also need equates
        for addr in list(self.jump_targets | self.call_targets):
            if self.mem.is_populated(addr) and addr not in self.labels:
                self.labels[addr] = f"L_{addr:04X}"
        # User symbols name their addresses even when nothing references them
        # (skipped when mid-instruction: that would need an equate nobody uses)
        for addr, name, _c in self.sym.items():
            if "+" in name or not self.mem.is_populated(addr):
                continue
            if addr in self.owner and self.owner[addr] != addr:
                if addr in self.labels:
                    self.labels[addr] = name
                continue
            self.labels[addr] = name
        # Mid-instruction labels are defined relative to their covering
        # instruction (COVER+n), which needs a label of its own
        self.mid_refs: dict[int, int] = {}
        for addr in list(self.labels):
            cover = self.owner.get(addr)
            if cover is not None and cover != addr:
                self.mid_refs[addr] = cover
                self.labels.setdefault(cover, f"L_{cover:04X}")

    # ---------------- pass 2: text ----------------

    def _user_ref(self, addr: int):
        """User symbol text for an external address ("NAME" or "NAME+n"),
        recording the base symbol for the equate block."""
        n = self.sym.name(addr)
        if not n:
            return None
        base = n.split("+")[0]
        base_addr = self.sym.by_name.get(base)
        if base_addr is None:
            return None
        if self.mem.is_populated(base_addr):
            if self.labels.get(base_addr) != base:
                return None
        else:
            self.used_user.add(base_addr)
        return n

    def _sym16(self, addr: int) -> str:
        if self.mem.is_populated(addr):
            if addr in self.labels:
                return self.labels[addr]
            return self._user_ref(addr) or f"${addr:04X}"
        u = self._user_ref(addr)
        if u:
            return u
        if addr in ROM_LABELS and self._builtin_ok(ROM_LABELS[addr], addr):
            self.used_rom.add(addr)
            return ROM_LABELS[addr]
        if addr in HW_LABELS and self._builtin_ok(HW_LABELS[addr], addr):
            self.used_hw.add(addr)
            return HW_LABELS[addr]
        if addr in self.labels:
            return self.labels[addr]
        return f"${addr:04X}"

    def _sym8(self, addr: int) -> str:
        if self.mem.is_populated(addr):
            if addr in self.labels:
                return self.labels[addr]
            return self._user_ref(addr) or f"${addr:02X}"
        u = self._user_ref(addr)
        if u:
            return u
        if self.zp_names and addr in ZP_LABELS and self._builtin_ok(
                ZP_LABELS[addr].split("+")[0],
                addr - int(ZP_LABELS[addr].split("+")[1]) if "+" in ZP_LABELS[addr] else addr):
            name = ZP_LABELS[addr]
            # "LINNUM+1" style names: define only the base symbol
            self.used_zp.add(addr - int(name.split("+")[1]) if "+" in name else addr)
            return ZP_LABELS[addr]
        return f"${addr:02X}"

    def format_operand(self, ins: Instr) -> str:
        mode, v = ins.mode, ins.value
        if mode == IMP:
            return ""
        if mode == ACC:
            return "A"
        if mode == IMM:
            return f"#${v:02X}"
        if mode in (ZP, ZPX, ZPY):
            # symbolic zero-page operands get z: so ca65 keeps the 2-byte
            # form even when the symbol is a forward reference
            s8 = self._sym8(v)
            if not s8.startswith("$"):
                s8 = f"z:{s8}"
            return s8 + {ZP: "", ZPX: ",X", ZPY: ",Y"}[mode]
        if mode == INDX:
            return f"({self._sym8(v)},X)"
        if mode == INDY:
            return f"({self._sym8(v)}),Y"
        if mode == ZPIND:
            return f"({self._sym8(v)})"
        if mode == REL:
            return self._sym16(v)
        if mode == ZPREL:
            return f"{self._sym8(ins.zp)},{self._sym16(v)}"
        # 16-bit modes: force absolute when the address is in zero page.
        # JMP (ind) / JMP (ind,X) only exist in absolute form, and ca65
        # rejects a: inside the parentheses.
        s = self._sym16(v)
        if v < 0x100 and mode not in (IND, ABSINDX):
            s = f"a:{s}"
        if mode == ABS:
            return s
        if mode == ABSX:
            return f"{s},X"
        if mode == ABSY:
            return f"{s},Y"
        if mode == IND:
            return f"({s})"
        if mode == ABSINDX:
            return f"({s},X)"
        return s

    def disassemble_instruction(self, pc: int) -> tuple:
        """(mnemonic, operand, consumed, comment) for the instruction at pc."""
        ins = self.instrs.get(pc) or self.decode(pc)
        if ins is None:
            return (".byte", "$??", 1, "; unpopulated")
        if not ins.valid:
            return (".byte", f"${ins.opcode:02X}", 1, "; undefined opcode")
        comment = ""
        if ins.mode in ABS_MODES and ins.mnemonic not in ("JSR", "JMP"):
            c = self.sym.comment(ins.value)
            comment = f"; {c}" if c else hw_comment(ins.value)
        return (ins.mnemonic, self.format_operand(ins), ins.size, comment)

    def _string_lines(self, pc: int, end: int, kind: str) -> tuple:
        """Return (text_bytes, next_pc) for a string run starting at pc."""
        a = pc
        while a <= end and self.data_kind.get(a) == kind and (a == pc or a not in self.labels) \
                and a - pc < 40:
            a += 1
        return bytes(self.mem.byte_at(i) for i in range(pc, a)), a

    @staticmethod
    def _ca65_string(text: str) -> str:
        """Render text as a .byte argument list, splitting out quotes."""
        parts = []
        buf = ""
        for ch in text:
            if ch == '"':
                if buf:
                    parts.append(f'"{buf}"')
                    buf = ""
                parts.append("$22")
            else:
                buf += ch
        if buf:
            parts.append(f'"{buf}"')
        return ",".join(parts)

    def _build_lines(self, annotate: bool):
        self.lines = []
        self.line_len: dict[int, int] = {}
        ranges = self.mem.get_contiguous_ranges()
        for rng_start, rng_end in ranges:
            pc = rng_start
            while pc <= rng_end:
                if pc in self.instrs:
                    ins = self.instrs[pc]
                    mnemonic, operand, consumed, comment = self.disassemble_instruction(pc)
                    if annotate:
                        if mnemonic in ("JSR", "JMP") and ins.mode in (ABS,) and not comment:
                            d = self.describe(ins.value)
                            comment = f"; {d}" if d else ""
                        overlaps = [a for a, c in self.mid_refs.items() if c == pc]
                        if overlaps:
                            what = ", ".join(f"{self.labels[a]} (+{a - pc})" for a in sorted(overlaps))
                            note = f"; overlapping entry/ref: {what}"
                            comment = f"{comment} | {note[2:]}" if comment else note
                        if pc in self.backward_branches:
                            comment = (comment + " (loop)") if comment else "; loop back"
                    self.lines.append((pc, self.instr_bytes(ins), mnemonic, operand, comment))
                    pc += consumed
                    continue

                if pc in self.table_entries:
                    size, target, rts = self.table_entries[pc]
                    sym = self._sym16(target)
                    expr = f"{sym}-1" if rts else sym
                    how = "RTS dispatch (address-1)" if rts else "dispatch address"
                    if size == 2:
                        self.lines.append((pc, f"{self.mem.byte_at(pc):02X} {self.mem.byte_at(pc + 1):02X}",
                                           ".word", expr, f"; {how}"))
                    else:
                        self.lines.append((pc, f"{self.mem.byte_at(pc):02X}", ".byte", f"<({expr})",
                                           f"; {how}, low byte"))
                    pc += size
                    continue

                if pc in self.inline_data:
                    kind, n = self.inline_data[pc]
                    if kind == "mli":
                        cmd = self.mem.byte_at(pc)
                        name = MLI_CALLS.get(cmd, "unknown call")
                        self.lines.append((pc, f"{cmd:02X}", ".byte", f"${cmd:02X}", f"; MLI {name}"))
                        param = self.mem.word_at(pc + 1)
                        self.lines.append((pc + 1, f"{param & 0xFF:02X} {param >> 8:02X}", ".word",
                                           self._sym16(param), "; parameter block"))
                    pc += n
                    continue

                kind = self.data_kind.get(pc, "byte")
                if kind in ("vector", "pointer"):
                    target = self.mem.word_at(pc)
                    name = VECTOR_NAMES.get(pc, "jump") if kind == "vector" else "jump"
                    self.lines.append((pc, f"{target & 0xFF:02X} {target >> 8:02X}", ".word",
                                       self._sym16(target), f"; {name} vector"))
                    pc += 2
                    continue
                if kind in ("string", "hstring"):
                    raw, nxt = self._string_lines(pc, rng_end, kind)
                    text = "".join(chr(b & 0x7F) for b in raw)
                    hex_b = " ".join(f"{b:02X}" for b in raw[:4]) + (" ..." if len(raw) > 4 else "")
                    if kind == "string":
                        self.lines.append((pc, hex_b, ".byte", self._ca65_string(text), "; ASCII"))
                    else:
                        self.used_hasc = True
                        self.lines.append((pc, hex_b, "HASC", self._ca65_string(text), "; high-bit ASCII"))
                    pc = nxt
                    continue
                if kind in ("zero", "ff"):
                    a = pc
                    while a <= rng_end and self.data_kind.get(a) == kind and (a == pc or a not in self.labels):
                        a += 1
                    fill = 0x00 if kind == "zero" else 0xFF
                    if a - pc >= 4:
                        self.lines.append((pc, f"{fill:02X} ...", ".res", f"{a - pc}, ${fill:02X}",
                                           f"; {a - pc} bytes of ${fill:02X}"))
                        pc = a
                        continue
                    kind = "byte"   # short run (split by a label): emit as .byte
                # plain bytes (including 'io' and undecodable gaps), up to 8 per line
                a = pc
                while a <= rng_end and a - pc < 8 and a not in self.instrs and a not in self.inline_data \
                        and (self.data_kind.get(a, "byte") in ("byte", "io") or
                             (a == pc and kind == "byte")) \
                        and (a == pc or a not in self.labels):
                    a += 1
                raw = bytes(self.mem.byte_at(i) for i in range(pc, a))
                comment = "; I/O space" if kind == "io" else ""
                if not comment:
                    txt = "".join(chr(b & 0x7F) if is_printable(b & 0x7F) else "." for b in raw)
                    comment = f"; {txt}"
                self.lines.append((pc, " ".join(f"{b:02X}" for b in raw), ".byte",
                                   ",".join(f"${b:02X}" for b in raw), comment))
                pc = a

        # Lines tile each range contiguously: a line's length is the gap to
        # the next line start (or to the end of its range)
        ends = {s: e for s, e in ranges}
        starts = sorted(ends)
        pcs = [ln[0] for ln in self.lines]
        for i, pc in enumerate(pcs):
            rng_end = next(e for s, e in ((s, ends[s]) for s in reversed(starts)) if s <= pc)
            nxt = pcs[i + 1] if i + 1 < len(pcs) and pcs[i + 1] <= rng_end else rng_end + 1
            self.line_len[pc] = nxt - pc

    def disassemble(self, show_hex: bool = True, annotate: bool = False) -> str:
        self.analyze()
        self._build_lines(annotate)
        return self._format_output(show_hex, annotate)

    def _format_output(self, show_hex: bool, annotate: bool) -> str:
        out = []
        line_starts = {pc for (pc, *_r) in self.lines}
        cpu_name = "6502X" if (self.cpu == "6502" and self.undocumented) else \
                   ("65C02" if self.cpu != "6502" else "6502")

        out.append("; =============================================")
        out.append(f"; Apple II {self.cpu.upper()} disassembly (ca65 syntax)")
        out.append("; =============================================")
        if self.rom_name:
            out.append(f"; ROM image: {self.rom_name}")
            out.append("; (stores into $D000-$FFFF write language-card RAM, not this ROM)")
        out.append(f'                 .setcpu "{cpu_name}"')
        out.append("")

        if self.used_hasc:
            out.append("; High-bit ASCII string helper")
            out.append(".macro HASC str")
            out.append("        .repeat .strlen(str), i")
            out.append("        .byte .strat(str, i) | $80")
            out.append("        .endrep")
            out.append(".endmacro")
            out.append("")

        rom_eq = sorted(a for a in self.used_rom if not self.mem.is_populated(a))
        if rom_eq:
            out.append("; =============================================")
            out.append("; ROM / OS Entry Points Used")
            out.append("; =============================================")
            for addr in rom_eq:
                desc = f"  ; {ROM_DESCRIPTIONS[addr]}" if annotate and addr in ROM_DESCRIPTIONS else ""
                out.append(f"{ROM_LABELS[addr]:16s} = ${addr:04X}{desc}")
            out.append("")

        hw_eq = sorted(a for a in self.used_hw if not self.mem.is_populated(a))
        if hw_eq:
            out.append("; =============================================")
            out.append("; Hardware I/O (soft switches)")
            out.append("; =============================================")
            for addr in hw_eq:
                desc = f"  ; {HW_DESCRIPTIONS[addr]}" if addr in HW_DESCRIPTIONS else ""
                out.append(f"{HW_LABELS[addr]:16s} = ${addr:04X}{desc}")
            out.append("")

        zp_eq = sorted(a for a in self.used_zp if not self.mem.is_populated(a))
        if zp_eq:
            out.append("; =============================================")
            out.append("; Zero Page")
            out.append("; =============================================")
            for addr in zp_eq:
                desc = f"  ; {ZP_DESCRIPTIONS[addr]}" if addr in ZP_DESCRIPTIONS else ""
                out.append(f"{ZP_LABELS[addr]:16s} = ${addr:02X}{desc}")
            out.append("")

        user_eq = sorted(a for a in self.used_user if not self.mem.is_populated(a))
        if user_eq:
            out.append("; =============================================")
            out.append("; User Symbols")
            out.append("; =============================================")
            for addr in user_eq:
                c = self.sym.comment(addr)
                fmt = f"${addr:02X}" if addr < 0x100 else f"${addr:04X}"
                out.append(f"{self.sym.name(addr):16s} = {fmt}" + (f"  ; {c}" if c else ""))
            out.append("")

        # Labels that are not at a line start: inside an instruction they
        # are written COVER+n (documents the overlap; the value is identical),
        # inside a data line they stay numeric
        mid = sorted(a for a, name in self.labels.items()
                     if a not in line_starts and self.mem.is_populated(a))
        if mid:
            out.append("; =============================================")
            out.append("; Mid-instruction / mid-data references")
            out.append("; =============================================")
            for addr in mid:
                cover = self.mid_refs.get(addr)
                if cover is not None and addr >= 0x100 and cover in line_starts:
                    ins = self.instrs[cover]
                    out.append(f"{self.labels[addr]:16s} = {self.labels[cover]}+{addr - cover}"
                               f"  ; inside {ins.mnemonic} at ${cover:04X}")
                else:
                    out.append(f"{self.labels[addr]:16s} = ${addr:04X}")
            out.append("")

        ranges = self.mem.get_contiguous_ranges()
        out.append("; =============================================")
        out.append(f"; Memory ranges: {len(ranges)}")
        for s, e in ranges:
            out.append(f";   ${s:04X}-${e:04X} ({e - s + 1} bytes)")
        if self.entry_addr is not None:
            out.append(f"; Entry: ${self.entry_addr:04X}")
        n_swept = len(self.swept)
        n_filled = len(self.instrs) - len(self.traced) - n_swept
        out.append(f"; Traced instructions: {len(self.traced)}, swept: {n_swept}, filled: {n_filled}"
                   f" (fill mode: {self.fill})")
        for note in self.auto_found:
            out.append(f"; Auto-detected {note}")
        if self.sym.sources:
            out.append(f"; Symbols: {', '.join(self.sym.sources)} ({len(self.sym)} entries)")
        out.append("; =============================================")
        out.append("")

        prev_end = None
        prev_was_data = False
        for (pc, hex_bytes, mnemonic, operand, comment) in self.lines:
            if prev_end is None or pc > prev_end + 1:
                out.append("")
                out.append(f"                 .org   ${pc:04X}")
                out.append("")

            label_str = self.labels.get(pc, "")

            if annotate:
                is_data = (mnemonic.startswith(".") or mnemonic == "HASC") and \
                          "MLI" not in comment and "parameter block" not in comment
                if is_data and "dispatch" in comment and not prev_was_data:
                    out.append("; ---- Dispatch table ----")
                    prev_was_data = True
                    is_data = True
                if label_str and label_str.startswith("SUB_"):
                    out.append("")
                    out.append(f"; ---- {label_str} ----")
                elif label_str and pc in self.call_targets and not label_str.startswith("L_"):
                    d = self.describe(pc)
                    out.append("")
                    out.append(f"; ---- {label_str}{': ' + d if d else ''} ----")
                if is_data and not prev_was_data:
                    if mnemonic in (".byte", "HASC") and "ASCII" in comment:
                        out.append("; ---- Data: ASCII string ----")
                    elif mnemonic == ".res":
                        out.append(f"; ---- Data: fill ({operand}) ----")
                    elif mnemonic == ".word" and "vector" in comment:
                        out.append("; ---- Vectors / jump pointers ----")
                    else:
                        out.append("; ---- Data ----")
                prev_was_data = is_data

            instr = f"{mnemonic:8s}{operand}" if operand else mnemonic
            instr = instr.ljust(30) if len(instr) < 30 else instr + " "
            if show_hex:
                if label_str:
                    out.append(f"{label_str}:")
                out.append(f"  {pc:04X}  {hex_bytes:10s}  {instr}{comment}")
            else:
                if label_str and len(label_str) > 15:
                    out.append(f"{label_str}:")
                    label_str = ""
                lab = f"{label_str}:" if label_str else ""
                out.append(f"{lab:16s} {instr}{comment}")

            prev_end = pc + self.line_len[pc] - 1

        return "\n".join(line.rstrip() for line in out) + "\n"

# ===========================================================================
# CLI
# ===========================================================================

def parse_table_spec(spec: str) -> dict:
    """ADDR:COUNT[:rts][:stride=N][:hi=XX] -> table dict.

    Word table by default (little-endian addresses). rts = entries hold
    address-1 (pushed and entered with RTS). stride = bytes between entries
    (e.g. 3 for Applesoft's precedence+address operator table). hi=XX = the
    table holds only low bytes; XX is the fixed high byte.
    """
    parts = spec.split(":")
    if len(parts) < 2:
        raise argparse.ArgumentTypeError(f"bad --table spec {spec!r}: need ADDR:COUNT")
    t = {"addr": int(parts[0], 16) if not parts[0].lower().startswith("0x") else int(parts[0], 0),
         "count": int(parts[1], 0), "rts": False, "stride": None, "hi": None}
    for opt in parts[2:]:
        if opt == "rts":
            t["rts"] = True
        elif opt.startswith("stride="):
            t["stride"] = int(opt[7:], 0)
        elif opt.startswith("hi="):
            t["hi"] = int(opt[3:], 16)
        else:
            raise argparse.ArgumentTypeError(f"bad --table option {opt!r}")
    if t["stride"] is None:
        t["stride"] = 1 if t["hi"] is not None else 2
    return t


def _addr(s: str) -> int:
    s = s.strip()
    if s.startswith("$"):
        return int(s[1:], 16)
    if s.lower().startswith("0x"):
        return int(s, 16)
    return int(s, 16)   # bare numbers are hex, as elsewhere in Apple II docs


def parse_range(spec: str) -> tuple:
    """'$C000-$C0FF' / '0xC000-0xC0FF' / 'C000-C0FF' -> (start, end) inclusive."""
    a, b = spec.split("-", 1)
    s_, e_ = _addr(a), _addr(b)
    if e_ < s_:
        raise argparse.ArgumentTypeError(f"bad range {spec!r}")
    return s_, e_


def build_disassembler(args) -> tuple:
    segments, info = load_image(args.file, org=args.org, raw=args.raw)
    mem = MemoryImage()
    for org, data in segments:
        mem.load_segment(org, data)
    cpu = args.cpu
    if cpu == "auto":
        cpu = info.get("cpu_hint") or "6502"
    entry = info.get("entry")
    tables = [parse_table_spec(t) for t in args.table]
    symbols = load_symbols(args.symbols)
    regions = [parse_range(r) for r in args.data_region]
    fill = "none" if args.no_fill else args.fill
    if not args.no_presets:
        tables += info.get("tables", [])
    dasm = Disassembler6502(mem, entry_addr=entry, cpu=cpu, undocumented=args.undocumented,
                            entries=args.entry, fill=fill, exclude=info.get("exclude"),
                            zp_names=args.zp_names or bool(info.get("is_rom")), tables=tables,
                            symbols=symbols, data_regions=regions, auto_tables=not args.no_auto_tables)
    if info.get("is_rom"):
        dasm.rom_name = info.get("rom_name") or "ROM"
    return dasm, info


def add_common_args(parser):
    parser.add_argument("file", help="Binary, AppleSingle, or ROM image")
    parser.add_argument("--org", type=lambda x: int(x, 0), default=None,
                        help="Load address (hex, e.g. 0x2000); auto for AppleSingle/DOS 3.3")
    parser.add_argument("--raw", action="store_true", help="Skip container detection")
    parser.add_argument("--cpu", choices=["auto", "6502", "65c02", "r65c02"], default="auto",
                        help="CPU (default: auto from ROM ID bytes, else 6502)")
    parser.add_argument("--undocumented", action="store_true",
                        help="Decode NMOS undocumented opcodes (ca65 6502X)")
    parser.add_argument("--entry", type=lambda x: int(x, 0), action="append", default=[],
                        help="Extra entry point to trace from (repeatable)")
    parser.add_argument("--table", action="append", default=[], metavar="ADDR:COUNT[:rts][:stride=N][:hi=XX]",
                        help="Dispatch table (hex ADDR): trace its targets, emit as .word/.byte "
                             "(rts = entries are address-1; hi=XX = low-byte table)")
    parser.add_argument("--no-presets", action="store_true",
                        help="Ignore dispatch tables the loader recognizes in known ROMs")
    parser.add_argument("--zp-names", action="store_true",
                        help="Use Monitor/Applesoft zero-page names (default on for ROM images)")
    parser.add_argument("--symbols", action="append", default=[], metavar="FILE",
                        help="Symbol file (repeatable): orchard schema-v1.0 JSON, flat JSON, "
                             "or ca65 'NAME = $XXXX ; comment' lines. First definition wins; "
                             "overrides built-in and generated names")
    parser.add_argument("--data-region", action="append", default=[], metavar="START-END",
                        help="Force an inclusive hex range to be data (repeatable), e.g. CB99-CBD3")
    parser.add_argument("--fill", choices=["validated", "all", "none"], default="validated",
                        help="Unreached bytes: 'validated' = code only if it follows traced code "
                             "or is a target and decodes cleanly to RTS/JMP (default); "
                             "'all' = decode everything decodable; 'none' = data")
    parser.add_argument("--no-fill", action="store_true", help="Same as --fill none")
    parser.add_argument("--no-auto-tables", action="store_true",
                        help="Disable automatic JMP-table / pointer-table detection")


def main():
    parser = argparse.ArgumentParser(description="6502/65C02 disassembler for Apple II")
    add_common_args(parser)
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--no-hex", action="store_true",
                        help="Omit address/hex columns (reassemblable ca65 source)")
    parser.add_argument("--annotate", action="store_true",
                        help="Subroutine separators, ROM call descriptions, loop markers")
    parser.add_argument("--syntax", choices=["ca65"], default="ca65")
    args = parser.parse_args()

    dasm, info = build_disassembler(args)
    print(f"; Format: {info['format']}" + (f" ({info['rom_name']})" if info.get("rom_name") else ""),
          file=sys.stderr)
    for s in info["segments"]:
        print(f";   ${s['org']:04X}-${s['org'] + s['length'] - 1:04X} ({s['length']} bytes)", file=sys.stderr)
    if info.get("entry") is not None:
        print(f"; Entry: ${info['entry']:04X}  CPU: {dasm.cpu}", file=sys.stderr)
    for n in info["notes"]:
        print(f"; {n}", file=sys.stderr)

    output = dasm.disassemble(show_hex=not args.no_hex, annotate=args.annotate)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(output)


if __name__ == "__main__":
    main()

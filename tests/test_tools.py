"""Tests for the 6502 disassembler tools (Apple II plus the other machines).

Run: python3 -m unittest discover -s tests -v   (or python3 -m pytest tests/)
Round-trip tests need cc65 (ca65 + ld65) and are skipped without it.
"""

import os
import random
import shutil
import struct
import subprocess
import sys
import re
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import a2loader  # noqa: E402
import annotator  # noqa: E402
import loader  # noqa: E402
import machines  # noqa: E402
import dasm6502  # noqa: E402
import json  # noqa: E402
import symbols  # noqa: E402
from dasm6502 import Disassembler6502, MemoryImage  # noqa: E402
import xref  # noqa: E402

HAVE_CA65 = shutil.which("ca65") and shutil.which("ld65")


def make_dasm(data: bytes, org: int, cpu="6502", **kw) -> Disassembler6502:
    mem = MemoryImage()
    mem.load_segment(org, data)
    return Disassembler6502(mem, entry_addr=kw.pop("entry", org), cpu=cpu, **kw)


def assemble(src: str, tmp: str, name: str) -> bytes:
    s = os.path.join(tmp, name + ".s")
    o = os.path.join(tmp, name + ".o")
    b = os.path.join(tmp, name + ".bin")
    with open(s, "w") as f:
        f.write(src)
    r = subprocess.run(["ca65", s, "-o", o], capture_output=True, text=True)
    if r.returncode:
        raise AssertionError("ca65 failed:\n" + r.stderr[:2000])
    subprocess.run(["ld65", "-t", "none", o, "-o", b], check=True, capture_output=True, text=True)
    with open(b, "rb") as f:
        return f.read()


def applesingle(data: bytes, ptype: int, aux: int, name: bytes = b"TEST") -> bytes:
    """Build an AppleSingle v2 file with name, ProDOS info and data fork."""
    entries = [(3, name), (11, struct.pack(">HHI", 0xC3, ptype, aux)), (1, data)]
    header = b"\x00\x05\x16\x00" + struct.pack(">I", 0x00020000) + b"\x00" * 16
    header += struct.pack(">H", len(entries))
    off = len(header) + 12 * len(entries)
    descs, body = b"", b""
    for eid, payload in entries:
        descs += struct.pack(">III", eid, off + len(body), len(payload))
        body += payload
    return header + descs + body


class TestOpcodeTables(unittest.TestCase):
    def test_table_sizes(self):
        self.assertEqual(len(dasm6502.OPCODES_6502), 151)
        self.assertEqual(len(dasm6502.OPCODES_65C02), 178)
        self.assertEqual(len(dasm6502.OPCODES_R65C02), 210)

    def test_instruction_sizes(self):
        d = make_dasm(bytes([0xAD, 0x34, 0x12, 0xB1, 0x12, 0xEA]), 0x1000)
        self.assertEqual([d.decode(a).size for a in (0x1000, 0x1003, 0x1005)], [3, 2, 1])

    def test_branch_target_math(self):
        # BNE -3 at $1002 -> $1001 ; BEQ +$7F at $1000 -> $1081
        d = make_dasm(bytes([0xF0, 0x7F, 0xD0, 0xFD]), 0x1000)
        self.assertEqual(d.decode(0x1000).value, 0x1081)
        self.assertEqual(d.decode(0x1002).value, 0x1001)
        # a branch wrapping past $FFFF cannot be written in ca65: decoded as data
        d = make_dasm(bytes([0xD0, 0x10]), 0xFFF8)
        self.assertFalse(d.decode(0xFFF8).valid)

    def test_cpu_gating(self):
        code = bytes([0x64, 0x12, 0x80, 0x00, 0x60])   # STZ / BRA only exist on 65C02
        text6502 = make_dasm(code, 0x0800, cpu="6502").disassemble(show_hex=False)
        text65c02 = make_dasm(code, 0x0800, cpu="65c02").disassemble(show_hex=False)
        self.assertNotIn("BRA", text6502)
        self.assertIn(".byte", text6502)
        self.assertIn("BRA", text65c02)
        self.assertIn("STZ", text65c02)

    def test_zero_page_forced_absolute(self):
        text = make_dasm(bytes([0xAD, 0x12, 0x00, 0x60]), 0x0800).disassemble(show_hex=False)
        self.assertIn("LDA     a:$0012", text)


class TestAnalysis(unittest.TestCase):
    def test_mli_inline_args(self):
        # JSR $BF00 / .byte $C8 / .word $0810 / RTS
        code = bytes([0x20, 0x00, 0xBF, 0xC8, 0x10, 0x08, 0x60])
        d = make_dasm(code, 0x0800)
        text = d.disassemble(show_hex=True, annotate=True)
        self.assertIn("MLI OPEN", text)
        self.assertIn(0x0806, d.instrs)            # RTS traced after the 3 inline bytes
        self.assertNotIn(0x0803, d.instrs)

    def test_trace_stops_at_rts_and_keeps_strings_as_data(self):
        code = bytes([0xA9, 0x00, 0x60]) + b"HELLO WORLD" + b"\x00"
        d = make_dasm(code, 0x0800)
        text = d.disassemble(show_hex=False)
        self.assertIn('"HELLO WORLD"', text)

    def test_high_bit_strings(self):
        code = bytes([0x60]) + bytes(c | 0x80 for c in b"APPLE II")
        text = make_dasm(code, 0x0800).disassemble(show_hex=False)
        self.assertIn('HASC    "APPLE II"', text)

    def test_jmp_indirect_pointer_traced(self):
        # JMP ($0805) ; .word $0807 ; $0807: RTS
        code = bytes([0x6C, 0x05, 0x08, 0xEA, 0xEA, 0x07, 0x08, 0x60])
        d = make_dasm(code, 0x0800)
        d.analyze()
        self.assertEqual(d.data_kind.get(0x0805), "pointer")
        self.assertIn(0x0807, d.traced)

    def test_rom_vectors_traced(self):
        rom = bytearray([0xEA] * 0x800)
        rom[0x0262] = 0x60                         # $FA62 RTS
        rom[0x07FA:0x0800] = bytes([0x62, 0xFA, 0x62, 0xFA, 0x62, 0xFA])
        d = make_dasm(bytes(rom), 0xF800, entry=None)
        text = d.disassemble(show_hex=False, annotate=True)
        self.assertIn(0xFA62, d.traced)
        self.assertIn("RESET vector", text)

    def test_dispatch_tables(self):
        # $0800: word table (address-1) -> $0806 ; $0802: lo-byte table, hi=$08 -> $0807
        code = bytes([0x05, 0x08, 0x06, 0xEA, 0xEA, 0xEA, 0x60, 0x60])
        t1 = dasm6502.parse_table_spec("0800:1:rts")
        t2 = dasm6502.parse_table_spec("0802:1:rts:hi=08")
        self.assertEqual((t2["stride"], t2["hi"]), (1, 0x08))
        d = make_dasm(code, 0x0800, entry=None, tables=[t1, t2])
        text = d.disassemble(show_hex=False)
        self.assertIn(0x0806, d.traced)
        self.assertIn(0x0807, d.traced)
        self.assertIn(".word   SUB_0806-1", text)
        self.assertIn(".byte   <(SUB_0807-1)", text)

    def test_table_stride(self):
        t = dasm6502.parse_table_spec("D0B3:10:rts:stride=3")
        self.assertEqual((t["addr"], t["count"], t["rts"], t["stride"]), (0xD0B3, 10, True, 3))

    def test_xref_finds_rom_calls_and_switches(self):
        code = bytes([0x20, 0xED, 0xFD, 0xAD, 0x30, 0xC0, 0x60])
        x = xref.CrossReferenceBuilder(make_dasm(code, 0x0800))
        x.analyze()
        self.assertIn(0xFDED, x.rom_calls)
        self.assertIn(0xC030, x.hw_accesses)
        self.assertIn("COUT", x.format_callgraph())


class TestLoader(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, name, data):
        p = os.path.join(self.tmp, name)
        with open(p, "wb") as f:
            f.write(data)
        return p

    def test_applesingle_bin(self):
        p = self.write("prog.as", applesingle(b"\xA9\x00\x60", 0x06, 0x6000))
        info = a2loader.identify_file(p)
        self.assertEqual(info["format"], "applesingle")
        self.assertEqual(info["prodos_type_name"], "BIN")
        self.assertEqual(info["segments"][0]["org"], 0x6000)
        self.assertEqual(info["segments"][0]["data"], b"\xA9\x00\x60")
        self.assertEqual(info["name"], "TEST")

    def test_applesingle_sys_loads_at_2000(self):
        p = self.write("prog.as", applesingle(b"\x60", 0xFF, 0x0000))
        self.assertEqual(a2loader.identify_file(p)["segments"][0]["org"], 0x2000)

    def test_dos33_header(self):
        p = self.write("prog.bin", b"\x00\x03\x03\x00\xA9\x00\x60")
        info = a2loader.identify_file(p)
        self.assertEqual(info["format"], "dos33_bin")
        self.assertEqual(info["segments"][0]["org"], 0x0300)

    def test_filename_suffix(self):
        p = self.write("GAME#064000", b"\x60")
        self.assertEqual(a2loader.identify_file(p)["segments"][0]["org"], 0x4000)

    def test_org_override_and_raw(self):
        p = self.write("prog.as", applesingle(b"\x60", 0x06, 0x6000))
        self.assertEqual(a2loader.identify_file(p, org=0x1000)["segments"][0]["org"], 0x1000)
        self.assertEqual(a2loader.identify_file(p, raw=True)["format"], "raw")

    def test_rom_detection(self):
        rom = bytearray(0x800)
        rom[0x7FC:0x7FE] = bytes([0x62, 0xFA])     # RESET -> $FA62
        rom[0xFBB3 - 0xF800] = 0x06
        rom[0xFBC0 - 0xF800] = 0xE0                # enhanced IIe
        info = a2loader.identify_file(self.write("rom.bin", bytes(rom)))
        self.assertTrue(info["is_rom"])
        self.assertEqual(info["segments"][0]["org"], 0xF800)
        self.assertEqual(info["entry"], 0xFA62)
        self.assertEqual(info["cpu_hint"], "65c02")


class TestSymbolsAndCoverage(unittest.TestCase):
    """--symbols, --data-region, auto tables, validated fill, COVER+n."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, name, text):
        p = os.path.join(self.tmp, name)
        with open(p, "w") as f:
            f.write(text)
        return p

    def test_orchard_schema(self):
        p = self.write("a2.json", json.dumps({
            "schema_version": "1.0",
            "categories": {
                "page_zero": {"0x0067": {"name": "TXTTAB", "size": 2, "comment": "prog start"}},
                "monitor_rom": {"0xFDED": {"name": "COUT", "comment": "char out"},
                                "0xFDED_dup": {"name": "COUTX"}},
                "bdos_functions": {"9": {"name": "PRINTSTR"}},
                "memory_map_regions": {"0x0400": {"name": "TEXT1"}}}}))
        t = symbols.load_symbols([p])
        self.assertEqual(t.name(0xFDED), "COUT")          # first definition wins
        self.assertEqual(t.name(0x0068), "TXTTAB+1")      # size 2
        self.assertEqual(t.comment(0x0067), "prog start")
        self.assertIsNone(t.name(0x0400))                 # region category skipped
        self.assertEqual(len(list(t.items())), 2)

    def test_alias_does_not_block_real_name(self):
        p = self.write("r.json", json.dumps({"schema_version": "1.0", "categories": {"x": {
            "0xC800": {"name": "EXP_ROM", "size": 2048},
            "0xCFFF": {"name": "EXPROMOFF"}}}}))
        t = symbols.load_symbols([p])
        self.assertEqual(t.name(0xCFFF), "EXPROMOFF")
        self.assertEqual(t.name(0xC801), "EXP_ROM+1")
        self.assertEqual(json.loads(t.to_json())["categories"]["user"]["0xC800"]["size"], 2048)

    def test_flat_json_and_text(self):
        p1 = self.write("f.json", json.dumps({"0xC311": "AUXMOVE", "$C314": {"name": "XFER", "comment": "x"}}))
        p2 = self.write("s.inc", "; comment\nHOOK = $03F5 ; ampersand\n$0300 MYSUB my routine\nbad-name = $10\n")
        t = symbols.load_symbols([p1, p2])
        self.assertEqual((t.name(0xC311), t.name(0xC314), t.comment(0xC314)), ("AUXMOVE", "XFER", "x"))
        self.assertEqual((t.name(0x03F5), t.comment(0x03F5)), ("HOOK", "ampersand"))
        self.assertEqual(t.name(0x0300), "MYSUB")
        roundtrip = symbols.SymbolTable()
        roundtrip._load_json(json.loads(t.to_json()), "rt")
        self.assertEqual(roundtrip.name(0xC314), "XFER")

    def test_symbols_rename_labels_and_externals(self):
        p = self.write("u.inc", "MAIN = $0800\nPRINT = $0806 ; print it\nMYHOOK = $03F5 ; hook\n")
        tbl = symbols.load_symbols([p])
        code = bytes([0x20, 0x06, 0x08, 0x4C, 0xF5, 0x03, 0x60])
        text = make_dasm(code, 0x0800, symbols=tbl).disassemble(show_hex=False, annotate=True)
        self.assertIn("MAIN:", text)
        self.assertIn("JSR     PRINT", text)
        self.assertIn("MYHOOK           = $03F5  ; hook", text)
        self.assertIn("; ---- PRINT: print it ----", text)

    def test_user_name_shadows_builtin(self):
        # user calls $0300 "COUT": the ROM's COUT must not be emitted too
        p = self.write("u.inc", "COUT = $0300\n")
        code = bytes([0x20, 0x00, 0x03, 0x20, 0xED, 0xFD, 0x60])
        text = make_dasm(code, 0x0800, symbols=symbols.load_symbols([p])).disassemble(show_hex=False)
        self.assertIn("JSR     COUT", text)
        self.assertIn("JSR     $FDED", text)

    def test_data_region(self):
        code = bytes([0xA9, 0x00, 0xEA, 0xEA, 0x60])
        d = make_dasm(code, 0x0800, data_regions=[(0x0802, 0x0803)])
        d.analyze()
        self.assertNotIn(0x0802, d.instrs)
        self.assertNotIn(0x0804, d.traced)

    def test_parse_range(self):
        self.assertEqual(dasm6502.parse_range("$CB99-$CBD3"), (0xCB99, 0xCBD3))
        self.assertEqual(dasm6502.parse_range("0xC000-0xC0FF"), (0xC000, 0xC0FF))
        self.assertEqual(dasm6502.parse_range("C000-C0FF"), (0xC000, 0xC0FF))

    def test_jump_table_detected(self):
        # RTS, then 3 JMPs to $0810/$0811/$0812 (RTS each)
        code = bytes([0x60, 0x4C, 0x10, 0x08, 0x4C, 0x11, 0x08, 0x4C, 0x12, 0x08]) + bytes(6) + bytes([0x60] * 3)
        d = make_dasm(code, 0x0800)
        d.analyze()
        self.assertTrue({0x0801, 0x0804, 0x0807, 0x0810, 0x0811, 0x0812} <= d.traced)
        self.assertTrue(any("jump table $0801" in n for n in d.auto_found))

    def test_pointer_table_detected(self):
        # $0800: JSR $0818 / $081A / $081C / $081E / RTS         (13 bytes)
        # $080D: .word $0818 $081A $081C $081E $0820 ($0820 reached only via table)
        code = bytes([0x20, 0x18, 0x08, 0x20, 0x1A, 0x08, 0x20, 0x1C, 0x08, 0x20, 0x1E, 0x08, 0x60,
                      0x18, 0x08, 0x1A, 0x08, 0x1C, 0x08, 0x1E, 0x08, 0x20, 0x08, 0x00,
                      0xEA, 0x60, 0xEA, 0x60, 0xEA, 0x60, 0xEA, 0x60, 0xE8, 0x60])
        d = make_dasm(code, 0x0800)
        text = d.disassemble(show_hex=False)
        self.assertIn(0x0820, d.traced)
        self.assertIn(".word   SUB_0820", text)
        self.assertTrue(any("pointer table $080D x5" in n for n in d.auto_found))

    def test_pointer_table_needs_routine_entries(self):
        # words hitting arbitrary instruction starts (not call/branch targets) are not a table
        code = bytes([0xEA] * 12 + [0x60, 0x01, 0x08, 0x03, 0x08, 0x05, 0x08, 0x07, 0x08])
        d = make_dasm(code, 0x0800)
        d.analyze()
        self.assertFalse(d.auto_found)

    def test_validated_fill(self):
        # traced: JMP $0810. $0803 (after a traced terminal, decodes to RTS) -> swept.
        # $0806: invalid byte; $0807 LDA/RTS is not vouched -> stays data.
        code = bytes([0x4C, 0x10, 0x08, 0xA9, 0x01, 0x60, 0x02, 0xA9, 0x05, 0x60]).ljust(0x10, b"\x02") \
            + bytes([0x60])
        d = make_dasm(code, 0x0800)
        d.analyze()
        self.assertIn(0x0803, d.swept)
        self.assertNotIn(0x0807, d.instrs)
        d_all = make_dasm(code, 0x0800, fill="all")
        d_all.analyze()
        self.assertIn(0x0807, d_all.instrs)

    def test_mid_instruction_cover_equate(self):
        # $0800: BIT $01A9 / RTS ; second entry at $0801 = LDA #$01 (classic skip)
        code = bytes([0x2C, 0xA9, 0x01, 0x60])
        text = make_dasm(code, 0x0800, entries=[0x0801]).disassemble(show_hex=False, annotate=True)
        self.assertIn("SUB_0801         = SUB_0800+1", text)

    def test_apply_symbols_renames_chunks(self):
        chunk = os.path.join(self.tmp, "chunk_00_0800.asm")
        with open(chunk, "w") as f:
            f.write("SUB_0806:\n  0806  60          RTS\n  0800  20 06 08    JSR     SUB_0806 ; calls SUB_0806\n")
        man = os.path.join(self.tmp, "manifest.json")
        with open(man, "w") as f:
            json.dump({"chunks": [{"id": 0, "filename": "chunk_00_0800.asm", "path": chunk,
                                   "start_addr": "0x0800", "end_addr": "0x0806"}]}, f)
        sym = self.write("names.inc", "PRINT = $0806\n")

        class A:
            apply_symbols = [sym]
            manifest = man
        annotator.do_apply_symbols(A)
        text = open(chunk).read()
        self.assertNotIn("SUB_0806", text)
        self.assertIn("PRINT:", text)
        self.assertIn("JSR     PRINT ; calls PRINT", text)


IDENT = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")


def undefined_symbols(text: str) -> tuple[set, list]:
    """(identifiers used but never defined, symbols defined twice) in a
    --no-hex listing: what ca65 would reject even when it isn't installed."""
    defined, dupes, used = set(), [], set()
    in_macro = False
    for line in text.splitlines():
        code = re.sub(r'"[^"]*"', '""', line).split(";", 1)[0].rstrip()
        code = re.sub(r"\$[0-9A-Fa-f]+", "", code)
        lab = re.match(r"^([A-Za-z_]\w*):\s+(\S.*)$", code)
        if lab:    # "LABEL:  LDA ..." on one line
            if lab.group(1) in defined:
                dupes.append(lab.group(1))
            defined.add(lab.group(1))
            code = "                 " + lab.group(2)
        if code.startswith(".macro"):
            in_macro = True
        if in_macro:
            in_macro = not code.startswith(".endmacro")
            continue
        m = re.match(r"^([A-Za-z_]\w*):$", code) or re.match(r"^([A-Za-z_]\w*)\s+=", code)
        if m:
            if m.group(1) in defined:
                dupes.append(m.group(1))
            defined.add(m.group(1))
            if "=" in code:
                used.update(IDENT.findall(code.split("=", 1)[1]))
            continue
        parts = code.split(None, 1)
        if len(parts) == 2 and not parts[0].startswith("."):
            used.update(n for n in IDENT.findall(re.sub(r"\b[az]:", "", parts[1]))
                        if n not in ("X", "Y", "A"))
        elif len(parts) == 2 and parts[0] in (".word", ".byte"):
            used.update(IDENT.findall(parts[1]))
    return used - defined, dupes


def write(tmp: str, name: str, data: bytes) -> str:
    p = os.path.join(tmp, name)
    with open(p, "wb") as f:
        f.write(data)
    return p


def c64_prg() -> bytes:
    """10 SYS2061 + code that prints, sets the border and hooks CINV."""
    basic = bytes([0x0B, 0x08, 0x0A, 0x00, 0x9E]) + b"2061" + bytes(3)
    code = bytes([0xA9, 0x05, 0x8D, 0x20, 0xD0,          # LDA #5 / STA EXTCOL
                  0xA9, 0x41, 0x20, 0xD2, 0xFF,          # LDA #'A' / JSR CHROUT
                  0x78, 0xA9, 0x1F, 0x8D, 0x14, 0x03,    # SEI / LDA #<$081F / STA CINV
                  0xA9, 0x08, 0x8D, 0x15, 0x03,          # LDA #>$081F / STA CINV+1
                  0x58, 0x60,                            # CLI / RTS
                  0xEE, 0x19, 0xD0, 0x4C, 0x31, 0xEA])   # $081F: INC VICIRQ / JMP $EA31
    return struct.pack("<H", 0x0801) + basic + code


class TestMachines(unittest.TestCase):
    """Reference tables and profiles for every machine."""

    def test_every_machine_loads(self):
        for mid in machines.MACHINES:
            ms = machines.MachineSymbols(mid)
            self.assertGreater(len(ms.rom) + len(ms.hw), 10, mid)
            if mid != "apple2":
                self.assertTrue(os.path.exists(os.path.join(ROOT, "reference", mid, "memory_map.md")), mid)
                self.assertTrue(os.path.exists(os.path.join(ROOT, "reference", mid, "rom_entry_points.md")), mid)

    def test_counts_match_reference_index(self):
        # counts from reference/MACHINES.md (zero page / ROM-file rows)
        for mid, zp in (("c64", 65), ("c128", 47), ("vic20", 49), ("bbc_b", 37), ("atari800xl", 103)):
            self.assertEqual(len(machines.MachineSymbols(mid).zp), zp, mid)
        self.assertEqual(len(machines.MachineSymbols("bbc_b").codes), 13)

    def test_names_are_unique_valid_symbols(self):
        reserved = machines._reserved_names()
        for mid in machines.MACHINES:
            if mid == "apple2":
                continue
            t = dasm6502.MachineTables(mid)
            seen = {}
            for tbl in (t.rom_labels, t.hw_labels, t.zp_labels):
                for a, n in tbl.items():
                    base = n.split("+")[0]
                    self.assertRegex(base, r"^[A-Za-z_][A-Za-z0-9_]*$", f"{mid} ${a:04X}")
                    self.assertNotIn(base.upper(), reserved, f"{mid} {n}")
                    if "+" not in n:
                        self.assertNotIn(n, seen, f"{mid}: {n} at ${a:04X} and ${seen.get(n, 0):04X}")
                        seen[n] = a

    def test_duplicate_names_get_address_suffix(self):
        t = dasm6502.MachineTables("c64")
        self.assertEqual(t.rom_labels[0xFFF0], "PLOT")
        self.assertEqual(t.rom_labels[0xE50A], "PLOT_E50A")

    def test_resolve_aliases(self):
        self.assertEqual(machines.resolve("C64"), "c64")
        self.assertEqual(machines.resolve("bbc"), "bbc_b")
        self.assertEqual(machines.resolve("bbcb"), "bbc_b")
        self.assertEqual(machines.resolve(None), "apple2")
        with self.assertRaises(ValueError):
            machines.resolve("zx81")

    def test_parser_shared_with_annotator(self):
        rows_a = list(annotator.PatternAnnotator._parse_table_rows(os.path.join(ROOT, "reference", "rom_entry_points.md")))
        self.assertEqual(rows_a, list(machines.parse_table_rows(os.path.join(ROOT, "reference", "rom_entry_points.md"))))
        rows = list(machines.parse_table_rows(os.path.join(ROOT, "reference", "c64", "rom_entry_points.md")))
        self.assertIn(("$FFD2", "CHROUT"), [(r[0], r[1]) for r in rows])


class TestMachineLoaders(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_cbm_prg_with_sys_stub(self):
        info = loader.identify_file(write(self.tmp, "hello.prg", c64_prg()))
        self.assertEqual(info["format"], "cbm_prg")
        self.assertEqual(info["machine_id"], "c64")
        self.assertEqual(info["segments"][0]["org"], 0x0801)
        self.assertEqual(info["entry"], 2061)

    def test_prg_detected_without_extension_and_vic20(self):
        prg = bytearray(c64_prg())
        prg[0:2] = struct.pack("<H", 0x1001)
        prg[2:4] = struct.pack("<H", 0x100B)
        info = loader.identify_file(write(self.tmp, "game", bytes(prg)))
        self.assertEqual((info["format"], info["machine_id"]), ("cbm_prg", "vic20"))

    def test_p00_container(self):
        p00 = b"C64File\x00" + b"HELLO".ljust(17, b"\x00") + b"\x00" + c64_prg()
        info = loader.identify_file(write(self.tmp, "hello.p00", p00))
        self.assertEqual(info["entry"], 2061)

    def test_atari_xex_runad_initad(self):
        seg1 = bytes([0xA9, 0x00, 0x60])
        seg2 = bytes([0xEA, 0x60])
        xex = (b"\xff\xff" + struct.pack("<HH", 0x2000, 0x2002) + seg1 +
               struct.pack("<HH", 0x02E2, 0x02E3) + struct.pack("<H", 0x2000) +
               b"\xff\xff" + struct.pack("<HH", 0x3000, 0x3001) + seg2 +
               struct.pack("<HH", 0x02E0, 0x02E1) + struct.pack("<H", 0x3000))
        info = loader.identify_file(write(self.tmp, "a.xex", xex))
        self.assertEqual(info["format"], "atari_xex")
        self.assertEqual(info["machine_id"], "atari800xl")
        self.assertEqual([s["org"] for s in info["segments"]], [0x2000, 0x3000])
        self.assertEqual(info["entry"], 0x3000)
        self.assertEqual(info["entries"], [0x2000])

    def test_atari_car(self):
        body = bytearray(8192)
        body[0x1FFA:0x1FFC] = struct.pack("<H", 0xA010)
        body[0x1FFE:0x2000] = struct.pack("<H", 0xA000)
        car = b"CART" + struct.pack(">II", 1, 0) + bytes(4) + bytes(body)
        info = loader.identify_file(write(self.tmp, "x.car", car))
        self.assertEqual(info["segments"][0]["org"], 0xA000)
        self.assertEqual(info["entry"], 0xA010)
        self.assertIn(0xA000, info["entries"])

    def ines(self, banks: int, mapper: int = 0) -> bytes:
        prg = bytearray()
        for b in range(banks):
            bank = bytearray([b]) * 16384
            bank[0x3FFC:0x3FFE] = struct.pack("<H", 0xC000)
            prg += bank
        return b"NES\x1a" + bytes([banks, 1, (mapper & 0xF) << 4, mapper & 0xF0]) + bytes(8) + bytes(prg)

    def test_ines_nrom(self):
        info = loader.identify_file(write(self.tmp, "a.nes", self.ines(1)))
        self.assertEqual(info["machine_id"], "nes")
        self.assertEqual(info["segments"][0]["org"], 0xC000)
        self.assertEqual(info["entry"], 0xC000)
        info = loader.identify_file(write(self.tmp, "b.nes", self.ines(2)))
        self.assertEqual((info["segments"][0]["org"], info["segments"][0]["length"]), (0x8000, 32768))

    def test_ines_banked_with_bank_option(self):
        p = write(self.tmp, "c.nes", self.ines(8, mapper=2))
        info = loader.identify_file(p)
        self.assertEqual([s["org"] for s in info["segments"]], [0xC000])
        self.assertEqual(info["segments"][0]["data"][0], 7)       # last bank is fixed
        info = loader.identify_file(p, bank=3)
        self.assertEqual([s["org"] for s in info["segments"]], [0x8000, 0xC000])
        self.assertEqual(info["segments"][0]["data"][0], 3)
        self.assertEqual(loader.identify_file(p, machine="famicom")["machine_id"], "famicom")

    def test_lynx_bll(self):
        body = bytes([0x64, 0x10, 0x60])
        bll = b"\x80\x08" + struct.pack(">HH", 0x0400, len(body) + 10) + b"BS93" + body
        info = loader.identify_file(write(self.tmp, "a.o", bll))
        self.assertEqual((info["format"], info["machine_id"], info["entry"]), ("lynx_bll", "lynx", 0x0400))
        self.assertEqual(info["cpu_hint"], "65sc02")

    def test_bbc_sideways_rom_and_inf(self):
        rom = bytearray([0xFF]) * 16384
        rom[0:9] = bytes([0x4C, 0x30, 0x80, 0x4C, 0x20, 0x80, 0xC2, 0x10, 0x01])
        rom[9:14] = b"DEMO\x00"
        rom[0x10:0x14] = b"\x00(C)"
        info = loader.identify_file(write(self.tmp, "demo.rom", bytes(rom)))
        self.assertEqual((info["format"], info["machine_id"]), ("bbc_rom", "bbc_b"))
        self.assertEqual(info["segments"][0]["org"], 0x8000)
        self.assertEqual(info["entry"], 0x8000)
        self.assertEqual(info["entries"], [0x8003])
        self.assertIn("DEMO", info["rom_name"])
        p = write(self.tmp, "PROG", bytes([0x60]))
        with open(p + ".inf", "w") as f:
            f.write("$.PROG FFFF1900 FFFF1900 00000001\n")
        info = loader.identify_file(p)
        self.assertEqual((info["format"], info["segments"][0]["org"], info["entry"]), ("bbc_inf", 0x1900, 0x1900))

    def test_raw_os_rom_signatures(self):
        kernal = bytearray(8192)
        kernal[0x1FD2:0x1FD5] = bytes([0x6C, 0x26, 0x03])        # $FFD2 JMP ($0326)
        kernal[0x1FFC:0x1FFE] = struct.pack("<H", 0xFCE2)
        info = loader.identify_file(write(self.tmp, "kernal.bin", bytes(kernal)))
        self.assertEqual((info["segments"][0]["org"], info["machine_id"]), (0xE000, "c64"))
        self.assertEqual(info["entry"], 0xFCE2)
        kernal[0x1FFC:0x1FFE] = struct.pack("<H", 0xFD22)
        self.assertEqual(loader.identify_file(write(self.tmp, "vic.bin", bytes(kernal)))["machine_id"], "vic20")
        mos = bytearray(16384)
        mos[0x3FEE:0x3FF1] = bytes([0x6C, 0x0E, 0x02])          # $FFEE JMP ($020E)
        mos[0x3FFC:0x3FFE] = struct.pack("<H", 0xD9CD)
        info = loader.identify_file(write(self.tmp, "mos.bin", bytes(mos)))
        self.assertEqual((info["segments"][0]["org"], info["machine_id"]), (0xC000, "bbc_b"))
        atari = bytearray(10240)
        for i in range(6):
            atari[0xE450 - 0xD800 + 3 * i] = 0x4C
        atari[0x27FC:0x27FE] = struct.pack("<H", 0xE477)
        info = loader.identify_file(write(self.tmp, "osb.rom", bytes(atari)))
        self.assertEqual((info["segments"][0]["org"], info["machine_id"]), (0xD800, "atari800"))
        basic = bytearray(8192)
        basic[4:12] = b"CBMBASIC"
        info = loader.identify_file(write(self.tmp, "basic.bin", bytes(basic)))
        self.assertEqual((info["segments"][0]["org"], info["machine_id"]), (0xA000, "c64"))

    def test_machine_raw_org_guess(self):
        p = write(self.tmp, "cart.bin", bytes(8192))
        self.assertEqual(loader.identify_file(p, machine="vic20")["segments"][0]["org"], 0xE000)

    def test_apple_files_stay_apple(self):
        p = write(self.tmp, "x.as", applesingle(bytes([0x60]), 0x06, 0x0800))
        info = loader.identify_file(p)
        self.assertIn(info["machine_id"], (None, "apple2"))
        self.assertEqual(info["segments"][0]["org"], 0x0800)

    def test_a2loader_shim(self):
        self.assertTrue(a2loader.identify_file.__code__.co_filename.endswith("loader.py"))
        self.assertTrue(hasattr(a2loader, "parse_applesingle") and hasattr(a2loader, "parse_ines"))


class TestMachineDisassembly(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def build(self, path, *extra):
        import argparse as ap
        parser = ap.ArgumentParser()
        dasm6502.add_common_args(parser)
        return dasm6502.build_disassembler(parser.parse_args([path, *extra]))

    def test_c64_symbols_and_vector_hook(self):
        dasm, info = self.build(write(self.tmp, "h.prg", c64_prg()))
        self.assertEqual(dasm.machine, "c64")
        text = dasm.disassemble(show_hex=False, annotate=True)
        self.assertIn("; Machine: c64", text)
        self.assertIn("CHROUT           = $FFD2", text)
        self.assertIn("EXTCOL           = $D020", text)
        self.assertIn("STA     CINV+1", text)
        self.assertIn("SUB_081F:", text)                 # hooked IRQ handler traced
        self.assertIn("handler installed in CINV", text)
        self.assertEqual(undefined_symbols(text), (set(), []))

    def test_machine_flag_overrides(self):
        code = bytes([0x20, 0xEE, 0xFF, 0x8D, 0x4E, 0xFE, 0x60])   # JSR OSWRCH / STA SYSVIA_IER
        p = write(self.tmp, "b.bin", code)
        dasm, _ = self.build(p, "--org", "0x1900", "--machine", "bbc")
        text = dasm.disassemble(show_hex=False)
        self.assertIn("JSR     OSWRCH", text)
        self.assertEqual(undefined_symbols(text)[0], set())
        dasm, _ = self.build(p, "--org", "0x1900")
        self.assertNotIn("OSWRCH", dasm.disassemble(show_hex=False))   # apple2 by default

    def test_apple_listing_has_no_machine_line(self):
        text = make_dasm(bytes([0x20, 0xED, 0xFD, 0x60]), 0x0800).disassemble(show_hex=False)
        self.assertNotIn("; Machine:", text)
        self.assertIn("; Apple II 6502 disassembly", text)

    def test_random_bytes_define_every_symbol(self):
        """For every machine (zero-page names on, as for ROMs), every symbol
        the listing uses is defined exactly once: what ca65 checks."""
        rng = random.Random(64)
        for mid in machines.MACHINES:
            for org in (0x0000, 0x8000, 0xC000):
                data = bytes(rng.randrange(256) for _ in range(0x1000))
                text = make_dasm(data, org, machine=mid, zp_names=True).disassemble(show_hex=False)
                self.assertEqual(undefined_symbols(text), (set(), []), f"{mid} @ ${org:04X}")

    def test_bbc_osbyte_annotation(self):
        code = bytes([0xA9, 0x83, 0x20, 0xF4, 0xFF, 0x60])        # LDA #&83 / JSR OSBYTE
        dasm = make_dasm(code, 0x1900, machine="bbc_b")
        asm = os.path.join(self.tmp, "l.asm")
        with open(asm, "w") as f:
            f.write(dasm.disassemble(annotate=True))
        a = annotator.PatternAnnotator(os.path.join(ROOT, "reference"), "bbc_b")
        self.assertEqual(a.annotate_file(asm), 1)
        with open(asm) as f:
            self.assertIn("OSBYTE &83: OSBYTE_OSHWM", f.read())

    def test_split_records_machine(self):
        dasm, _ = self.build(write(self.tmp, "h.prg", c64_prg()))
        asm = os.path.join(self.tmp, "l.asm")
        with open(asm, "w") as f:
            f.write(dasm.disassemble(annotate=True))
        x = xref.CrossReferenceBuilder(self.build(write(self.tmp, "h2.prg", c64_prg()))[0])
        x.analyze()
        sec = os.path.join(self.tmp, "s.json")
        with open(sec, "w") as f:
            f.write(x.format_sections())
        out = os.path.join(self.tmp, "chunks")
        import argparse as ap
        annotator.do_split(ap.Namespace(asm=asm, sections=sec, output_dir=out))
        with open(os.path.join(out, "manifest.json")) as f:
            self.assertEqual(json.load(f)["machine"], "c64")
        self.assertIn(0xD020, x.hw_accesses)


class TestCpuVariants(unittest.TestCase):
    def test_wdc_stp_wai(self):
        d = make_dasm(bytes([0xCB, 0xDB, 0xEA]), 0x0800, cpu="w65c02")
        text = d.disassemble(show_hex=False)
        self.assertIn("$CB", text)
        self.assertIn("WAI (WDC 65C02)", text)
        self.assertIn("STP (WDC 65C02)", text)
        self.assertNotIn(0x0802, d.traced)                  # STP stops the trace
        self.assertIn(0x0F, dasm6502.OPCODES_W65C02)        # BBR0 too

    def test_reserved_cmos_nops(self):
        # $02 nn = 2-byte NOP, $5C nn nn = 3-byte NOP, $03 = 1-byte NOP
        code = bytes([0x02, 0x99, 0x5C, 0x11, 0x22, 0x03, 0xA9, 0x01, 0x60])
        d = make_dasm(code, 0x0800, cpu="65c02")
        d.analyze()
        self.assertEqual(d.instrs[0x0800].size, 2)
        self.assertEqual(d.instrs[0x0802].size, 3)
        self.assertEqual(d.instrs[0x0805].size, 1)
        self.assertIn(0x0808, d.traced)                     # RTS reached
        text = d.disassemble(show_hex=False)
        self.assertIn(".byte   $5C,$11,$22", text)
        self.assertIn("reserved opcode: 3-byte NOP", text)
        d6 = make_dasm(code, 0x0800, cpu="6502")
        d6.analyze()
        self.assertNotIn(0x0808, d6.traced)                 # NMOS: undefined, trace stops
        # Rockwell: $x7 / $xF are bit instructions, not NOPs
        d = make_dasm(bytes([0x07, 0x10, 0x60]), 0x0800, cpu="r65c02")
        d.analyze()
        self.assertEqual(d.instrs[0x0800].mnemonic, "RMB0")

    def test_reserved_nops_not_used_by_fill(self):
        d = make_dasm(bytes([0x60, 0x03, 0x13, 0x23, 0x60]), 0x0800, cpu="65c02")
        d.analyze()
        self.assertNotIn(0x0801, d.instrs)

    def test_cpu_names(self):
        for cpu, name in (("65sc02", "65SC02"), ("65c12", "65SC02"), ("w65c02", "65C02"), ("r65c02", "65C02")):
            text = make_dasm(bytes([0x60]), 0x0800, cpu=cpu).disassemble(show_hex=False)
            self.assertIn(f'.setcpu "{name}"', text, cpu)
        with self.assertRaises(ValueError):
            make_dasm(bytes([0x60]), 0x0800, cpu="65816")

    def test_machine_default_cpu(self):
        tmp = tempfile.mkdtemp()
        try:
            body = bytes([0x80, 0x00, 0x60])          # BRA +0: only valid on CMOS
            p = write(tmp, "a.o", b"\x80\x08" + struct.pack(">HH", 0x0400, 13) + b"BS93" + body)
            import argparse as ap
            parser = ap.ArgumentParser()
            dasm6502.add_common_args(parser)
            dasm, _ = dasm6502.build_disassembler(parser.parse_args([p]))
            self.assertEqual(dasm.cpu, "65sc02")
            self.assertIn("BRA", dasm.disassemble(show_hex=False))
        finally:
            shutil.rmtree(tmp)

    def test_nmos_jmp_indirect_bug_note(self):
        code = bytes([0x6C, 0xFF, 0x10])
        self.assertIn("NMOS page-wrap bug", make_dasm(code, 0x0800).disassemble(annotate=True))
        self.assertNotIn("page-wrap", make_dasm(code, 0x0800, cpu="65c02").disassemble(annotate=True))


@unittest.skipUnless(HAVE_CA65, "cc65 not installed")
class TestRoundTrip(unittest.TestCase):
    """Disassembly with --no-hex must reassemble to the identical bytes."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def roundtrip(self, data: bytes, org: int, cpu: str, **kw):
        text = make_dasm(data, org, cpu=cpu, **kw).disassemble(show_hex=False, annotate=True)
        out = assemble(text, self.tmp, "rt")
        self.assertEqual(out, data, f"round-trip mismatch for cpu={cpu}")

    def test_fixtures(self):
        for name, org, cpu in (("allmodes", 0x2000, "6502"), ("c02modes", 0x0800, "65c02")):
            with open(os.path.join(ROOT, "tests", "fixtures", name + ".s")) as f:
                data = assemble(f.read(), self.tmp, name)
            self.roundtrip(data, org, cpu)

    def test_random_bytes_all_cpus(self):
        rng = random.Random(6502)
        for cpu in ("6502", "65c02", "r65c02", "w65c02", "65sc02", "65c12"):
            data = bytes(rng.randrange(256) for _ in range(4096))
            self.roundtrip(data, 0x4000, cpu)

    def test_random_bytes_every_machine(self):
        rng = random.Random(1982)
        for mid, prof in machines.MACHINES.items():
            data = bytes(rng.randrange(256) for _ in range(0x1000))
            for org in (0x0000, 0xC000):
                self.roundtrip(data, org, prof["default_cpu"], machine=mid, zp_names=True)

    def test_cmos_reserved_nops_reassemble(self):
        code = bytes([0x02, 0x99, 0x5C, 0x11, 0x22, 0x03, 0xCB, 0xDB, 0x60])
        for cpu in ("65c02", "65sc02", "w65c02"):
            self.roundtrip(code, 0x0800, cpu)

    def test_random_undocumented(self):
        rng = random.Random(1977)
        data = bytes(rng.randrange(256) for _ in range(4096))
        self.roundtrip(data, 0x0800, "6502", undocumented=True)

    def test_dispatch_tables_reassemble(self):
        code = bytes([0x05, 0x08, 0x06, 0xEA, 0xEA, 0xEA, 0x60, 0x60])
        tables = [dasm6502.parse_table_spec("0800:1:rts"), dasm6502.parse_table_spec("0802:1:rts:hi=08")]
        self.roundtrip(code, 0x0800, "6502", entry=None, tables=tables)

    def test_symbols_and_cover_equates_reassemble(self):
        tmp = self.tmp
        p = os.path.join(tmp, "u.inc")
        with open(p, "w") as f:
            f.write("PTR = $0004\nPRINT = $0806\nHOOK = $03F5\n")
        tbl = symbols.load_symbols([p])
        # image at $0000: LDA PTR (zero page, forward-referenced label) / JSR ...
        code = bytes([0xA5, 0x04, 0x60, 0xEA, 0x00, 0x00])
        self.roundtrip(code, 0x0000, "6502", symbols=tbl)
        code = bytes([0x2C, 0xA9, 0x01, 0x20, 0xF5, 0x03, 0x60])
        self.roundtrip(code, 0x0800, "6502", symbols=tbl, entries=[0x0801])

    def test_random_bytes_fill_modes(self):
        rng = random.Random(8)
        data = bytes(rng.randrange(256) for _ in range(2048))
        for mode in ("all", "none"):
            self.roundtrip(data, 0x6000, "65c02", fill=mode)

    def test_jmp_indirect_through_zero_page(self):
        # JMP ($0054) / JMP ($0054,X): absolute-only modes, no a: prefix allowed
        self.roundtrip(bytes([0x6C, 0x54, 0x00, 0x7C, 0x54, 0x00]), 0x1000, "65c02")

    def test_zero_page_and_top_of_memory(self):
        rng = random.Random(42)
        self.roundtrip(bytes(rng.randrange(256) for _ in range(0x200)), 0x0000, "65c02")
        # zero-page names on (as for ROM images), including "NAME+1" entries
        self.roundtrip(bytes(rng.randrange(256) for _ in range(0x1000)), 0x6000, "6502", zp_names=True)
        self.roundtrip(bytes(rng.randrange(256) for _ in range(0x800)), 0xF800, "6502")


if __name__ == "__main__":
    unittest.main()

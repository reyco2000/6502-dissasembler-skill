"""Tests for the Apple II 6502 disassembler tools.

Run: python3 -m unittest discover -s tests -v   (or python3 -m pytest tests/)
Round-trip tests need cc65 (ca65 + ld65) and are skipped without it.
"""

import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import a2loader  # noqa: E402
import annotator  # noqa: E402
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
        for cpu in ("6502", "65c02", "r65c02"):
            data = bytes(rng.randrange(256) for _ in range(4096))
            self.roundtrip(data, 0x4000, cpu)

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

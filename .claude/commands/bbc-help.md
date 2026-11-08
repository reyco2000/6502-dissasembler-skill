Look up quick reference information for Acorn BBC Micro (Model A, B, B+, Master 128) 6502 development. Read and use the files under `reference/` to answer questions about:

- **Machines**: `bbc_a` (Model A), `bbc_b` (Model B (default)), `bbc_bplus` (Model B+), `bbc_master` (Master 128 (65C12: use the default CPU 65c12)); `reference/MACHINES.md` lists every supported machine and the sources
- `reference/bbc_b/memory_map.md` / `rom_entry_points.md`: Model B, MOS 1.20 (the A/B+/Master folders have the same layout with their own notes)
- `reference/bbc_master/memory_map.md` / `rom_entry_points.md`: Master 128: MOS 3.20, ACCCON, extra workspace
- **Topics**: MOS calls (OSWRCH, OSBYTE, OSWORD, OSFILE…), OSBYTE/OSWORD reason codes, page-2 RAM vectors, SHEILA/FRED/JIM I/O, VIAs, CRTC/ULA, sideways ROM header and service calls, shadow RAM (B+/Master)
- **Opcodes**: the tables in `tools/dasm6502.py` (`OPCODES_6502`, `OPCODES_UNDOC`, `OPCODES_65C02_EXTRA`, `OPCODES_W65C02`, `CMOS_NOP_SIZE`)

When answering, always provide:
1. The hex address (or register / reason code)
2. The symbolic name
3. A brief description, including register inputs/outputs
4. Example usage in ca65 6502 assembly if relevant

$arguments: topic — what to look up (e.g. "OSBYTE &83", "WRCHV", "ROMSEL", "service call 4", "ACCCON")

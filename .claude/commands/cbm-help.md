Look up quick reference information for Commodore 8-bit (C64, C128, VIC-20) 6502 development. Read and use the files under `reference/` to answer questions about:

- **Machines**: `c64` (Commodore 64), `c128` (Commodore 128 (8502 side)), `vic20` (VIC-20); `reference/MACHINES.md` lists every supported machine and the sources
- `reference/c64/memory_map.md` / `rom_entry_points.md`: C64: zero page, $0200-$03FF vectors, VIC-II/SID/CIA, banking
- `reference/c128/memory_map.md` / `rom_entry_points.md`: C128: MMU, VDC, BASIC 7.0 and KERNAL jumbo table
- `reference/vic20/memory_map.md` / `rom_entry_points.md`: VIC-20: block map, VIC 6560/6561, VIAs, KERNAL
- **Topics**: KERNAL calls (CHROUT, GETIN, LOAD…), BASIC ROM routines, VIC-II/SID/CIA registers, the 6510 $00/$01 port and banking, C128 MMU/VDC, VIC-20 VIAs, zero page and page-2/3 vectors
- **Opcodes**: the tables in `tools/dasm6502.py` (`OPCODES_6502`, `OPCODES_UNDOC`, `OPCODES_65C02_EXTRA`, `OPCODES_W65C02`, `CMOS_NOP_SIZE`)

When answering, always provide:
1. The hex address (or register / reason code)
2. The symbolic name
3. A brief description, including register inputs/outputs
4. Example usage in ca65 6502 assembly if relevant

$arguments: topic — what to look up (e.g. "CHROUT", "$D020", "CINV", "MMU CR", "SID voice 1")

Look up quick reference information for NES / Famicom 6502 development. Read and use the files under `reference/` to answer questions about:

- **Machines**: `nes` (NES (default)), `famicom` (Famicom (same core; $4016/$4017 expansion and microphone differences)); `reference/MACHINES.md` lists every supported machine and the sources
- `reference/nes/memory_map.md` / `rom_entry_points.md`: CPU/PPU/APU maps, iNES header, mapper registers
- `reference/famicom/memory_map.md` / `rom_entry_points.md`: Famicom differences: expansion port, microphone, FDS
- **Topics**: PPU/APU registers and bit fields, OAM DMA, controller reading, iNES header fields, mapper registers (MMC1, MMC3, UxROM, CNROM), vblank/NMI conventions, Famicom differences
- **Opcodes**: the tables in `tools/dasm6502.py` (`OPCODES_6502`, `OPCODES_UNDOC`, `OPCODES_65C02_EXTRA`, `OPCODES_W65C02`, `CMOS_NOP_SIZE`)

When answering, always provide:
1. The hex address (or register / reason code)
2. The symbolic name
3. A brief description, including register inputs/outputs
4. Example usage in ca65 6502 assembly if relevant

$arguments: topic — what to look up (e.g. "PPUCTRL", "$4014", "MMC1", "iNES flags 6", "controller read")

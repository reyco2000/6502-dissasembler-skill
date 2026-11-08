Look up quick reference information for Atari 8-bit (400 / 800 / 600XL / 800XL / 1200XL) 6502 development. Read and use the files under `reference/` to answer questions about:

- **Machines**: `atari400` (Atari 400), `atari800` (Atari 800), `atari600xl` (Atari 600XL), `atari800xl` (Atari 800XL (default for .xex)), `atari1200xl` (Atari 1200XL); `reference/MACHINES.md` lists every supported machine and the sources
- `reference/atari800xl/memory_map.md` / `rom_entry_points.md`: 800XL (XL/XE OS); the other models' folders have the same layout
- `reference/atari800/memory_map.md` / `rom_entry_points.md`: 400/800 OS-A/OS-B
- **Topics**: OS vectors and the $E450 jump table (CIOV, SIOV, SETVBV…), IOCBs, ANTIC/GTIA/POKEY/PIA registers, display-list opcodes, shadow registers, zero page and page-2 vectors, PORTB banking per model
- **Opcodes**: the tables in `tools/dasm6502.py` (`OPCODES_6502`, `OPCODES_UNDOC`, `OPCODES_65C02_EXTRA`, `OPCODES_W65C02`, `CMOS_NOP_SIZE`)

When answering, always provide:
1. The hex address (or register / reason code)
2. The symbolic name
3. A brief description, including register inputs/outputs
4. Example usage in ca65 6502 assembly if relevant

$arguments: topic — what to look up (e.g. "CIOV", "SDLSTL", "VVBLKI", "$D40A", "PORTB 800XL")

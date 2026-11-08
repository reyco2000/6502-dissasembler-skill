Look up quick reference information for Atari Lynx 6502 development. Read and use the files under `reference/` to answer questions about:

- **Machines**: `lynx` (Atari Lynx (CPU 65SC02 by default)); `reference/MACHINES.md` lists every supported machine and the sources
- `reference/lynx/memory_map.md` / `rom_entry_points.md`: Suzy/Mikey registers, MAPCTL, boot ROM entry points, cart header
- **Topics**: Suzy and Mikey registers, sprite control blocks, the math unit, timers and interrupts, MAPCTL, the boot ROM and cart/BLL headers
- **Opcodes**: the tables in `tools/dasm6502.py` (`OPCODES_6502`, `OPCODES_UNDOC`, `OPCODES_65C02_EXTRA`, `OPCODES_W65C02`, `CMOS_NOP_SIZE`)

When answering, always provide:
1. The hex address (or register / reason code)
2. The symbolic name
3. A brief description, including register inputs/outputs
4. Example usage in ca65 6502 assembly if relevant

$arguments: topic — what to look up (e.g. "SPRGO", "MAPCTL", "timer 0", "INTRST", "BLL header")

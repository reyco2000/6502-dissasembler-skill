Look up quick reference information for Apple II 6502/65C02 development. Read and use the files in the `reference/` directory to answer questions about:

- **Memory map, soft switches, zero page, vectors**: `reference/apple2_memory_map.md`: $C000-$C0FF switches, language card, Disk II, page 3 hooks, ProDOS global page, machine ID bytes, screen layout
- **ROM and OS calls**: `reference/rom_entry_points.md`: Monitor, Applesoft, DOS 3.3 vectors, ProDOS MLI command codes, calling conventions, common idioms
- **Opcodes**: the tables in `tools/dasm6502.py` (`OPCODES_6502`, `OPCODES_65C02_EXTRA`, `OPCODES_ROCKWELL`, `OPCODES_UNDOC`)

When answering, always provide:
1. The hex address (or opcode / MLI command byte)
2. The symbolic name
3. A brief description of what it does, including register inputs/outputs
4. Example usage in ca65 6502 assembly if relevant

$arguments: topic — what to look up (e.g. "COUT", "KBDSTRB", "language card", "hi-res page 2", "MLI OPEN", "BIT #imm")

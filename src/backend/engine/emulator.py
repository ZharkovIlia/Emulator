from src.backend.model.commands import Commands
from src.backend.utils.exceptions import EmulatorBreakpointNotInROM, EmulatorOddBreakpoint, EmulatorWrongAddress, \
    UnknownCommand
from src.backend.utils.disasm_instruction import DisasmInstruction, DisasmState
from src.backend.utils.romfiller import ROMFiller

from src.backend.model.memory import Memory
from src.backend.model.registers import Register, StackPointer, ProgramCounter
from src.backend.model.programstatus import ProgramStatus
from src.backend.engine.cpu import CPU

from bitarray import bitarray


class Emulator:
    def __init__(self):
        self._memory = Memory()
        self._registers = list(Register() for _ in range(6))
        self._registers.append(StackPointer())
        self._registers.append(ProgramCounter())
        self._registers[CPU.ProgramCounter].set(size="word", signed=False, value=Memory.Part.ROM.start)

        self._program_status = ProgramStatus()
        self._cpu = CPU(memory=self._memory, registers=self._registers, program_status=self._program_status)

        self._breakpoints = set()
        self._instructions = {}

        self._start_instructions = Memory.Part.ROM.start
        self._end_instructions = self._start_instructions
        self._fill_ROM()
        self._disasm_from_to(self._start_instructions, self._end_instructions)

    def step(self):
        self._cpu.execute_next()

    def run(self):
        while True:
            self._cpu.execute_next()
            if self.current_pc in self._breakpoints:
                break

    def toggle_breakpoint(self, address: int):
        if address % 2 == 1:
            raise EmulatorOddBreakpoint()

        if address in self._breakpoints:
            self._breakpoints.remove(address)
        else:
            self._breakpoints.add(address)

    def disasm(self, address: int, num: int, type: str) -> list:
        if address % 2 == 1 or address < 0 or address >= Memory.SIZE:
            raise EmulatorWrongAddress(address)

        assert type in ("octal", "instructions")

        result = []
        if num <= 0:
            return result

        if type == "instructions":
            while address in self._instructions and self._instructions[address].state is DisasmState.PART_OF_PREVIOUS:
                address -= 2

        while len(result) < num and address < Memory.SIZE:
            breakpoint_set = address in self._breakpoints
            if type == "octal":
                dis_instr = DisasmInstruction()
                dis_instr.set_state(state=DisasmState.NOT_AN_INSTRUCTION,
                                    representation="{:06o}".format(
                                        int(self._memory.load(size="word", address=address).to01(), 2)
                                    ))
                result.append((address, dis_instr, breakpoint_set))

            elif address not in self._instructions:
                result.append((address, DisasmInstruction(), breakpoint_set))

            else:
                result.append((address, self._instructions[address], breakpoint_set))
                address += self._instructions[address].num_next * 2

            address += 2

        address = result[0][0]
        while len(result) < num and address > 0:
            address -= 2
            breakpoint_set = address in self._breakpoints
            if type == "octal":
                dis_instr = DisasmInstruction()
                dis_instr.set_state(state=DisasmState.NOT_AN_INSTRUCTION,
                                    representation="{:06o}".format(
                                        int(self._memory.load(size="word", address=address).to01(), 2)
                                    ))
                result.insert(0, (address, dis_instr, breakpoint_set))

            elif address not in self._instructions:
                result.insert(0, (address, DisasmInstruction(), breakpoint_set))

            else:
                address -= self._instructions[address].num_next * 2
                breakpoint_set = address in self._breakpoints
                result.insert(0, (address, self._instructions[address], breakpoint_set))

        return result

    @property
    def memory(self) -> Memory:
        return self._memory

    @property
    def registers(self) -> list:
        return self._registers

    @property
    def program_status(self) -> ProgramStatus:
        return self._program_status

    @property
    def current_pc(self) -> int:
        return self._registers[CPU.ProgramCounter].get(size="word", signed=False)

    def _fill_ROM(self):
        self._glyphs = ROMFiller.get_glyphs()
        self._glyphs_start = self._memory.Part.ROM.end - len(self._glyphs["data"])*16
        for i, v in enumerate(self._glyphs["data"]):
            self._memory.store(address=self._glyphs_start + i*16, size="word", value=v)

    def _disasm_from_to(self, from_: int, to: int):
        tmp_ps = ProgramStatus()
        stored = True
        cur_next_instruction, num_next_instructions = 0, 0
        tmp_addr: int = None
        tmp_repr: str = None
        data, sizes = [], []
        for addr in range(from_, to, 2):
            self._instructions[addr] = DisasmInstruction()
            if not stored:
                data.append(int(self._memory.load(size=sizes[cur_next_instruction], address=addr).to01(), 2))
                cur_next_instruction += 1
                if cur_next_instruction == num_next_instructions:
                    self._instructions[tmp_addr].set_state(state=DisasmState.DISASSEMBLED,
                                                           representation=tmp_repr.format(*data),
                                                           num_next=num_next_instructions)
                    stored = True
                self._instructions[addr].set_state(state=DisasmState.PART_OF_PREVIOUS,
                                                   num_next=num_next_instructions)
                continue

            try:
                com = Commands.get_command_by_code(code=self._memory.load(size="word", address=addr),
                                                   program_status=tmp_ps)
            except UnknownCommand as exc:
                self._instructions[addr].set_state(state=DisasmState.NOT_AN_INSTRUCTION)
                continue

            tmp_repr = com.string_representation + " "

            if com.has_src_operand and com.has_dest_operand:
                tmp_repr = tmp_repr + com.src_operand.string_representation + ", " + \
                           com.dest_operand.string_representation

            elif com.has_dest_operand and com.has_offset:
                tmp_repr = tmp_repr + com.dest_operand.string_representation + ", " + "{:o}".format(com.offset)

            elif com.has_src_operand:
                tmp_repr = tmp_repr + com.src_operand.string_representation

            elif com.has_dest_operand:
                tmp_repr = tmp_repr + com.dest_operand.string_representation

            elif com.has_offset:
                tmp_repr = tmp_repr + "{:o}".format(com.offset)

            elif com.has_number:
                tmp_repr = tmp_repr + "{:o}".format(com.number)

            if com.num_next_instructions != 0:
                cur_next_instruction, num_next_instructions = 0, com.num_next_instructions
                stored = False
                data, sizes = [], []
                if com.has_src_operand and com.src_operand.require_next_instruction:
                    sizes.append("byte" if com.src_operand.reg == 7 and com.src_operand.mode == 2 and com.on_byte
                                 else "word")
                if com.has_dest_operand and com.dest_operand.require_next_instruction:
                    sizes.append("byte" if com.dest_operand.reg == 7 and com.dest_operand.mode == 2 and com.on_byte
                                 else "word")
                tmp_addr = addr
            else:
                self._instructions[addr].set_state(state=DisasmState.DISASSEMBLED, representation=tmp_repr,
                                                   num_next=0)

        if not stored:
            for addr in range(tmp_addr, to, 2):
                self._instructions[addr].set_state(state=DisasmState.NOT_AN_INSTRUCTION)

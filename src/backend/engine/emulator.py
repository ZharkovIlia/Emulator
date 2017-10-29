from src.backend.model.commands import Commands
from src.backend.utils.exceptions import EmulatorBreakpointNotInROM, EmulatorOddBreakpoint, EmulatorWrongAddress
from src.backend.utils.disasm_instruction import DisasmInstruction, DisasmState

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
        self._registers[CPU.ProgramCounter].set_word(Memory.Part.ROM.start)

        self._program_status = ProgramStatus()
        self._cpu = CPU(memory=self._memory, registers=self._registers, program_status=self._program_status)

        self._breakpoints = set()
        self._instructions = {address: DisasmInstruction() for address in range(Memory.SIZE // 2)}

        self._fill_ROM()
        self._disasm_ROM()

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
        if Memory.get_type_by_address(address) != Memory.Part.ROM:
            raise EmulatorBreakpointNotInROM()

        if address in self._breakpoints:
            self._breakpoints.remove(address)
        else:
            self._breakpoints.add(address)

    def code(self, address: int) -> str:
        if address % 2 == 1 or address < 0 or address >= Memory.SIZE:
            raise EmulatorWrongAddress(address)
        return "0{:o}".format(int(self._memory.load(size="word", address=address).to01(), 2))

    def disasm(self, address: int) -> (str, bool):
        if address % 2 == 1 or address < 0 or address >= Memory.SIZE:
            raise EmulatorWrongAddress(address)

        return ("Not an instruction", False)

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
        pass

    def _disasm_ROM(self):
        pass


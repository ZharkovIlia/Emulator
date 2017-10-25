from src.backend.extra.exceptions import EmulatorBreakpointNotInROM, EmulatorOddBreakpoint
from src.backend.model.memory import Memory
from src.backend.model.registers import Register, StackPointer, ProgramCounter
from src.backend.model.programstatus import ProgramStatus

from bitarray import bitarray


class Emulator:
    def __init__(self):
        self._memory = Memory()
        self._registers = list(Register() for _ in range(6))
        self._registers.append(StackPointer())
        self._registers.append(ProgramCounter())

        self._program_status = ProgramStatus()
        self._breakpoints = bitarray(self._memory.SIZE // 2, endian='big')
        self._breakpoints.setall(False)

    def step(self):
        pass

    def run(self):
        pass

    def toggle_breakpoint(self, address: int):
        if address % 2 == 1:
            raise EmulatorOddBreakpoint()

        if Memory.get_type_by_address(address) != Memory.Part.ROM:
            raise EmulatorBreakpointNotInROM()
        self._breakpoints[address // 2] = not self._breakpoints[address // 2]

    @property
    def memory(self):
        return self._memory

    @property
    def registers(self):
        return self._registers

    @property
    def program_status(self):
        return self._program_status


if __name__ == "__main__":
    e = Emulator()
    for elem in e.registers:
        elem.set(size="word", signed=False, value=128)
        print(elem.get(size="byte", signed=True))

    a = bitarray("1001", endian='big')
    a[2] = not a[2]
    print(a)

from src.backend.model.memory import Memory
from src.backend.model.programstatus import ProgramStatus


class CPU:
    def __init__(self, memory: Memory, registers: list, program_status: ProgramStatus):
        self._memory = memory
        self._registers = registers
        self._program_status = program_status

    def execute_next(self):
        pass
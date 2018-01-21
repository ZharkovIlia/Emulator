from bitarray import bitarray

from src.backend.model.memory import Memory
from src.backend.model.programstatus import ProgramStatus
from src.backend.model.commands import Commands, Operation


class CPU:
    StackPointer = 6
    ProgramCounter = 7

    def __init__(self, memory: Memory, registers: list, program_status: ProgramStatus, commands: dict = None):
        self._memory = memory
        self._registers = registers
        self._program_status = program_status
        self._commands: dict = commands

    def execute_next(self):
        if self._commands is None:
            instr = self.fetch_next_instruction(size="word")
            command = Commands.get_command_by_code(code=instr, program_status=self._program_status)
        else:
            command = self._commands[self._registers[CPU.ProgramCounter].get(size="word", signed=False)]
            self.fetch_next_instruction()

        for op in command:
            optype = op["operation"]
            if optype is Operation.DECODE:
                continue

            elif optype is Operation.FETCH_NEXT_INSTRUCTION:
                next_instr = self.fetch_next_instruction(size=op["size"])
                op["callback"](next_instr)

            elif optype is Operation.FETCH_REGISTER:
                reg = self._registers[op["register"]]
                op["callback"](reg.byte() if op["size"] == "byte" else reg.word())

            elif optype is Operation.FETCH_ADDRESS:
                op["callback"](self._memory.load(address=op["address"](), size=op["size"]))

            elif optype is Operation.EXECUTE or optype is Operation.ALU:
                op["callback"]()

            elif optype is Operation.INCREMENT_REGISTER:
                self._registers[op["register"]].inc(value=op["value"])

            elif optype is Operation.DECREMENT_REGISTER:
                self._registers[op["register"]].dec(value=op["value"])

            elif optype is Operation.STORE_REGISTER:
                reg = self._registers[op["register"]]
                reg.set_byte(value=op["value"]()) if op["size"] == "byte" else reg.set_word(value=op["value"]())

            elif optype is Operation.STORE_ADDRESS:
                self._memory.store(address=op["address"](), size=op["size"], value=op["value"]())

            elif optype is Operation.BRANCH_IF:
                if op["if"]():
                    self._registers[7].inc(value=op["offset"])

            elif optype is Operation.DONE:
                break

    def fetch_next_instruction(self, size: str) -> bitarray:
        instr = self._memory.load(address=self._registers[CPU.ProgramCounter].get(size="word", signed=False),
                                  size=size)
        self._registers[CPU.ProgramCounter].inc(value=2)
        return instr

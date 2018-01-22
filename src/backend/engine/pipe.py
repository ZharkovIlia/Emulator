import enum
from collections import deque

from bitarray import bitarray

from src.backend.engine.cash import CashMemory
from src.backend.engine.pool_registers import PoolRegisters
from src.backend.model.commands import AbstractCommand, Operation, JumpCommand, BranchCommand, Commands
from src.backend.model.programstatus import ProgramStatus


class PipeComponentState(enum.Enum):
    WAIT_NEXT_COMMAND = enum.auto()
    IN_PROGRESS = enum.auto()
    WAIT_DATA = enum.auto()
    WAIT_INSTRUCTION = enum.auto()
    WAIT_PREV_COMPONENT = enum.auto()
    FINISHED = enum.auto()


class Execution:
    def __init__(self, cycles: int, callback=None):
        self._cycles_left = cycles
        self._done = self._cycles_left == 0
        self._callback = callback

    @property
    def done(self):
        return self._done

    def callback(self):
        if self._callback is not None:
            self._callback()

    def cycle(self) -> None:
        if self._done:
            return

        self._cycles_left -= 1
        self._done = self._cycles_left == 0


class PipeComponent:
    def __init__(self):
        self._worked = False
        self._state: PipeComponentState = PipeComponentState.WAIT_NEXT_COMMAND
        self._address = 0
        self._rw: str = None
        self._commandsQueue = deque()
        self._opnum = 0

    @property
    def address(self):
        return self._address

    @property
    def rw(self):
        return self._rw

    @property
    def worked(self):
        return self._worked

    @property
    def state(self):
        return self._state

    def new_cycle(self):
        self._worked = False

    def add_command(self, command: AbstractCommand):
        raise NotImplementedError()

    def cycle(self) -> bool:
        raise NotImplementedError()

    def continue_(self):
        if self._state == PipeComponentState.WAIT_PREV_COMPONENT:
            self._state = PipeComponentState.IN_PROGRESS

        elif self._state == PipeComponentState.FINISHED:
            self._commandsQueue.popleft()
            if len(self._commandsQueue) == 0:
                self._state = PipeComponentState.WAIT_NEXT_COMMAND
                self._opnum = 0
            else:
                self._state = PipeComponentState.WAIT_PREV_COMPONENT
                self._opnum = 0


class InstructionFetcher(PipeComponent):
    PC = 7

    def __init__(self, imem: CashMemory, registers: PoolRegisters):
        super(InstructionFetcher, self).__init__()
        self._imem = imem
        self._registers = registers
        self._decoded = False
        self._next_instruction: bitarray = None
        self._decoder = None

    def set_decoder(self, decoder):
        self._decoder = decoder

    def command_decoded(self):
        self._decoded = True
        if self._state == PipeComponentState.IN_PROGRESS and self._next_instruction is not None:
            self._worked = True

    def add_command(self, command: AbstractCommand):
        com = [{"operation": Operation.FETCH_NEXT_INSTRUCTION,
                "size": "word",
                "callback": lambda instr: None}]

        for op in command:
            if op["operation"] == Operation.FETCH_NEXT_INSTRUCTION:
                com.append(op)

        self._commandsQueue.append(com)
        if self._state == PipeComponentState.WAIT_NEXT_COMMAND:
            assert len(self._commandsQueue) == 1
            self._state = PipeComponentState.IN_PROGRESS
            self._opnum = 0

    def cycle(self) -> bool:
        if self._worked or self._state in (PipeComponentState.FINISHED, PipeComponentState.WAIT_NEXT_COMMAND):
            return False

        self._worked = True
        if self._state == PipeComponentState.IN_PROGRESS:
            if self._next_instruction is not None:
                if self._decoded:
                    self._commandsQueue[0][self._opnum]["callback"](self._next_instruction)
                    self._opnum += 1
                    self._next_instruction = None

                    success = self._registers.inc_fetch(regnum=self.PC, value=2)
                    assert success

            else:
                success, self._address = self._registers.get(regnum=self.PC, size="word", signed=False)
                assert success

                success, instr = self._imem.load(address=self._address,
                                                 size=self._commandsQueue[0][self._opnum]["size"])

                if success and self._opnum != 0:
                    self._next_instruction = instr

                elif success and self._opnum == 0:
                    self._state = PipeComponentState.FINISHED
                    self._opnum += 1
                    success = self._registers.inc_fetch(regnum=self.PC, value=2)
                    assert success

                else:
                    self._state = PipeComponentState.WAIT_INSTRUCTION
                    self._rw = 'r'

        elif self._state == PipeComponentState.WAIT_INSTRUCTION:
            success, instr = self._imem.load(address=self._address,
                                             size=self._commandsQueue[0][self._opnum]["size"])

            if success and self._opnum != 0:
                self._next_instruction = instr
                self._state = PipeComponentState.IN_PROGRESS

            elif success and self._opnum == 0:
                self._state = PipeComponentState.FINISHED
                self._opnum += 1

                success = self._registers.inc_fetch(regnum=self.PC, value=2)
                assert success

        if self._opnum == len(self._commandsQueue[0]) and self._state != PipeComponentState.FINISHED:
            self._commandsQueue.popleft()
            self._state = PipeComponentState.WAIT_NEXT_COMMAND
            self._decoded = False
            self._decoder.instruction_fetched()

        return True

    def continue_(self):
        assert self._state == PipeComponentState.FINISHED
        if self._opnum == len(self._commandsQueue[0]):
            self._commandsQueue.popleft()
            self._state = PipeComponentState.WAIT_NEXT_COMMAND

        else:
            self._state = PipeComponentState.IN_PROGRESS


class Decoder(PipeComponent):
    def __init__(self):
        super(Decoder, self).__init__()
        self._fetcher: InstructionFetcher = None
        self._wait_for_fetching = False

    def set_fetcher(self, fetcher: InstructionFetcher):
        self._fetcher = fetcher

    def instruction_fetched(self):
        assert self._wait_for_fetching
        self._state = PipeComponentState.FINISHED
        self._wait_for_fetching = False
        self._worked = True

    def add_command(self, command: AbstractCommand):
        com = dict(ops=[])
        if command.num_next_instructions != 0:
            com["next"] = True
        else:
            com["next"] = False

        for op in command:
            if op["operation"] == Operation.DECODE:
                com["ops"].append(op)

        assert len(com["ops"]) == 1
        self._commandsQueue.append(com)
        if self._state == PipeComponentState.WAIT_NEXT_COMMAND:
            assert len(self._commandsQueue) == 1
            self._state = PipeComponentState.WAIT_PREV_COMPONENT
            self._opnum = 0

    def cycle(self) -> bool:
        if self._state in (PipeComponentState.WAIT_PREV_COMPONENT, PipeComponentState.FINISHED,
                           PipeComponentState.WAIT_NEXT_COMMAND) \
                or self._wait_for_fetching or self._worked:
            return False

        self._worked = True
        assert self._state == PipeComponentState.IN_PROGRESS
        if self._commandsQueue[0]["next"]:
            self._fetcher.command_decoded()
            self._wait_for_fetching = True

        else:
            self._state = PipeComponentState.FINISHED

        return True


class OperandsFetcher(PipeComponent):
    PC = 7

    def __init__(self, dmem: CashMemory, registers: PoolRegisters):
        super(OperandsFetcher, self).__init__()
        self._registers = registers
        self._dmem = dmem
        self._blocking_reg = False
        self._blocking_mem = False
        self._num_block = 0
        self._execution: Execution = None

    def add_command(self, command: AbstractCommand):
        com = dict(ops=[], blreg=[], blmem=[])

        for op in command:
            if op["operation"] in (Operation.FETCH_REGISTER, Operation.FETCH_ADDRESS, Operation.INCREMENT_REGISTER,
                                   Operation.DECREMENT_REGISTER, Operation.EXECUTE):
                com["ops"].append(op)

            elif op["operation"] == Operation.STORE_REGISTER:
                com["blreg"].append(op["register"])
            elif op["operation"] == Operation.BRANCH_IF:
                com["blreg"].append(self.PC)
            elif op["operation"] == Operation.STORE_ADDRESS:
                com["blmem"].append(op["address"])

        self._commandsQueue.append(com)
        if self._state == PipeComponentState.WAIT_NEXT_COMMAND:
            assert len(self._commandsQueue) == 1
            self._state = PipeComponentState.WAIT_PREV_COMPONENT
            self._opnum = 0

    def cycle(self) -> bool:
        if self._worked or self._state in (PipeComponentState.WAIT_PREV_COMPONENT, PipeComponentState.FINISHED,
                                           PipeComponentState.WAIT_NEXT_COMMAND):
            return False

        if len(self._commandsQueue[0]["ops"]) == 0 and len(self._commandsQueue[0]["blreg"]) == 0 \
                and len(self._commandsQueue[0]["blmem"]) == 0:
            self._state = PipeComponentState.FINISHED
            return False

        self._worked = True

        if self._blocking_reg:
            self._block_reg()
            return True

        if self._blocking_mem:
            self._block_mem()
            return True

        if len(self._commandsQueue[0]["ops"]) == 0:
            self._num_block = 0
            self._block_reg()
            return True

        self._execute_null_cycle_operations()
        if self._opnum == len(self._commandsQueue[0]["ops"]):
            self._num_block = 0
            self._block_reg()
            return True

        op = self._commandsQueue[0]["ops"][self._opnum]
        optype = op["operation"]
        if self._state == PipeComponentState.IN_PROGRESS:
            if self._execution is not None:
                self._execution.cycle()
                if self._execution.done:
                    self._execution.callback()
                    self._opnum += 1
                    self._execution = None

            elif optype == Operation.FETCH_REGISTER:
                reg = op["register"]
                success, bitarr = self._registers.byte(regnum=reg) if op["size"] == "byte" \
                    else self._registers.word(regnum=reg)
                if success:
                    op["callback"](bitarr)
                    self._opnum += 1

            elif optype == Operation.FETCH_ADDRESS:
                self._address = op["address"]()
                success, data = self._dmem.load(address=self._address, size=op["size"])
                if success:
                    if self._address % 2 == 1:
                        self._execution = Execution(2, lambda: op["callback"](data))
                    else:
                        op["callback"](data)
                        self._opnum += 1
                else:
                    self._state = PipeComponentState.WAIT_DATA
                    self._rw = 'r'

            elif optype == Operation.INCREMENT_REGISTER:
                reg = op["register"]
                assert reg != 7
                success = self._registers.inc_fetch(regnum=reg, value=op["value"])
                if success:
                    self._opnum += 1

            elif optype == Operation.DECREMENT_REGISTER:
                reg = op["register"]
                assert reg != 7
                success = self._registers.dec_fetch(regnum=reg, value=op["value"])
                if success:
                    self._opnum += 1

            elif optype == Operation.EXECUTE:
                cycles = op["cycles"]
                if cycles == 1:
                    op["callback"]()
                    self._opnum += 1

                if cycles > 1:
                    self._execution = Execution(cycles, lambda: op["callback"]())
                    self._execution.cycle()

        elif self._state == PipeComponentState.WAIT_DATA:
            assert optype == Operation.FETCH_ADDRESS
            success, data = self._dmem.load(address=self._address, size=op["size"])
            if success:
                self._state = PipeComponentState.IN_PROGRESS
                if self._address % 2 == 1:
                    self._execution = Execution(2, lambda: op["callback"](data))
                else:
                    op["callback"](data)
                    self._opnum += 1

        if self._opnum == len(self._commandsQueue[0]["ops"]):
            self._num_block = 0
            self._block_reg()

        return True

    def _execute_null_cycle_operations(self):
        while self._opnum < len(self._commandsQueue[0]["ops"]):
            op = self._commandsQueue[0]["ops"][self._opnum]
            if op["operation"] == Operation.EXECUTE and op["cycles"] == 0:
                op["callback"]()
                self._opnum += 1
            else:
                break

    def _block_reg(self):
        while self._num_block < len(self._commandsQueue[0]["blreg"]):
            success = self._registers.block(self._commandsQueue[0]["blreg"][self._num_block], True)
            if not success:
                break
            else:
                self._num_block += 1

        if self._num_block < len(self._commandsQueue[0]["blreg"]):
            self._blocking_reg = True
        else:
            self._blocking_reg = False
            self._num_block = 0
            self._block_mem()

    def _block_mem(self):
        while self._num_block < len(self._commandsQueue[0]["blmem"]):
            if self._state == PipeComponentState.IN_PROGRESS:
                address = self._commandsQueue[0]["blmem"][self._num_block]()
                success = self._dmem.block(address, True)
                if not success:
                    break
                else:
                    self._num_block += 1

        if self._num_block < len(self._commandsQueue[0]["blmem"]):
            self._blocking_mem = True
        else:
            self._blocking_mem = False
            self._state = PipeComponentState.FINISHED


class ALU(PipeComponent):
    def __init__(self):
        super(ALU, self).__init__()
        self._execution: Execution = None

    def add_command(self, command: AbstractCommand):
        com = []
        for op in command:
            if op["operation"] == Operation.ALU:
                com.append(op)

        self._commandsQueue.append(com)
        if self._state == PipeComponentState.WAIT_NEXT_COMMAND:
            assert len(self._commandsQueue) == 1
            self._state = PipeComponentState.WAIT_PREV_COMPONENT
            self._opnum = 0

    def cycle(self) -> bool:
        if self._worked or self._state in (PipeComponentState.WAIT_PREV_COMPONENT, PipeComponentState.FINISHED,
                                           PipeComponentState.WAIT_NEXT_COMMAND):
            return False

        if len(self._commandsQueue[0]) == 0:
            self._state = PipeComponentState.FINISHED
            return False

        self._worked = True
        assert self._state == PipeComponentState.IN_PROGRESS

        op = self._commandsQueue[0][self._opnum]
        if self._execution is not None:
            self._execution.cycle()
            if self._execution.done:
                op["callback"]()
                self._opnum += 1
                self._execution = None

        else:
            cycles = op["cycles"]
            assert cycles > 0
            if cycles == 1:
                op["callback"]()
                self._opnum += 1

            elif cycles > 1:
                self._execution = Execution(cycles)
                self._execution.cycle()

        if self._opnum == len(self._commandsQueue[0]):
            self._state = PipeComponentState.FINISHED

        return True


class DataWriter(PipeComponent):
    PC = 7

    def __init__(self, dmem: CashMemory, registers: PoolRegisters):
        super(DataWriter, self).__init__()
        self._registers = registers
        self._dmem = dmem
        self._execution: Execution = None

    def add_command(self, command: AbstractCommand):
        com = []

        for op in command:
            if op["operation"] in (Operation.STORE_REGISTER, Operation.STORE_ADDRESS, Operation.BRANCH_IF):
                com.append(op)

        self._commandsQueue.append(com)
        if self._state == PipeComponentState.WAIT_NEXT_COMMAND:
            assert len(self._commandsQueue) == 1
            self._state = PipeComponentState.WAIT_PREV_COMPONENT
            self._opnum = 0

    def cycle(self) -> bool:
        if self._worked or self._state in (PipeComponentState.WAIT_PREV_COMPONENT, PipeComponentState.FINISHED,
                                           PipeComponentState.WAIT_NEXT_COMMAND):
            return False

        if len(self._commandsQueue[0]) == 0:
            self._state = PipeComponentState.FINISHED
            return False

        self._worked = True

        op = self._commandsQueue[0][self._opnum]
        optype = op["operation"]
        if self._state == PipeComponentState.IN_PROGRESS:
            if self._execution is not None:
                self._execution.cycle()
                if self._execution.done:
                    self._execution.callback()
                    self._opnum += 1
                    self._execution = None

            elif optype == Operation.STORE_REGISTER:
                reg = op["register"]
                value = op["value"]()
                success = self._registers.set_byte(regnum=reg, value=value) if op["size"] == "byte" \
                    else self._registers.set_word(regnum=reg, value=value)
                assert success
                self._opnum += 1
                self._unblock_reg_if_stored(reg)

            elif optype == Operation.STORE_ADDRESS:
                self._address = op["address"]()
                success = self._dmem.store(address=self._address, size=op["size"], value=op["value"]())
                if success:
                    if self._address % 2 == 1:
                        self._execution = Execution(2, lambda: None)
                    else:
                        self._opnum += 1
                else:
                    self._state = PipeComponentState.WAIT_DATA
                    self._rw = 'w'

            elif optype == Operation.BRANCH_IF:
                if op["if"]():
                    success = self._registers.inc_store(regnum=self.PC, value=op["offset"])
                    assert success

                self._opnum += 1
                self._unblock_reg_if_stored(self.PC)

        elif self._state == PipeComponentState.WAIT_DATA:
            assert optype == Operation.STORE_ADDRESS
            success = self._dmem.store(address=self._address, size=op["size"], value=op["value"]())
            if success:
                self._state = PipeComponentState.IN_PROGRESS
                if self._address % 2 == 1:
                    self._execution = Execution(2, lambda: None)
                else:
                    self._opnum += 1

        if self._opnum == len(self._commandsQueue[0]):
            self._unblock_mem()

        return True

    def _unblock_reg_if_stored(self, regnum: int):
        stored = True
        for opnum in range(self._opnum, len(self._commandsQueue[0])):
            op = self._commandsQueue[0][opnum]
            stored = stored and (op["operation"] == Operation.STORE_REGISTER and op["register"] != regnum or
                                 op["operation"] == Operation.BRANCH_IF and regnum != 7)

        if stored:
            success = self._registers.block(regnum, False)
            assert success

    def _unblock_mem(self):
        for op in self._commandsQueue[0]:
            if op["operation"] != Operation.STORE_ADDRESS:
                continue

            success = self._dmem.block(op["address"](), False)
            assert success

        self._state = PipeComponentState.FINISHED


class Pipe:
    PC = 7

    def __init__(self, dmem: CashMemory, imem: CashMemory, pool_registers: PoolRegisters,
                 ps: ProgramStatus, commands: dict=None, enabled=True):
        instr_fetcher = InstructionFetcher(imem, pool_registers)
        decoder = Decoder()
        instr_fetcher.set_decoder(decoder)
        decoder.set_fetcher(instr_fetcher)

        self._components = [instr_fetcher, decoder]
        self._components.append(OperandsFetcher(dmem, pool_registers))
        self._components.append(ALU())
        self._components.append(DataWriter(dmem, pool_registers))
        self._program_status = ps
        self._commands: dict = commands
        self._pc = pool_registers.registers[self.PC]
        self._imem = imem
        self._dmem = dmem

        self.enabled = enabled
        self._branch = False
        self._last_instruction_address = self._pc.get(size="word", signed=False)
        self.clear_statistics()
        self._add_command()

    @property
    def cycles(self):
        return self._cycles

    @property
    def instructions(self):
        return self._instructions

    @property
    def last_instruction_address(self):
        return self._last_instruction_address

    def clear_statistics(self):
        self._instructions = 0
        self._cycles = 0

    def cycle(self) -> bool:
        self._cycles += 1
        new_command = False
        if self.empty() or self.enabled and self._components[0].state == PipeComponentState.WAIT_NEXT_COMMAND \
                and not self._branch:
            new_command = True
            self._add_command()

        new_command = self._progress(fetch_new_instruction=True) or new_command

        return new_command

    def barrier(self) -> int:
        cycles = 0
        while not self.empty():
            cycles += 1
            self._progress(fetch_new_instruction=False)

        self._cycles += cycles
        self._branch = False
        return cycles

    def empty(self) -> bool:
        empty = True
        for component in self._components:
            empty = empty and component.state == PipeComponentState.WAIT_NEXT_COMMAND

        return empty

    def _progress(self, fetch_new_instruction: bool) -> bool:
        new_command = False
        for component in self._components:
            component.new_cycle()

        imem_ready = self._imem.cycle()
        dmem_ready = self._dmem.cycle()
        worked = False

        for component in self._components:
            if component.state == PipeComponentState.WAIT_DATA and dmem_ready \
                    and component.address == self._dmem.address and component.rw == self._dmem.rw:
                worked = component.cycle() or worked

            if component.state == PipeComponentState.WAIT_INSTRUCTION and imem_ready \
                    and component.address == self._imem.address and component.rw == self._imem.rw:
                worked = component.cycle() or worked

        for pos in range(len(self._components) - 1, -1, -1):
            worked = self._advance(dmem_ready, imem_ready, pos) or worked

        if fetch_new_instruction and (self.empty() or self.enabled and not self._branch and
                                      self._components[0].state == PipeComponentState.WAIT_NEXT_COMMAND):
            new_command = True
            self._branch = False
            self._add_command()

        if self.enabled or not worked:
            self._advance(dmem_ready, imem_ready, 0)

        return new_command

    def _advance(self, dmem_ready: bool, imem_ready: bool, pos: int) -> bool:
        worked = False
        for i in range(pos, len(self._components)):
            component = self._components[i]
            try_cycle = not (component.state == PipeComponentState.WAIT_DATA and not dmem_ready) and \
                not (component.state == PipeComponentState.WAIT_INSTRUCTION and not imem_ready)
            if i != pos:
                try_cycle = try_cycle and not self._components[i - 1].worked

            if try_cycle:
                worked = component.cycle() or worked

            if i == len(self._components) - 1 and self._components[i].state == PipeComponentState.FINISHED:
                self._components[i].continue_()

            elif self._components[i].state == PipeComponentState.FINISHED and \
                    self._components[i + 1].state == PipeComponentState.WAIT_PREV_COMPONENT:
                self._components[i].continue_()
                self._components[i + 1].continue_()

        return worked

    def _add_command(self):
        self._instructions += 1
        self._last_instruction_address = self._pc.get(size="word", signed=False)
        if self._commands is None:
            instr = self._imem.memory.load(address=self._last_instruction_address, size="word")
            command = Commands.get_command_by_code(code=instr, program_status=self._program_status)
        else:
            command = self._commands[self._last_instruction_address]

        if isinstance(command, JumpCommand) or isinstance(command, BranchCommand):
            self._branch = True

        for component in self._components:
            component.add_command(command)

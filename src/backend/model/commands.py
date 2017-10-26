import enum
import re

from src.backend.extra.exceptions import\
    CommandWrongNumberBits,\
    UnknownCommand,\
    OperandWrongNumberOfBits,\
    OperandWrongPCMode,\
    OperandBothRequireNextInstruction
from bitarray import bitarray

from src.backend.model.programstatus import ProgramStatus
from src.backend.model.registers import Register


class Operation(enum.Enum):
    DECODE                  = enum.auto()
    EXECUTE                 = enum.auto()
    FETCH_NEXT_INSTRUCTION  = enum.auto()
    FETCH_REGISTER          = enum.auto()
    FETCH_ADDRESS           = enum.auto()
    STORE_REGISTER          = enum.auto()
    STORE_ADDRESS           = enum.auto()
    DONE                    = enum.auto()
    INCREMENT_REGISTER      = enum.auto()
    DECREMENT_REGISTER      = enum.auto()


class Operand:
    def __init__(self, reg: bitarray, mode: bitarray=None):
        if reg.length() != 3 or (mode is not None and mode.length() != 3):
            raise OperandWrongNumberOfBits()

        tmp = bitarray("00000", endian='big')
        tmp.extend(reg)
        self._reg = int.from_bytes(tmp.tobytes(), byteorder='big', signed=False)

        self._mode = None
        if mode is not None:
            tmp = bitarray("00000", endian='big')
            tmp.extend(mode)
            self._mode = int.from_bytes(tmp.tobytes(), byteorder='big', signed=False)

        if self._reg == 7 and self._mode not in (2, 3, 6, 7):
            raise OperandWrongPCMode()

        self._next_instruction = None
        self._inner_register = Register()
        self._inner_address = None

    def is_pc(self) -> bool:
        return self._reg == 7

    def set_next_instruction(self, instr: bitarray):
        self._next_instruction = int.from_bytes(instr.tobytes(), byteorder='big', signed=False)

    def add_next_instruction_to_inner_register(self):
        self._inner_register.inc(value=self._next_instruction)

    def copy_inner_register_to_inner_address(self):
        self._inner_address = Register()
        self._inner_address.set_word(self._inner_register.word())

    @property
    def inner_register(self):
        return self._inner_register

    @property
    def reg(self) -> int:
        return self._reg

    @property
    def mode(self) -> int:
        return self._mode

    @property
    def require_next_instruction(self) -> bool:
        return self._reg == 7 or self._mode // 2 == 3

    @property
    def string_representation(self):
        result = ""
        if self._reg == 7:
            if self._mode // 2 == 1:
                result = "#{}"
            elif self._mode // 2 == 3:
                result = "{}(PC)"
            if self._mode % 2 == 1:
                result = "@" + result
        else:
            result = "R{}".format(self._reg)
            if self._mode != 0:
                result = "({})".format(result)

            if self._mode // 2 == 1:
                result = result + "+"
            elif self._mode // 2 == 2:
                result = "-" + result
            elif self._mode // 2 == 3:
                result = "{}" + result

            if self._mode % 2 == 1 and self._mode != 1:
                result = "@" + result

        if self.require_next_instruction and self._next_instruction is not None:
            result = result.format(self._next_instruction)
        return result

    def add_fetch(self, operations: list, size: str):
        if self._mode // 2 == 2:
            value = 1 if self._mode == 4 and size == "byte" else 2
            operations.append({"operation": Operation.DECREMENT_REGISTER,
                               "register": self._reg,
                               "value": value})

        if self._mode // 2 == 3:
            operations.append({"operation": Operation.FETCH_NEXT_INSTRUCTION,
                               "callback": self.set_next_instruction})

        fetch_size = size if self._mode == 0 else "word"
        operations.append({"operation": Operation.FETCH_REGISTER,
                           "register": self._reg,
                           "size": fetch_size,
                           "callback": self._inner_register.set_byte
                           if fetch_size == "byte" else self._inner_register.set_word})

        if self._mode == 0:
            return

        if self._mode // 2 == 1:
            value = 1 if self._mode == 2 and size == "byte" else 2
            operations.append({"operation": Operation.INCREMENT_REGISTER,
                               "register": self._reg,
                               "value": value})

        if self._mode // 2 == 3:
            operations.append({"operation": Operation.EXECUTE,
                               "callback": self.add_next_instruction_to_inner_register})

        if self._mode in (1, 2, 4, 6):
            operations.append({"operation": Operation.EXECUTE,
                               "callback": self.copy_inner_register_to_inner_address})

        fetch_size = size if self._mode in (1, 2, 4, 6) else "word"
        operations.append({"operation": Operation.FETCH_ADDRESS,
                           "address": lambda: self._inner_register.get(size="word", signed=False),
                           "size": fetch_size,
                           "callback": self._inner_register.set_byte
                           if fetch_size == "byte" else self._inner_register.set_word})

        if self._mode in (1, 2, 4, 6):
            return

        operations.append({"operation": Operation.EXECUTE,
                           "callback": self.copy_inner_register_to_inner_address})
        operations.append({"operation": Operation.FETCH_ADDRESS,
                           "address": lambda: self._inner_register.get(size="word", signed=False),
                           "size": size,
                           "callback": self._inner_register.set_byte
                           if size == "byte" else self._inner_register.set_word})

    def add_store(self, operations: list, size: str):
        value = lambda: (self._inner_register.byte() if size == "byte" else self._inner_register.word())
        if self._mode == 0:
            operations.append({"operation": Operation.STORE_REGISTER,
                               "register": self._reg,
                               "size": size,
                               "value": value})

        else:
            operations.append({"operation": Operation.STORE_ADDRESS,
                               "address": lambda: self._inner_address.get(size="word", signed=False),
                               "size": size,
                               "value": value})


class AbstractCommand:
    def __init__(self, program_status: ProgramStatus):
        self._program_status = program_status
        self._cur_operation = 0
        self._operations = []

        self._string_representation = None
        self._on_byte = False
        self._src_operand = None
        self._dest_operand = None
        self._type = None

    @property
    def on_byte(self):
        return self._on_byte

    @property
    def program_status(self):
        return self._program_status

    @property
    def has_src_operand(self):
        return self._src_operand is not None

    @property
    def has_dest_operand(self):
        return self._dest_operand is not None

    @property
    def src_operand(self):
        return self._src_operand

    @property
    def dest_operand(self):
        return self._dest_operand

    @property
    def type(self):
        return self._type

    def __iter__(self):
        self._cur_operation = 0
        return self

    def __next__(self):
        if self._cur_operation < len(self._operations):
            self._cur_operation += 1
            return self._operations[self._cur_operation - 1]
        raise StopIteration()

    def _add_decode(self):
        self._operations.append({"operation": Operation.DECODE,
                                 "callback": None})

    def _add_execute(self, callback):
        self._operations.append({"operation": Operation.EXECUTE,
                                 "callback": callback})

    def _add_done(self):
        self._operations.append({"operation": Operation.DONE,
                                 "callback": None})


class DoubleOperandCommand(AbstractCommand):
    def __init__(self, src_operand: Operand, dest_operand: Operand, program_status: ProgramStatus):
        super(DoubleOperandCommand, self).__init__(program_status)
        self._src_operand = src_operand
        self._dest_operand = dest_operand
        if self._src_operand.require_next_instruction and self._dest_operand.require_next_instruction:
            raise OperandBothRequireNextInstruction()

    def _add_fetch_operands(self, size: str):
        self._src_operand.add_fetch(operations=self._operations, size=size)
        self._dest_operand.add_fetch(operations=self._operations, size=size)

    def _add_store_operands(self, size: str):
        self._dest_operand.add_store(operations=self._operations, size=size)


class SingleOperandCommand(AbstractCommand):
    def __init__(self, dest_operand: Operand, program_status: ProgramStatus):
        super(SingleOperandCommand, self).__init__(program_status)
        self._dest_operand = dest_operand

    def _add_fetch_operands(self, size: str):
        self._dest_operand.add_fetch(operations=self._operations, size=size)

    def _add_store_operands(self, size: str):
        self._dest_operand.add_store(operations=self._operations, size=size)


class CLRCommand(SingleOperandCommand):
    def __init__(self, matcher, program_status: ProgramStatus):
        super(CLRCommand, self).__init__(dest_operand=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         program_status=program_status)

        self._type = InstanceCommand.CLR
        self._on_byte = (matcher.group("msb") == "1")
        self._string_representation = "CLR" + ("B" if self.on_byte else "")
        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        self.program_status.clear()
        self.program_status.set(bit='Z', value=True)
        self._dest_operand.inner_register.set(size="byte" if self._on_byte else "word", signed=False, value=0)


_REG_PATTERN = r'(?P<{}>[01]{})'
_MODE_PATTERN = r'(?P<{}>[01]{})'
_MSB_PATTERN = r'(?P<msb>0|1)'
_SRC_PATTERN = _MODE_PATTERN.format("srcmode", "{3}") + _REG_PATTERN.format("srcreg", "{3}")
_DEST_PATTERN = _MODE_PATTERN.format("destmode", "{3}") + _REG_PATTERN.format("destreg", "{3}")


class InstanceCommand(enum.Enum):
    CLR = (_MSB_PATTERN + r'000101000' + _DEST_PATTERN, CLRCommand)

    def __init__(self, pattern, klass):
        self._pattern = re.compile(pattern=pattern)
        self._klass = klass

    @property
    def pattern(self):
        return self._pattern

    @property
    def klass(self):
        return self._klass


class Commands:
    @staticmethod
    def get_command_by_code(code: bitarray, program_status: ProgramStatus) -> AbstractCommand:
        if code.length() != 16:
            raise CommandWrongNumberBits()

        for command_instance in list(InstanceCommand):
            matcher = command_instance.pattern.match(code.to01())
            if matcher is not None:
                return command_instance.klass(matcher, program_status)

        raise UnknownCommand(code=code)


if __name__ == "__main__":
    ps = ProgramStatus()
    ps.set('N', True)
    ps.set('C', True)
    com = Commands.get_command_by_code(bitarray("1000101000000000", endian='big'), program_status=ps)
    print(com.dest_operand.mode)
    print(com.dest_operand.reg)
    for i in com._operations:
        print(i["operation"].name)

    print('----------------------')
    com = Commands.get_command_by_code(bitarray("1000101000001000", endian='big'), program_status=ps)
    print(com.dest_operand.mode)
    print(com.dest_operand.reg)
    for i in com._operations:
        print(i["operation"].name)

    print('----------------------')
    com = Commands.get_command_by_code(bitarray("1000101000010000", endian='big'), program_status=ps)
    print(com.dest_operand.mode)
    print(com.dest_operand.reg)
    for i in com._operations:
        print(i["operation"].name)

    print('----------------------')
    com = Commands.get_command_by_code(bitarray("1000101000011000", endian='big'), program_status=ps)
    print(com.dest_operand.mode)
    print(com.dest_operand.reg)
    for i in com._operations:
        print(i["operation"].name)

    print('----------------------')
    com = Commands.get_command_by_code(bitarray("1000101000100000", endian='big'), program_status=ps)
    print(com.dest_operand.mode)
    print(com.dest_operand.reg)
    for i in com._operations:
        print(i["operation"].name)

    print('----------------------')
    com = Commands.get_command_by_code(bitarray("1000101000101000", endian='big'), program_status=ps)
    print(com.dest_operand.mode)
    print(com.dest_operand.reg)
    for i in com._operations:
        print(i["operation"].name)

    print('----------------------')
    com = Commands.get_command_by_code(bitarray("1000101000110000", endian='big'), program_status=ps)
    print(com.dest_operand.mode)
    print(com.dest_operand.reg)
    for i in com._operations:
        print(i["operation"].name)

    print('----------------------')
    com = Commands.get_command_by_code(bitarray("1000101000111000", endian='big'), program_status=ps)
    print(com.dest_operand.mode)
    print(com.dest_operand.reg)
    for i in com._operations:
        print(i["operation"].name)

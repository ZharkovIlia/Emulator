import enum
import re

from src.backend.extra.exceptions import\
    CommandWrongNumberBits,\
    UnknownCommand,\
    OperandWrongNumberOfBits,\
    OperandWrongPCMode
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
        def value():
            return self._inner_register.byte() if size == "byte" else self._inner_register.word()

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
    def __init__(self, program_status: ProgramStatus, type, on_byte: bool):
        self._program_status = program_status
        self._cur_operation = 0
        self._operations = []

        self._string_representation = type.string_representation + ("B" if on_byte else "")
        self._on_byte = on_byte
        self._src_operand = None
        self._dest_operand = None
        self._type = type

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

    @property
    def string_representation(self):
        return self._string_representation

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
    def __init__(self, src_operand: Operand, dest_operand: Operand, **kwargs):
        super(DoubleOperandCommand, self).__init__(**kwargs)
        self._src_operand = src_operand
        self._dest_operand = dest_operand

    def _add_fetch_operands(self, size: str):
        self._src_operand.add_fetch(operations=self._operations, size=size)
        self._dest_operand.add_fetch(operations=self._operations, size=size)

    def _add_store_operands(self, size: str):
        self._dest_operand.add_store(operations=self._operations, size=size)


class SingleOperandCommand(AbstractCommand):
    def __init__(self, dest_operand: Operand, **kwargs):
        super(SingleOperandCommand, self).__init__(**kwargs)
        self._dest_operand = dest_operand

    def _add_fetch_operands(self, size: str):
        self._dest_operand.add_fetch(operations=self._operations, size=size)

    def _add_store_operands(self, size: str):
        self._dest_operand.add_store(operations=self._operations, size=size)


class CLRCommand(SingleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(CLRCommand, self).__init__(dest_operand=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        self.program_status.clear()
        self.program_status.set(bit='Z', value=True)
        self._dest_operand.inner_register.set(size="byte" if self.on_byte else "word", signed=False, value=0)


class COMCommand(SingleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(COMCommand, self).__init__(dest_operand=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        size = "byte" if self.on_byte else "word"
        value = self.dest_operand.inner_register.get(size=size, signed=True)
        value = ~value
        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)
        self.program_status.set(bit="V", value=False)
        self.program_status.set(bit="C", value=True)
        self.dest_operand.inner_register.set(size=size, signed=True, value=value)


class INCCommand(SingleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(INCCommand, self).__init__(dest_operand=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        size = "byte" if self.on_byte else "word"
        value = self.dest_operand.inner_register.get(size=size, signed=True)
        if value == Register.BOUND_PROPERTIES[(size, True)][1]:
            value = Register.BOUND_PROPERTIES[(size, True)][0]
            self.program_status.set(bit="V", value=True)
        else:
            value += 1
            self.program_status.set(bit="V", value=False)

        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)
        self.dest_operand.inner_register.set(size=size, signed=True, value=value)


class DECCommand(SingleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(DECCommand, self).__init__(dest_operand=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        size = "byte" if self.on_byte else "word"
        value = self.dest_operand.inner_register.get(size=size, signed=True)
        if value == Register.BOUND_PROPERTIES[(size, True)][0]:
            value = Register.BOUND_PROPERTIES[(size, True)][1]
            self.program_status.set(bit="V", value=True)
        else:
            value -= 1
            self.program_status.set(bit="V", value=False)

        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)
        self.dest_operand.inner_register.set(size=size, signed=True, value=value)


class NEGCommand(SingleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(NEGCommand, self).__init__(dest_operand=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        size = "byte" if self.on_byte else "word"
        value = self.dest_operand.inner_register.get(size=size, signed=True)
        if value != Register.BOUND_PROPERTIES[(size, True)][0]:
            value = -value

        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)
        self.program_status.set(bit="V", value=(value == Register.BOUND_PROPERTIES[(size, True)][0]))
        self.program_status.set(bit="C", value=value != 0)
        self.dest_operand.inner_register.set(size=size, signed=True, value=value)


class TSTCommand(SingleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(TSTCommand, self).__init__(dest_operand=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        size = "byte" if self.on_byte else "word"
        value = self.dest_operand.inner_register.get(size=size, signed=True)

        self.program_status.clear()
        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)


class ASRCommand(SingleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(ASRCommand, self).__init__(dest_operand=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        size = "byte" if self.on_byte else "word"
        value = self.dest_operand.inner_register.get(size=size, signed=True)

        self.program_status.set(bit="C", value=value % 2 == 1)
        value >>= 1
        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)
        self.program_status.set(bit="V", value=self.program_status.get(bit="C") ^
                                               self.program_status.get(bit="N"))

        self.dest_operand.inner_register.set(size=size, signed=True, value=value)


class ASLCommand(SingleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(ASLCommand, self).__init__(dest_operand=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        size = "byte" if self.on_byte else "word"
        value = self.dest_operand.inner_register.get(size=size, signed=False)

        value <<= 1
        self.program_status.set(bit="C", value=value > Register.BOUND_PROPERTIES[(size, False)][1])
        value %= (Register.BOUND_PROPERTIES[(size, False)][1] + 1)
        self.program_status.set(bit="N", value=value > Register.BOUND_PROPERTIES[(size, True)][1])
        self.program_status.set(bit="Z", value=value == 0)
        self.program_status.set(bit="V", value=self.program_status.get(bit="C") ^
                                               self.program_status.get(bit="N"))

        self.dest_operand.inner_register.set(size=size, signed=False, value=value)


class RORCommand(SingleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(RORCommand, self).__init__(dest_operand=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        size = "byte" if self.on_byte else "word"
        value = self.dest_operand.inner_register.get(size=size, signed=False)

        tmp_bit = (value % 2 == 1)
        value >>= 1
        value += (0 if self.program_status.get(bit="C") is False else Register.BOUND_PROPERTIES[(size, True)][1] + 1)
        self.program_status.set(bit="C", value=tmp_bit)
        self.program_status.set(bit="N", value=value > Register.BOUND_PROPERTIES[(size, True)][1])
        self.program_status.set(bit="Z", value=value == 0)
        self.program_status.set(bit="V", value=self.program_status.get(bit="C") ^
                                               self.program_status.get(bit="N"))

        self.dest_operand.inner_register.set(size=size, signed=False, value=value)


class ROLCommand(SingleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(ROLCommand, self).__init__(dest_operand=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        size = "byte" if self.on_byte else "word"
        value = self.dest_operand.inner_register.get(size=size, signed=False)

        value <<= 1
        value += (0 if self.program_status.get(bit="C") is False else 1)
        self.program_status.set(bit="C", value=value > Register.BOUND_PROPERTIES[(size, False)][1])
        value %= (Register.BOUND_PROPERTIES[(size, False)][1] + 1)
        self.program_status.set(bit="N", value=value > Register.BOUND_PROPERTIES[(size, True)][1])
        self.program_status.set(bit="Z", value=value == 0)
        self.program_status.set(bit="V", value=self.program_status.get(bit="C") ^
                                               self.program_status.get(bit="N"))

        self.dest_operand.inner_register.set(size=size, signed=False, value=value)


class SWABCommand(SingleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(SWABCommand, self).__init__(dest_operand=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                               mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        self.dest_operand.inner_register.reverse()
        value = self.dest_operand.inner_register.get(size="byte", signed=True)

        self.program_status.clear()
        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)


class ADCCommand(SingleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(ADCCommand, self).__init__(dest_operand=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        size = "byte" if self.on_byte else "word"
        tmp_bit = self.program_status.get(bit="C")
        value = self.dest_operand.inner_register.get(size=size, signed=True)

        self.program_status.set(bit="C", value=(value == -1 and tmp_bit is True))
        if value == Register.BOUND_PROPERTIES[(size, True)][1] and tmp_bit is True:
            value = Register.BOUND_PROPERTIES[(size, True)][0]
            self.program_status.set(bit="V", value=True)
        else:
            value += (0 if tmp_bit is False else 1)
            self.program_status.set(bit="V", value=False)

        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)
        self.dest_operand.inner_register.set(size=size, signed=True, value=value)


class SBCCommand(SingleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(SBCCommand, self).__init__(dest_operand=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        size = "byte" if self.on_byte else "word"
        tmp_bit = self.program_status.get(bit="C")
        value = self.dest_operand.inner_register.get(size=size, signed=True)

        self.program_status.set(bit="C", value=not (value == 0 and tmp_bit is True))
        self.program_status.set(bit="V", value=value == Register.BOUND_PROPERTIES[(size, True)][0])
        if value == Register.BOUND_PROPERTIES[(size, True)][0] and tmp_bit is True:
            value = Register.BOUND_PROPERTIES[(size, True)][1]
        else:
            value -= (0 if tmp_bit is False else 1)

        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)
        self.dest_operand.inner_register.set(size=size, signed=True, value=value)


class SXTCommand(SingleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(SXTCommand, self).__init__(dest_operand=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        value = 0 if self.program_status.get(bit="N") is False else Register.BOUND_PROPERTIES[("word", False)][1]

        self.program_status.set(bit="Z", value=value == 0)
        self.dest_operand.inner_register.set(size="word", signed=False, value=value)


class MOVCommand(DoubleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(MOVCommand, self).__init__(src_operand=Operand(reg=bitarray(matcher.group("srcreg"), endian='big'),
                                                             mode=bitarray(matcher.group("srcmode"), endian='big')),
                                         dest_pattern=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        size_store = "byte" if self.on_byte else "word"
        if self.on_byte and self.dest_operand.mode == 0:
            size_store = 'word'
        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size=size_store)

    def execute(self):
        size = "byte" if self.on_byte else "word"
        if self.on_byte and self.dest_operand.mode == 0:
            size = 'word'
        value = self.src_operand.inner_register.get(size=size, signed=True)

        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)
        self.program_status.set(bit="V", value=False)
        self.dest_operand.inner_register.set(size=size, signed=True, value=value)


class CMPCommand(DoubleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(CMPCommand, self).__init__(src_operand=Operand(reg=bitarray(matcher.group("srcreg"), endian='big'),
                                                             mode=bitarray(matcher.group("srcmode"), endian='big')),
                                         dest_pattern=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        size = "byte" if self.on_byte else "word"
        num_bytes = 1 if self.on_byte else 2
        value_src = self.src_operand.inner_register.get(size=size, signed=True)
        value_dest = self.dest_operand.inner_register.get(size=size, signed=True)

        tmp = ~value_dest
        tmp = int.from_bytes(tmp.to_bytes(num_bytes, byteorder='big', signed=True), byteorder='big', signed=False)
        tmp += int.from_bytes(value_src.to_bytes(num_bytes, byteorder='big', signed=True), byteorder='big', signed=False)
        tmp += 1
        self.program_status.set(bit="C", value=not (tmp > Register.BOUND_PROPERTIES[(size, False)][1]))
        tmp %= (Register.BOUND_PROPERTIES[(size, False)][1] + 1)
        tmp = int.from_bytes(tmp.to_bytes(num_bytes, byteorder='big', signed=False), byteorder='big', signed=True)

        self.program_status.set(bit="V", value=value_dest ^ value_src < 0 and not value_dest ^ tmp < 0)
        self.program_status.set(bit="N", value=tmp < 0)
        self.program_status.set(bit="Z", value=tmp == 0)


class ADDCommand(DoubleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(ADDCommand, self).__init__(src_operand=Operand(reg=bitarray(matcher.group("srcreg"), endian='big'),
                                                             mode=bitarray(matcher.group("srcmode"), endian='big')),
                                         dest_pattern=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        size = "byte" if self.on_byte else "word"
        num_bytes = 1 if self.on_byte else 2
        value_src = self.src_operand.inner_register.get(size=size, signed=True)
        value_dest = self.dest_operand.inner_register.get(size=size, signed=True)

        tmp = int.from_bytes(value_dest.to_bytes(num_bytes, byteorder='big', signed=True), byteorder='big', signed=False)
        tmp += int.from_bytes(value_src.to_bytes(num_bytes, byteorder='big', signed=True), byteorder='big', signed=False)
        self.program_status.set(bit="C", value=(tmp > Register.BOUND_PROPERTIES[(size, False)][1]))
        tmp %= (Register.BOUND_PROPERTIES[(size, False)][1] + 1)
        tmp = int.from_bytes(tmp.to_bytes(num_bytes, byteorder='big', signed=False), byteorder='big', signed=True)

        self.program_status.set(bit="V", value=not value_dest ^ value_src < 0 and value_src ^ tmp < 0)
        self.program_status.set(bit="N", value=tmp < 0)
        self.program_status.set(bit="Z", value=tmp == 0)
        self.dest_operand.inner_register.set(size=size, signed=True, value=tmp)


class SUBCommand(DoubleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(SUBCommand, self).__init__(src_operand=Operand(reg=bitarray(matcher.group("srcreg"), endian='big'),
                                                             mode=bitarray(matcher.group("srcmode"), endian='big')),
                                         dest_pattern=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        size = "byte" if self.on_byte else "word"
        num_bytes = 1 if self.on_byte else 2
        value_src = self.src_operand.inner_register.get(size=size, signed=True)
        value_dest = self.dest_operand.inner_register.get(size=size, signed=True)

        tmp = ~value_src
        tmp = int.from_bytes(tmp.to_bytes(num_bytes, byteorder='big', signed=True), byteorder='big', signed=False)
        tmp += int.from_bytes(value_dest.to_bytes(num_bytes, byteorder='big', signed=True), byteorder='big', signed=False)
        tmp += 1
        self.program_status.set(bit="C", value=not (tmp > Register.BOUND_PROPERTIES[(size, False)][1]))
        tmp %= (Register.BOUND_PROPERTIES[(size, False)][1] + 1)
        tmp = int.from_bytes(tmp.to_bytes(num_bytes, byteorder='big', signed=False), byteorder='big', signed=True)

        self.program_status.set(bit="V", value=value_dest ^ value_src < 0 and not value_src ^ tmp < 0)
        self.program_status.set(bit="N", value=tmp < 0)
        self.program_status.set(bit="Z", value=tmp == 0)
        self.dest_operand.inner_register.set(size=size, signed=True, value=tmp)


class BITCommand(DoubleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(BITCommand, self).__init__(src_operand=Operand(reg=bitarray(matcher.group("srcreg"), endian='big'),
                                                             mode=bitarray(matcher.group("srcmode"), endian='big')),
                                         dest_pattern=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        size = "byte" if self.on_byte else "word"
        value_src = self.src_operand.inner_register.get(size=size, signed=True)
        value_dest = self.dest_operand.inner_register.get(size=size, signed=True)

        tmp = value_src & value_dest
        self.program_status.set(bit="N", value=tmp < 0)
        self.program_status.set(bit="Z", value=tmp == 0)
        self.program_status.set(bit="V", value=False)


class BICCommand(DoubleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(BICCommand, self).__init__(src_operand=Operand(reg=bitarray(matcher.group("srcreg"), endian='big'),
                                                             mode=bitarray(matcher.group("srcmode"), endian='big')),
                                         dest_pattern=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        size = "byte" if self.on_byte else "word"
        value_src = self.src_operand.inner_register.get(size=size, signed=True)
        value_dest = self.dest_operand.inner_register.get(size=size, signed=True)

        tmp = ~value_src
        tmp = tmp & value_dest
        self.program_status.set(bit="N", value=tmp < 0)
        self.program_status.set(bit="Z", value=tmp == 0)
        self.program_status.set(bit="V", value=False)
        self.dest_operand.inner_register.set(size=size, signed=True, value=tmp)


class BISCommand(DoubleOperandCommand):
    def __init__(self, matcher, **kwargs):
        super(BISCommand, self).__init__(src_operand=Operand(reg=bitarray(matcher.group("srcreg"), endian='big'),
                                                             mode=bitarray(matcher.group("srcmode"), endian='big')),
                                         dest_pattern=Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                                              mode=bitarray(matcher.group("destmode"), endian='big')),
                                         **kwargs)

        self._add_decode()
        self._add_fetch_operands(size="byte" if self.on_byte else "word")
        self._add_execute(self.execute)
        self._add_store_operands(size="byte" if self.on_byte else "word")

    def execute(self):
        size = "byte" if self.on_byte else "word"
        value_src = self.src_operand.inner_register.get(size=size, signed=True)
        value_dest = self.dest_operand.inner_register.get(size=size, signed=True)

        tmp = value_src | value_dest
        self.program_status.set(bit="N", value=tmp < 0)
        self.program_status.set(bit="Z", value=tmp == 0)
        self.program_status.set(bit="V", value=False)
        self.dest_operand.inner_register.set(size=size, signed=True, value=tmp)


_COMM_PATTERN = r'(?P<{}>[01]{})'
_MSB_PATTERN = r'(?P<msb>0|1)'
_SRC_PATTERN = _COMM_PATTERN.format("srcmode", "{3}") + _COMM_PATTERN.format("srcreg", "{3}")
_DEST_PATTERN = _COMM_PATTERN.format("destmode", "{3}") + _COMM_PATTERN.format("destreg", "{3}")
_REG_PATTERN = _COMM_PATTERN.format("reg", "{3}")


class InstanceCommand(enum.Enum):
    CLR  = (_MSB_PATTERN + r'000101000'  + _DEST_PATTERN,                CLRCommand,  "CLR")
    COM  = (_MSB_PATTERN + r'000101001'  + _DEST_PATTERN,                COMCommand,  "COM")
    INC  = (_MSB_PATTERN + r'000101010'  + _DEST_PATTERN,                INCCommand,  "INC")
    DEC  = (_MSB_PATTERN + r'000101011'  + _DEST_PATTERN,                DECCommand,  "DEC")
    NEG  = (_MSB_PATTERN + r'000101100'  + _DEST_PATTERN,                NEGCommand,  "NEG")
    TST  = (_MSB_PATTERN + r'000101111'  + _DEST_PATTERN,                TSTCommand,  "TST")
    ASR  = (_MSB_PATTERN + r'000110010'  + _DEST_PATTERN,                ASRCommand,  "ASR")
    ASL  = (_MSB_PATTERN + r'000110011'  + _DEST_PATTERN,                ASLCommand,  "ASL")
    ROR  = (_MSB_PATTERN + r'000110000'  + _DEST_PATTERN,                RORCommand,  "ROR")
    SWAB = (               r'0000000011' + _DEST_PATTERN,                SWABCommand, "SWAB")
    ADC  = (_MSB_PATTERN + r'000101101'  + _DEST_PATTERN,                ADCCommand,  "ADC")
    SBC  = (_MSB_PATTERN + r'000101110'  + _DEST_PATTERN,                SBCCommand,  "SBC")
    SXT  = (               r'0000110111' + _DEST_PATTERN,                SXTCommand,  "SXT")
    MOV  = (_MSB_PATTERN + r'001'        + _SRC_PATTERN + _DEST_PATTERN, MOVCommand,  "MOV")
    CMP  = (_MSB_PATTERN + r'010'        + _SRC_PATTERN + _DEST_PATTERN, CMPCommand,  "CMP")
    ADD  = (               r'0110'       + _SRC_PATTERN + _DEST_PATTERN, ADDCommand,  "ADD")
    SUB  = (               r'1110'       + _SRC_PATTERN + _DEST_PATTERN, SUBCommand,  "SUB")
    BIT  = (_MSB_PATTERN + r'011'        + _SRC_PATTERN + _DEST_PATTERN, BITCommand,  "BIT")
    BIC  = (_MSB_PATTERN + r'100'        + _SRC_PATTERN + _DEST_PATTERN, BICCommand,  "BIC")
    BIS  = (_MSB_PATTERN + r'101'        + _SRC_PATTERN + _DEST_PATTERN, BISCommand,  "BIS")
    MUL  = (               r'0111000'    + _REG_PATTERN + _SRC_PATTERN,  MULCommand,  "MUL")
    DIV  = (               r'0111001'    + _REG_PATTERN + _SRC_PATTERN,  DIVCommand,  "DIV")
    ASH  = (               r'0111010'    + _REG_PATTERN + _SRC_PATTERN,  ASHCommand,  "ASH")
    ASHC = (               r'0111011'    + _REG_PATTERN + _SRC_PATTERN,  ASHCCommand, "ASHC")
    XOR  = (               r'0111100'    + _REG_PATTERN + _SRC_PATTERN,  XORCommand,  "XOR")

    def __init__(self, pattern, klass, representation: str):
        self._pattern = re.compile(pattern=pattern)
        self._klass = klass
        self._string_representation = representation

    @property
    def pattern(self):
        return self._pattern

    @property
    def klass(self):
        return self._klass

    @property
    def string_representation(self):
        return self._string_representation


class Commands:
    @staticmethod
    def get_command_by_code(code: bitarray, program_status: ProgramStatus) -> AbstractCommand:
        if code.length() != 16:
            raise CommandWrongNumberBits()

        for command_instance in list(InstanceCommand):
            matcher = command_instance.pattern.match(code.to01())
            if matcher is not None:
                on_byte = False
                if "msb" in matcher.groupdict():
                    on_byte = (matcher.group("msb") == "1")
                return command_instance.klass(matcher, program_status=program_status,
                                              type=command_instance, on_byte=on_byte)

        raise UnknownCommand(code=code)

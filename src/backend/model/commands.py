import enum
import re

from src.backend.extra.exceptions import\
    CommandWrongNumberBits,\
    UnknownCommand,\
    OperandWrongNumberOfBits,\
    OperandWrongPCMode,\
    CommandJMPToRegister
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
    INCREMENT_REGISTER      = enum.auto()
    DECREMENT_REGISTER      = enum.auto()
    BRANCH_IF               = enum.auto()
    JUMP                    = enum.auto()


class Operand:
    def __init__(self, reg: bitarray, mode: bitarray):
        if reg.length() != 3 or mode.length() != 3:
            raise OperandWrongNumberOfBits()

        tmp = bitarray("00000", endian='big')
        tmp.extend(reg)
        self._reg = int.from_bytes(tmp.tobytes(), byteorder='big', signed=False)

        tmp = bitarray("00000", endian='big')
        tmp.extend(mode)
        self._mode = int.from_bytes(tmp.tobytes(), byteorder='big', signed=False)

        if self._reg == 7 and self._mode not in (2, 3, 6, 7):
            raise OperandWrongPCMode()

        self._next_instruction = None
        self._inner_register = Register()
        self._inner_address = None

        self.do_not_fetch_operand = False

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

        if self._mode == 0 and self.do_not_fetch_operand:
            return
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

        if self._mode in (1, 2, 4, 6) and self.do_not_fetch_operand:
            return
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

        if self.do_not_fetch_operand:
            return
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
    def __init__(self, program_status: ProgramStatus, type_, on_byte: bool):
        self._program_status = program_status
        self._cur_operation = 0
        self._operations = []

        self._string_representation = type_.string_representation + ("B" if on_byte else "")
        self._on_byte = on_byte
        self._size = 'byte' if self._on_byte else 'word'
        self._src_operand = None
        self._dest_operand = None
        self._type = type_

    @property
    def size(self):
        return self._size

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

    @property
    def dest_stored(self):
        return self._type.dest_stored

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

    def _add_fetch_operands(self, size: str):
        if self._src_operand is not None:
            self._src_operand.add_fetch(operations=self._operations, size=size)
        if self._dest_operand is not None:
            self._dest_operand.add_fetch(operations=self._operations, size=size)

    def _add_store_operands(self, size: str):
        if self._dest_operand is not None:
            self._dest_operand.add_store(operations=self._operations, size=size)


class DoubleOperandCommand(AbstractCommand):
    def __init__(self, matcher, **kwargs):
        super(DoubleOperandCommand, self).__init__(**kwargs)
        self._src_operand = Operand(reg=bitarray(matcher.group("srcreg"), endian='big'),
                                    mode=bitarray(matcher.group("srcmode"), endian='big'))
        self._dest_operand = Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                     mode=bitarray(matcher.group("destmode"), endian='big'))

        self._add_all_operations()

    def _add_all_operations(self):
        self._add_decode()
        self._add_fetch_operands(size=self.size)
        self._add_execute(self.execute)
        if self.dest_stored:
            self._add_store_operands(size=self.size)

    def execute(self):
        raise NotImplementedError()


class SingleOperandCommand(AbstractCommand):
    def __init__(self, matcher, **kwargs):
        super(SingleOperandCommand, self).__init__(**kwargs)
        self._dest_operand = Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                     mode=bitarray(matcher.group("destmode"), endian='big'))

        self._add_all_operations()

    def _add_all_operations(self):
        self._add_decode()
        self._add_fetch_operands(size=self.size)
        self._add_execute(self.execute)
        if self.dest_stored:
            self._add_store_operands(size=self.size)

    def execute(self):
        raise NotImplementedError()


class RegisterSourceCommand(AbstractCommand):
    def __init__(self, matcher, **kwargs):
        super(RegisterSourceCommand, self).__init__(**kwargs)
        self._src_operand = Operand(reg=bitarray(matcher.group("reg"), endian='big'),
                                    mode=bitarray("000", endian='big'))
        self._dest_operand = Operand(reg=bitarray(matcher.group("destreg"), endian='big'),
                                     mode=bitarray(matcher.group("destmode"), endian='big'))

        self._add_all_operations()

    def _add_all_operations(self):
        self._add_decode()
        self._add_fetch_operands(size=self.size)
        self._add_execute(self.execute)
        if self.dest_stored:
            self._add_store_operands(size=self.size)

    def execute(self):
        raise NotImplementedError()


class BranchCommand(AbstractCommand):
    def __init__(self, matcher, **kwargs):
        super(BranchCommand, self).__init__(**kwargs)
        self._offset = int.from_bytes(bitarray(matcher.group("offset"), endian='big').tobytes(),
                                      byteorder='big', signed=True)
        self._offset *= 2
        self._if_branch = False

        self._add_all_operations()

    @property
    def offset(self):
        return self._offset

    def _add_all_operations(self):
        self._add_decode()
        self._add_execute(self.execute)
        self._add_branch()

    def _add_branch(self):
        self._operations.append({"operation": Operation.BRANCH_IF,
                                 "if": lambda: self._if_branch,
                                 "offset": self._offset})

    def execute(self):
        raise NotImplementedError()


class JMPCommand(AbstractCommand):
    def __init__(self, matcher, **kwargs):
        super(JMPCommand, self).__init__(**kwargs)
        dest_reg = bitarray(matcher.group("destreg"), endian='big')
        dest_mode = bitarray(matcher.group("destmode"), endian='big')
        if dest_mode.to01() == "000":
            raise CommandJMPToRegister()
        self._dest_operand = Operand(reg=dest_reg, mode=dest_mode)
        self._dest_operand.do_not_fetch_operand = True

        self._add_decode()
        self._add_fetch_operands(size="word")
        self._add_jump()

    def _add_jump(self):
        self._operations.append({"operation": Operation.JUMP,
                                 "address": lambda: self.dest_operand.inner_register.get(size="word", signed=False)})


class JSRCommand(AbstractCommand):
    def __init__(self, matcher, **kwargs):
        super(JSRCommand, self).__init__(**kwargs)

        dest_reg = bitarray(matcher.group("destreg"), endian='big')
        dest_mode = bitarray(matcher.group("destmode"), endian='big')
        self._src_reg = bitarray(matcher.group("reg"), endian='big')
        if dest_mode.to01() == "000":
            raise CommandJMPToRegister()
        if self._src_reg.length() != 3:
            raise OperandWrongNumberOfBits()

        self._dest_operand = Operand(reg=dest_reg, mode=dest_mode)
        self._dest_operand.do_not_fetch_operand = True

        self._add_decode()
        self._add_fetch_operands(size="word")
        self._add_push_onto_stack()
        self._add_mov_pc_to_reg()
        self._add_jump()

    def _add_push_onto_stack(self):
        self._subcommand = Commands.get_command_by_code(code=bitarray("0001000" + self._src_reg.to01() + "100110"),
                                                        program_status=ProgramStatus())
        index_decode = None
        for i, op in enumerate(self._subcommand._operations):
            if op["operation"] == Operation.DECODE:
                index_decode = i
                break
        self._subcommand._operations.pop(index_decode)
        self._operations.extend(self._subcommand._operations)

    def _add_mov_pc_to_reg(self):
        self._tmp_pc = Register()
        tmp = bitarray("00000", endian='big')
        tmp.extend(self._src_reg)
        self._reg_index = int.from_bytes(tmp.tobytes(), byteorder='big', signed=False)
        self._operations.append({"operation": Operation.FETCH_REGISTER,
                                 "register": 7,
                                 "size": "word",
                                 "callback": self._tmp_pc.set_word})

        self._operations.append({"operation": Operation.STORE_REGISTER,
                                 "register": self._reg_index,
                                 "size": "word",
                                 "value": lambda: self._tmp_pc.word()})

    def _add_jump(self):
        self._operations.append({"operation": Operation.JUMP,
                                 "address": lambda: self.dest_operand.inner_register.get(size="word", signed=False)})


class RTSCommand(AbstractCommand):
    def __init__(self, matcher, **kwargs):
        super(RTSCommand, self).__init__(**kwargs)

        self._src_reg = bitarray(matcher.group("reg"), endian='big')
        if self._src_reg.length() != 3:
            raise OperandWrongNumberOfBits()

        self._src_operand = Operand(reg=self._src_reg, mode=bitarray("000", endian='big'))

        self._add_decode()
        self._add_fetch_operands(size="word")
        self._add_jump()
        self._add_pop_from_stack()

    def _add_pop_from_stack(self):
        self._subcommand = Commands.get_command_by_code(code=bitarray("0001"  + "010110000" + self._src_reg.to01()),
                                                        program_status=ProgramStatus())
        index_decode = None
        for i, op in enumerate(self._subcommand._operations):
            if op["operation"] == Operation.DECODE:
                index_decode = i
                break
        self._subcommand._operations.pop(index_decode)
        self._operations.extend(self._subcommand._operations)

    def _add_jump(self):
        self._operations.append({"operation": Operation.JUMP,
                                 "address": lambda: self.src_operand.inner_register.get(size="word", signed=False)})


class CLRCommand(SingleOperandCommand):
    def __init__(self, **kwargs):
        super(CLRCommand, self).__init__(**kwargs)

    def execute(self):
        self.program_status.clear()
        self.program_status.set(bit='Z', value=True)
        self._dest_operand.inner_register.set(size=self.size, signed=False, value=0)


class COMCommand(SingleOperandCommand):
    def __init__(self, **kwargs):
        super(COMCommand, self).__init__(**kwargs)

    def execute(self):
        value = self.dest_operand.inner_register.get(size=self.size, signed=True)
        value = ~value
        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)
        self.program_status.set(bit="V", value=False)
        self.program_status.set(bit="C", value=True)
        self.dest_operand.inner_register.set(size=self.size, signed=True, value=value)


class INCCommand(SingleOperandCommand):
    def __init__(self, **kwargs):
        super(INCCommand, self).__init__(**kwargs)

    def execute(self):
        value = self.dest_operand.inner_register.get(size=self.size, signed=True)
        if value == Register.BOUND_PROPERTIES[(self.size, True)][1]:
            value = Register.BOUND_PROPERTIES[(self.size, True)][0]
            self.program_status.set(bit="V", value=True)
        else:
            value += 1
            self.program_status.set(bit="V", value=False)

        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)
        self.dest_operand.inner_register.set(size=self.size, signed=True, value=value)


class DECCommand(SingleOperandCommand):
    def __init__(self, **kwargs):
        super(DECCommand, self).__init__(**kwargs)

    def execute(self):
        value = self.dest_operand.inner_register.get(size=self.size, signed=True)
        if value == Register.BOUND_PROPERTIES[(self.size, True)][0]:
            value = Register.BOUND_PROPERTIES[(self.size, True)][1]
            self.program_status.set(bit="V", value=True)
        else:
            value -= 1
            self.program_status.set(bit="V", value=False)

        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)
        self.dest_operand.inner_register.set(size=self.size, signed=True, value=value)


class NEGCommand(SingleOperandCommand):
    def __init__(self, **kwargs):
        super(NEGCommand, self).__init__(**kwargs)

    def execute(self):
        value = self.dest_operand.inner_register.get(size=self.size, signed=True)
        if value != Register.BOUND_PROPERTIES[(self.size, True)][0]:
            value = -value

        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)
        self.program_status.set(bit="V", value=(value == Register.BOUND_PROPERTIES[(self.size, True)][0]))
        self.program_status.set(bit="C", value=value != 0)
        self.dest_operand.inner_register.set(size=self.size, signed=True, value=value)


class TSTCommand(SingleOperandCommand):
    def __init__(self, **kwargs):
        super(TSTCommand, self).__init__(**kwargs)

    def execute(self):
        value = self.dest_operand.inner_register.get(size=self.size, signed=True)

        self.program_status.clear()
        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)


class ASRCommand(SingleOperandCommand):
    def __init__(self, **kwargs):
        super(ASRCommand, self).__init__(**kwargs)

    def execute(self):
        value = self.dest_operand.inner_register.get(size=self.size, signed=True)

        self.program_status.set(bit="C", value=value % 2 == 1)
        value >>= 1
        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)
        self.program_status.set(bit="V", value=self.program_status.get(bit="C") ^
                                self.program_status.get(bit="N"))

        self.dest_operand.inner_register.set(size=self.size, signed=True, value=value)


class ASLCommand(SingleOperandCommand):
    def __init__(self, **kwargs):
        super(ASLCommand, self).__init__(**kwargs)

    def execute(self):
        value = self.dest_operand.inner_register.get(size=self.size, signed=False)

        value <<= 1
        self.program_status.set(bit="C", value=value > Register.BOUND_PROPERTIES[(self.size, False)][1])
        value %= (Register.BOUND_PROPERTIES[(self.size, False)][1] + 1)
        self.program_status.set(bit="N", value=value > Register.BOUND_PROPERTIES[(self.size, True)][1])
        self.program_status.set(bit="Z", value=value == 0)
        self.program_status.set(bit="V", value=self.program_status.get(bit="C") ^
                                self.program_status.get(bit="N"))

        self.dest_operand.inner_register.set(size=self.size, signed=False, value=value)


class RORCommand(SingleOperandCommand):
    def __init__(self, **kwargs):
        super(RORCommand, self).__init__(**kwargs)

    def execute(self):
        value = self.dest_operand.inner_register.get(size=self.size, signed=False)

        tmp_bit = (value % 2 == 1)
        value >>= 1
        value += (0 if self.program_status.get(bit="C") is False
                  else Register.BOUND_PROPERTIES[(self.size, True)][1] + 1)
        self.program_status.set(bit="C", value=tmp_bit)
        self.program_status.set(bit="N", value=value > Register.BOUND_PROPERTIES[(self.size, True)][1])
        self.program_status.set(bit="Z", value=value == 0)
        self.program_status.set(bit="V", value=self.program_status.get(bit="C") ^
                                self.program_status.get(bit="N"))

        self.dest_operand.inner_register.set(size=self.size, signed=False, value=value)


class ROLCommand(SingleOperandCommand):
    def __init__(self, **kwargs):
        super(ROLCommand, self).__init__(**kwargs)

    def execute(self):
        value = self.dest_operand.inner_register.get(size=self.size, signed=False)

        value <<= 1
        value += (0 if self.program_status.get(bit="C") is False else 1)
        self.program_status.set(bit="C", value=value > Register.BOUND_PROPERTIES[(self.size, False)][1])
        value %= (Register.BOUND_PROPERTIES[(self.size, False)][1] + 1)
        self.program_status.set(bit="N", value=value > Register.BOUND_PROPERTIES[(self.size, True)][1])
        self.program_status.set(bit="Z", value=value == 0)
        self.program_status.set(bit="V", value=self.program_status.get(bit="C") ^
                                self.program_status.get(bit="N"))

        self.dest_operand.inner_register.set(size=self.size, signed=False, value=value)


class SWABCommand(SingleOperandCommand):
    def __init__(self, **kwargs):
        super(SWABCommand, self).__init__(**kwargs)

    def execute(self):
        self.dest_operand.inner_register.reverse()
        value = self.dest_operand.inner_register.get(size="byte", signed=True)

        self.program_status.clear()
        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)


class ADCCommand(SingleOperandCommand):
    def __init__(self, **kwargs):
        super(ADCCommand, self).__init__(**kwargs)

    def execute(self):
        tmp_bit = self.program_status.get(bit="C")
        value = self.dest_operand.inner_register.get(size=self.size, signed=True)

        self.program_status.set(bit="C", value=(value == -1 and tmp_bit is True))
        if value == Register.BOUND_PROPERTIES[(self.size, True)][1] and tmp_bit is True:
            value = Register.BOUND_PROPERTIES[(self.size, True)][0]
            self.program_status.set(bit="V", value=True)
        else:
            value += (0 if tmp_bit is False else 1)
            self.program_status.set(bit="V", value=False)

        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)
        self.dest_operand.inner_register.set(size=self.size, signed=True, value=value)


class SBCCommand(SingleOperandCommand):
    def __init__(self, **kwargs):
        super(SBCCommand, self).__init__(**kwargs)

    def execute(self):
        tmp_bit = self.program_status.get(bit="C")
        value = self.dest_operand.inner_register.get(size=self.size, signed=True)

        self.program_status.set(bit="C", value=not (value == 0 and tmp_bit is True))
        self.program_status.set(bit="V", value=value == Register.BOUND_PROPERTIES[(self.size, True)][0])
        if value == Register.BOUND_PROPERTIES[(self.size, True)][0] and tmp_bit is True:
            value = Register.BOUND_PROPERTIES[(self.size, True)][1]
        else:
            value -= (0 if tmp_bit is False else 1)

        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)
        self.dest_operand.inner_register.set(size=self.size, signed=True, value=value)


class SXTCommand(SingleOperandCommand):
    def __init__(self, **kwargs):
        super(SXTCommand, self).__init__(**kwargs)

    def execute(self):
        value = 0 if self.program_status.get(bit="N") is False else Register.BOUND_PROPERTIES[("word", False)][1]

        self.program_status.set(bit="Z", value=value == 0)
        self.dest_operand.inner_register.set(size="word", signed=False, value=value)


class MOVCommand(DoubleOperandCommand):
    def __init__(self, **kwargs):
        super(MOVCommand, self).__init__(**kwargs)

    def execute(self):
        size_exec = self.size
        value = self.src_operand.inner_register.get(size=size_exec, signed=True)
        if self.on_byte and self.dest_operand.mode == 0:
            size_exec = 'word'

        self.program_status.set(bit="N", value=value < 0)
        self.program_status.set(bit="Z", value=value == 0)
        self.program_status.set(bit="V", value=False)
        self.dest_operand.inner_register.set(size=size_exec, signed=True, value=value)

    def _add_all_operations(self):
        self.dest_operand.do_not_fetch_operand = True
        size_store = self.size
        if self.on_byte and self.dest_operand.mode == 0:
            size_store = 'word'
        self._add_decode()
        self._add_fetch_operands(size=self.size)
        self._add_execute(self.execute)
        self._add_store_operands(size=size_store)


class CMPCommand(DoubleOperandCommand):
    def __init__(self, **kwargs):
        super(CMPCommand, self).__init__(**kwargs)

    def execute(self):
        num_bytes = 1 if self.on_byte else 2
        value_src = self.src_operand.inner_register.get(size=self.size, signed=True)
        value_dest = self.dest_operand.inner_register.get(size=self.size, signed=True)

        tmp = ~value_dest
        tmp = int.from_bytes(tmp.to_bytes(num_bytes, byteorder='big', signed=True),
                             byteorder='big', signed=False)
        tmp += int.from_bytes(value_src.to_bytes(num_bytes, byteorder='big', signed=True),
                              byteorder='big', signed=False)
        tmp += 1
        self.program_status.set(bit="C", value=not (tmp > Register.BOUND_PROPERTIES[(self.size, False)][1]))
        tmp %= (Register.BOUND_PROPERTIES[(self.size, False)][1] + 1)
        tmp = int.from_bytes(tmp.to_bytes(num_bytes, byteorder='big', signed=False),
                             byteorder='big', signed=True)

        self.program_status.set(bit="V", value=value_dest ^ value_src < 0 and not value_dest ^ tmp < 0)
        self.program_status.set(bit="N", value=tmp < 0)
        self.program_status.set(bit="Z", value=tmp == 0)


class ADDCommand(DoubleOperandCommand):
    def __init__(self, **kwargs):
        super(ADDCommand, self).__init__(**kwargs)

    def execute(self):
        value_src = self.src_operand.inner_register.get(size="word", signed=True)
        value_dest = self.dest_operand.inner_register.get(size="word", signed=True)

        tmp = int.from_bytes(value_dest.to_bytes(2, byteorder='big', signed=True),
                             byteorder='big', signed=False)
        tmp += int.from_bytes(value_src.to_bytes(2, byteorder='big', signed=True),
                              byteorder='big', signed=False)
        self.program_status.set(bit="C", value=(tmp > Register.BOUND_PROPERTIES[("word", False)][1]))
        tmp %= (Register.BOUND_PROPERTIES[("word", False)][1] + 1)
        tmp = int.from_bytes(tmp.to_bytes(2, byteorder='big', signed=False),
                             byteorder='big', signed=True)

        self.program_status.set(bit="V", value=not value_dest ^ value_src < 0 and value_src ^ tmp < 0)
        self.program_status.set(bit="N", value=tmp < 0)
        self.program_status.set(bit="Z", value=tmp == 0)
        self.dest_operand.inner_register.set(size="word", signed=True, value=tmp)


class SUBCommand(DoubleOperandCommand):
    def __init__(self, **kwargs):
        super(SUBCommand, self).__init__(**kwargs)

    def execute(self):
        value_src = self.src_operand.inner_register.get(size="word", signed=True)
        value_dest = self.dest_operand.inner_register.get(size="word", signed=True)

        tmp = ~value_src
        tmp = int.from_bytes(tmp.to_bytes(2, byteorder='big', signed=True),
                             byteorder='big', signed=False)
        tmp += int.from_bytes(value_dest.to_bytes(2, byteorder='big', signed=True),
                              byteorder='big', signed=False)
        tmp += 1
        self.program_status.set(bit="C", value=not (tmp > Register.BOUND_PROPERTIES[("word", False)][1]))
        tmp %= (Register.BOUND_PROPERTIES[("word", False)][1] + 1)
        tmp = int.from_bytes(tmp.to_bytes(2, byteorder='big', signed=False),
                             byteorder='big', signed=True)

        self.program_status.set(bit="V", value=value_dest ^ value_src < 0 and not value_src ^ tmp < 0)
        self.program_status.set(bit="N", value=tmp < 0)
        self.program_status.set(bit="Z", value=tmp == 0)
        self.dest_operand.inner_register.set(size="word", signed=True, value=tmp)


class BITCommand(DoubleOperandCommand):
    def __init__(self, **kwargs):
        super(BITCommand, self).__init__(**kwargs)

    def execute(self):
        value_src = self.src_operand.inner_register.get(size=self.size, signed=True)
        value_dest = self.dest_operand.inner_register.get(size=self.size, signed=True)

        tmp = value_src & value_dest
        self.program_status.set(bit="N", value=tmp < 0)
        self.program_status.set(bit="Z", value=tmp == 0)
        self.program_status.set(bit="V", value=False)


class BICCommand(DoubleOperandCommand):
    def __init__(self, **kwargs):
        super(BICCommand, self).__init__(**kwargs)

    def execute(self):
        value_src = self.src_operand.inner_register.get(size=self.size, signed=True)
        value_dest = self.dest_operand.inner_register.get(size=self.size, signed=True)

        tmp = ~value_src
        tmp = tmp & value_dest
        self.program_status.set(bit="N", value=tmp < 0)
        self.program_status.set(bit="Z", value=tmp == 0)
        self.program_status.set(bit="V", value=False)
        self.dest_operand.inner_register.set(size=self.size, signed=True, value=tmp)


class BISCommand(DoubleOperandCommand):
    def __init__(self, **kwargs):
        super(BISCommand, self).__init__(**kwargs)

    def execute(self):
        value_src = self.src_operand.inner_register.get(size=self.size, signed=True)
        value_dest = self.dest_operand.inner_register.get(size=self.size, signed=True)

        tmp = value_src | value_dest
        self.program_status.set(bit="N", value=tmp < 0)
        self.program_status.set(bit="Z", value=tmp == 0)
        self.program_status.set(bit="V", value=False)
        self.dest_operand.inner_register.set(size=self.size, signed=True, value=tmp)


class XORCommand(RegisterSourceCommand):
    def __init__(self, **kwargs):
        super(XORCommand, self).__init__(**kwargs)

    def execute(self):
        value_src = self.src_operand.inner_register.get(size="word", signed=True)
        value_dest = self.dest_operand.inner_register.get(size="word", signed=True)

        tmp = value_src ^ value_dest
        self.program_status.set(bit="N", value=tmp < 0)
        self.program_status.set(bit="Z", value=tmp == 0)
        self.program_status.set(bit="V", value=False)
        self.dest_operand.inner_register.set(size="word", signed=True, value=tmp)


class BRCommand(BranchCommand):
    def __init__(self, **kwargs):
        super(BRCommand, self).__init__(**kwargs)

    def execute(self):
        self._if_branch = True


class BNECommand(BranchCommand):
    def __init__(self, **kwargs):
        super(BNECommand, self).__init__(**kwargs)

    def execute(self):
        self._if_branch = not self.program_status.get(bit="Z")


class BEQCommand(BranchCommand):
    def __init__(self, **kwargs):
        super(BEQCommand, self).__init__(**kwargs)

    def execute(self):
        self._if_branch = self.program_status.get(bit="Z")


class BPLCommand(BranchCommand):
    def __init__(self, **kwargs):
        super(BPLCommand, self).__init__(**kwargs)

    def execute(self):
        self._if_branch = not self.program_status.get(bit="N")


class BMICommand(BranchCommand):
    def __init__(self, **kwargs):
        super(BMICommand, self).__init__(**kwargs)

    def execute(self):
        self._if_branch = self.program_status.get(bit="N")


class BVCCommand(BranchCommand):
    def __init__(self, **kwargs):
        super(BVCCommand, self).__init__(**kwargs)

    def execute(self):
        self._if_branch = not self.program_status.get(bit="V")


class BVSCommand(BranchCommand):
    def __init__(self, **kwargs):
        super(BVSCommand, self).__init__(**kwargs)

    def execute(self):
        self._if_branch = self.program_status.get(bit="V")


class BCCCommand(BranchCommand):
    def __init__(self, **kwargs):
        super(BCCCommand, self).__init__(**kwargs)

    def execute(self):
        self._if_branch = not self.program_status.get(bit="C")


class BCSCommand(BranchCommand):
    def __init__(self, **kwargs):
        super(BCSCommand, self).__init__(**kwargs)

    def execute(self):
        self._if_branch = self.program_status.get(bit="C")


class BGECommand(BranchCommand):
    def __init__(self, **kwargs):
        super(BGECommand, self).__init__(**kwargs)

    def execute(self):
        self._if_branch = not (self.program_status.get(bit="N") ^ self.program_status.get(bit="V"))


class BLTCommand(BranchCommand):
    def __init__(self, **kwargs):
        super(BLTCommand, self).__init__(**kwargs)

    def execute(self):
        self._if_branch = (self.program_status.get(bit="N") ^ self.program_status.get(bit="V"))


class BGTCommand(BranchCommand):
    def __init__(self, **kwargs):
        super(BGTCommand, self).__init__(**kwargs)

    def execute(self):
        self._if_branch = not (self.program_status.get(bit="Z") or
                               (self.program_status.get(bit="N") ^ self.program_status.get(bit="V")))


class BLECommand(BranchCommand):
    def __init__(self, **kwargs):
        super(BLECommand, self).__init__(**kwargs)

    def execute(self):
        self._if_branch = (self.program_status.get(bit="Z") or
                           (self.program_status.get(bit="N") ^ self.program_status.get(bit="V")))


class BHICommand(BranchCommand):
    def __init__(self, **kwargs):
        super(BHICommand, self).__init__(**kwargs)

    def execute(self):
        self._if_branch = not self.program_status.get(bit="C") and not self.program_status.get(bit="Z")


class BLOSCommand(BranchCommand):
    def __init__(self, **kwargs):
        super(BLOSCommand, self).__init__(**kwargs)

    def execute(self):
        self._if_branch = self.program_status.get(bit="C") or self.program_status.get(bit="Z")


_COMM_PATTERN = r'(?P<{}>[01]{})'
_MSB_PATTERN = r'(?P<msb>0|1)'
_SRC_PATTERN = _COMM_PATTERN.format("srcmode", "{3}") + _COMM_PATTERN.format("srcreg", "{3}")
_DEST_PATTERN = _COMM_PATTERN.format("destmode", "{3}") + _COMM_PATTERN.format("destreg", "{3}")
_REG_PATTERN = _COMM_PATTERN.format("reg", "{3}")
_OFFSET_PATTERN = _COMM_PATTERN.format("offset", "{8}")


class InstanceCommand(enum.Enum):
    CLR  = (_MSB_PATTERN + r'000101000'  + _DEST_PATTERN,                CLRCommand,  "CLR",  True)
    COM  = (_MSB_PATTERN + r'000101001'  + _DEST_PATTERN,                COMCommand,  "COM",  True)
    INC  = (_MSB_PATTERN + r'000101010'  + _DEST_PATTERN,                INCCommand,  "INC",  True)
    DEC  = (_MSB_PATTERN + r'000101011'  + _DEST_PATTERN,                DECCommand,  "DEC",  True)
    NEG  = (_MSB_PATTERN + r'000101100'  + _DEST_PATTERN,                NEGCommand,  "NEG",  True)
    TST  = (_MSB_PATTERN + r'000101111'  + _DEST_PATTERN,                TSTCommand,  "TST",  False)
    ASR  = (_MSB_PATTERN + r'000110010'  + _DEST_PATTERN,                ASRCommand,  "ASR",  True)
    ASL  = (_MSB_PATTERN + r'000110011'  + _DEST_PATTERN,                ASLCommand,  "ASL",  True)
    ROR  = (_MSB_PATTERN + r'000110000'  + _DEST_PATTERN,                RORCommand,  "ROR",  True)
    ROL  = (_MSB_PATTERN + r'000110001'  + _DEST_PATTERN,                ROLCommand,  "ROL",  True)
    SWAB = (               r'0000000011' + _DEST_PATTERN,                SWABCommand, "SWAB", True)
    ADC  = (_MSB_PATTERN + r'000101101'  + _DEST_PATTERN,                ADCCommand,  "ADC",  True)
    SBC  = (_MSB_PATTERN + r'000101110'  + _DEST_PATTERN,                SBCCommand,  "SBC",  True)
    SXT  = (               r'0000110111' + _DEST_PATTERN,                SXTCommand,  "SXT",  True)
    MOV  = (_MSB_PATTERN + r'001'        + _SRC_PATTERN + _DEST_PATTERN, MOVCommand,  "MOV",  True)
    CMP  = (_MSB_PATTERN + r'010'        + _SRC_PATTERN + _DEST_PATTERN, CMPCommand,  "CMP",  False)
    ADD  = (               r'0110'       + _SRC_PATTERN + _DEST_PATTERN, ADDCommand,  "ADD",  True)
    SUB  = (               r'1110'       + _SRC_PATTERN + _DEST_PATTERN, SUBCommand,  "SUB",  True)
    BIT  = (_MSB_PATTERN + r'011'        + _SRC_PATTERN + _DEST_PATTERN, BITCommand,  "BIT",  False)
    BIC  = (_MSB_PATTERN + r'100'        + _SRC_PATTERN + _DEST_PATTERN, BICCommand,  "BIC",  True)
    BIS  = (_MSB_PATTERN + r'101'        + _SRC_PATTERN + _DEST_PATTERN, BISCommand,  "BIS",  True)
    XOR  = (               r'0111100'    + _REG_PATTERN + _DEST_PATTERN, XORCommand,  "XOR",  True)
    BR   = (               r'00000001'   + _OFFSET_PATTERN,              BRCommand,   "BR",   False)
    BNE  = (               r'00000010'   + _OFFSET_PATTERN,              BNECommand,  "BNE",  False)
    BEQ  = (               r'00000011'   + _OFFSET_PATTERN,              BEQCommand,  "BEQ",  False)
    BPL  = (               r'10000000'   + _OFFSET_PATTERN,              BPLCommand,  "BPL",  False)
    BMI  = (               r'10000001'   + _OFFSET_PATTERN,              BMICommand,  "BMI",  False)
    BVC  = (               r'10000100'   + _OFFSET_PATTERN,              BVCCommand,  "BVC",  False)
    BVS  = (               r'10000101'   + _OFFSET_PATTERN,              BVSCommand,  "BVS",  False)
    BCC  = (               r'10000110'   + _OFFSET_PATTERN,              BCCCommand,  "BCC",  False)
    BCS  = (               r'10000111'   + _OFFSET_PATTERN,              BCSCommand,  "BCS",  False)
    BGE  = (               r'00000100'   + _OFFSET_PATTERN,              BGECommand,  "BGE",  False)
    BLT  = (               r'00000101'   + _OFFSET_PATTERN,              BLTCommand,  "BLT",  False)
    BGT  = (               r'00000110'   + _OFFSET_PATTERN,              BGTCommand,  "BGT",  False)
    BLE  = (               r'00000111'   + _OFFSET_PATTERN,              BLECommand,  "BLE",  False)
    BHI  = (               r'10000010'   + _OFFSET_PATTERN,              BHICommand,  "BHI",  False)
    BLOS = (               r'10000011'   + _OFFSET_PATTERN,              BLOSCommand, "BLOS", False)
    JMP  = (               r'0000000001' + _DEST_PATTERN,                JMPCommand,  "JMP",  False)
    JSR  = (               r'0000100'    + _REG_PATTERN + _DEST_PATTERN, JSRCommand,  "JSR",  False)
    RTS  = (               r'0000000010000' + _REG_PATTERN,              RTSCommand,  "RTS",  False)

    #BHIS = (               r'10000110'   + _OFFSET_PATTERN,              BHISCommand, "BHIS", False)
    #BLO  = (               r'10000111'   + _OFFSET_PATTERN,              BLOCommand,  "BLO",  False)
    #MUL  = (               r'0111000'    + _REG_PATTERN + _SRC_PATTERN,  MULCommand,  "MUL",  True)
    #DIV  = (               r'0111001'    + _REG_PATTERN + _SRC_PATTERN,  DIVCommand,  "DIV",  True)
    #ASH  = (               r'0111010'    + _REG_PATTERN + _SRC_PATTERN,  ASHCommand,  "ASH",  True)
    #ASHC = (               r'0111011'    + _REG_PATTERN + _SRC_PATTERN,  ASHCCommand, "ASHC", True)

    def __init__(self, pattern, klass, representation: str, dest_stored: bool):
        self._pattern = re.compile(pattern=pattern)
        self._klass = klass
        self._string_representation = representation
        self._dest_stored = dest_stored

    @property
    def pattern(self):
        return self._pattern

    @property
    def klass(self):
        return self._klass

    @property
    def string_representation(self):
        return self._string_representation

    @property
    def dest_stored(self):
        return self._dest_stored


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
                return command_instance.klass(matcher=matcher, program_status=program_status,
                                              type_=command_instance, on_byte=on_byte)

        raise UnknownCommand(code=code)

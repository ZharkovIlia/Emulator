import enum
import re

from src.backend.utils.exceptions import CommandWrongNumberBits, UnknownCommand, OperandWrongNumberOfBits, \
    OperandWrongPCMode, CommandJMPToRegister, CommandException
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
    ALU                     = enum.auto()


class Operand:
    def __init__(self, reg: str, mode: str):
        if len(reg) != 3 or len(mode) != 3:
            raise OperandWrongNumberOfBits()

        self._reg = int(reg, 2)
        self._mode = int(mode, 2)

        if self._reg == 7 and self._mode not in (0, 2, 3, 6, 7):
            raise OperandWrongPCMode()

        self._next_instruction = None
        self._inner_register = Register()
        self._inner_address = None

        self.do_not_fetch_operand = False

    def is_pc(self) -> bool:
        return self._reg == 7

    def set_next_instruction(self, instr: bitarray):
        assert instr.length() == 16
        self._next_instruction = int(instr.to01(), 2)

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
        return (self._reg == 7 and self._mode != 0) or self._mode // 2 == 3

    @property
    def string_representation(self):
        result = ""
        if self._reg == 7:
            if self._mode == 0:
                result = "PC"
            elif self._mode // 2 == 1:
                result = "#{:o}"
            elif self._mode // 2 == 3:
                result = "{:o}(PC)"
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
                result = "{:o}" + result

            if self._mode % 2 == 1 and self._mode != 1:
                result = "@" + result

        if self.require_next_instruction and self._next_instruction is not None:
            result = result.format(self._next_instruction)
        return result

    def add_fetch(self, operations: list, size: str):
        if self._mode // 2 == 2:
            value = 1 if self._mode == 4 and size == "byte" and self._reg not in (6, 7) else 2
            operations.append({"operation": Operation.DECREMENT_REGISTER,
                               "register": self._reg,
                               "value": value})

        if self._mode // 2 == 3:
            operations.append({"operation": Operation.FETCH_NEXT_INSTRUCTION,
                               "size": "word",
                               "callback": self.set_next_instruction})

        if self._reg == 7 and self._mode // 2 == 1:
            fetch_size = size if self._mode == 2 else "word"
            operations.append({"operation": Operation.FETCH_NEXT_INSTRUCTION,
                               "size": fetch_size,
                               "callback": self._inner_register.set_byte
                               if fetch_size == "byte" else self._inner_register.set_word})

        if self._mode == 0 and self.do_not_fetch_operand:
            return

        if not (self._reg == 7 and self._mode // 2 == 1):
            fetch_size = size if self._mode == 0 else "word"
            operations.append({"operation": Operation.FETCH_REGISTER,
                               "register": self._reg,
                               "size": fetch_size,
                               "callback": self._inner_register.set_byte
                               if fetch_size == "byte" else self._inner_register.set_word})

        if self._mode == 0:
            return

        if self._mode // 2 == 1 and not self._reg == 7:
            value = 1 if self._mode == 2 and size == "byte" and self._reg not in (6, 7) else 2
            operations.append({"operation": Operation.INCREMENT_REGISTER,
                               "register": self._reg,
                               "value": value})

        if self._mode // 2 == 3:
            operations.append({"operation": Operation.EXECUTE,
                               "callback": self.add_next_instruction_to_inner_register,
                               "cycles": 1})

        if self._mode in (1, 2, 4, 6) and not (self._reg == 7 and self._mode // 2 == 1):
            operations.append({"operation": Operation.EXECUTE,
                               "callback": self.copy_inner_register_to_inner_address,
                               "cycles": 0})

        if self._mode in (1, 2, 4, 6) and self.do_not_fetch_operand:
            return

        if not (self._reg == 7 and self._mode // 2 == 1):
            fetch_size = size if self._mode in (1, 2, 4, 6) else "word"
            operations.append({"operation": Operation.FETCH_ADDRESS,
                               "address": lambda: self._inner_register.get(size="word", signed=False),
                               "size": fetch_size,
                               "callback": self._inner_register.set_byte
                               if fetch_size == "byte" else self._inner_register.set_word})

        if self._mode in (1, 2, 4, 6):
            return

        operations.append({"operation": Operation.EXECUTE,
                           "callback": self.copy_inner_register_to_inner_address,
                           "cycles": 0})

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
            assert not (self._reg == 7 and self._mode == 2)
            operations.append({"operation": Operation.STORE_ADDRESS,
                               "address": lambda: self._inner_address.get(size="word", signed=False),
                               "size": size,
                               "value": value})


class AbstractCommand:
    def __init__(self, program_status: ProgramStatus, type_, on_byte: bool, alu_cycles: int, add_decode=True):
        self._program_status = program_status
        self._cur_operation = 0
        self._operations = []

        self._string_representation = type_.string_representation + ("B" if on_byte else "")
        self._on_byte = on_byte
        self._decode = add_decode
        self._size = 'byte' if self._on_byte else 'word'
        self._src_operand: Operand = None
        self._dest_operand: Operand = None
        self._offset = None
        self._number = None
        self._type = type_
        self._alu_cycles = alu_cycles

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
    def has_offset(self):
        return self._offset is not None

    @property
    def has_number(self):
        return self._number

    @property
    def src_operand(self):
        return self._src_operand

    @property
    def dest_operand(self):
        return self._dest_operand

    @property
    def offset(self):
        return self._offset

    @property
    def number(self):
        return self._number

    @property
    def type(self):
        return self._type

    @property
    def string_representation(self):
        return self._string_representation

    @property
    def dest_stored(self):
        return self._type.dest_stored

    @property
    def num_next_instructions(self) -> int:
        num = 0
        if self.has_dest_operand and self.dest_operand.require_next_instruction:
            num += 1
        if self.has_src_operand and self.src_operand.require_next_instruction:
            num += 1
        return num

    def __iter__(self):
        self._cur_operation = 0
        return self

    def __next__(self):
        if self._cur_operation < len(self._operations):
            self._cur_operation += 1
            return self._operations[self._cur_operation - 1]
        raise StopIteration()

    def _add_decode(self):
        if self._decode:
            self._operations.append({"operation": Operation.DECODE,
                                     "callback": None})

    def _add_execute(self, callback):
        assert self._alu_cycles != 0
        self._operations.append({"operation": Operation.ALU,
                                 "callback": callback,
                                 "cycles": self._alu_cycles})

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
        self._src_operand = Operand(reg=matcher.group("srcreg"), mode=matcher.group("srcmode"))
        self._dest_operand = Operand(reg=matcher.group("destreg"), mode=matcher.group("destmode"))

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
        self._dest_operand = Operand(reg=matcher.group("destreg"), mode=matcher.group("destmode"))

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
        self._src_operand = Operand(reg=matcher.group("reg"), mode="000")
        self._dest_operand = Operand(reg=matcher.group("destreg"), mode=matcher.group("destmode"))

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
        self._matcher = matcher
        self._if_branch = False

        self._extract_offset()
        self._add_all_operations()

    def _extract_offset(self):
        self._offset = int.from_bytes(bitarray(self._matcher.group("offset"), endian='big').tobytes(),
                                      byteorder='big', signed=True)

    def _add_all_operations(self):
        self._add_decode()
        self._add_execute(self.execute)
        self._add_branch()

    def _add_branch(self):
        self._operations.append({"operation": Operation.BRANCH_IF,
                                 "if": lambda: self._if_branch,
                                 "offset": self._offset * 2})

    def execute(self):
        raise NotImplementedError()


class JumpCommand(AbstractCommand):
    def __init__(self, **kwargs):
        super(JumpCommand, self).__init__(**kwargs)


class MULCommand(AbstractCommand):
    def __init__(self, matcher, **kwargs):
        super(MULCommand, self).__init__(**kwargs)
        self._dest_operand = Operand(reg=matcher.group("reg"), mode="000")
        self._src_operand = Operand(reg=matcher.group("srcreg"), mode=matcher.group("srcmode"))

        self._dest_reg = int(matcher.group("reg"), 2)
        if self._dest_reg in (6, 7):
            raise CommandException(what="Cannot perform multiplication on SP or PC as a destination")
        if self._dest_reg % 2 == 0:
            self._additional_reg = Register()
        self._add_all_operations()

    def execute(self):
        value_src = self.src_operand.inner_register.get(size="word", signed=True)
        value_dest = self.dest_operand.inner_register.get(size="word", signed=True)
        tmp = value_dest * value_src
        self.program_status.set(bit="N", value=tmp < 0)
        self.program_status.set(bit="Z", value=tmp == 0)
        self.program_status.set(bit="V", value=False)
        if tmp < Register.BOUND_PROPERTIES[("word", True)][0] or tmp > Register.BOUND_PROPERTIES[("word", True)][1]:
            self.program_status.set(bit="C", value=True)

        bitarr = bitarray(endian='big')
        bitarr.frombytes(tmp.to_bytes(4, byteorder='big', signed=True))
        self.dest_operand.inner_register.set_word(value=bitarr[16:32])
        if self._dest_reg % 2 == 0:
            self._additional_reg.set_word(value=bitarr[0:16])

    def _add_all_operations(self):
        self._add_decode()
        self._add_fetch_operands(size="word")
        self._add_execute(self.execute)
        self._add_store_operands(size="word")

    def _add_store_operands(self, size: str):
        self._dest_operand.add_store(operations=self._operations, size="word")
        if self._dest_reg % 2 == 0:
            self._operations.append({"operation": Operation.STORE_REGISTER,
                                     "register": self._dest_reg + 1,
                                     "size": "word",
                                     "value": self._additional_reg.word})


class JMPCommand(JumpCommand):
    def __init__(self, matcher, **kwargs):
        super(JMPCommand, self).__init__(**kwargs)
        dest_reg = matcher.group("destreg")
        dest_mode = matcher.group("destmode")
        if dest_mode == "000":
            raise CommandJMPToRegister()
        self._dest_operand = Operand(reg=dest_reg, mode=dest_mode)
        self._dest_operand.do_not_fetch_operand = True

        self._add_decode()
        self._add_fetch_operands(size="word")
        self._add_jump()

    def _add_jump(self):
        self._operations.append({"operation": Operation.STORE_REGISTER,
                                 "register": 7,
                                 "size": "word",
                                 "value": lambda: self.dest_operand.inner_register.word()})


class JSRCommand(JumpCommand):
    def __init__(self, matcher, **kwargs):
        super(JSRCommand, self).__init__(**kwargs)

        dest_reg = matcher.group("destreg")
        dest_mode = matcher.group("destmode")
        self._src_reg = matcher.group("reg")
        if dest_mode == "000":
            raise CommandJMPToRegister()
        if len(self._src_reg) != 3:
            raise OperandWrongNumberOfBits()

        self._dest_operand = Operand(reg=dest_reg, mode=dest_mode)
        self._dest_operand.do_not_fetch_operand = True

        self._add_decode()
        self._add_fetch_operands(size="word")
        self._add_push_onto_stack()
        self._add_mov_pc_to_reg()
        self._add_jump()

    def _add_push_onto_stack(self):
        self._subcommand = Commands.get_command_by_code(code=bitarray("0001000" + self._src_reg + "100110",
                                                                      endian='big'),
                                                        program_status=ProgramStatus(), add_decode=False)

        self._src_operand = self._subcommand.src_operand
        self._operations.extend(self._subcommand._operations)

    def _add_mov_pc_to_reg(self):
        tmp_subcommand = Commands.get_command_by_code(code=bitarray("0001000111000" + self._src_reg,
                                                                    endian="big"),
                                                      program_status=ProgramStatus(), add_decode=False)

        self._operations.extend(tmp_subcommand._operations)

    def _add_jump(self):
        self._operations.append({"operation": Operation.STORE_REGISTER,
                                 "register": 7,
                                 "size": "word",
                                 "value": lambda: self.dest_operand.inner_register.word()})


class RTSCommand(JumpCommand):
    def __init__(self, matcher, **kwargs):
        super(RTSCommand, self).__init__(**kwargs)

        self._src_reg = matcher.group("reg")
        if len(self._src_reg) != 3:
            raise OperandWrongNumberOfBits()

        self._src_operand = Operand(reg=self._src_reg, mode="000")

        self._add_decode()
        self._add_fetch_operands(size="word")
        self._add_jump()
        self._add_pop_from_stack()

    def _add_pop_from_stack(self):
        self._subcommand = Commands.get_command_by_code(code=bitarray("0001"  + "010110000" + self._src_reg,
                                                                      endian='big'),
                                                        program_status=ProgramStatus(), add_decode=False)

        self._operations.extend(self._subcommand._operations)

    def _add_jump(self):
        self._operations.append({"operation": Operation.STORE_REGISTER,
                                 "register": 7,
                                 "size": "word",
                                 "value": lambda: self.src_operand.inner_register.word()})


class MARKCommand(JumpCommand):
    def __init__(self, matcher, **kwargs):
        super(MARKCommand, self).__init__(**kwargs)

        tmp = bitarray("00", endian='big')
        tmp.extend(bitarray(matcher.group("number"), endian='big'))
        self._number = int.from_bytes(tmp.tobytes(), byteorder='big', signed=False)

        self._add_decode()
        self._add_all_operations()

    def _add_all_operations(self):
        self._tmp_sp = Register()
        self._tmp_r5 = Register()
        self._inner_register = Register()

        self._operations.append({"operation": Operation.FETCH_REGISTER,
                                 "register": 6,
                                 "size": "word",
                                 "callback": self._tmp_sp.set_word})

        self._operations.append({"operation": Operation.EXECUTE,
                                 "callback": lambda: self._tmp_sp.inc(value=self._number * 2)})

        self._operations.append({"operation": Operation.FETCH_REGISTER,
                                 "register": 5,
                                 "size": "word",
                                 "callback": self._tmp_r5.set_word})

        self._operations.append({"operation": Operation.FETCH_ADDRESS,
                                 "address": lambda: self._tmp_sp.get(size="word", signed=False),
                                 "size": "word",
                                 "callback": self._inner_register.set_word})

        self._operations.append({"operation": Operation.EXECUTE,
                                 "callback": lambda: self._tmp_sp.inc(value=2)})

        self._operations.append({"operation": Operation.STORE_REGISTER,
                                 "register": 6,
                                 "size": "word",
                                 "value": lambda: self._tmp_sp.word()})

        self._operations.append({"operation": Operation.STORE_REGISTER,
                                 "register": 5,
                                 "size": "word",
                                 "value": lambda: self._inner_register.word()})

        self._add_jump()

    def _add_jump(self):
        self._operations.append({"operation": Operation.STORE_REGISTER,
                                 "register": 7,
                                 "size": "word",
                                 "value": lambda: self._tmp_r5.word()})


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
    def __init__(self, alu_cycles, on_byte, **kwargs):
        if on_byte:
            alu_cycles += 1
        super(ASRCommand, self).__init__(alu_cycles=alu_cycles, on_byte=on_byte, **kwargs)

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
    def __init__(self, alu_cycles, on_byte, **kwargs):
        if on_byte:
            alu_cycles += 1
        super(RORCommand, self).__init__(alu_cycles=alu_cycles, on_byte=on_byte, **kwargs)

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
    def __init__(self, alu_cycles, on_byte, **kwargs):
        if on_byte:
            alu_cycles += 3
        super(MOVCommand, self).__init__(alu_cycles=alu_cycles, on_byte=on_byte, **kwargs)

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
        value_src = self.src_operand.inner_register.get(size=self.size, signed=False)
        value_dest = self.dest_operand.inner_register.get(size=self.size, signed=False)
        max_signed = Register.BOUND_PROPERTIES[(self.size, True)][1]

        tmp = self.dest_operand.inner_register.byte() if self.on_byte else self.dest_operand.inner_register.word()
        tmp.invert()
        tmp = value_src + int(tmp.to01(), 2) + 1

        self.program_status.set(bit="C", value=not (tmp > Register.BOUND_PROPERTIES[(self.size, False)][1]))
        tmp %= (Register.BOUND_PROPERTIES[(self.size, False)][1] + 1)
        self.program_status.set(bit="V", value=value_dest ^ value_src > max_signed
                                and not value_dest ^ tmp > max_signed)
        self.program_status.set(bit="N", value=tmp > max_signed)
        self.program_status.set(bit="Z", value=tmp == 0)


class ADDCommand(DoubleOperandCommand):
    def __init__(self, **kwargs):
        super(ADDCommand, self).__init__(**kwargs)

    def execute(self):
        value_src = self.src_operand.inner_register.get(size="word", signed=False)
        value_dest = self.dest_operand.inner_register.get(size="word", signed=False)
        max_signed_word = Register.BOUND_PROPERTIES[("word", True)][1]
        tmp = value_dest + value_src
        self.program_status.set(bit="C", value=(tmp > Register.BOUND_PROPERTIES[("word", False)][1]))
        tmp %= (Register.BOUND_PROPERTIES[("word", False)][1] + 1)
        self.program_status.set(bit="V", value=not value_dest ^ value_src > max_signed_word
                                and value_src ^ tmp > max_signed_word)
        self.program_status.set(bit="N", value=tmp > max_signed_word)
        self.program_status.set(bit="Z", value=tmp == 0)
        self.dest_operand.inner_register.set(size="word", signed=False, value=tmp)


class SUBCommand(DoubleOperandCommand):
    def __init__(self, **kwargs):
        super(SUBCommand, self).__init__(**kwargs)

    def execute(self):
        value_src = self.src_operand.inner_register.get(size="word", signed=False)
        value_dest = self.dest_operand.inner_register.get(size="word", signed=False)
        max_signed_word = Register.BOUND_PROPERTIES[("word", True)][1]

        tmp = self.src_operand.inner_register.word()
        tmp.invert()
        tmp = value_dest + int(tmp.to01(), 2) + 1

        self.program_status.set(bit="C", value=not (tmp > Register.BOUND_PROPERTIES[("word", False)][1]))
        tmp %= (Register.BOUND_PROPERTIES[("word", False)][1] + 1)
        self.program_status.set(bit="V", value=value_dest ^ value_src > max_signed_word
                                and not value_src ^ tmp > max_signed_word)
        self.program_status.set(bit="N", value=tmp > max_signed_word)
        self.program_status.set(bit="Z", value=tmp == 0)
        self.dest_operand.inner_register.set(size="word", signed=False, value=tmp)


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


class SOBCommand(BranchCommand):
    def __init__(self, **kwargs):
        super(SOBCommand, self).__init__(**kwargs)

    def execute(self):
        self._if_branch = self._inner_ps.get(bit='Z') is False

    def _extract_offset(self):
        tmp = bitarray("00", endian='big')
        tmp.extend(bitarray(self._matcher.group("offset"), endian='big'))
        self._offset = int.from_bytes(tmp.tobytes(), byteorder='big', signed=False)
        self._src_reg = bitarray(self._matcher.group("reg"), endian='big')

    def _add_all_operations(self):
        self._add_decode()
        self._add_decrement()
        self._add_execute(self.execute)
        self._add_branch()

    def _add_decrement(self):
        self._inner_ps = ProgramStatus()
        self._subcommand = Commands.get_command_by_code(code=bitarray("0000101011000" + self._src_reg.to01(),
                                                                      endian='big'),
                                                        program_status=self._inner_ps, add_decode=False)

        self._dest_operand = self._subcommand.dest_operand
        self._operations.extend(self._subcommand._operations)

    def _add_branch(self):
        self._operations.append({"operation": Operation.BRANCH_IF,
                                 "if": lambda: self._if_branch,
                                 "offset": -2 * self._offset})


_COMM_PATTERN = r'(?P<{}>[01]{})'
_MSB_PATTERN = r'(?P<msb>0|1)'
_SRC_PATTERN = _COMM_PATTERN.format("srcmode", "{3}") + _COMM_PATTERN.format("srcreg", "{3}")
_DEST_PATTERN = _COMM_PATTERN.format("destmode", "{3}") + _COMM_PATTERN.format("destreg", "{3}")
_REG_PATTERN = _COMM_PATTERN.format("reg", "{3}")
_OFFSET_PATTERN = _COMM_PATTERN.format("offset", "{8}")
_NUMBER_PATTERN = _COMM_PATTERN.format("number", "{6}")
_SOB_OFFSET_PTRN = _COMM_PATTERN.format("offset", "{6}")


class InstanceCommand(enum.Enum):
    CLR  = (_MSB_PATTERN + r'000101000'  + _DEST_PATTERN,                CLRCommand,  "CLR",  True,  4)
    COM  = (_MSB_PATTERN + r'000101001'  + _DEST_PATTERN,                COMCommand,  "COM",  True,  4)
    INC  = (_MSB_PATTERN + r'000101010'  + _DEST_PATTERN,                INCCommand,  "INC",  True,  4)
    DEC  = (_MSB_PATTERN + r'000101011'  + _DEST_PATTERN,                DECCommand,  "DEC",  True,  4)
    NEG  = (_MSB_PATTERN + r'000101100'  + _DEST_PATTERN,                NEGCommand,  "NEG",  True,  4)
    TST  = (_MSB_PATTERN + r'000101111'  + _DEST_PATTERN,                TSTCommand,  "TST",  False, 4)
    ASR  = (_MSB_PATTERN + r'000110010'  + _DEST_PATTERN,                ASRCommand,  "ASR",  True,  5)
    ASL  = (_MSB_PATTERN + r'000110011'  + _DEST_PATTERN,                ASLCommand,  "ASL",  True,  4)
    ROR  = (_MSB_PATTERN + r'000110000'  + _DEST_PATTERN,                RORCommand,  "ROR",  True,  5)
    ROL  = (_MSB_PATTERN + r'000110001'  + _DEST_PATTERN,                ROLCommand,  "ROL",  True,  4)
    SWAB = (               r'0000000011' + _DEST_PATTERN,                SWABCommand, "SWAB", True,  4)
    ADC  = (_MSB_PATTERN + r'000101101'  + _DEST_PATTERN,                ADCCommand,  "ADC",  True,  4)
    SBC  = (_MSB_PATTERN + r'000101110'  + _DEST_PATTERN,                SBCCommand,  "SBC",  True,  4)
    SXT  = (               r'0000110111' + _DEST_PATTERN,                SXTCommand,  "SXT",  True,  4)
    MOV  = (_MSB_PATTERN + r'001'        + _SRC_PATTERN + _DEST_PATTERN, MOVCommand,  "MOV",  True,  3)
    CMP  = (_MSB_PATTERN + r'010'        + _SRC_PATTERN + _DEST_PATTERN, CMPCommand,  "CMP",  False, 3)
    ADD  = (               r'0110'       + _SRC_PATTERN + _DEST_PATTERN, ADDCommand,  "ADD",  True,  3)
    SUB  = (               r'1110'       + _SRC_PATTERN + _DEST_PATTERN, SUBCommand,  "SUB",  True,  3)
    BIT  = (_MSB_PATTERN + r'011'        + _SRC_PATTERN + _DEST_PATTERN, BITCommand,  "BIT",  False, 3)
    BIC  = (_MSB_PATTERN + r'100'        + _SRC_PATTERN + _DEST_PATTERN, BICCommand,  "BIC",  True,  3)
    BIS  = (_MSB_PATTERN + r'101'        + _SRC_PATTERN + _DEST_PATTERN, BISCommand,  "BIS",  True,  3)
    MUL  = (               r'0111000'    + _SRC_PATTERN + _REG_PATTERN,  MULCommand,  "MUL",  True,  40)
    XOR  = (               r'0111100'    + _REG_PATTERN + _DEST_PATTERN, XORCommand,  "XOR",  True,  3)
    BR   = (               r'00000001'   + _OFFSET_PATTERN,              BRCommand,   "BR",   False, 7)
    BNE  = (               r'00000010'   + _OFFSET_PATTERN,              BNECommand,  "BNE",  False, 7)
    BEQ  = (               r'00000011'   + _OFFSET_PATTERN,              BEQCommand,  "BEQ",  False, 7)
    BPL  = (               r'10000000'   + _OFFSET_PATTERN,              BPLCommand,  "BPL",  False, 7)
    BMI  = (               r'10000001'   + _OFFSET_PATTERN,              BMICommand,  "BMI",  False, 7)
    BVC  = (               r'10000100'   + _OFFSET_PATTERN,              BVCCommand,  "BVC",  False, 7)
    BVS  = (               r'10000101'   + _OFFSET_PATTERN,              BVSCommand,  "BVS",  False, 7)
    BCC  = (               r'10000110'   + _OFFSET_PATTERN,              BCCCommand,  "BCC",  False, 7)
    BCS  = (               r'10000111'   + _OFFSET_PATTERN,              BCSCommand,  "BCS",  False, 7)
    BGE  = (               r'00000100'   + _OFFSET_PATTERN,              BGECommand,  "BGE",  False, 7)
    BLT  = (               r'00000101'   + _OFFSET_PATTERN,              BLTCommand,  "BLT",  False, 7)
    BGT  = (               r'00000110'   + _OFFSET_PATTERN,              BGTCommand,  "BGT",  False, 7)
    BLE  = (               r'00000111'   + _OFFSET_PATTERN,              BLECommand,  "BLE",  False, 7)
    BHI  = (               r'10000010'   + _OFFSET_PATTERN,              BHICommand,  "BHI",  False, 7)
    BLOS = (               r'10000011'   + _OFFSET_PATTERN,              BLOSCommand, "BLOS", False, 7)
    JMP  = (               r'0000000001' + _DEST_PATTERN,                JMPCommand,  "JMP",  False, 0)
    JSR  = (               r'0000100'    + _REG_PATTERN + _DEST_PATTERN, JSRCommand,  "JSR",  False, 0)
    RTS  = (               r'0000000010000' + _REG_PATTERN,              RTSCommand,  "RTS",  False, 0)
    MARK = (               r'0000110100' + _NUMBER_PATTERN,              MARKCommand, "MARK", False, 0)
    SOB  = (               r'0111111' + _REG_PATTERN + _SOB_OFFSET_PTRN, SOBCommand,  "SOB",  False, 7)

    #BHIS = (               r'10000110'   + _OFFSET_PATTERN,              BHISCommand, "BHIS", False)
    #BLO  = (               r'10000111'   + _OFFSET_PATTERN,              BLOCommand,  "BLO",  False)
    #DIV  = (               r'0111001'    + _REG_PATTERN + _SRC_PATTERN,  DIVCommand,  "DIV",  True)
    #ASH  = (               r'0111010'    + _REG_PATTERN + _SRC_PATTERN,  ASHCommand,  "ASH",  True)
    #ASHC = (               r'0111011'    + _REG_PATTERN + _SRC_PATTERN,  ASHCCommand, "ASHC", True)

    def __init__(self, pattern, klass, representation: str, dest_stored: bool, alu_cycles):
        self._pattern = re.compile(pattern=pattern)
        self._klass = klass
        self._string_representation = representation
        self._dest_stored = dest_stored
        self._alu_cycles = alu_cycles

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

    @property
    def alu_cycles(self):
        return self._alu_cycles


class Commands:
    @staticmethod
    def get_command_by_code(code: bitarray, program_status: ProgramStatus, add_decode=True) -> AbstractCommand:
        if code.length() != 16:
            raise CommandWrongNumberBits()

        for command_instance in list(InstanceCommand):
            matcher = command_instance.pattern.match(code.to01())
            if matcher is not None:
                on_byte = False
                if "msb" in matcher.groupdict():
                    on_byte = (matcher.group("msb") == "1")
                return command_instance.klass(matcher=matcher, program_status=program_status, type_=command_instance,
                                              on_byte=on_byte, add_decode=add_decode,
                                              alu_cycles=command_instance.alu_cycles)

        raise UnknownCommand(code=code)

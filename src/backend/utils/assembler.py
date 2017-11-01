import enum
import re

from bitarray import bitarray


_WHITESPACES_PATTERN = r'\s*'
_REQUIRED_WHITESPACES_PATTERN = r'\s+'
_MSB_PATTERN = r'(?P<msb>B?)'
_OPERAND_PATTERN = r'(?P<{}>(?:\w|\(|\)|\#|\@|\-|\+)+)'

_REG_PATTERN = r'R(?P<{}>[0-7])'
_NUMBER_PATTERN = r'(?P<{}>\-?\d+)'
_UNSIGNED_NUMBER_PATTERN = r'(?P<{}>\d+)'
_MODE_0_PATTERN = _REG_PATTERN
_MODE_1_PATTERN = r'\(' + _REG_PATTERN + '\)'
_MODE_2_PATTERN = _MODE_1_PATTERN + r'\+'
_MODE_3_PATTERN = r'\@' + _MODE_2_PATTERN
_MODE_4_PATTERN = r'\-' + _MODE_1_PATTERN
_MODE_5_PATTERN = r'\@' + _MODE_4_PATTERN
_MODE_6_PATTERN = _NUMBER_PATTERN + _MODE_1_PATTERN
_MODE_7_PATTERN = r'\@' + _MODE_6_PATTERN

_IMMEDIATE_PATTERN = r'\#' + _NUMBER_PATTERN
_ABSOLUTE_PATTERN = r'\@' + _IMMEDIATE_PATTERN


class AssemblerException(Exception):
    def __init__(self, what: str):
        self.what = what

    def __str__(self):
        return self.what


class OperandMode:
    def get_bits(self, operand: str, has_mode: bool, instr: list):
        raise NotImplementedError()


class _OPERAND_MODE_0(OperandMode):
    def __init__(self):
        self.pattern = re.compile((r'^' + _MODE_0_PATTERN + r'$').format("regnum"))
        self.mode = "000"

    def get_bits(self, operand: str, has_mode: bool, instr: list):
        matcher = self.pattern.match(operand)
        if matcher is None:
            return None
        result = ""
        if has_mode:
            result = result + self.mode
        return "{}{:03b}".format(result, int(matcher.group("regnum")))


class _OPERAND_MODE_1(OperandMode):
    def __init__(self):
        self.pattern = re.compile((r'^' + _MODE_1_PATTERN + r'$').format("regnum"))
        self.mode = "001"

    def get_bits(self, operand: str, has_mode: bool, instr: list):
        if not has_mode:
            return None
        matcher = self.pattern.match(operand)
        if matcher is None:
            return None
        result = self.mode
        return "{}{:03b}".format(result, int(matcher.group("regnum")))


class _OPERAND_MODE_2(_OPERAND_MODE_1):
    def __init__(self):
        super(_OPERAND_MODE_2, self).__init__()
        self.pattern = re.compile((r'^' + _MODE_2_PATTERN + r'$').format("regnum"))
        self.mode = "010"


class _OPERAND_MODE_3(_OPERAND_MODE_1):
    def __init__(self):
        super(_OPERAND_MODE_3, self).__init__()
        self.pattern = re.compile((r'^' + _MODE_3_PATTERN + r'$').format("regnum"))
        self.mode = "011"


class _OPERAND_MODE_4(_OPERAND_MODE_1):
    def __init__(self):
        super(_OPERAND_MODE_4, self).__init__()
        self.pattern = re.compile((r'^' + _MODE_4_PATTERN + r'$').format("regnum"))
        self.mode = "100"


class _OPERAND_MODE_5(_OPERAND_MODE_1):
    def __init__(self):
        super(_OPERAND_MODE_5, self).__init__()
        self.pattern = re.compile((r'^' + _MODE_5_PATTERN + r'$').format("regnum"))
        self.mode = "101"


class _OPERAND_MODE_6(OperandMode):
    def __init__(self):
        self.pattern = re.compile((r'^' + _MODE_6_PATTERN + r'$').format("number", "regnum"))
        self.mode = "110"

    def get_bits(self, operand: str, has_mode: bool, instr: list):
        matcher = self.pattern.match(operand)
        if matcher is None:
            return None
        result = ""
        if has_mode:
            result = result + self.mode
        tmp = Assembler.negative_to_positive(matcher.group("number"), 2)
        instr.append(bitarray("{:016b}".format(int(tmp, 8)), endian='big'))
        return "{}{:03b}".format(result, int(matcher.group("regnum")))


class _OPERAND_MODE_7(_OPERAND_MODE_6):
    def __init__(self):
        super(_OPERAND_MODE_7, self).__init__()
        self.pattern = re.compile((r'^' + _MODE_7_PATTERN + r'$').format("number", "regnum"))
        self.mode = "111"


class _OPERAND_IMMEDIATE(OperandMode):
    def __init__(self):
        self.pattern = re.compile((r'^' + _IMMEDIATE_PATTERN + r'$').format("number"))
        self.mode = "010"
        self.reg = "111"

    def get_bits(self, string: str, has_mode: bool, instr: list):
        matcher = self.pattern.match(string)
        if matcher is None:
            return None
        tmp = Assembler.negative_to_positive(matcher.group("number"), 2)
        instr.append(bitarray("{:016b}".format(int(tmp, 8)), endian='big'))
        return self.mode + self.reg


class _OPERAND_ABSOLUTE(_OPERAND_IMMEDIATE):
    def __init__(self):
        super(_OPERAND_ABSOLUTE, self).__init__()
        self.pattern = re.compile((r'^' + _ABSOLUTE_PATTERN + r'$').format("number"))
        self.mode = "011"


class OperandPatterns(enum.Enum):
    MODE_0 = _OPERAND_MODE_0()
    MODE_1 = _OPERAND_MODE_1()
    MODE_2 = _OPERAND_MODE_2()
    MODE_3 = _OPERAND_MODE_3()
    MODE_4 = _OPERAND_MODE_4()
    MODE_5 = _OPERAND_MODE_5()
    MODE_6 = _OPERAND_MODE_6()
    MODE_7 = _OPERAND_MODE_7()
    MODE_IMMEDIATE = _OPERAND_IMMEDIATE()
    MODE_ABSOLUTE = _OPERAND_ABSOLUTE()

    def __init__(self, operand_mode: OperandMode):
        self._opmode = operand_mode

    def get_bits(self, string: str, has_mode: bool, instr: list) -> str:
        return self._opmode.get_bits(string, has_mode, instr)


class InstructionPartType(enum.Enum):
    NAME = enum.auto()
    MSB = enum.auto()
    SRC = enum.auto()
    DEST = enum.auto()
    REG = enum.auto()
    NUMBER = enum.auto()
    WHITESPACE = enum.auto()
    OPCODE = enum.auto()
    COMMA = enum.auto()
    OFFSET = enum.auto()
    SOB_OFFSET = enum.auto()
    MARK_NUMBER = enum.auto()


class InstructionPart:
    def __init__(self, pattern: str, pattern_type: InstructionPartType):
        self.pattern = pattern
        self.pattern_type = pattern_type


def _SINGLE_OPERAND_INSTRUCTION(name: str, has_msb: bool, has_dest_mode=True) -> list:
    result = [InstructionPart(_WHITESPACES_PATTERN, InstructionPartType.WHITESPACE),
              InstructionPart(name, InstructionPartType.NAME)]
    if has_msb:
        result.append(InstructionPart(_MSB_PATTERN, InstructionPartType.MSB))

    result.extend([InstructionPart(_REQUIRED_WHITESPACES_PATTERN, InstructionPartType.WHITESPACE),
                   InstructionPart("", InstructionPartType.OPCODE)])

    if has_dest_mode:
        result.append(InstructionPart(_OPERAND_PATTERN.format("dest"), InstructionPartType.DEST))
    else:
        result.append(InstructionPart(_OPERAND_PATTERN.format("reg"), InstructionPartType.REG))

    result.append(InstructionPart(_WHITESPACES_PATTERN, InstructionPartType.WHITESPACE))
    return result


def _DOUBLE_OPERAND_INSTRUCTION(name: str, has_msb: bool, has_src_mode=True, has_dest_mode=True) -> list:
    result = [InstructionPart(_WHITESPACES_PATTERN, InstructionPartType.WHITESPACE),
              InstructionPart(name, InstructionPartType.NAME)]
    if has_msb:
        result.append(InstructionPart(_MSB_PATTERN, InstructionPartType.MSB))

    result.extend([InstructionPart(_REQUIRED_WHITESPACES_PATTERN, InstructionPartType.WHITESPACE),
                   InstructionPart("", InstructionPartType.OPCODE)])
    if has_src_mode:
        result.append(InstructionPart(_OPERAND_PATTERN.format("src"), InstructionPartType.SRC))
    else:
        result.append(InstructionPart(_OPERAND_PATTERN.format("reg"), InstructionPartType.REG))
    result.extend([InstructionPart(_WHITESPACES_PATTERN, InstructionPartType.WHITESPACE),
                   InstructionPart(r',', InstructionPartType.COMMA),
                   InstructionPart(_WHITESPACES_PATTERN, InstructionPartType.WHITESPACE)])

    if has_dest_mode:
        result.append(InstructionPart(_OPERAND_PATTERN.format("dest"), InstructionPartType.DEST))
    else:
        result.append(InstructionPart(_OPERAND_PATTERN.format("reg"), InstructionPartType.REG))

    result.append(InstructionPart(_WHITESPACES_PATTERN, InstructionPartType.WHITESPACE))
    return result


def _BRANCH_INSTRUCTION(name: str) -> list:
    result = [InstructionPart(_WHITESPACES_PATTERN, InstructionPartType.WHITESPACE),
              InstructionPart(name, InstructionPartType.NAME),
              InstructionPart(_REQUIRED_WHITESPACES_PATTERN, InstructionPartType.WHITESPACE),
              InstructionPart("", InstructionPartType.OPCODE),
              InstructionPart(_NUMBER_PATTERN.format("offset"), InstructionPartType.OFFSET),
              InstructionPart(_WHITESPACES_PATTERN, InstructionPartType.WHITESPACE)]

    return result


def _MARK_INSTRUCTION() -> list:
    result = [InstructionPart(_WHITESPACES_PATTERN, InstructionPartType.WHITESPACE),
              InstructionPart("MARK", InstructionPartType.NAME),
              InstructionPart(_REQUIRED_WHITESPACES_PATTERN, InstructionPartType.WHITESPACE),
              InstructionPart("", InstructionPartType.OPCODE),
              InstructionPart(_UNSIGNED_NUMBER_PATTERN.format("number"), InstructionPartType.MARK_NUMBER),
              InstructionPart(_WHITESPACES_PATTERN, InstructionPartType.WHITESPACE)]

    return result


def _SOB_INSTRUCTION() -> list:
    result = [InstructionPart(_WHITESPACES_PATTERN, InstructionPartType.WHITESPACE),
              InstructionPart("SOB", InstructionPartType.NAME),
              InstructionPart(_REQUIRED_WHITESPACES_PATTERN, InstructionPartType.WHITESPACE),
              InstructionPart("", InstructionPartType.OPCODE),
              InstructionPart(_OPERAND_PATTERN.format("reg"), InstructionPartType.REG),
              InstructionPart(_WHITESPACES_PATTERN, InstructionPartType.WHITESPACE),
              InstructionPart(r',', InstructionPartType.COMMA),
              InstructionPart(_WHITESPACES_PATTERN, InstructionPartType.WHITESPACE),
              InstructionPart(_UNSIGNED_NUMBER_PATTERN.format("offset"), InstructionPartType.SOB_OFFSET),
              InstructionPart(_WHITESPACES_PATTERN, InstructionPartType.WHITESPACE)]

    return result


class InstructionPatterns(enum.Enum):
    CLR  = (_SINGLE_OPERAND_INSTRUCTION("CLR", True),                       '000101000')
    COM  = (_SINGLE_OPERAND_INSTRUCTION("COM", True),                       '000101001')
    INC  = (_SINGLE_OPERAND_INSTRUCTION("INC", True),                       '000101010')
    DEC  = (_SINGLE_OPERAND_INSTRUCTION("DEC", True),                       '000101011')
    NEG  = (_SINGLE_OPERAND_INSTRUCTION("NEG", True),                       '000101100')
    TST  = (_SINGLE_OPERAND_INSTRUCTION("TST", True),                       '000101111')
    ASR  = (_SINGLE_OPERAND_INSTRUCTION("ASR", True),                       '000110010')
    ASL  = (_SINGLE_OPERAND_INSTRUCTION("ASL", True),                       '000110011')
    ROR  = (_SINGLE_OPERAND_INSTRUCTION("ROR", True),                       '000110000')
    ROL  = (_SINGLE_OPERAND_INSTRUCTION("ROL", True),                       '000110001')
    SWAB = (_SINGLE_OPERAND_INSTRUCTION("SWAB", False),                     '0000000011')
    ADC  = (_SINGLE_OPERAND_INSTRUCTION("ADC", True),                       '000101101')
    SBC  = (_SINGLE_OPERAND_INSTRUCTION("SBC", True),                       '000101110')
    SXT  = (_SINGLE_OPERAND_INSTRUCTION("SXT", False),                      '0000110111')
    JMP  = (_SINGLE_OPERAND_INSTRUCTION("JMP", False),                      '0000000001')
    RTS  = (_SINGLE_OPERAND_INSTRUCTION("RTS", False, has_dest_mode=False), '0000000010000')

    MOV  = (_DOUBLE_OPERAND_INSTRUCTION("MOV", True),                       '001')
    CMP  = (_DOUBLE_OPERAND_INSTRUCTION("CMP", True),                       '010')
    ADD  = (_DOUBLE_OPERAND_INSTRUCTION("ADD", False),                      '0110')
    SUB  = (_DOUBLE_OPERAND_INSTRUCTION("SUB", False),                      '1110')
    BIT  = (_DOUBLE_OPERAND_INSTRUCTION("BIT", True),                       '011')
    BIC  = (_DOUBLE_OPERAND_INSTRUCTION("BIC", True),                       '100')
    BIS  = (_DOUBLE_OPERAND_INSTRUCTION("BIS", True),                       '101')
    MUL  = (_DOUBLE_OPERAND_INSTRUCTION("MUL", False, has_dest_mode=False), '0111000')
    XOR  = (_DOUBLE_OPERAND_INSTRUCTION("XOR", False, has_src_mode=False),  '0111100')
    JSR  = (_DOUBLE_OPERAND_INSTRUCTION("JSR", False, has_src_mode=False),  '0000100')

    BR   = (_BRANCH_INSTRUCTION("BR"),                                      '00000001')
    BNE  = (_BRANCH_INSTRUCTION("BNE"),                                     '00000010')
    BEQ  = (_BRANCH_INSTRUCTION("BEQ"),                                     '00000011')
    BPL  = (_BRANCH_INSTRUCTION("BPL"),                                     '10000000')
    BMI  = (_BRANCH_INSTRUCTION("BMI"),                                     '10000001')
    BVC  = (_BRANCH_INSTRUCTION("BVC"),                                     '10000100')
    BVS  = (_BRANCH_INSTRUCTION("BVS"),                                     '10000101')
    BCC  = (_BRANCH_INSTRUCTION("BCC"),                                     '10000110')
    BCS  = (_BRANCH_INSTRUCTION("BCS"),                                     '10000111')
    BGE  = (_BRANCH_INSTRUCTION("BGE"),                                     '00000100')
    BLT  = (_BRANCH_INSTRUCTION("BLT"),                                     '00000101')
    BGT  = (_BRANCH_INSTRUCTION("BGT"),                                     '00000110')
    BLE  = (_BRANCH_INSTRUCTION("BLE"),                                     '00000111')
    BHI  = (_BRANCH_INSTRUCTION("BHI"),                                     '10000010')
    BLOS = (_BRANCH_INSTRUCTION("BLOS"),                                    '10000011')

    MARK = (_MARK_INSTRUCTION(),                                            '0000110100')
    SOB  = (_SOB_INSTRUCTION(),                                             '0111111')

    def __init__(self, parts: list, opcode: str):
        self.opcode = opcode
        self.parts = parts
        self.pattern = re.compile(r'^' + "".join(part.pattern for part in parts) + r'$')


class Assembler:
    @staticmethod
    def assemble(lines: list):
        result = []
        for line in lines:
            line = line.strip()
            if line == "" or line.startswith('#'):
                continue

            found = False
            instruction_bits = bitarray(endian='big')
            additional_instructions = []
            for instructionPattern in list(InstructionPatterns):
                matcher = instructionPattern.pattern.match(line)
                if matcher is None:
                    continue

                found = True
                for part in instructionPattern.parts:
                    if part.pattern_type is InstructionPartType.MSB:
                        if matcher.group("msb") == "B":
                            instruction_bits.extend("1")
                        else:
                            instruction_bits.extend("0")

                    elif part.pattern_type is InstructionPartType.OPCODE:
                        instruction_bits.extend(instructionPattern.opcode)

                    elif part.pattern_type is InstructionPartType.DEST \
                            or part.pattern_type is InstructionPartType.SRC \
                            or part.pattern_type is InstructionPartType.REG:
                        group = ""
                        has_mode = True
                        if part.pattern_type is InstructionPartType.DEST:
                            group = "dest"
                        elif part.pattern_type is InstructionPartType.SRC:
                            group = "src"
                        elif part.pattern_type is InstructionPartType.REG:
                            group = "reg"
                            has_mode = False

                        operand = matcher.group(group)
                        op_bits = None
                        for mode in list(OperandPatterns):
                            bits = mode.get_bits(operand, has_mode, additional_instructions)
                            if bits is not None:
                                op_bits = bits
                                break

                        if op_bits is None:
                            raise AssemblerException(what="Unrecognized construction {} in the instruction {}"
                                                     .format(operand, line))

                        instruction_bits.extend(op_bits)

                    elif part.pattern_type is InstructionPartType.OFFSET:
                        tmp = Assembler.negative_to_positive(matcher.group("offset"), bytes_=1)
                        instruction_bits.extend("{:08b}".format(int(tmp, 8)))

                    elif part.pattern_type is InstructionPartType.SOB_OFFSET:
                        instruction_bits.extend("{:06b}".format(int(matcher.group("offset"), 8)))

                    elif part.pattern_type is InstructionPartType.MARK_NUMBER:
                        instruction_bits.extend("{:06b}".format(int(matcher.group("number"), 8)))
                    else:
                        continue

            if not found or instruction_bits.length() != 16:
                raise AssemblerException(what="Unrecognized instruction '{}'".format(line))
            for instr in additional_instructions:
                if instr.length() != 16:
                    raise AssemblerException(what="Unrecognized instruction '{}'".format(line))

            result.append(instruction_bits)
            result.extend(additional_instructions)

        return result

    @staticmethod
    def negative_to_positive(number: str, bytes_: int) -> str:
        tmp = int(number, 8)
        if tmp >= 0:
            return number
        return "{:o}".format(int.from_bytes(
            tmp.to_bytes(bytes_, byteorder='big', signed=True), byteorder='big', signed=False
        ))

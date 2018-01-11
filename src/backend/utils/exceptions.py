from bitarray import bitarray


class EmulatorException(Exception):
    def __init__(self, what: str):
        self.what = what

    def __str__(self):
        return self.what


class EmulatorOddBreakpoint(EmulatorException):
    def __init__(self):
        super(EmulatorOddBreakpoint, self).__init__("Tried to toggle breakpoint on odd address")


class EmulatorWrongAddress(EmulatorException):
    def __init__(self, address: int):
        super(EmulatorWrongAddress, self).__init__(what="Address {} is wrong".format(address))


class MemoryException(EmulatorException):
    def __init__(self, what: str):
        super(MemoryException, self).__init__(what)


class MemoryIndexOutOfBound(MemoryException):
    def __init__(self):
        super(MemoryIndexOutOfBound, self).__init__("Index out of bound")


class MemoryOddAddressing(MemoryException):
    def __init__(self):
        super(MemoryOddAddressing, self).__init__("Odd addressing error")


class MemoryWrongConfiguration(MemoryException):
    def __init__(self):
        super(MemoryWrongConfiguration, self).__init__(what="Wrong layout of memory and devices")


class CashWrongBlockException(MemoryException):
    def __init__(self):
        super(CashWrongBlockException, self).__init__(what="Cash is disabled or address to block is address of device")


class CashUnblockException(MemoryException):
    def __init__(self):
        super(CashUnblockException, self).__init__(what="Tried to unblock unblocked cash line")


class RegisterException(EmulatorException):
    def __init__(self, what: str):
        super(RegisterException, self).__init__(what)


class RegisterWrongNumberBits(RegisterException):
    def __init__(self, bits: int):
        super(RegisterWrongNumberBits, self).__init__("Number of bits isn't equal to {}".format(bits))


class RegisterOutOfBound(RegisterException):
    def __init__(self, value: int, bytes: int, signed: bool):
        tmp = "Signed" if signed else "Unsigned"
        super(RegisterOutOfBound, self).__init__("{} value {} is not placed in {} bytes".format(tmp, value, bytes))


class RegisterOddValue(RegisterException):
    def __init__(self):
        super(RegisterOddValue, self).__init__("Tried to set odd value to SP or PC")


class StackOverflow(RegisterException):
    def __init__(self, sp):
        super(StackOverflow, self).__init__(what="Stack pointer is out of bounds")
        self.sp = sp


class ProgramStatusException(EmulatorException):
    def __init__(self, what: str):
        super(ProgramStatusException, self).__init__(what)


class CommandException(EmulatorException):
    def __init__(self, what: str):
        super(CommandException, self).__init__(what=what)


class CommandWrongNumberBits(CommandException):
    def __init__(self):
        super(CommandWrongNumberBits, self).__init__(what="Number of bits doesn't equal to 16")


class UnknownCommand(CommandException):
    def __init__(self, code: bitarray):
        super(UnknownCommand, self).__init__(what="Unrecognized command with code {}".format(code.to01()))


class OperandWrongNumberOfBits(CommandException):
    def __init__(self):
        super(OperandWrongNumberOfBits, self).__init__(what="Number of bits doesn't equal to 3")


class OperandWrongPCMode(CommandException):
    def __init__(self):
        super(OperandWrongPCMode, self).__init__(what="Mode of PC operand is not in (2, 3, 6, 7)")


class CommandJMPToRegister(CommandException):
    def __init__(self):
        super(CommandJMPToRegister, self).__init__(what="Cannot jump to register")


class VideoException(EmulatorException):
    def __init__(self, what: str):
        super(VideoException, self).__init__(what)


class VideoWrongMode(VideoException):
    def __init__(self):
        super(VideoWrongMode, self).__init__(what="Wrong video mode")
class EmulatorException(Exception):
    def __init__(self, what):
        self.what = what

    def __str__(self):
        return self.what


class MemoryException(EmulatorException):
    def __init__(self, what: str):
        super(MemoryException, self).__init__(what)


class MemoryIndexOutOfBound(MemoryException):
    def __init__(self):
        super(MemoryIndexOutOfBound, self).__init__("Index out of bound")


class MemoryOddAddressing(MemoryException):
    def __init__(self):
        super(MemoryOddAddressing, self).__init__("Odd addressing error")


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


class ProgramStatusException(EmulatorException):
    def __init__(self, what: str):
        super(ProgramStatusException, self).__init__(what)


class EmulatorOddBreakpoint(EmulatorException):
    def __init__(self):
        super(EmulatorOddBreakpoint, self).__init__("Tried to toggle breakpoint on odd address")


class EmulatorBreakpointNotInROM(EmulatorException):
    def __init__(self):
        super(EmulatorBreakpointNotInROM, self).__init__("Address of breakpoint is not in ROM")
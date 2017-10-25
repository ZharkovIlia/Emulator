class EmulatorException(Exception):
    pass


class MemoryException(EmulatorException):
    def __init__(self, what: str):
        super(MemoryException, self).__init__()
        self.what = what


class MemoryIndexOutOfBound(MemoryException):
    def __init__(self):
        super(MemoryIndexOutOfBound, self).__init__("Index out of bound")


class MemoryOddAddressing(MemoryException):
    def __init__(self):
        super(MemoryOddAddressing, self).__init__("Odd addressing error")


class RegisterException(EmulatorException):
    def __init__(self, what):
        super(RegisterException, self).__init__()
        self.what = what


class RegisterWrongNumberBits(RegisterException):
    def __init__(self, bits: int):
        super(WrongNumberBits, self).__init__("Number of bits isn't equal to {}".format(bits))


class RegisterOutOfBound(RegisterException):
    def __init__(self, value: int, bytes: int, signed: bool):
        tmp = "Signed" if signed else "Unsigned"
        super(RegisterOutOfBound, self).__init__("{} value {} is not placed in {} bytes".format(tmp, value, bytes))


class RegisterOddValue(RegisterException):
    def __init__(self):
        super(RegisterOddValue, self).__init__("Tried to set odd value to SP or PC")
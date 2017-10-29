from src.backend.extra.exceptions import \
    RegisterOutOfBound, \
    RegisterWrongNumberBits, \
    RegisterException, \
    RegisterOddValue, \
    StackOverflow

from bitarray import bitarray


class Register:
    def __init__(self):
        self._data = bitarray((False for _ in range(16)), endian="big")
        self._integer_representations = {}

    def get(self, size: str, signed: bool) -> int:
        if size not in ("byte", "word"):
            raise RegisterException(what="size is not in ('byte', 'word')")

        if (size, signed) not in self._integer_representations:
            self._integer_representations[(size, signed)] \
                = int.from_bytes(Register.INTEGER_REPRESENTATION_PROPERTIES[size]["getter"](self).tobytes(),
                                 byteorder='big', signed=signed)

        return self._integer_representations[(size, signed)]

    def set(self, size: str, signed: bool, value: int):
        if size not in ("byte", "word"):
            raise RegisterException(what="size is not in ('byte', 'word')")

        min_value = Register.BOUND_PROPERTIES[(size, signed)][0]
        max_value = Register.BOUND_PROPERTIES[(size, signed)][1]
        num_bytes = Register.INTEGER_REPRESENTATION_PROPERTIES[size]["bytes"]
        if value < min_value or value > max_value:
            raise RegisterOutOfBound(value=value, bytes=num_bytes, signed=signed)

        data = bitarray(endian='big')
        data.frombytes(value.to_bytes(num_bytes, byteorder='big', signed=signed))
        Register.INTEGER_REPRESENTATION_PROPERTIES[size]["setter"](self, data)
        self._integer_representations[(size, signed)] = value

    def byte(self) -> bitarray:
        return self._data[8: 16]

    def set_byte(self, value: bitarray):
        self._reset_integer_representations()
        if value.length() != 8:
            raise RegisterWrongNumberBits(8)
        self._data[8: 16] = value

    def word(self) -> bitarray:
        return self._data[0: 16]

    def set_word(self, value: bitarray):
        self._reset_integer_representations()
        if value.length() != 16:
            raise RegisterWrongNumberBits(16)
        self._data[0: 16] = value

    def reverse(self):
        tmp = self._data[0: 8]
        self._data[0: 8] = self._data[8: 16]
        self._data[8: 16] = tmp

    def _reset_integer_representations(self):
        self._integer_representations.clear()

    INTEGER_REPRESENTATION_PROPERTIES = {"byte": {"getter": byte, "setter": set_byte, "bytes": 1},
                                         "word": {"getter": word, "setter": set_word, "bytes": 2}}

    BOUND_PROPERTIES = {("byte", True): (-128, 127),
                        ("byte", False): (0, 255),
                        ("word", True): (-32768, 32767),
                        ("word", False): (0, 65535)}

    def inc(self, value: int=1):
        self.set(size="word", signed=False, value=self.get(size="word", signed=False) + value)

    def dec(self, value: int=1):
        self.set(size="word", signed=False, value=self.get(size="word", signed=False) - value)


class OnlyEvenValueRegister(Register):
    def __init__(self):
        super(OnlyEvenValueRegister, self).__init__()

    def set_byte(self, value: bitarray):
        raise NotImplementedError()

    def set_word(self, value: bitarray):
        if value.length() > 0 and value[-1] is True:
            raise RegisterOddValue()
        super().set_word(value)

    def set(self, size: str, signed: bool, value: int):
        if size == 'byte':
            raise NotImplementedError()
        if value % 2 == 1:
            raise RegisterOddValue()
        super().set(size, signed, value)

    def get(self, size: str, signed: bool) -> int:
        if size == 'byte':
            raise NotImplementedError()
        return super().get(size, signed)

    def inc(self, value: int=2):
        if value % 2 == 1:
            raise RegisterOddValue()
        super().inc(value=value)

    def dec(self, value: int=2):
        if value % 2 == 1:
            raise RegisterOddValue()
        super().dec(value=value)

    def reverse(self):
        raise NotImplementedError()


class StackPointer(OnlyEvenValueRegister):
    def __init__(self):
        super(StackPointer, self).__init__()
        self._upper_bound = 65534
        self._lower_bound = 0

    class error_when_overflow:
        def __init__(self):
            pass

        def __call__(self, call):
            def wrapper(self, **kwargs):
                result = call(self, **kwargs)
                num_value = self.get(size="word", signed=False)
                if num_value < self._lower_bound or num_value > self._upper_bound:
                    raise StackOverflow(self)
                return result

            return wrapper

    @error_when_overflow()
    def set_word(self, value: bitarray):
        super().set_word(value)

    @error_when_overflow()
    def set(self, size: str, signed: bool, value: int):
        super().set(size, signed, value)

    @error_when_overflow()
    def dec(self, value: int = 2):
        super().dec(value)

    @error_when_overflow()
    def inc(self, value: int = 2):
        super().inc(value)

    def set_upper_bound(self, value):
        if value % 2 == 1:
            raise RegisterOddValue()
        self._upper_bound = value

    def set_lower_bound(self, value):
        if value % 2 == 1:
            raise RegisterOddValue()
        self._lower_bound = value

class ProgramCounter(OnlyEvenValueRegister):
    def __init__(self):
        super(ProgramCounter, self).__init__()

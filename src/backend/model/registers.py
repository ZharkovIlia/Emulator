from src.backend.extra.exceptions import \
    RegisterOutOfBound, \
    RegisterWrongNumberBits, \
    RegisterException, \
    RegisterOddValue

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
                = int.from_bytes(Register.INTEGER_REPRESENTATION_PROPERTIES[size]["getter"](self, shallow=True).tobytes(),
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
        Register.INTEGER_REPRESENTATION_PROPERTIES[size]["setter"](self, data, shallow=True)
        self._integer_representations[(size, signed)] = value

    def byte(self, shallow=False) -> bitarray:
        return self._data[8: 16] if shallow else self._data[8: 16].copy()

    def set_byte(self, value: bitarray, shallow=False):
        self._reset_integer_representations()
        if value.length() != 8:
            raise RegisterWrongNumberBits(8)
        self._data[8: 16] = value if shallow else value.copy()

    def word(self, shallow=False) -> bitarray:
        return self._data if shallow else self._data.copy()

    def set_word(self, value: bitarray, shallow=False):
        self._reset_integer_representations()
        if value.length() != 16:
            raise RegisterWrongNumberBits(16)
        self._data = value if shallow else value.copy()

    def _reset_integer_representations(self):
        self._integer_representations.clear()

    INTEGER_REPRESENTATION_PROPERTIES = {"byte": {"getter": byte, "setter": set_byte, "bytes": 1},
                                         "word": {"getter": word, "setter": set_word, "bytes": 2}}

    BOUND_PROPERTIES = {("byte", True): (-128, 127),
                        ("byte", False): (0, 255),
                        ("word", True): (-32768, 32767),
                        ("word", False): (0, 65536)}

    def inc(self, value: int=1):
        self.set(size="word", signed=False, value=self.get(size="word", signed=False) + value)

    def dec(self, value: int=1):
        self.set(size="word", signed=False, value=self.get(size="word", signed=False) - value)


class OnlyOddValueRegister(Register):
    def set_byte(self, value: bitarray, shallow=False):
        if value.length() > 0 and value[-1] is True:
            raise RegisterOddValue()
        super().set_byte(value, shallow=shallow)

    def set_word(self, value: bitarray, shallow=True):
        if value.length() > 0 and value[-1] is True:
            raise RegisterOddValue()
        return super().set_word(value, shallow=shallow)

    def set(self, size: str, signed: bool, value: int):
        if value % 2 == 1:
            raise RegisterOddValue()
        return super().set(size, signed, value)

    def inc(self, value: int=1):
        self.set(size="word", signed=False, value=self.get(size="word", signed=False) + 2)

    def dec(self, value: int=1):
        self.set(size="word", signed=False, value=self.get(size="word", signed=False) - 2)


class StackPointer(OnlyOddValueRegister):
    pass


class ProgramCounter(OnlyOddValueRegister):
    pass

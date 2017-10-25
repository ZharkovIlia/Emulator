from src.backend.extra.exceptions import RegisterOutOfBound, RegisterWrongNumberBits, RegisterException

from bitarray import bitarray

a = bitarray("1100000011111110", endian="big")
print(int.from_bytes(a.tobytes(), byteorder='big', signed=True))

#exit(0)

class Register:
    #MIN_SIGNED_LOW = -128
    #MAX_SIGNED_LOW = 127

    #MIN_UNSIGNED_LOW = 0
    #MAX_UNSIGNED_LOW = 255

    #MIN_SIGNED_FULL = -32768
    #MAX_SIGNED_FULL = 32767

    #MIN_UNSIGNED_FULL = 0
    #MAX_UNSIGNED_FULL = 65536

    def __init__(self):
        self._data = bitarray((False for _ in range(16)), endian="big")
        self._integer_representations = {}
        self._low_signed = None
        self._low_unsigned = None
        self._full_signed = None
        self._full_unsigned = None

    def get(self, size: str, signed: bool):
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

        min = Register.BOUND_PROPERTIES[(size, signed)][0]
        max = Register.BOUND_PROPERTIES[(size, signed)][1]
        num_bytes = Register.INTEGER_REPRESENTATION_PROPERTIES[size]["bytes"]
        if value < min or value > max:
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
        return self._data

    def set_word(self, value: bitarray):
        self._reset_integer_representations()
        if value.length() != 16:
            raise RegisterWrongNumberBits(16)
        self._data = value

    def _reset_integer_representations(self):
        self._integer_representations.clear()

    INTEGER_REPRESENTATION_PROPERTIES = {"byte": {"getter": byte, "setter": set_byte, "bytes": 1},
                                         "word": {"getter": word, "setter": set_word, "bytes": 2}}

    BOUND_PROPERTIES = {("byte", True): (-128, 127),
                        ("byte", False): (0, 255),
                        ("word", True): (-32768, 32767),
                        ("word", False): (0, 65536)}


if __name__ == "__main__":
    r = Register()
    r.set_word(bitarray("1000000110000010"))

    print(r.word())
    print(r.byte())

    print(r.get(size="byte", signed=True))
    print(r.get(size="byte", signed=False))
    print(r.get(size="word", signed=True))
    print(r.get(size="word", signed=False))

    r.set(size="byte", signed=True, value=127)

    print(r.word())
    print(r.byte())

    print(r.get(size="byte", signed=True))
    print(r.get(size="byte", signed=False))
    print(r.get(size="word", signed=True))
    print(r.get(size="word", signed=False))

    r.set(size="byte", signed=False, value=255)

    print(r.word())
    print(r.byte())

    print(r.get(size="byte", signed=True))
    print(r.get(size="byte", signed=False))
    print(r.get(size="word", signed=True))
    print(r.get(size="word", signed=False))

    r.set(size="word", signed=True, value=-1)

    print(r.word())
    print(r.byte())

    print(r.get(size="byte", signed=True))
    print(r.get(size="byte", signed=False))
    print(r.get(size="word", signed=True))
    print(r.get(size="word", signed=False))

    r.set(size="word", signed=False, value=1)

    print(r.word())
    print(r.byte())

    print(r.get(size="byte", signed=True))
    print(r.get(size="byte", signed=False))
    print(r.get(size="word", signed=True))
    print(r.get(size="word", signed=False))
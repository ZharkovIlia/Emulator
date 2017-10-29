from src.backend.utils.exceptions import MemoryException, MemoryIndexOutOfBound, MemoryOddAddressing
from bitarray import bitarray
import enum

class Memory:
    SIZE = 64 * 1024

    class Part(enum.Enum):
        RAM = (0, 16*1024)
        VRAM = (16*1024, 32*1024)
        ROM = (32*1024, 48*1024)
        IO = (48*1024, 64*1024)

        def __init__(self, start, end):
            self._start = start
            self._end = end

        @property
        def start(self):
            return self._start

        @property
        def end(self):
            return self._end

        @property
        def size(self):
            return self._end - self._start

    def __init__(self):
        self._data = bytearray(0 for _ in range(0, Memory.SIZE))

    def load(self, address: int, size: str) -> bitarray:
        Memory._check_arguments(address, size)
        value = bitarray(endian='big')
        value.frombytes(bytes(self._data[address: address+1]))
        if size == 'word':
            tmp = bitarray(endian='big')
            tmp.frombytes(bytes(self._data[address+1: address+2]))
            tmp.extend(value)
            value = tmp
        return value

    def store(self, address: int, size: str, value: bitarray) -> None:
        Memory._check_arguments(address, size)
        num_bytes = 1 if size == 'byte' else 2
        if value.length() != num_bytes * 8:
            raise MemoryException(what="num of stored bits doesn't correspond to predefined size")

        self._data[address: address+1] = value[value.length() - 8: value.length()].tobytes()
        if num_bytes == 2:
            self._data[address+1: address+2] = value[0: 8].tobytes()

    @staticmethod
    def _check_arguments(address: int, size: str):
        if size not in ("byte", "word"):
            raise MemoryException(what="size is not in ('byte', 'word')")

        num_bytes = 1 if size == 'byte' else 2
        if num_bytes == 2 and address % 2 == 1:
            raise MemoryOddAddressing()

        if address < 0:
            raise MemoryIndexOutOfBound()

        if address > Memory.SIZE - num_bytes:
            raise MemoryIndexOutOfBound()

    @property
    def data(self):
        return self._data

    @staticmethod
    def get_type_by_address(address):
        if address < 0 or address >= Memory.SIZE:
            raise MemoryIndexOutOfBound()

        for part in list(Memory.Part):
            if part.start <= address < part.end:
                return part

        assert False

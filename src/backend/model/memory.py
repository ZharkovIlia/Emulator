from src.backend.utils.exceptions import MemoryException, MemoryIndexOutOfBound, MemoryOddAddressing, \
    MemoryWrongConfiguration
from src.backend.model.video import VideoMemory, VideoMemoryRegisterModeStart, VideoMemoryRegisterOffset, VideoMode
from bitarray import bitarray
import enum


class MemoryPart(enum.Enum):
    RAM = (0, 16 * 1024)
    VRAM = (16 * 1024, 32 * 1024)
    ROM = (32 * 1024, 48 * 1024)

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


class Memory:
    SIZE = 64 * 1024

    def __init__(self):
        self._data = bytearray(0 for _ in range(0, Memory.SIZE))
        self._video = VideoMemory(MemoryPart.VRAM.start)
        self._start_io = Memory.SIZE - 4

        self._video_register_mode_start = VideoMemoryRegisterModeStart(self._start_io)
        self._video_register_mode_start.set_word(value=bitarray("00" + "{:014b}".format(MemoryPart.VRAM.start // 4),
                                                                endian='big'))
        self._video.set_VRAM_start(MemoryPart.VRAM.start)
        self._video.set_mode(VideoMode.MODE_O.mode)

        self._video_register_offset = VideoMemoryRegisterOffset(self._start_io + 2)
        self._video_register_offset.set(size="word", signed=False, value=0)
        self._video.set_offset(0)
        self._check_configuration()

    def load(self, address: int, size: str) -> bitarray:
        Memory._check_arguments(address, size)
        bitarr = self._load_from_devices(address, size)
        if bitarr is not None:
            return bitarr

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
        if self._store_to_devices(address, size, value):
            return

        num_bytes = 1 if size == 'byte' else 2
        if value.length() != num_bytes * 8:
            raise MemoryException(what="num of stored bits doesn't correspond to predefined size")

        self._data[address: address+1] = value[value.length() - 8: value.length()].tobytes()
        if num_bytes == 2:
            self._data[address+1: address+2] = value[0: 8].tobytes()

    @property
    def video_register_mode_start_address(self) -> int:
        return self._video_register_mode_start.address

    @property
    def video_register_offset_address(self) -> int:
        return self._video_register_offset.address

    @property
    def data(self):
        return self._data

    @property
    def video(self) -> VideoMemory:
        return self._video

    @staticmethod
    def get_type_by_address(address):
        if address < 0 or address >= Memory.SIZE:
            raise MemoryIndexOutOfBound()

        for part in list(MemoryPart):
            if part.start <= address < part.end:
                return part

        assert False

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

    def _check_configuration(self):
        if self._video.VRAM_start + self._video.size > MemoryPart.ROM.start \
                or MemoryPart.ROM.end > self._start_io \
                or self._video.VRAM_start < MemoryPart.VRAM.start:
            raise MemoryWrongConfiguration()

    def _load_from_devices(self, address: int, size: str):
        if address >= self._video.VRAM_start and address < self._video.VRAM_start + self._video.size:
            return self._video.load(address=address, size=size)

        if (address // 2) * 2 == self._video_register_mode_start.address:
            return self._video_register_mode_start.load(address=address, size=size)

        if (address // 2) * 2 == self._video_register_offset.address:
            return self._video_register_offset.load(address=address, size=size)

        return None

    def _store_to_devices(self, address: int, size: str, value: bitarray) -> bool:
        if address >= self._video.VRAM_start and address < self._video.VRAM_start + self._video.size:
            self._video.store(address=address, size=size, value=value)
            return True

        if (address // 2) * 2 == self._video_register_mode_start.address:
            self._video_register_mode_start.store(address=address, size=size, value=value)
            self._video.set_mode(self._video_register_mode_start.mode)
            self._video.set_VRAM_start(self._video_register_mode_start.VRAM_start)
            self._check_configuration()
            return True

        if (address // 2) * 2 == self._video_register_offset.address:
            self._video_register_offset.store(address=address, size=size, value=value)
            self._video.set_offset(self._video_register_offset.offset)
            return True

        return False

    def operation_on_device(self, address: int) -> bool:
        if address >= self._video.VRAM_start and address < self._video.VRAM_start + self._video.size \
                or (address // 2) * 2 == self._video_register_mode_start.address \
                or (address // 2) * 2 == self._video_register_offset.address:
            return True

        return False

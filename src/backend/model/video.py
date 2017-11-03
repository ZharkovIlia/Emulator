import enum

from PyQt5.QtGui import QImage, qRgb
from bitarray import bitarray

from src.backend.utils.exceptions import VideoException, VideoWrongMode
from src.backend.model.registers import MemoryRegister


class VideoMemoryRegisterModeStart(MemoryRegister):
    def __init__(self, address: int):
        super(VideoMemoryRegisterModeStart, self).__init__(address)

    @property
    def VRAM_start(self) -> int:
        return int(self._data[2:16].to01(), 2) * 4

    @property
    def mode(self) -> int:
        return int(self._data[0:2].to01(), 2)


class VideoMemoryRegisterOffset(MemoryRegister):
    def __init__(self, address: int):
        super(VideoMemoryRegisterOffset, self).__init__(address)

    @property
    def offset(self):
        return int(self._data[7:16].to01(), 2)


class VideoModes(enum.Enum):
    MODE_O = (0, 256, 256, 1, {
        0: qRgb(255, 255, 255),
        1: qRgb(0, 0, 0)
    })

    def __init__(self, mode: int, height: int, width: int, depth: int, color_table: dict):
        self.mode = mode
        self.height = height
        self.width = width
        self.depth = depth
        self.color_table = color_table


class VideoMemory:
    def __init__(self, VRAM_start, on_show=None):
        self._on_show = on_show
        self._mode: VideoModes = None
        self._image: QImage = None
        self._offset = 0
        self._size: int = None
        self._VRAM_start: int = None
        self.set_VRAM_start(VRAM_start)
        self.set_mode(0)

    def set_mode(self, mode: int):
        if mode not in (md.mode for md in list(VideoModes)):
            raise VideoWrongMode()

        if self._mode is not None and mode == self._mode.mode:
            return
        for md in list(VideoModes):
            if md.mode == mode:
                self._mode = md

        self._image = QImage(self._mode.width, self._mode.height, QImage.Format_Indexed8)
        for k, v in self._mode.color_table.items():
            self._image.setColor(k, v)
        self._image.fill(0)

        assert self._mode.width * self._mode.height * self._mode.depth % 16 == 0, "Wrong configuration"
        assert self._mode.width * self._mode.depth % 8 == 0, "Wrong configuration"
        assert 8 % self._mode.depth == 0, "Wrong configuration"
        self._size = self._mode.width * self._mode.height * self._mode.depth // 8

    def set_VRAM_start(self, VRAM_start):
        if VRAM_start % 2 == 1:
            raise VideoException(what="VRAM cannot start at odd address")
        self._VRAM_start = VRAM_start

    def set_offset(self, offset):
        new_offset = offset % self._mode.height
        if self._offset == new_offset:
            return

        image = QImage(self._mode.width, self._mode.height, QImage.Format_Indexed8)
        image.setColorTable(self._image.colorTable())
        diff = new_offset - self._offset
        for y in range(self._mode.height):
            from_y = y + diff
            if from_y < 0:
                from_y += self._mode.height
            if from_y >= self._mode.height:
                from_y -= self._mode.height
            for x in range(self._mode.width):
                image.setPixel(x, y, self._image.pixelIndex(x, from_y))

        self._image = image

    def set_on_show(self, on_show):
        self._on_show = on_show

    def load(self, address: int, size: str) -> bitarray:
        points = self._get_pixels_by_address(address)
        bitarr = bitarray(endian="big")
        for point in points:
            bitarr.extend(self._pixel_to_bits(point=point))

        if size == 'word':
            tmp = self.load(address=address+1, size='byte')
            tmp.extend(bitarr)
            bitarr = tmp

        return bitarr

    def store(self, address: int, size: str, value: bitarray):
        points = self._get_pixels_by_address(address)
        tmp = value[value.length() - 8: value.length()]
        tmp_pos = 0
        for point in points:
            self._image.setPixel(point[0], point[1], int(tmp[tmp_pos: tmp_pos + self._mode.depth].to01(), 2))
            tmp_pos += self._mode.depth

        if size == 'word':
            self.store(address=address+1, size="byte", value=value[0: 8])

    def show(self):
        if self._on_show is not None:
            self._on_show(self._image)

    @property
    def size(self):
        return self._size

    @property
    def VRAM_start(self):
        return self._VRAM_start

    @property
    def image(self) -> QImage:
        return self._image

    def _get_pixels_by_address(self, address: int) -> list:
        result = []
        relative = address - self._VRAM_start
        pixels = relative * 8 / self._mode.depth
        y = pixels // self._mode.width
        x = pixels % self._mode.width
        for _ in range(8 // self._mode.depth):
            result.append((x, y))
            x += 1

        return result

    def _pixel_to_bits(self, point) -> str:
        return ("{:0" + str(self._mode.depth) + "b}").format(self._image.pixelIndex(point[0], point[1]))

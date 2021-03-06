import enum

from PyQt5.QtGui import QImage, qRgb
from bitarray import bitarray

from src.backend.model.registers import Register, VideoMemoryRegisterModeStart, \
    VideoMemoryRegisterOffset
from src.backend.utils.exceptions import VideoException, VideoWrongMode


class VideoMode(enum.Enum):
    MODE_O = (0, 256, 256, 1, {
        0: qRgb(0, 0, 0),
        1: qRgb(255, 255, 255)
    })

    def __init__(self, mode: int, height: int, width: int, depth: int, color_table: dict):
        self.mode = mode
        self.height = height
        self.width = width
        self.depth = depth
        self.color_table = color_table


class VideoMemory:
    def __init__(self, reg_mode: VideoMemoryRegisterModeStart, reg_offset: VideoMemoryRegisterOffset, on_show=None):
        self._on_show = on_show
        self._mode: VideoMode = None
        self._image: QImage = None
        self._offset = 0
        self._size: int = None
        self._VRAM_start: int = None
        self._white_index: int = None
        self.set_mode(reg_mode)
        self.set_offset(reg_offset)

    def set_mode(self, reg_mode: VideoMemoryRegisterModeStart):
        VRAM_start = reg_mode.VRAM_start
        if VRAM_start % 2 == 1:
            raise VideoException(what="VRAM cannot start at odd address")
        self._VRAM_start = VRAM_start
        mode = reg_mode.mode

        if mode not in (md.mode for md in list(VideoMode)):
            raise VideoWrongMode()

        if self._mode is not None and mode == self._mode.mode:
            return
        for md in list(VideoMode):
            if md.mode == mode:
                self._mode = md

        self._image = QImage(self._mode.width, self._mode.height, QImage.Format_Indexed8)
        for k, v in self._mode.color_table.items():
            self._image.setColor(k, v)
        white = qRgb(255, 255, 255)
        self._white_index = None
        for index, color in self._mode.color_table.items():
            if color == white:
                self._white_index = index
                break
        assert self._white_index is not None
        self._image.fill(self._white_index)

        assert self._mode.width * self._mode.height * self._mode.depth % 16 == 0, "Wrong configuration"
        assert self._mode.width * self._mode.depth % 8 == 0, "Wrong configuration"
        assert 8 % self._mode.depth == 0, "Wrong configuration"
        self._size = self._mode.width * self._mode.height * self._mode.depth // 8

    def set_offset(self, reg_offset: VideoMemoryRegisterOffset):
        offset = reg_offset.offset
        if reg_offset.bit_clear:
            self._image.fill(self._white_index)
            reg_offset.bit_clear = False
            self._offset = offset
            return

        if self._offset == offset:
            return

        image = QImage(self._mode.width, self._mode.height, QImage.Format_Indexed8)
        image.setColorTable(self._image.colorTable())
        diff = offset - self._offset
        if diff < 0:
            diff = reg_offset.MAX_OFFSET + diff + 1
        self._offset = offset
        for y in range(self._mode.height):
            from_y = y + diff
            for x in range(self._mode.width):
                if from_y >= self._mode.height:
                    image.setPixel(x, y, self._white_index)
                else:
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
    def mode(self):
        return self._mode

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
        pixels = relative * 8 // self._mode.depth
        y = pixels // self._mode.width
        x = pixels % self._mode.width
        for _ in range(8 // self._mode.depth):
            result.append((x, y))
            x += 1

        return result

    def _pixel_to_bits(self, point) -> str:
        return ("{:0" + str(self._mode.depth) + "b}").format(self._image.pixelIndex(point[0], point[1]))

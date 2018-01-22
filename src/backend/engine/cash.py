from bitarray import bitarray

from src.backend.model.memory import Memory
from src.backend.utils.exceptions import CashWrongBlockException, CashUnblockException



class CashLine:
    def __init__(self, string: int, lru: int):
        self.reliable = False
        self.tag = 0
        self.string = string
        self.lru = lru
        self.modified = False
        self.missed = False


class BusRequest:
    CPU_CYCLES_PER_BUS_CYCLE = 5

    def __init__(self, num_bus_cycles, line: CashLine = None):
        self._num_bus_cycles_left = num_bus_cycles
        self.done = (num_bus_cycles == 0)
        self._cpu_cycle = 0
        self._line = line

    @property
    def line(self):
        return self._line

    def cycle(self) -> None:
        if self.done:
            return

        self._cpu_cycle += 1
        if self._cpu_cycle == self.CPU_CYCLES_PER_BUS_CYCLE:
            self._num_bus_cycles_left -= 1
            self._cpu_cycle = 0

        if self._num_bus_cycles_left != 0:
            return

        self.done = True
        if self._line is not None:
            self._line.blocked = False
            self._line.reliable = True
            self._line.modified = False
            self._line.missed = True


class CashMemory:
    BITS_FOR_TAG = 7
    BITS_FOR_STRING = 6
    BITS_FOR_WORDS = 3
    ASSOCIATION_DEGREE = 2

    LRU_NOT_EJECT = -1

    WORDS_IN_LINE = (2 ** BITS_FOR_WORDS) // 2
    NUM_STRINGS = 2 ** BITS_FOR_STRING

    def __init__(self, memory: Memory, enabled=True):
        self._memory = memory
        self._bus_request = BusRequest(0)
        self._enabled = enabled
        self.strings = []
        self._busy = False
        self._address = -1
        self._rw: str = None
        self.clear_statistics()
        for string in range(0, self.NUM_STRINGS):
            self.strings.append([CashLine(string, self.ASSOCIATION_DEGREE - i - 1)
                                 for i in range(0, self.ASSOCIATION_DEGREE)])

        self._pool_addr_blocked = set()

    @property
    def enabled(self):
        return self._enabled

    @property
    def busy(self):
        return self._busy

    @property
    def hits(self):
        return self._hits

    @property
    def misses(self):
        return self._misses

    @property
    def address(self):
        return self._address

    @property
    def rw(self):
        return self._rw

    def clear_statistics(self):
        self._hits = 0
        self._misses = 0

    def clear_address(self):
        self._address = -1

    def load(self, address: int, size: str) -> (bool, bitarray):
        if (address // 2) * 2 in self._pool_addr_blocked:
            return False, None

        if not self._busy and self._address != -1 and self._address != address:
            return False, None

        if not self._enabled or self._memory.operation_on_device(address):
            return self._load_if_disabled(address, size)

        (string, tag) = self._get_string_tag(address)
        line = self._find(string, tag)

        if line is not None:
            self._change_lru(line)
            if not self._busy:
                self._address = -1

            if line.missed:
                line.missed = False
                self._misses += 1
            else:
                self._hits += 1
            return True, self._memory.load(address, size)

        if not self._busy:
            self._eject(string, tag, address, 'r')

        return False, None

    def store(self, address: int, size: str, value: bitarray) -> bool:
        if not self._busy and self._address != -1 and self._address != address:
            return False

        if not self._enabled or self._memory.operation_on_device(address):
            return self._store_if_disabled(address, size, value)

        (string, tag) = self._get_string_tag(address)
        line = self._find(string, tag)

        if line is not None:
            self._change_lru(line)
            if not self._busy:
                self._address = -1

            self._memory.store(address, size, value)
            line.modified = True

            if line.missed:
                line.missed = False
                self._misses += 1
            else:
                self._hits += 1
            return True

        if not self._busy:
            self._eject(string, tag, address, 'w')

        return False

    def cycle(self) -> bool:
        if self._bus_request.done:
            return not self._busy

        self._bus_request.cycle()
        if self._bus_request.done:
            self._busy = False
            if self._bus_request.line is not None:
                self._change_lru(self._bus_request.line)

        return not self._busy

    def block(self, address: int, block: bool) -> bool:
        if ((address // 2) * 2 in self._pool_addr_blocked) != block:
            if block:
                self._pool_addr_blocked.add((address // 2) * 2)
            else:
                self._pool_addr_blocked.remove((address // 2) * 2)
            return True

        if (address // 2) * 2 not in self._pool_addr_blocked and not block:
            raise CashUnblockException()

        return False

    def _load_if_disabled(self, address: int, size: str) -> (bool, bitarray):
        if self._busy:
            return False, None

        if self._address == address and self._rw == 'r':
            self._rw = None
            self._address = -1
            return True, self._memory.load(address, size)

        if self._address == -1:
            self._rw = 'r'
            self._address = address
            self._bus_request = BusRequest(2)
            self._busy = True

        return False, None

    def _store_if_disabled(self, address: int, size: str, value: bitarray) -> bool:
        if self._busy:
            return False

        if self._address == address and self._rw == 'w':
            self._rw = None
            self._address = -1
            self._memory.store(address, size, value)
            return True

        if self._address == -1:
            self._rw = 'w'
            self._address = address
            self._bus_request = BusRequest(2)
            self._busy = True

        return False

    def _find(self, string: int, tag: int):
        for line in self.strings[string]:
            if line.reliable and line.tag == tag:
                return line

        return None

    def _get_string_tag(self, address) -> (int, int):
        bitarr = bitarray(endian='big')
        bitarr.frombytes(address.to_bytes(2, byteorder='big', signed=False))
        string = int(bitarr[self.BITS_FOR_TAG: self.BITS_FOR_TAG + self.BITS_FOR_STRING].to01(), 2)
        tag = int(bitarr[0: self.BITS_FOR_TAG].to01(), 2)
        return string, tag

    def _eject(self, string: int, tag: int, address: int, rw: str):
        assert not self._busy

        line_for_ejection: CashLine = self.strings[string][0]
        if line_for_ejection.lru == self.LRU_NOT_EJECT:
            print("warning: cannot eject cash line")
            return

        self._address = address
        self._rw = rw

        line_for_ejection.lru = self.LRU_NOT_EJECT
        self.strings[string].sort(key=lambda ln: ln.lru, reverse=True)

        line_for_ejection.reliable = False
        line_for_ejection.tag = tag
        num_memory_cycles = 2 + self.WORDS_IN_LINE
        if line_for_ejection.modified:
            num_memory_cycles += 2 + self.WORDS_IN_LINE
        self._bus_request = BusRequest(num_memory_cycles, line_for_ejection)
        self._busy = True

    def _lru_normalize(self, string: int):
        lines = self.strings[string]
        lines.sort(key=lambda ln: ln.lru, reverse=True)
        assert lines[self.ASSOCIATION_DEGREE - 1].lru in (self.LRU_NOT_EJECT, 0)

        for i in range(self.ASSOCIATION_DEGREE - 1, -1, -1):
            if lines[i].lru == self.LRU_NOT_EJECT:
                continue
            elif i != self.ASSOCIATION_DEGREE - 1:
                assert lines[i].lru > lines[i+1].lru
                lines[i].lru = lines[i+1].lru + 1

    def _change_lru(self, line_lru: CashLine):
        assert line_lru.reliable

        for line in self.strings[line_lru.string]:
            if line is not line_lru and line.lru != self.LRU_NOT_EJECT:
                line.lru += 1

        line_lru.lru = 0
        self._lru_normalize(line_lru.string)

from bitarray import bitarray

from src.backend.utils.exceptions import PoolRegistersUnblockException


class PoolRegisters:
    def __init__(self, registers: list, enabled=True):
        assert len(registers) == 8
        self._registers = registers
        self._blocked = [False for _ in range(8)]
        self._enabled = enabled

    def get(self, regnum: int, size: str, signed: bool) -> (bool, int):
        if self._blocked[regnum]:
            return False, None
        return True, self._registers[regnum].get(size, signed)

    def set(self, regnum: int, size: str, signed: bool, value: bitarray) -> bool:
        self._registers[regnum].set(size, signed)
        return True

    def byte(self, regnum: int) -> (bool, bitarray):
        if self._blocked[regnum]:
            return False, None
        return True, self._registers[regnum].byte()

    def word(self, regnum: int) -> (bool, bitarray):
        if self._blocked[regnum]:
            return False, None
        return True, self._registers[regnum].word()

    def set_byte(self, regnum: int, value: bitarray) -> bool:
        self._registers[regnum].set_byte(value)
        return True

    def set_word(self, regnum: int, value: bitarray) -> bool:
        self._registers[regnum].set_word(value)
        return True

    def inc(self, regnum: int, value: int) -> bool:
        if self._blocked[regnum]:
            return False
        self._registers[regnum].inc(value)
        return True

    def dec(self, regnum: int, value: int) -> bool:
        if self._blocked[regnum]:
            return False
        self._registers[regnum].dec(value)
        return True

    @property
    def enabled(self):
        return self._enabled

    @property
    def registers(self):
        return self._registers

    def block(self, regnum: int, block: bool) -> bool:
        if self._blocked[regnum] != block:
            self._blocked[regnum] = block
            return True

        if not block and not self._blocked:
            raise PoolRegistersUnblockException()

        return False

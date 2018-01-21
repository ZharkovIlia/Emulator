from bitarray import bitarray


class PoolRegisters:
    def __init__(self, registers: list, enabled=True):
        assert len(registers) == 8
        self._registers = registers
        self.enabled = enabled

    @property
    def registers(self):
        return self._registers

    def get(self, regnum: int, size: str, signed: bool) -> (bool, int):
        return True, self._registers[regnum].get(size, signed)

    def inc(self, regnum: int, value: int) -> bool:
        self._registers[regnum].inc(value)
        return True

    def dec(self, regnum: int, value: int) -> bool:
        self._registers[regnum].dec(value)
        return True

    def byte(self, regnum) -> (bool, bitarray):
        return True, self._registers[regnum].byte()

    def set_byte(self, regnum, value: bitarray) -> bool:
        self._registers[regnum].set_byte(value)
        return True

    def word(self, regnum) -> (bool, bitarray):
        return True, self._registers[regnum].word()

    def set_word(self, regnum, value: bitarray) -> bool:
        self._registers[regnum].set_word(value)
        return True

    def block(self, regnum: int, block: bool) -> bool:
        return True
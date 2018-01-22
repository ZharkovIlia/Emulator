from bitarray import bitarray

from src.backend.utils.exceptions import PoolRegistersUnblockException


class PoolRegisters:
    def __init__(self, registers: list):
        assert len(registers) == 8
        self._registers = registers
        self._blocked = [False for _ in range(8)]
        self._reader = self.reader(self)
        self._writer = self.writer(self)

        self.get = self._reader(lambda regnum, size, signed: self._registers[regnum].get(size=size, signed=signed))
        self.set = self._writer(lambda regnum, size, signed, value:
                                self._registers[regnum].set(size=size, signed=signed, value=value))
        self.byte = self._reader(lambda regnum: self._registers[regnum].byte())
        self.word = self._reader(lambda regnum: self._registers[regnum].word())
        self.set_word = self._writer(lambda regnum, value: self._registers[regnum].set_word(value=value))
        self.set_byte = self._writer(lambda regnum, value: self._registers[regnum].set_byte(value=value))
        self.inc_fetch = self._reader(lambda regnum, value: self._registers[regnum].inc(value=value))
        self.inc_store = self._writer(lambda regnum, value: self._registers[regnum].inc(value=value))
        self.dec_fetch = self._reader(lambda regnum, value: self._registers[regnum].dec(value=value))
        self.dec_store = self._writer(lambda regnum, value: self._registers[regnum].dec(value=value))

    class reader:
        def __init__(self, pool):
            self._pool = pool

        def __call__(self, call):
            def wrapper(regnum: int, **kwargs):
                if self._pool._blocked[regnum]:
                    return False, None
                else:
                    result = call(regnum=regnum, **kwargs)
                    return True, result

            return wrapper

    class writer:
        def __init__(self, pool):
            self._pool = pool

        def __call__(self, call):
            def wrapper(**kwargs):
                call(**kwargs)
                return True

            return wrapper

    @property
    def registers(self):
        return self._registers

    def block(self, regnum: int, block: bool) -> bool:
        if self._blocked[regnum] != block:
            self._blocked[regnum] = block
            return True

        if not block and not self._blocked[regnum]:
            raise PoolRegistersUnblockException()

        return False

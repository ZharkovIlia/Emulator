from src.backend.utils.exceptions import PoolRegistersUnblockException


class PoolRegisters:
    def __init__(self, registers: list, enabled=True):
        assert len(registers) == 8
        self._registers = registers
        self._blocked = [False for _ in range(8)]
        self._enabled = enabled
        self._reader = self.reader(self)
        self._writer = self.writer(self)

        self.get = self._reader(lambda regnum, size, signed: self._registers[regnum].get(size, signed))
        self.set = self._writer(lambda regnum, size, signed, value: self._registers[regnum].set(size, signed, value))
        self.byte = self._reader(lambda regnum: self._registers[regnum].byte())
        self.word = self._reader(lambda regnum: self._registers[regnum].word())
        self.set_word = self._writer(lambda regnum, value: self._registers[regnum].set_word(value))
        self.set_byte = self._writer(lambda regnum, value: self._registers[regnum].set_byte(value))
        self.inc = self._reader(lambda regnum, value: self._registers[regnum].inc(value))
        self.dec = self._reader(lambda regnum, value: self._registers[regnum].dec(value))

    class reader:
        def __init__(self, pool):
            self._pool = pool

        def __call__(self, call):
            def wrapper(regnum: int, **kwargs):
                result = call(regnum=regnum, **kwargs)
                if self._pool._blocked[regnum]:
                    if result is None:
                        return False
                    else:
                        return False, None
                else:
                    if result is None:
                        return True
                    else:
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

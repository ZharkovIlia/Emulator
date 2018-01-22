from collections import deque

from PyQt5.QtCore import QMutex

from src.backend.engine.pipe import Pipe
from src.backend.model.memory import Memory
from src.backend.model.programstatus import ProgramStatus
from src.backend.model.registers import KeyboardRegister, StackPointer, ProgramCounter


class Keyboard:
    INTERRUPT_VECTOR = {"PC": 0, "PS": 2}
    ALPHABET = "abcdefghijklmnopqrstuvwxyz"
    ENTER = len(ALPHABET)
    BACKSPACE = ENTER + 1

    def __init__(self, register: KeyboardRegister, pipe: Pipe, memory: Memory, program_status: ProgramStatus,
                 program_counter: ProgramCounter, stack_pointer: StackPointer):
        self._register = register
        self._pipe = pipe
        self._memory = memory
        self._ps = program_status
        self._pc = program_counter
        self._sp = stack_pointer
        self._buffer = deque()
        self._lock = QMutex()

    @property
    def interrupt_permitted(self) -> bool:
        return self._register.interrupt_permitted

    def interrupt(self) -> bool:
        self._lock.lock()
        if not self._register.interrupt_permitted or len(self._buffer) == 0:
            return False

        self._register.interrupt_permitted = False
        self._register.key_index = self._buffer.popleft()
        self._pipe.barrier()

        self._sp.dec(value=2)
        self._memory.store(address=self._sp.get(size="word", signed=False), size="word", value=self._ps.word())

        self._sp.dec(value=2)
        self._memory.store(address=self._sp.get(size="word", signed=False), size="word", value=self._pc.word())

        self._pc.set_word(value=self._memory.load(address=self.INTERRUPT_VECTOR["PC"], size="word"))
        self._ps.set_word(value=self._memory.load(address=self.INTERRUPT_VECTOR["PS"], size="word"))

        self._pipe.add_command()
        self._lock.unlock()
        return True

    def add_alpha(self, alpha: str):
        self._lock.lock()
        key_index = self.ALPHABET.find(alpha)
        if key_index == -1:
            print("warning: symbol is not an alpha or is not lower cased")
            return

        self._buffer.append(key_index)
        self._lock.unlock()

    def add_enter(self):
        self._lock.lock()
        self._buffer.append(self.ENTER)
        self._lock.unlock()

    def add_backspace(self):
        self._lock.lock()
        self._buffer.append(self.BACKSPACE)
        self._lock.unlock()

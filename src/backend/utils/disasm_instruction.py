import enum

from bitarray import bitarray


class DisasmState(enum.Enum):
    NOT_AN_INSTRUCTION = enum.auto()
    UNDEFINED = enum.auto()
    DISASSEMBLED = enum.auto()
    PART_OF_PREVIOUS = enum.auto()


class DisasmInstruction:
    def __init__(self):
        self._state = DisasmState.UNDEFINED
        self._previous_code = bitarray(endian='big')
        self._str = None
        self._num_next = 0

    @property
    def previous_code(self) -> bitarray:
        return self._previous_code

    @property
    def state(self):
        return self._state

    @property
    def num_next(self):
        return self._num_next

    def set_state(self, state: DisasmState, code: bitarray, representation=None, num_next=0):
        self._previous_code = code
        self._state = state
        if state is DisasmState.NOT_AN_INSTRUCTION:
            self._str = "Not an instruction"
        elif state is DisasmState.UNDEFINED:
            self._str = None
        elif state is DisasmState.DISASSEMBLED:
            self._str = representation
            self._num_next = num_next
        elif state is DisasmState.PART_OF_PREVIOUS:
            self._str = None
            self._num_next = num_next

    def __str__(self):
        return self._str
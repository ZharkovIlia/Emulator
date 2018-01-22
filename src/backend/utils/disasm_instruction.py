import enum


class DisasmState(enum.Enum):
    NOT_AN_INSTRUCTION = enum.auto()
    DISASSEMBLED = enum.auto()
    PART_OF_PREVIOUS = enum.auto()


class DisasmInstruction:
    def __init__(self):
        self._state = DisasmState.NOT_AN_INSTRUCTION
        self._str = "Not an instruction"
        self._num_next: int = 0

    @property
    def state(self):
        return self._state

    @property
    def num_next(self):
        return self._num_next

    def set_state(self, state: DisasmState, representation=None, num_next: int=0):
        self._state = state
        if state is DisasmState.NOT_AN_INSTRUCTION:
            if representation is not None:
                self._str = representation
            else:
                self._str = "Not an instruction"

        elif state is DisasmState.DISASSEMBLED:
            self._str = representation
            assert num_next is not None
            self._num_next = num_next

        elif state is DisasmState.PART_OF_PREVIOUS:
            self._str = "Part of previous"
            assert num_next is not None
            self._num_next = num_next

    def __str__(self):
        return self._str

import enum


class DisasmState(enum.Enum):
    NOT_AN_INSTRUCTION = enum.auto()
    DISASSEMBLED = enum.auto()
    PART_OF_PREVIOUS = enum.auto()


class DisasmInstruction:
    def __init__(self):
        self._state = DisasmState.NOT_AN_INSTRUCTION
        self._str = "Not an instruction"

    @property
    def state(self):
        return self._state

    def set_state(self, state: DisasmState, representation=None):
        self._state = state
        if state is DisasmState.NOT_AN_INSTRUCTION:
            self._str = "Not an instruction"
        elif state is DisasmState.DISASSEMBLED:
            self._str = representation
        elif state is DisasmState.PART_OF_PREVIOUS:
            self._str = "Part of previous"

    def __str__(self):
        return self._str

from src.backend.model.registers import Register
from src.backend.utils.exceptions import ProgramStatusException


class ProgramStatus(Register):
    def __init__(self):
        super(ProgramStatus, self).__init__()
        self._bits_pos = {"V": 0, "N": 1, "C": 2, "Z": 3}

    def get_status(self, bit: str) -> bool:
        if bit not in self._bits_pos.keys():
            raise ProgramStatusException(what="Unknown bit {}".format(bit))

        return self._data[self._bits_pos[bit]]

    def set_status(self, bit: str, value: bool):
        if bit not in self._bits_pos.keys():
            raise ProgramStatusException(what="Unknown bit {}".format(bit))

        self._data[self._bits_pos[bit]] = value

    def clear(self):
        self._data.setall(False)

    @property
    def bits(self):
        return {k: self._data[v] for k, v in self._bits_pos.items()}

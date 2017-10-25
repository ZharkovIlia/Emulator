from src.backend.extra.exceptions import ProgramStatusException


class ProgramStatus:
    def __init__(self):
        self._bits = {"V": False,
                      "N": False,
                      "C": False,
                      "Z": False}

    def get(self, bit: str) -> bool:
        if bit not in self._bits.keys():
            raise ProgramStatusException(what="Unknown bit {}".format(bit))

        return self._bits[bit]

    def set(self, bit: str, value: bool):
        if bit not in self._bits.keys():
            raise ProgramStatusException(what="Unknown bit {}".format(bit))

        self._bits[bit] = value

    @property
    def bits(self):
        return self._bits
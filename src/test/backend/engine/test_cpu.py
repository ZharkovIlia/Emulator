import unittest
from bitarray import bitarray

from src.backend.engine.cpu import CPU
from src.backend.model.memory import Memory
from src.backend.model.programstatus import ProgramStatus
from src.backend.model.commands import Commands, Operation
from src.backend.model.registers import Register, ProgramCounter, StackPointer


class CPUTest(unittest.TestCase):
    def setUp(self):
        self.registers = list(Register() for _ in range(6))
        self.registers.append(StackPointer())
        self.registers.append(ProgramCounter())
        self.registers[1].set_word(value=bitarray("0000000010000000"))
        self.registers[7].set_word(value=bitarray("0000000100000000"))

        self.memory = Memory()
        self.memory.store(address=126, size="word", mem=bitarray("0101010100001111"))
        self.memory.store(address=128, size="word", mem=bitarray("0000000011111110"))

        self.ps = ProgramStatus()
        self.ps.set(bit="N", value=True)
        self.ps.set(bit="C", value=True)
        self.cpu = CPU(memory=self.memory, registers=self.registers, program_status=self.ps)

    def test_clr_program_status_correct(self):
        self.memory.store(address=256, size="word", mem=bitarray("0000101000000001"))
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=False, Z=True, C=False, V=False))

    def test_clr_word_mode_0_reg_general_purpose(self):
        self.memory.store(address=256, size="word", mem=bitarray("0000101000000001"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000000000000")

    def test_clr_byte_mode_0_reg_general_purpose(self):
        self.memory.store(address=256, size="word", mem=bitarray("1000101000000001"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000000000000")

    def test_clr_word_mode_1_reg_general_purpose(self):
        self.memory.store(address=256, size="word", mem=bitarray("0000101000001001"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000010000000")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000000000000")


if __name__ == "__main__":
    unittest.main()

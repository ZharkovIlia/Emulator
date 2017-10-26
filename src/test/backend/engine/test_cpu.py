import unittest
from bitarray import bitarray

from src.backend.engine.cpu import CPU
from src.backend.model.memory import Memory
from src.backend.model.programstatus import ProgramStatus
from src.backend.model.registers import Register, ProgramCounter, StackPointer


class CPUTest(unittest.TestCase):
    def setUp(self):
        self.registers = list(Register() for _ in range(6))
        self.registers.append(StackPointer())
        self.registers.append(ProgramCounter())
        self.registers[1].set_word(value=bitarray("0000000010000000"))
        self.registers[7].set_word(value=bitarray("0000000100000000"))

        self.memory = Memory()
        self.memory.store(address=510, size="word", mem=bitarray("0101010100001111"))
        self.memory.store(address=128, size="word", mem=bitarray("0000000111111110"))
        self.memory.store(address=21774, size="word", mem=bitarray("1111111111111111"))

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

    def test_clr_byte_mode_1_reg_general_purpose(self):
        self.memory.store(address=256, size="word", mem=bitarray("1000101000001001"))
        self.registers[1].set_word(value=bitarray("0000000010000001"))
        self.cpu.execute_next()
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000011111110")

    def test_clr_word_mode_2_reg_general_purpose(self):
        self.memory.store(address=256, size="word", mem=bitarray("0000101000010001"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000010000010")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000000000000")

    def test_clr_byte_mode_2_reg_general_purpose(self):
        self.memory.store(address=256, size="word", mem=bitarray("1000101000010001"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000010000001")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000100000000")

    def test_clr_word_mode_3_reg_general_purpose(self):
        self.memory.store(address=256, size="word", mem=bitarray("0000101000011001"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000010000010")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000111111110")
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0000000000000000")

    def test_clr_byte_mode_3_reg_general_purpose(self):
        self.memory.store(address=256, size="word", mem=bitarray("1000101000011001"))
        self.memory.store(address=128, size="word", mem=bitarray("0000000111111111"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000010000010")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000111111111")
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0000000000001111")

    def test_clr_word_mode_4_reg_general_purpose(self):
        self.memory.store(address=256, size="word", mem=bitarray("0000101000100001"))
        self.registers[1].set_word(value=bitarray("0000000010000010"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000010000000")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000000000000")

    def test_clr_byte_mode_4_reg_general_purpose(self):
        self.memory.store(address=256, size="word", mem=bitarray("1000101000100001"))
        self.registers[1].set_word(value=bitarray("0000000010000010"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000010000001")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000011111110")

    def test_clr_word_mode_5_reg_general_purpose(self):
        self.memory.store(address=256, size="word", mem=bitarray("0000101000101001"))
        self.registers[1].set_word(value=bitarray("0000000010000010"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000010000000")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000111111110")
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0000000000000000")

    def test_clr_byte_mode_5_reg_general_purpose(self):
        self.memory.store(address=256, size="word", mem=bitarray("1000101000101001"))
        self.registers[1].set_word(value=bitarray("0000000010000010"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000010000000")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000111111110")
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0101010100000000")

    def test_clr_word_mode_6_reg_general_purpose(self):
        self.memory.store(address=256, size="word", mem=bitarray("0000101000110001"))
        self.memory.store(address=258, size="word", mem=bitarray("0000000000000100"))
        self.registers[1].set_word(value=bitarray("0000000001111100"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000001111100")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000000000000")
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)

    def test_clr_byte_mode_6_reg_general_purpose(self):
        self.memory.store(address=256, size="word", mem=bitarray("1000101000110001"))
        self.memory.store(address=258, size="word", mem=bitarray("0000000000000101"))
        self.registers[1].set_word(value=bitarray("0000000001111100"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000001111100")
        self.assertEqual(self.memory.load(address=258, size="word").to01(), "0000000000000101")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000011111110")

    def test_clr_word_mode_7_reg_general_purpose(self):
        self.memory.store(address=256, size="word", mem=bitarray("0000101000111001"))
        self.memory.store(address=258, size="word", mem=bitarray("0000000000000100"))
        self.registers[1].set_word(value=bitarray("0000000001111100"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000001111100")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000111111110")
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0000000000000000")

    def test_clr_byte_mode_7_reg_general_purpose(self):
        self.memory.store(address=256, size="word", mem=bitarray("1000101000111001"))
        self.memory.store(address=258, size="word", mem=bitarray("0000000000000100"))
        self.memory.store(address=128, size="word", mem=bitarray("0000000111111111"))
        self.registers[1].set_word(value=bitarray("0000000001111100"))
        self.cpu.execute_next()
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000111111111")
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0000000000001111")

    def test_clr_word_mode_2_reg_pc(self):
        self.memory.store(address=256, size="word", mem=bitarray("0000101000010111"))
        self.memory.store(address=258, size="word", mem=bitarray("0000010101111111"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)
        self.assertEqual(self.memory.load(address=258, size="word").to01(), "0000000000000000")

    def test_clr_byte_mode_2_reg_pc(self):
        self.memory.store(address=256, size="word", mem=bitarray("1000101000010111"))
        self.memory.store(address=258, size="word", mem=bitarray("0000010101111111"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)
        self.assertEqual(self.memory.load(address=258, size="word").to01(), "0000010100000000")

    def test_clr_word_mode_3_reg_pc(self):
        self.memory.store(address=256, size="word", mem=bitarray("0000101000011111"))
        self.memory.store(address=258, size="word", mem=bitarray("0000000111111110"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0000000000000000")

    def test_clr_byte_mode_3_reg_pc(self):
        self.memory.store(address=256, size="word", mem=bitarray("1000101000011111"))
        self.memory.store(address=258, size="word", mem=bitarray("0000000111111110"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0101010100000000")

    def test_clr_word_mode_6_reg_pc(self):
        self.memory.store(address=256, size="word", mem=bitarray("0000101000110111"))
        self.memory.store(address=258, size="word", mem=bitarray("0000000011111010"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0000000000000000")

    def test_clr_byte_mode_6_reg_pc(self):
        self.memory.store(address=256, size="word", mem=bitarray("1000101000110111"))
        self.memory.store(address=258, size="word", mem=bitarray("0000000011111011"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0000000000001111")

    def test_clr_low_byte_mode_7_reg_pc(self):
        self.memory.store(address=256, size="word", mem=bitarray("1000101000111111"))
        self.memory.store(address=258, size="word", mem=bitarray("0000000011111010"))
        self.memory.store(address=510, size="word", mem=bitarray("0101010100001110"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0101010100001110")
        self.assertEqual(self.memory.load(address=21774, size="word").to01(), "1111111100000000")

    def test_clr_high_byte_mode_7_reg_pc(self):
        self.memory.store(address=256, size="word", mem=bitarray("1000101000111111"))
        self.memory.store(address=258, size="word", mem=bitarray("0000000011111010"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0101010100001111")
        self.assertEqual(self.memory.load(address=21774, size="word").to01(), "0000000011111111")

if __name__ == "__main__":
    unittest.main()

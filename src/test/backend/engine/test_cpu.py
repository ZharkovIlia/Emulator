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
        self.registers[2].set_word(value=bitarray("0111111100001111"))
        self.registers[3].set_word(value=bitarray("1111110000111111"))
        self.registers[7].set_word(value=bitarray("0000000100000000"))

        self.memory = Memory()
        self.memory.store(address=510, size="word", value=bitarray("0101010100001111"))
        self.memory.store(address=128, size="word", value=bitarray("0000000111111110"))
        self.memory.store(address=21774, size="word", value=bitarray("1111111111111111"))

        self.ps = ProgramStatus()
        self.ps.set(bit="N", value=True)
        self.ps.set(bit="C", value=True)
        self.cpu = CPU(memory=self.memory, registers=self.registers, program_status=self.ps)

    def test_clr_program_status_correct(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101000000001"))
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=False, Z=True, C=False, V=False))

    def test_clr_word_mode_0_reg_general_purpose(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101000000001"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000000000000")

    def test_clr_byte_mode_0_reg_general_purpose(self):
        self.memory.store(address=256, size="word", value=bitarray("1000101000000001"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000000000000")

    def test_clr_word_mode_1_reg_general_purpose(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101000001001"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000010000000")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000000000000")

    def test_clr_byte_mode_1_reg_general_purpose(self):
        self.memory.store(address=256, size="word", value=bitarray("1000101000001001"))
        self.registers[1].set_word(value=bitarray("0000000010000001"))
        self.cpu.execute_next()
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000011111110")

    def test_clr_word_mode_2_reg_general_purpose(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101000010001"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000010000010")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000000000000")

    def test_clr_byte_mode_2_reg_general_purpose(self):
        self.memory.store(address=256, size="word", value=bitarray("1000101000010001"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000010000001")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000100000000")

    def test_clr_word_mode_3_reg_general_purpose(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101000011001"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000010000010")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000111111110")
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0000000000000000")

    def test_clr_byte_mode_3_reg_general_purpose(self):
        self.memory.store(address=256, size="word", value=bitarray("1000101000011001"))
        self.memory.store(address=128, size="word", value=bitarray("0000000111111111"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000010000010")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000111111111")
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0000000000001111")

    def test_clr_word_mode_4_reg_general_purpose(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101000100001"))
        self.registers[1].set_word(value=bitarray("0000000010000010"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000010000000")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000000000000")

    def test_clr_byte_mode_4_reg_general_purpose(self):
        self.memory.store(address=256, size="word", value=bitarray("1000101000100001"))
        self.registers[1].set_word(value=bitarray("0000000010000010"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000010000001")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000011111110")

    def test_clr_word_mode_5_reg_general_purpose(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101000101001"))
        self.registers[1].set_word(value=bitarray("0000000010000010"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000010000000")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000111111110")
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0000000000000000")

    def test_clr_byte_mode_5_reg_general_purpose(self):
        self.memory.store(address=256, size="word", value=bitarray("1000101000101001"))
        self.registers[1].set_word(value=bitarray("0000000010000010"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000010000000")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000111111110")
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0101010100000000")

    def test_clr_word_mode_6_reg_general_purpose(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101000110001"))
        self.memory.store(address=258, size="word", value=bitarray("0000000000000100"))
        self.registers[1].set_word(value=bitarray("0000000001111100"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000001111100")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000000000000")
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)

    def test_clr_byte_mode_6_reg_general_purpose(self):
        self.memory.store(address=256, size="word", value=bitarray("1000101000110001"))
        self.memory.store(address=258, size="word", value=bitarray("0000000000000101"))
        self.registers[1].set_word(value=bitarray("0000000001111100"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000001111100")
        self.assertEqual(self.memory.load(address=258, size="word").to01(), "0000000000000101")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000011111110")

    def test_clr_word_mode_7_reg_general_purpose(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101000111001"))
        self.memory.store(address=258, size="word", value=bitarray("0000000000000100"))
        self.registers[1].set_word(value=bitarray("0000000001111100"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[1].word().to01(), "0000000001111100")
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000111111110")
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0000000000000000")

    def test_clr_byte_mode_7_reg_general_purpose(self):
        self.memory.store(address=256, size="word", value=bitarray("1000101000111001"))
        self.memory.store(address=258, size="word", value=bitarray("0000000000000100"))
        self.memory.store(address=128, size="word", value=bitarray("0000000111111111"))
        self.registers[1].set_word(value=bitarray("0000000001111100"))
        self.cpu.execute_next()
        self.assertEqual(self.memory.load(address=128, size="word").to01(), "0000000111111111")
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0000000000001111")

    def test_clr_word_mode_2_reg_pc(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101000010111"))
        self.memory.store(address=258, size="word", value=bitarray("0000010101111111"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)
        self.assertEqual(self.memory.load(address=258, size="word").to01(), "0000000000000000")

    def test_clr_byte_mode_2_reg_pc(self):
        self.memory.store(address=256, size="word", value=bitarray("1000101000010111"))
        self.memory.store(address=258, size="word", value=bitarray("0000010101111111"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)
        self.assertEqual(self.memory.load(address=258, size="word").to01(), "0000010100000000")

    def test_clr_word_mode_3_reg_pc(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101000011111"))
        self.memory.store(address=258, size="word", value=bitarray("0000000111111110"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0000000000000000")

    def test_clr_byte_mode_3_reg_pc(self):
        self.memory.store(address=256, size="word", value=bitarray("1000101000011111"))
        self.memory.store(address=258, size="word", value=bitarray("0000000111111110"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0101010100000000")

    def test_clr_word_mode_6_reg_pc(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101000110111"))
        self.memory.store(address=258, size="word", value=bitarray("0000000011111010"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0000000000000000")

    def test_clr_byte_mode_6_reg_pc(self):
        self.memory.store(address=256, size="word", value=bitarray("1000101000110111"))
        self.memory.store(address=258, size="word", value=bitarray("0000000011111011"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0000000000001111")

    def test_clr_low_byte_mode_7_reg_pc(self):
        self.memory.store(address=256, size="word", value=bitarray("1000101000111111"))
        self.memory.store(address=258, size="word", value=bitarray("0000000011111010"))
        self.memory.store(address=510, size="word", value=bitarray("0101010100001110"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0101010100001110")
        self.assertEqual(self.memory.load(address=21774, size="word").to01(), "1111111100000000")

    def test_clr_high_byte_mode_7_reg_pc(self):
        self.memory.store(address=256, size="word", value=bitarray("1000101000111111"))
        self.memory.store(address=258, size="word", value=bitarray("0000000011111010"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].get(size="word", signed=False), 260)
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "0101010100001111")
        self.assertEqual(self.memory.load(address=21774, size="word").to01(), "0000000011111111")

    def test_com_positive(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101001000010"))
        self.ps.clear()
        self.ps.set(bit="Z", value=True)
        self.ps.set(bit="V", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=1, Z=0, C=1, V=0))
        self.assertEqual(self.registers[2].word().to01(), "1000000011110000")

    def test_inc_not_overflow(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101010000010"))
        self.registers[2].set_word(value=bitarray("1111111111111111"))
        self.ps.clear()
        self.ps.set(bit="N", value=True)
        self.ps.set(bit="V", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=0, Z=1, C=0, V=0))
        self.assertEqual(self.registers[2].word().to01(), "0000000000000000")

    def test_inc_overflow(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101010000010"))
        self.registers[2].set_word(value=bitarray("0111111111111111"))
        self.ps.clear()
        self.ps.set(bit="Z", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=1, Z=0, C=0, V=1))
        self.assertEqual(self.registers[2].word().to01(), "1000000000000000")

    def test_dec_not_overflow(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101011000010"))
        self.registers[2].set_word(value=bitarray("0000000000000001"))
        self.ps.clear()
        self.ps.set(bit="N", value=True)
        self.ps.set(bit="V", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=0, Z=1, C=0, V=0))
        self.assertEqual(self.registers[2].word().to01(), "0000000000000000")

    def test_dec_overflow(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101011000010"))
        self.registers[2].set_word(value=bitarray("1000000000000000"))
        self.ps.clear()
        self.ps.set(bit="N", value=True)
        self.ps.set(bit="Z", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=0, Z=0, C=0, V=1))
        self.assertEqual(self.registers[2].word().to01(), "0111111111111111")

    def test_neg_positive(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101100000010"))
        self.registers[2].set_word(value=bitarray("0111111111111111"))
        self.ps.clear()
        self.ps.set(bit="Z", value=True)
        self.ps.set(bit="V", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=1, Z=0, C=1, V=0))
        self.assertEqual(self.registers[2].word().to01(), "1000000000000001")

    def test_neg_min_int(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101100000010"))
        self.registers[2].set_word(value=bitarray("1000000000000000"))
        self.ps.clear()
        self.ps.set(bit="Z", value=True)
        self.ps.set(bit="N", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=1, Z=0, C=1, V=1))
        self.assertEqual(self.registers[2].word().to01(), "1000000000000000")

    def test_neg_zero(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101100000010"))
        self.registers[2].set_word(value=bitarray("0000000000000000"))
        self.ps.clear()
        self.ps.set(bit="C", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=0, Z=1, C=0, V=0))
        self.assertEqual(self.registers[2].word().to01(), "0000000000000000")

    def test_test_negative(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101111000010"))
        self.registers[2].set_word(value=bitarray("1000000000000000"))
        self.ps.clear()
        self.ps.set(bit="C", value=True)
        self.ps.set(bit="V", value=True)
        self.ps.set(bit="Z", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=1, Z=0, C=0, V=0))
        self.assertEqual(self.registers[2].word().to01(), "1000000000000000")

    def test_asr_negative(self):
        self.memory.store(address=256, size="word", value=bitarray("0000110010000010"))
        self.registers[2].set_word(value=bitarray("1011000000000001"))
        self.ps.clear()
        self.ps.set(bit="V", value=True)
        self.ps.set(bit="Z", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=1, Z=0, C=1, V=0))
        self.assertEqual(self.registers[2].word().to01(), "1101100000000000")

    def test_asr_positive(self):
        self.memory.store(address=256, size="word", value=bitarray("0000110010000010"))
        self.registers[2].set_word(value=bitarray("0000000000000001"))
        self.ps.clear()
        self.ps.set(bit="N", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=0, Z=1, C=1, V=1))
        self.assertEqual(self.registers[2].word().to01(), "0000000000000000")

    def test_asl_negative(self):
        self.memory.store(address=256, size="word", value=bitarray("0000110011000010"))
        self.registers[2].set_word(value=bitarray("1011000000000001"))
        self.ps.clear()
        self.ps.set(bit="N", value=True)
        self.ps.set(bit="Z", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=0, Z=0, C=1, V=1))
        self.assertEqual(self.registers[2].word().to01(), "0110000000000010")

    def test_asl_positive(self):
        self.memory.store(address=256, size="word", value=bitarray("0000110011000010"))
        self.registers[2].set_word(value=bitarray("0100000000000000"))
        self.ps.clear()
        self.ps.set(bit="Z", value=True)
        self.ps.set(bit="C", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=1, Z=0, C=0, V=1))
        self.assertEqual(self.registers[2].word().to01(), "1000000000000000")

    def test_ror(self):
        self.memory.store(address=256, size="word", value=bitarray("0000110000000010"))
        self.registers[2].set_word(value=bitarray("0011000000000001"))
        self.ps.clear()
        self.ps.set(bit="C", value=True)
        self.ps.set(bit="V", value=True)
        self.ps.set(bit="Z", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=1, Z=0, C=1, V=0))
        self.assertEqual(self.registers[2].word().to01(), "1001100000000000")

    def test_rol(self):
        self.memory.store(address=256, size="word", value=bitarray("0000110001000010"))
        self.registers[2].set_word(value=bitarray("1100000000000000"))
        self.ps.clear()
        self.ps.set(bit="V", value=True)
        self.ps.set(bit="Z", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=1, Z=0, C=1, V=0))
        self.assertEqual(self.registers[2].word().to01(), "1000000000000000")

    def test_swab(self):
        self.memory.store(address=256, size="word", value=bitarray("0000000011000010"))
        self.registers[2].set_word(value=bitarray("1111111100000000"))
        self.ps.clear()
        self.ps.set(bit="V", value=True)
        self.ps.set(bit="C", value=True)
        self.ps.set(bit="Z", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=1, Z=0, C=0, V=0))
        self.assertEqual(self.registers[2].word().to01(), "0000000011111111")

    def test_adc_unsigned_overflow(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101101000010"))
        self.registers[2].set_word(value=bitarray("1111111111111111"))
        self.ps.clear()
        self.ps.set(bit="C", value=True)
        self.ps.set(bit="V", value=True)
        self.ps.set(bit="N", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=0, Z=1, C=1, V=0))
        self.assertEqual(self.registers[2].word().to01(), "0000000000000000")

    def test_adc_signed_overflow(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101101000010"))
        self.registers[2].set_word(value=bitarray("0111111111111111"))
        self.ps.clear()
        self.ps.set(bit="C", value=True)
        self.ps.set(bit="Z", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=1, Z=0, C=0, V=1))
        self.assertEqual(self.registers[2].word().to01(), "1000000000000000")

    def test_sbc_unsigned_overflow(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101110000010"))
        self.registers[2].set_word(value=bitarray("0000000000000000"))
        self.ps.clear()
        self.ps.set(bit="V", value=True)
        self.ps.set(bit="Z", value=True)
        self.ps.set(bit="C", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=1, Z=0, C=0, V=0))
        self.assertEqual(self.registers[2].word().to01(), "1111111111111111")

    def test_sbc_signed_overflow(self):
        self.memory.store(address=256, size="word", value=bitarray("0000101110000010"))
        self.registers[2].set_word(value=bitarray("1000000000000000"))
        self.ps.clear()
        self.ps.set(bit="C", value=True)
        self.ps.set(bit="N", value=True)
        self.ps.set(bit="Z", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=0, Z=0, C=1, V=1))
        self.assertEqual(self.registers[2].word().to01(), "0111111111111111")

    def test_sxt_set(self):
        self.memory.store(address=256, size="word", value=bitarray("0000110111000010"))
        self.registers[2].set_word(value=bitarray("1000010000011011"))
        self.ps.clear()
        self.ps.set(bit="V", value=True)
        self.ps.set(bit="N", value=True)
        self.ps.set(bit="Z", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=1, Z=0, C=0, V=1))
        self.assertEqual(self.registers[2].word().to01(), "1111111111111111")

    def test_sxt_cleared(self):
        self.memory.store(address=256, size="word", value=bitarray("0000110111000010"))
        self.registers[2].set_word(value=bitarray("1000010000011011"))
        self.ps.clear()
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=0, Z=1, C=0, V=0))
        self.assertEqual(self.registers[2].word().to01(), "0000000000000000")

    def test_mov_byte_reg(self):
        self.memory.store(address=256, size="word", value=bitarray("1001010111000010"))
        self.memory.store(address=258, size="word", value=bitarray("0000000011000000"))
        self.registers[2].set_word(value=bitarray("1000010101111011"))
        self.ps.clear()
        self.ps.set(bit="Z", value=True)
        self.ps.set(bit="V", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=1, Z=0, C=0, V=0))
        self.assertEqual(self.registers[2].word().to01(), "1111111111000000")

    def test_mov_byte_not_reg(self):
        self.memory.store(address=256, size="word", value=bitarray("1001010111001010"))
        self.memory.store(address=258, size="word", value=bitarray("0000001111000000"))
        self.registers[2].set_word(value=bitarray("0000000111111111"))
        self.ps.clear()
        self.ps.set(bit="Z", value=True)
        self.ps.set(bit="V", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=1, Z=0, C=0, V=0))
        self.assertEqual(self.registers[2].word().to01(), "0000000111111111")
        self.assertEqual(self.memory.load(address=510, size="word").to01(), "1100000000001111")

    def test_cmp_v_set_c_clear(self):
        self.memory.store(address=256, size="word", value=bitarray("0010000011000010"))
        self.registers[3].set_word(value=bitarray("1000100010100101"))
        self.registers[2].set_word(value=bitarray("0111111111111111"))
        self.ps.clear()
        self.ps.set(bit="Z", value=True)
        self.ps.set(bit="C", value=True)
        self.ps.set(bit="N", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=0, Z=0, C=0, V=1))
        self.assertEqual(self.registers[3].word().to01(), "1000100010100101")
        self.assertEqual(self.registers[2].word().to01(), "0111111111111111")

    def test_cmp_v_set_c_set(self):
        self.memory.store(address=256, size="word", value=bitarray("0010000011000010"))
        self.registers[3].set_word(value=bitarray("0000000010100101"))
        self.registers[2].set_word(value=bitarray("1000000000000000"))
        self.ps.clear()
        self.ps.set(bit="Z", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=1, Z=0, C=1, V=1))

    def test_add_v_set_c_set(self):
        self.memory.store(address=256, size="word", value=bitarray("0110000011000010"))
        self.registers[3].set_word(value=bitarray("1000000000000001"))
        self.registers[2].set_word(value=bitarray("1000000000000000"))
        self.ps.clear()
        self.ps.set(bit="N", value=True)
        self.ps.set(bit="Z", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=0, Z=0, C=1, V=1))

    def test_sub_v_set_c_set(self):
        self.memory.store(address=256, size="word", value=bitarray("1110000011000010"))
        self.registers[2].set_word(value=bitarray("1000100010100101"))
        self.registers[3].set_word(value=bitarray("0111111111111111"))
        self.ps.clear()
        self.ps.set(bit="Z", value=True)
        self.ps.set(bit="C", value=True)
        self.ps.set(bit="N", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=0, Z=0, C=0, V=1))
        self.assertEqual(self.registers[3].word().to01(), "0111111111111111")
        self.assertEqual(self.registers[2].word().to01(), "0000100010100110")

    def test_bit(self):
        self.memory.store(address=256, size="word", value=bitarray("0011000011000010"))
        self.registers[2].set_word(value=bitarray("1000100010100101"))
        self.registers[3].set_word(value=bitarray("0111011101011010"))
        self.ps.clear()
        self.ps.set(bit="V", value=True)
        self.ps.set(bit="N", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=0, Z=1, C=0, V=0))
        self.assertEqual(self.registers[3].word().to01(), "0111011101011010")
        self.assertEqual(self.registers[2].word().to01(), "1000100010100101")

    def test_bic(self):
        self.memory.store(address=256, size="word", value=bitarray("0100000011000010"))
        self.registers[2].set_word(value=bitarray("1000100010100101"))
        self.registers[3].set_word(value=bitarray("0111011111011010"))
        self.ps.clear()
        self.ps.set(bit="Z", value=True)
        self.ps.set(bit="V", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=1, Z=0, C=0, V=0))
        self.assertEqual(self.registers[3].word().to01(), "0111011111011010")
        self.assertEqual(self.registers[2].word().to01(), "1000100000100101")

    def test_bis(self):
        self.memory.store(address=256, size="word", value=bitarray("0101000011000010"))
        self.registers[2].set_word(value=bitarray("1000100010100101"))
        self.registers[3].set_word(value=bitarray("0111011111011010"))
        self.ps.clear()
        self.ps.set(bit="Z", value=True)
        self.ps.set(bit="V", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=1, Z=0, C=0, V=0))
        self.assertEqual(self.registers[3].word().to01(), "0111011111011010")
        self.assertEqual(self.registers[2].word().to01(), "1111111111111111")

    def test_xor(self):
        self.memory.store(address=256, size="word", value=bitarray("0111100011000010"))
        self.registers[2].set_word(value=bitarray("1000100010100101"))
        self.registers[3].set_word(value=bitarray("0111011111011010"))
        self.ps.clear()
        self.ps.set(bit="Z", value=True)
        self.ps.set(bit="V", value=True)
        self.cpu.execute_next()
        self.assertEqual(self.ps.bits, dict(N=1, Z=0, C=0, V=0))
        self.assertEqual(self.registers[3].word().to01(), "0111011111011010")
        self.assertEqual(self.registers[2].word().to01(), "1111111101111111")

    def test_br_positive(self):
        self.memory.store(address=256, size="word", value=bitarray("0000000100000001"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].word().to01(), "0000000100000100")

    def test_br_negative(self):
        self.memory.store(address=256, size="word", value=bitarray("0000000111111111"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].word().to01(), "0000000100000000")

    def test_jmp(self):
        self.memory.store(address=256, size="word", value=bitarray("0000000001001010"))
        self.registers[2].set_word(value=bitarray("1000100010100100"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].word().to01(), "1000100010100100")

    def test_jsr(self):
        self.memory.store(address=256, size="word", value=bitarray("0000100101001010"))
        self.registers[2].set_word(value=bitarray("0001110010100100"))
        self.registers[5].set_word(value=bitarray("1000100010100100"))
        self.registers[6].set_word(value=bitarray("1111111111111110"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[5].word().to01(), "0000000100000010")
        self.assertEqual(self.registers[6].word().to01(), "1111111111111100")
        self.assertEqual(self.registers[7].word().to01(), "0001110010100100")
        self.assertEqual(self.memory.load(address=65532, size="word").to01(), "1000100010100100")

    def test_rts(self):
        self.memory.store(address=256, size="word", value=bitarray("0000000010000101"))
        self.memory.store(address=65532, size="word", value=bitarray("0101001111111111"))
        self.registers[5].set_word(value=bitarray("1000100010100100"))
        self.registers[6].set_word(value=bitarray("1111111111111100"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[5].word().to01(), "0101001111111111")
        self.assertEqual(self.registers[6].word().to01(), "1111111111111110")
        self.assertEqual(self.registers[7].word().to01(), "1000100010100100")

    def test_mark(self):
        self.memory.store(address=256, size="word", value=bitarray("0000110100000010"))
        self.memory.store(address=65532, size="word", value=bitarray("0101001111111111"))
        self.registers[5].set_word(value=bitarray("1000100010100100"))
        self.registers[6].set_word(value=bitarray("1111111111111000"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[5].word().to01(), "0101001111111111")
        self.assertEqual(self.registers[6].word().to01(), "1111111111111110")
        self.assertEqual(self.registers[7].word().to01(), "1000100010100100")

    def test_sob_zero(self):
        self.memory.store(address=256, size="word", value=bitarray("0111111010000010"))
        self.registers[2].set_word(value=bitarray("0000000000000001"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].word().to01(), "0000000011111110")

    def test_sob_non_zero(self):
        self.memory.store(address=256, size="word", value=bitarray("0111111010000010"))
        self.registers[2].set_word(value=bitarray("0000000000000010"))
        self.cpu.execute_next()
        self.assertEqual(self.registers[7].word().to01(), "0000000100000010")


if __name__ == "__main__":
    unittest.main()

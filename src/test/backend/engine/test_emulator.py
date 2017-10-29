import unittest
from bitarray import bitarray

from src.backend.engine.emulator import Emulator
from src.backend.model.memory import Memory


class EmulatorDisasmTest(unittest.TestCase):
    def setUp(self):
        self.emu = Emulator()

    def test_two_instructions(self):
        self.emu.memory.store(address=Memory.Part.ROM.start, size="word", value=bitarray("0001011111000010"))
        self.emu.memory.store(address=Memory.Part.ROM.start + 2, size="word", value=bitarray("0000000011000000"))
        self.emu.memory.store(address=Memory.Part.ROM.start + 4, size="word", value=bitarray("0111111010000010"))
        self.emu._end_instructions = Memory.Part.ROM.start + 6
        self.emu._disasm_from_to(Memory.Part.ROM.start, Memory.Part.ROM.start + 6)
        self.assertEqual(self.emu.disasm(address=Memory.Part.ROM.start)[0], "MOV @#300, R2")
        self.assertEqual(self.emu.disasm(address=Memory.Part.ROM.start+2)[0], None)
        self.assertEqual(self.emu.disasm(address=Memory.Part.ROM.start+4)[0], "SOB R2, 2")

    def test_not_an_instruction(self):
        self.emu.memory.store(address=Memory.Part.ROM.start, size="word", value=bitarray("1111111111111111"))
        self.emu.memory.store(address=Memory.Part.ROM.start + 2, size="word", value=bitarray("0000110100111111"))
        self.emu.memory.store(address=Memory.Part.ROM.start, size="word", value=bitarray("1111111111111111"))
        self.emu._end_instructions = Memory.Part.ROM.start + 6
        self.emu._disasm_from_to(Memory.Part.ROM.start, Memory.Part.ROM.start + 6)
        self.assertEqual(self.emu.disasm(address=Memory.Part.ROM.start)[0], "Not an instruction")
        self.assertEqual(self.emu.disasm(address=Memory.Part.ROM.start + 2)[0], "MARK 77")
        self.assertEqual(self.emu.disasm(address=Memory.Part.ROM.start + 4)[0], "Not an instruction")

    def test_instruction_in_6_bytes(self):
        self.emu.memory.store(address=Memory.Part.ROM.start, size="word", value=bitarray("1010010111111100"))
        self.emu.memory.store(address=Memory.Part.ROM.start + 2, size="word", value=bitarray("1111111111000000"))
        self.emu.memory.store(address=Memory.Part.ROM.start + 4, size="word", value=bitarray("1111111111111111"))
        self.emu._end_instructions = Memory.Part.ROM.start + 6
        self.emu._disasm_from_to(Memory.Part.ROM.start, Memory.Part.ROM.start + 6)
        self.assertEqual(self.emu.disasm(address=Memory.Part.ROM.start)[0], "CMPB #300, @177777(R4)")

    def test_jsr_with_decrement(self):
        self.emu.memory.store(address=Memory.Part.ROM.start, size="word", value=bitarray("0000100111101000"))
        self.emu._end_instructions = Memory.Part.ROM.start + 2
        self.emu._disasm_from_to(Memory.Part.ROM.start, Memory.Part.ROM.start + 2)
        self.assertEqual(self.emu.disasm(address=Memory.Part.ROM.start)[0], "JSR PC, @-(R0)")

    def test_branch(self):
        self.emu.memory.store(address=Memory.Part.ROM.start, size="word", value=bitarray("0000000111111111"))
        self.emu._end_instructions = Memory.Part.ROM.start + 2
        self.emu._disasm_from_to(Memory.Part.ROM.start, Memory.Part.ROM.start + 2)
        self.assertEqual(self.emu.disasm(address=Memory.Part.ROM.start)[0], "BR -1")

    def test_jmp(self):
        self.emu.memory.store(address=Memory.Part.ROM.start, size="word", value=bitarray("0000000001011010"))
        self.emu._end_instructions = Memory.Part.ROM.start + 2
        self.emu._disasm_from_to(Memory.Part.ROM.start, Memory.Part.ROM.start + 2)
        self.assertEqual(self.emu.disasm(address=Memory.Part.ROM.start)[0], "JMP @(R2)+")

    def test_rts(self):
        self.emu.memory.store(address=Memory.Part.ROM.start, size="word", value=bitarray("0000000010000101"))
        self.emu._end_instructions = Memory.Part.ROM.start + 2
        self.emu._disasm_from_to(Memory.Part.ROM.start, Memory.Part.ROM.start + 2)
        self.assertEqual(self.emu.disasm(address=Memory.Part.ROM.start)[0], "RTS R5")

    def test_xor(self):
        self.emu.memory.store(address=Memory.Part.ROM.start, size="word", value=bitarray("0111100101001010"))
        self.emu._end_instructions = Memory.Part.ROM.start + 2
        self.emu._disasm_from_to(Memory.Part.ROM.start, Memory.Part.ROM.start + 2)
        self.assertEqual(self.emu.disasm(address=Memory.Part.ROM.start)[0], "XOR R5, (R2)")

    def test_clr_byte(self):
        self.emu.memory.store(address=Memory.Part.ROM.start, size="word", value=bitarray("1000101000000000"))
        self.emu._end_instructions = Memory.Part.ROM.start + 2
        self.emu._disasm_from_to(Memory.Part.ROM.start, Memory.Part.ROM.start + 2)
        self.assertEqual(self.emu.disasm(address=Memory.Part.ROM.start)[0], "CLRB R0")


if __name__ == "__main__":
    unittest.main()

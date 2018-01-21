import unittest

from bitarray import bitarray

from src.backend.engine.cash import CashMemory
from src.backend.model.memory import Memory


class CashTest(unittest.TestCase):
    def setUp(self):
        self.memory = Memory()
        self.cash = CashMemory(memory=self.memory)

    def test_load(self):
        self.assertEqual(self.cash.load(address=0b0000000000001010, size="word"), (False, None))
        for _ in range(29):
            self.assertEqual(self.cash.cycle(), False)

        self.assertEqual(self.cash.cycle(), True)

    def test_store(self):
        self.assertEqual(self.cash.store(address=0b0000000000001010, size="byte",
                                         value=bitarray("01010101")), False)
        for _ in range(29):
            self.assertEqual(self.cash.cycle(), False)

        self.assertEqual(self.cash.cycle(), True)

    def test_preferred_address(self):
        self.cash.store(address=0b0000000000001010, size="byte", value=bitarray("01010101"))
        for _ in range(30):
            self.cash.cycle()

        self.assertEqual(self.cash.store(address=0b0000000000001011, size="byte",
                                         value=bitarray("01010101")), False)
        self.assertEqual(self.cash.store(address=0b0000000000001010, size="byte",
                                         value=bitarray("01010101")), True)
        self.assertEqual(self.cash.store(address=0b0000000000001011, size="byte",
                                         value=bitarray("01010101")), True)

    def test_eject_modified(self):
        self.cash.store(address=0b0000001000001010, size="byte", value=bitarray("01010101"))
        for _ in range(30):
            self.cash.cycle()
        self.cash.store(address=0b0000001000001010, size="byte", value=bitarray("01010101"))

        self.cash.store(address=0b0000010000001010, size="byte", value=bitarray("01010101"))
        for _ in range(30):
            self.cash.cycle()
        self.cash.store(address=0b0000010000001010, size="byte", value=bitarray("01010101"))

        self.cash.store(address=0b0000100000001010, size="byte", value=bitarray("01010101"))
        for _ in range(59):
            self.assertEqual(self.cash.cycle(), False)
        self.assertEqual(self.cash.cycle(), True)
        self.cash.store(address=0b0000100000001010, size="byte", value=bitarray("01010101"))


        self.assertEqual(self.cash.load(address=0b0000010000001010, size="byte"), (True, bitarray("01010101")))
        self.assertEqual(self.cash.load(address=0b0000100000001010, size="byte"), (True, bitarray("01010101")))
        self.assertEqual(self.cash.load(address=0b0000001000001010, size="byte"), (False, None))

    def test_hits_misses(self):
        self.cash.store(address=0b0000000000001010, size="byte", value=bitarray("01010101"))
        for _ in range(30):
            self.cash.cycle()

        self.assertEqual(self.cash.store(address=0b0000000000001010, size="byte",
                                         value=bitarray("01010101")), True)

        self.assertEqual(self.cash.store(address=0b0000000000001011, size="byte",
                                         value=bitarray("01010101")), True)

        self.assertEqual(self.cash.load(address=0b0000000000001011, size="byte"), (True, bitarray("01010101")))

        self.assertEqual(self.cash.hits, 2)
        self.assertEqual(self.cash.misses, 1)

    def test_block(self):
        self.assertEqual(self.cash.block(address=0b0000000000001010, block=True), False)
        for _ in range(29):
            self.assertEqual(self.cash.cycle(), False)
        self.assertEqual(self.cash.cycle(), True)
        self.assertEqual(self.cash.block(address=0b0000000000001010, block=True), True)

        self.assertEqual(self.cash.store(address=0b0000000000001010, size="byte",
                                         value=bitarray("01010101")), True)

        self.assertEqual(self.cash.load(address=0b0000000000001010, size="byte"), (False, None))
        self.cash.block(address=0b0000000000001010, block=False)
        self.assertEqual(self.cash.load(address=0b0000000000001010, size="byte"), (True, bitarray("01010101")))

    def test_load_store_device(self):
        self.assertEqual(self.cash.store(address=16*1024, size="byte", value=bitarray("01010101")), False)
        for _ in range(30):
            self.cash.cycle()
        self.assertEqual(self.cash.load(address=16 * 1024, size="byte"), (False, None))
        self.assertEqual(self.cash.store(address=16 * 1024, size="byte", value=bitarray("01010101")), True)

        self.assertEqual(self.cash.load(address=16 * 1024, size="byte"), (False, None))
        for _ in range(30):
            self.cash.cycle()
        self.assertEqual(self.cash.store(address=16 * 1024, size="byte", value=bitarray("01010101")),
                         False)
        self.assertEqual(self.cash.load(address=16 * 1024, size="byte"), (True, bitarray("01010101")))

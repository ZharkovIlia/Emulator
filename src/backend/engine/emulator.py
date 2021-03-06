from src.backend.engine.cash import CashMemory
from src.backend.engine.keyboard import Keyboard
from src.backend.engine.pipe import Pipe
from src.backend.engine.pool_registers import PoolRegisters
from src.backend.model.commands import Commands
from src.backend.model.video import VideoMode
from src.backend.utils.assembler import Assembler
from src.backend.utils.exceptions import EmulatorOddBreakpoint, EmulatorWrongAddress, \
    UnknownCommand, EmulatorWrongConfiguration
from src.backend.utils.disasm_instruction import DisasmInstruction, DisasmState
from src.backend.utils.romfiller import ROMFiller

from src.backend.model.memory import Memory, MemoryPart
from src.backend.model.registers import Register, StackPointer, ProgramCounter
from src.backend.model.programstatus import ProgramStatus

from src.backend.utils.routines import Routines


class Emulator:
    SIZE_FONT_16_WIDTH = 26
    MAX_INIT_LENGTH = 100

    def __init__(self, video_on_show=None):
        self._memory = Memory()
        self._memory.video.set_on_show(video_on_show)

        self._registers = list(Register() for _ in range(6))
        self._pc = ProgramCounter()
        self._sp = StackPointer()
        self._registers.append(self._sp)
        self._registers.append(self._pc)
        self._pc.set(size="word", signed=False, value=MemoryPart.ROM.start)
        self._sp.set_upper_bound(MemoryPart.RAM.end)
        self._sp.set_lower_bound(256)

        self._program_status = ProgramStatus()

        self._breakpoints = set()
        self._instructions = {}
        self._commands = {}

        self._fill_ROM()
        self._icash = CashMemory(self._memory)
        self._dcash = CashMemory(self._memory)
        self._pool_registers = PoolRegisters(self._registers)
        self._pipe = Pipe(dmem=self._dcash, imem=self._icash, pool_registers=self._pool_registers,
                          ps=self._program_status, commands=self._commands, enabled=True)

        self._keyboard = Keyboard(register=self._memory.keyboard_register, pipe=self._pipe, memory=self._memory,
                                  program_status=self._program_status, program_counter=self._pc, stack_pointer=self._sp)
        self.stopped = False
        self._writing_glyph = False

    @property
    def keyboard(self):
        return self._keyboard

    @property
    def pipe(self):
        return self._pipe

    @property
    def icash(self):
        return self._icash

    @property
    def dcash(self):
        return self._dcash

    def step(self):
        while True:
            if self._keyboard.interrupt_permitted and self._writing_glyph:
                self._writing_glyph = False
                self._memory.video.show()

            if self._keyboard.interrupt():
                self._writing_glyph = True
                return

            if self._pipe.cycle():
                return

    def run(self):
        while True:
            self.step()
            if self.current_pc in self._breakpoints or self.stopped:
                break

    def toggle_breakpoint(self, address: int):
        if address % 2 == 1 or address < 0 or address >= Memory.SIZE:
            raise EmulatorOddBreakpoint()

        if address in self._breakpoints:
            self._breakpoints.remove(address)
        else:
            self._breakpoints.add(address)

    def breakpoint(self, address: int, set: bool):
        if set != (address in self._breakpoints):
            self.toggle_breakpoint(address)

    def disasm(self, address: int, num: int, type: str) -> list:
        if address % 2 == 1 or address < 0 or address >= Memory.SIZE:
            raise EmulatorWrongAddress(address)

        assert type in ("octal", "instructions")

        result = []
        if num <= 0:
            return result

        if type == "instructions":
            while address in self._instructions and self._instructions[address].state is DisasmState.PART_OF_PREVIOUS:
                address -= 2

        while len(result) < num and address < Memory.SIZE:
            breakpoint_set = address in self._breakpoints
            if type == "octal":
                dis_instr = DisasmInstruction()
                dis_instr.set_state(state=DisasmState.NOT_AN_INSTRUCTION,
                                    representation="{:06o}".format(
                                        int(self._memory.load(size="word", address=address).to01(), 2)
                                    ))
                result.append((address, dis_instr, breakpoint_set))

            elif address not in self._instructions:
                result.append((address, DisasmInstruction(), breakpoint_set))

            else:
                result.append((address, self._instructions[address], breakpoint_set))
                address += self._instructions[address].num_next * 2

            address += 2

        address = result[0][0]
        while len(result) < num and address > 0:
            address -= 2
            breakpoint_set = address in self._breakpoints
            if type == "octal":
                dis_instr = DisasmInstruction()
                dis_instr.set_state(state=DisasmState.NOT_AN_INSTRUCTION,
                                    representation="{:06o}".format(
                                        int(self._memory.load(size="word", address=address).to01(), 2)
                                    ))
                result.insert(0, (address, dis_instr, breakpoint_set))

            elif address not in self._instructions:
                result.insert(0, (address, DisasmInstruction(), breakpoint_set))

            else:
                address -= self._instructions[address].num_next * 2
                breakpoint_set = address in self._breakpoints
                result.insert(0, (address, self._instructions[address], breakpoint_set))

        return result

    @property
    def memory(self) -> Memory:
        return self._memory

    @property
    def registers(self) -> list:
        return self._registers

    @property
    def program_status(self) -> ProgramStatus:
        return self._program_status

    @property
    def current_pc(self) -> int:
        return self._pipe.last_instruction_address

    def _fill_ROM(self):
        self._glyphs = ROMFiller.get_glyphs(size=self.SIZE_FONT_16_WIDTH)
        self._glyphs_start = MemoryPart.ROM.end - len(self._glyphs["data"])
        for i, v in enumerate(self._glyphs["data"]):
            self._memory.store(address=self._glyphs_start + i, size="byte", value=v)

        init_start = MemoryPart.ROM.start
        draw_glyph_start = init_start + self.MAX_INIT_LENGTH
        draw_glyph = Routines.draw_glyph_mode_0(glyphs_start=self._glyphs_start, glyph_width=self._glyphs["width"],
                                                glyph_max_height=self._glyphs["max_height"],
                                                glyph_height=self._glyphs["min_height"],
                                                glyph_bitmap_size=self._glyphs["bitmap_size"],
                                                monitor_width=self._memory.video.mode.width,
                                                video_start=MemoryPart.VRAM.start,
                                                monitor_depth=self._memory.video.mode.depth)

        draw_glyph_end = draw_glyph_start + len(draw_glyph) * 2

        print_help_message = Routines.\
            print_help_message(draw_glyph_start=draw_glyph_start,
                               monitor_structure_start=self._sp.lower_bound,
                               video_register_offset_address=self._memory.video_register_offset_address)

        print_help_message_start = draw_glyph_end
        print_help_message_end = print_help_message_start + len(print_help_message) * 2

        keyboard_interrupt_start = print_help_message_end

        init = Routines.init(VRAM_start=MemoryPart.VRAM.start,
                             video_register_mode_start_address=self._memory.video_register_mode_start_address,
                             video_register_offset_address=self._memory.video_register_offset_address,
                             video_mode=VideoMode.MODE_O.mode, video_start=MemoryPart.VRAM.start,
                             keyboard_register_address=self._memory.keyboard_register_address,
                             keyboard_interrupt_subroutine_address=keyboard_interrupt_start,
                             monitor_structure_start=self._sp.lower_bound)

        init_end = init_start + len(init) * 2 + 4
        if init_end > draw_glyph_start:
            raise EmulatorWrongConfiguration(what="init is too long")

        assert self._memory.video.mode.width % self._glyphs["width"] == 0

        keyboard_interrupt = Routines.\
            keyboard_interrupt(keyboard_register_address=self._memory.keyboard_register_address,
                               monitor_structure_start=self._sp.lower_bound,
                               draw_glyph_start=draw_glyph_start, init_start=init_start,
                               glyph_height=self._glyphs["min_height"],
                               num_glyphs_width=self._memory.video.mode.width // self._glyphs["width"],
                               num_glyphs_height=(self._memory.video.mode.height -
                                                 (self._glyphs["max_height"] - self._glyphs["min_height"])) //
                                                 self._glyphs["min_height"],
                               video_register_offset_address=self._memory.video_register_offset_address,
                               print_help_message_start=print_help_message_start)

        keyboard_interrupt_end = keyboard_interrupt_start + len(keyboard_interrupt) * 2

        mainloop = Routines.mainloop_mode_0()
        mainloop_start = keyboard_interrupt_end
        mainloop_end = mainloop_start + len(mainloop) * 2

        jump_to_mainloop = Assembler.assemble(["JMP @#{:o}".format(mainloop_start)])

        if mainloop_end > self._glyphs_start:
            raise EmulatorWrongConfiguration(what="programs don't fit to ROM!")

        for i, v in enumerate(init):
            self._memory.store(address=init_start + i*2, size="word", value=v)

        self._memory.store(address=init_end - 4, size="word", value=jump_to_mainloop[0])
        self._memory.store(address=init_end - 2, size="word", value=jump_to_mainloop[1])

        for i, v in enumerate(draw_glyph):
            self._memory.store(address=draw_glyph_start + i*2, size="word", value=v)

        for i, v in enumerate(print_help_message):
            self._memory.store(address=print_help_message_start + i * 2, size="word", value=v)

        for i, v in enumerate(keyboard_interrupt):
            self._memory.store(address=keyboard_interrupt_start + i*2, size="word", value=v)

        for i, v in enumerate(mainloop):
            self._memory.store(address=mainloop_start + i*2, size="word", value=v)

        self._disasm_from_to(init_start, mainloop_end)

    def _disasm_from_to(self, from_: int, to: int):
        stored = True
        cur_next_instruction, num_next_instructions = 0, 0
        tmp_addr: int = None
        tmp_repr: str = None
        data, sizes = [], []
        for addr in range(from_, to, 2):
            self._instructions[addr] = DisasmInstruction()
            if not stored:
                data.append(int(self._memory.load(size=sizes[cur_next_instruction], address=addr).to01(), 2))
                cur_next_instruction += 1
                if cur_next_instruction == num_next_instructions:
                    self._instructions[tmp_addr].set_state(state=DisasmState.DISASSEMBLED,
                                                           representation=tmp_repr.format(*data),
                                                           num_next=num_next_instructions)
                    stored = True
                self._instructions[addr].set_state(state=DisasmState.PART_OF_PREVIOUS,
                                                   num_next=num_next_instructions)
                continue

            try:
                com = Commands.get_command_by_code(code=self._memory.load(size="word", address=addr),
                                                   program_status=self._program_status)
                self._commands[addr] = com

            except UnknownCommand:
                self._instructions[addr].set_state(state=DisasmState.NOT_AN_INSTRUCTION)
                continue

            tmp_repr = com.string_representation

            if com.has_src_operand and com.has_dest_operand:
                tmp_repr = tmp_repr + " " + com.src_operand.string_representation + ", " + \
                           com.dest_operand.string_representation

            elif com.has_dest_operand and com.has_offset:
                tmp_repr = tmp_repr + " " + com.dest_operand.string_representation + ", " + "{:o}".format(com.offset)

            elif com.has_src_operand:
                tmp_repr = tmp_repr + " " + com.src_operand.string_representation

            elif com.has_dest_operand:
                tmp_repr = tmp_repr + " " + com.dest_operand.string_representation

            elif com.has_offset:
                tmp_repr = tmp_repr + " {:o}".format(com.offset)

            elif com.has_number:
                tmp_repr = tmp_repr + " {:o}".format(com.number)

            if com.num_next_instructions != 0:
                cur_next_instruction, num_next_instructions = 0, com.num_next_instructions
                stored = False
                data, sizes = [], []
                if com.has_src_operand and com.src_operand.require_next_instruction:
                    sizes.append("byte" if com.src_operand.reg == 7 and com.src_operand.mode == 2 and com.on_byte
                                 else "word")
                if com.has_dest_operand and com.dest_operand.require_next_instruction:
                    sizes.append("byte" if com.dest_operand.reg == 7 and com.dest_operand.mode == 2 and com.on_byte
                                 else "word")
                tmp_addr = addr
            else:
                self._instructions[addr].set_state(state=DisasmState.DISASSEMBLED, representation=tmp_repr,
                                                   num_next=0)

        if not stored:
            for addr in range(tmp_addr, to, 2):
                self._instructions[addr].set_state(state=DisasmState.NOT_AN_INSTRUCTION)

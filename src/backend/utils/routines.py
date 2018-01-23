from src.backend.utils.assembler import Assembler
import src.backend.utils.assembler
import pathlib


class Routines:
    @staticmethod
    def draw_glyph(glyphs_start: int, glyph_width: int, glyph_height: int, glyph_bitmap_size: int,
                   monitor_width: int, video_start: int, monitor_depth: int) -> list:

        assert monitor_width * monitor_depth % 8 == 0, "Wrong configuration"
        path = pathlib.Path(src.backend.utils.__path__[0])
        path = path.parent.parent.parent / "resource" / "assembler" / "draw_glyph"

        with open(path) as f:
            content = f.read().format(glyphs_start=glyphs_start, glyph_height=glyph_height, glyph_width=glyph_width,
                                      glyph_bitmap_size=glyph_bitmap_size, monitor_width=monitor_width,
                                      monitor_depth=monitor_depth, video_start=video_start,
                                      monitor_width_div_8_mul_monitor_depth=(monitor_width * monitor_depth) // 8)

        return Assembler.assemble(content.splitlines())

    @staticmethod
    def draw_glyph_mode_0(glyphs_start: int, glyph_width: int, glyph_height: int, glyph_max_height: int,
                          glyph_bitmap_size: int, monitor_width: int, video_start: int, monitor_depth: int) -> list:

        assert glyph_width == 16 and monitor_depth == 1 and monitor_width % 16 == 0 \
               and video_start % 2 == 0 and glyphs_start % 2 == 0, "Wrong configuration"

        path = pathlib.Path(src.backend.utils.__path__[0])
        path = path.parent.parent.parent / "resource" / "assembler" / "draw_glyph_16_mode_0"

        with open(path) as f:
            content = f.read().format(glyphs_start=glyphs_start, glyph_height=glyph_height,
                                      glyph_max_height=glyph_max_height, glyph_bitmap_size=glyph_bitmap_size,
                                      monitor_width_div_8=monitor_width // 8,
                                      video_start=video_start)

        return Assembler.assemble(content.splitlines())

    @staticmethod
    def mainloop(draw_glyph_start: int, glyph_width: int) -> list:
        path = pathlib.Path(src.backend.utils.__path__[0])
        path = path.parent.parent.parent / "resource" / "assembler" / "mainloop"

        with open(path) as f:
            content = f.read().format(draw_glyph_start=draw_glyph_start, glyph_width=glyph_width)
        return Assembler.assemble(content.splitlines())

    @staticmethod
    def mainloop_mode_0() -> list:
        path = pathlib.Path(src.backend.utils.__path__[0])
        path = path.parent.parent.parent / "resource" / "assembler" / "mainloop_16_mode_0"

        with open(path) as f:
            content = f.read()
        return Assembler.assemble(content.splitlines())

    @staticmethod
    def init(VRAM_start: int, video_register_mode_start_address: int, video_register_offset_address: int,
             keyboard_register_address: int, video_mode: int, video_start: int,
             keyboard_interrupt_subroutine_address: int, monitor_structure_start: int) -> list:
        assert video_start % 4 == 0, "Wrong configuration"
        path = pathlib.Path(src.backend.utils.__path__[0])
        path = path.parent.parent.parent / "resource" / "assembler" / "init"

        with open(path) as f:
            content = f.read().format(VRAM_start=VRAM_start, keyboard_register_address=keyboard_register_address,
                                      video_register_mode_start_address=video_register_mode_start_address,
                                      video_register_offset_address=video_register_offset_address,
                                      video_mode=video_mode, video_start=video_start,
                                      keyboard_interrupt_subroutine_address=keyboard_interrupt_subroutine_address,
                                      monitor_structure_start=monitor_structure_start)

        return Assembler.assemble(content.splitlines())

    @staticmethod
    def keyboard_interrupt(keyboard_register_address: int, monitor_structure_start: int, draw_glyph_start: int,
                           init_start: int, glyph_height: int, num_glyphs_width: int, num_glyphs_height: int,
                           video_register_offset_address: int, print_help_message_start: int) -> list:
        path = pathlib.Path(src.backend.utils.__path__[0])
        path = path.parent.parent.parent / "resource" / "assembler" / "keyboard_interrupt"

        with open(path) as f:
            content = f.read().format(keyboard_register_address=keyboard_register_address,
                                      monitor_structure_start=monitor_structure_start,
                                      draw_glyph_start=draw_glyph_start, init_start=init_start,
                                      glyph_height=glyph_height, num_glyphs_width=num_glyphs_width,
                                      num_glyphs_height=num_glyphs_height,
                                      video_register_offset_address=video_register_offset_address,
                                      num_glyphs_all=num_glyphs_height * num_glyphs_width,
                                      print_help_message_start=print_help_message_start)

        return Assembler.assemble(content.splitlines())

    @staticmethod
    def print_help_message(draw_glyph_start: int, monitor_structure_start: int,
                           video_register_offset_address: int) -> list:
        path = pathlib.Path(src.backend.utils.__path__[0])
        path = path.parent.parent.parent / "resource" / "assembler" / "print_help_message"

        with open(path) as f:
            content = f.read().format(draw_glyph_start=draw_glyph_start,
                                      monitor_structure_start=monitor_structure_start,
                                      video_register_offset_address=video_register_offset_address)

        return Assembler.assemble(content.splitlines())

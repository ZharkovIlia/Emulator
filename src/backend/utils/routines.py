from src.backend.utils.assembler import Assembler


class Routines:
    @staticmethod
    def draw_glyph(glyphs_start: int, glyph_width: int, glyph_height: int, glyph_bitmap_size,
                   monitor_width: int, vram_start: int, monitor_depth: int) -> list:

        assert monitor_width * monitor_depth % 8 == 0, "Wrong configuration"
        f = open("../../resource/assembler/draw_glyph")
        content = f.read().format(glyphs_start=glyphs_start, glyph_height=glyph_height, glyph_width=glyph_width,
                                  glyph_bitmap_size=glyph_bitmap_size, monitor_width=monitor_width,
                                  monitor_depth=monitor_depth, vram_start=vram_start,
                                  monitor_width_div_8_mul_monitor_depth=monitor_width * monitor_depth // 8)

        return Assembler.assemble(content.splitlines())

    @staticmethod
    def mainloop(draw_glyph_start: int, glyph_width: int) -> list:
        f = open("../../resource/assembler/mainloop")
        content = f.read().format(draw_glyph_start=draw_glyph_start, glyph_width=glyph_width)
        return Assembler.assemble(content.splitlines())

    @staticmethod
    def init(VRAM_start: int, video_register_mode_start_address: int, video_register_offset_address: int,
             video_mode: int, video_start: int) -> list:
        assert video_start % 4 == 0, "Wrong configuration"
        f = open("../../resource/assembler/init")
        content = f.read().format(VRAM_start=VRAM_start,
                                  video_register_mode_start_address=video_register_mode_start_address,
                                  video_register_offset_address=video_register_offset_address,
                                  video_mode=video_mode, video_start=video_start)

        return Assembler.assemble(content.splitlines())


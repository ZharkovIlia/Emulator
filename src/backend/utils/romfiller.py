from PIL import ImageDraw, Image, ImageFont
from bitarray import bitarray


class ROMFiller:
    @staticmethod
    def get_glyphs() -> list:
        alphabet = "abcdefghijklmnopqrstuvwxyz"
        font = ImageFont.truetype("../../../resource/FreeMono.ttf", size=20)
        width, min_height = font.getsize(text='a')
        max_height = min_height
        for alpha in alphabet:
            size = font.getsize(text=alpha)
            assert size[0] == width, "Font is not fixed"
            max_height = max(max_height, size[1])
            min_height = min(min_height, size[1])

        data = [bitarray("{:016b}".format(width), endian='big'),
                bitarray("{:016b}".format(min_height), endian='big'),
                bitarray("{:016b}".format(max_height), endian='big')]

        struct_size = width * max_height
        struct_size = ((struct_size - 1) // 16 + 1) * 16  # Now struct_size is aligned
        struct_size += 16
        data.append(bitarray("{:016b}".format(struct_size), endian='big'))

        for alpha in alphabet:
            size = font.getsize(text=alpha)
            im = Image.new(mode="1", size=size, color="white")
            txt = ImageDraw.Draw(im)
            txt.text(xy=(0, 0), text=alpha, fill=0, font=font)

            struct_bitmap_size = bitarray("{:016b}".format(size[1] * width), endian='big')
            data.append(struct_bitmap_size)

            struct_bitmap = list(bitarray("".join("0" for _ in range(16)), endian='big')
                                 for _ in range(struct_size // 16 - 1))
            index_array = 0
            index_bit = 0
            bitarr = None

            for pixel in list(im.getdata()):
                if index_bit == 0:
                    bitarr = struct_bitmap[index_array]

                bitarr[index_bit] = True if pixel == 0 else False
                index_bit += 1
                if index_bit % 16 == 0:
                    index_bit = 0
                    index_array += 1

            data.extend(struct_bitmap)

        return data

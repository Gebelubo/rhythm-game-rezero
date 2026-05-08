from src.funcs.cg_lib import line_bresenham, scanline_fill, set_pixel
from src.utils.fonts import FONT_5X7
import math

TEXT_SCALE = 0.65


def _txt(screen, font, text, x, y,
         color=(255,255,255),
         center=False,
         scale_size=None):

    # usa automaticamente o tamanho da fonte pygame
    if scale_size is None:
        h = font.get_height()

        if h >= 40:
            scale_size = 5
        elif h >= 28:
            scale_size = 4
        elif h >= 20:
            scale_size = 3
        else:
            scale_size = 2

    scale_size = max(1, math.ceil(scale_size * TEXT_SCALE))
    char_w = 5 * scale_size
    char_h = 7 * scale_size
    spacing = max(1, scale_size)

    total_w = len(text) * (char_w + spacing)

    if center:
        x -= total_w // 2
        y -= char_h // 2

    ox = x

    for ch in text.upper():

        bitmap = FONT_5X7.get(ch, FONT_5X7[" "])

        for row in range(7):
            for col in range(5):

                if bitmap[row][col] == "1":

                    px = ox + col * scale_size
                    py = y  + row * scale_size

                    for sy in range(scale_size):
                        for sx in range(scale_size):

                            set_pixel(
                                screen,
                                px + sx,
                                py + sy,
                                color
                            )

        ox += char_w + spacing


def _draw_btn(screen, bx, by, bw, bh, label, font,
                  active=False, color=(115,75,250)):
        bg  = tuple(min(255, c // 2 + (30 if active else 0)) for c in color)
        brd = color if active else tuple(c // 2 for c in color)
        scanline_fill(screen, [(bx,by),(bx+bw,by),(bx+bw,by+bh),(bx,by+bh)], bg)
        for off in range(2 if active else 1):
            o = off
            line_bresenham(screen, bx+o,    by+o,    bx+bw-o, by+o,    brd)
            line_bresenham(screen, bx+bw-o, by+o,    bx+bw-o, by+bh-o, brd)
            line_bresenham(screen, bx+bw-o, by+bh-o, bx+o,    by+bh-o, brd)
            line_bresenham(screen, bx+o,    by+bh-o, bx+o,    by+o,    brd)
        tc = (255, 255, 255) if active else (180, 180, 210)
        _txt(screen, font, label, bx + bw // 2, by + bh // 2, tc, center=True)
def draw_coin(surface, cx, cy, radius=12):
    """
    Desenha uma moedinha pixel-art usando apenas set_pixel.
    cx, cy = centro
    """

    gold_light = (255, 225, 90)
    gold_mid   = (235, 185, 40)
    gold_dark  = (170, 120, 20)
    outline    = (90, 60, 10)
    shine      = (255, 255, 180)

    # círculo preenchido
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):

            if dx*dx + dy*dy <= radius*radius:

                # gradiente simples
                dist = math.sqrt(dx*dx + dy*dy)
                t = dist / radius

                if t < 0.45:
                    col = gold_light
                elif t < 0.80:
                    col = gold_mid
                else:
                    col = gold_dark

                set_pixel(surface, cx + dx, cy + dy, col)

    # borda
    for ang in range(360):
        rad = math.radians(ang)

        x = int(cx + math.cos(rad) * radius)
        y = int(cy + math.sin(rad) * radius)

        set_pixel(surface, x, y, outline)

    # brilho superior esquerdo
    for dy in range(-radius // 2, 0):
        for dx in range(-radius // 2, 0):

            if dx*dx + dy*dy <= (radius // 2)*(radius // 2):
                set_pixel(surface, cx + dx - 2, cy + dy - 2, shine)

    # símbolo $
    symbol = [
        "00100",
        "01110",
        "10100",
        "01110",
        "00101",
        "01110",
        "00100",
    ]

    scale = max(1, radius // 6)

    ox = cx - (5 * scale) // 2
    oy = cy - (7 * scale) // 2

    for row in range(7):
        for col in range(5):

            if symbol[row][col] == "1":

                px = ox + col * scale
                py = oy + row * scale

                for sy in range(scale):
                    for sx in range(scale):
                        set_pixel(surface, px + sx, py + sy, outline)

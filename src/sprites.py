from src.config import (
    CHAR_SIZE, DIRECTIONS, LANE_COLORS,
)
from src.lib.cg_lib import (
    set_pixel,
    circle_midpoint,
    scanline_fill,
    draw_polygon,
)

from src.utils.render import arrow_poly

import os
import pygame

def load_sprites(folder: str = 'sprites', size: int = CHAR_SIZE) -> dict:

    sprites = {}
    for name in ['idle'] + DIRECTIONS:
        sprites[name] = None
        for ext in ('.png', '.jpg', '.bmp', '.gif'):
            path = os.path.join(folder, name + ext)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    sprites[name] = pygame.transform.smoothscale(img, (size, size))
                    break
                except Exception:
                    pass
    return sprites


def draw_char(surface: pygame.Surface, sprites: dict,
              anim: str, cx: int, cy: int) -> None:

    s = sprites.get(anim)
    if s:
        surface.blit(s, (cx - CHAR_SIZE // 2, cy - CHAR_SIZE // 2))
        return

    r  = CHAR_SIZE // 2
    c  = LANE_COLORS.get(anim, (160, 160, 220))
    bg = (40, 40, 72)

    for i in range(r, r - 4, -1):
        circle_midpoint(surface, cx, cy, i, bg)

    if anim in DIRECTIONS:
        verts = arrow_poly(anim, cx, cy, int(r * 0.58))
        scanline_fill(surface, verts, c)
        draw_polygon(surface, verts, tuple(min(255, v + 70) for v in c))
    else:
        ex = int(r * 0.28)
        ey = int(r * 0.12)
        er = max(3, int(r * 0.13))
        circle_midpoint(surface, cx - ex, cy - ey, er, (220, 220, 255))
        circle_midpoint(surface, cx + ex, cy - ey, er, (220, 220, 255))
        for dx in range(-int(r * 0.32), int(r * 0.32) + 1):
            sy = int(dy_smile := (dx / (r * 0.32)) ** 2 * r * 0.18)
            set_pixel(surface, cx + dx, cy + int(r * 0.22) + sy, (220, 220, 255))

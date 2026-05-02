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

    anim_names = set()
    if os.path.isdir(folder):
        for fn in os.listdir(folder):
            if not fn.lower().endswith(('.png', '.jpg', '.bmp', '.gif')):
                continue
            base = fn.rsplit('.', 1)[0]
            parts = base.rsplit('_', 1)
            if len(parts) == 2 and parts[1].isdigit():
                anim_names.add(parts[0])
            else:
                anim_names.add(base)

    for name in anim_names:
        frames = []
        for f in range(64):
            found = False
            for ext in ('.png', '.jpg', '.bmp', '.gif'):
                path = os.path.join(folder, f'{name}_{f}{ext}')
                if os.path.exists(path):
                    try:
                        img = pygame.image.load(path).convert_alpha()
                        frames.append(pygame.transform.smoothscale(img, (size, size)))
                        found = True
                        break
                    except Exception:
                        pass
            if not found:
                if f == 0:
                    for ext in ('.png', '.jpg', '.bmp', '.gif'):
                        path = os.path.join(folder, f'{name}{ext}')
                        if os.path.exists(path):
                            try:
                                img = pygame.image.load(path).convert_alpha()
                                frames.append(pygame.transform.smoothscale(img, (size, size)))
                                break
                            except Exception:
                                pass
                break
        if frames:
            sprites[name] = frames

    return sprites


def draw_char(surface: pygame.Surface, sprites: dict,
              anim: str, cx: int, cy: int, frame: int = 0, size: int = CHAR_SIZE) -> None:

    frames = sprites.get(anim)
    if not frames:
        frames = sprites.get('idle')

    if frames:
        s = frames[frame % len(frames)]
        if s:
            surface.blit(s, (cx - size // 2, cy - size // 2))
            return

    r  = size // 2
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
            sy = int((dx / (r * 0.32)) ** 2 * r * 0.18)
            set_pixel(surface, cx + dx, cy + int(r * 0.22) + sy, (220, 220, 255))
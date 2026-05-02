from src.lib.cg_lib import (
    scanline_fill,
    draw_polygon,
    line_bresenham,
    rotate,
    load_texture,
    texture_map_triangle,
)
from src.config import (
    W, H, HUD_H,
    LANE_W, LANE_COUNT,
    TARGET_Y,
    DIRECTIONS, LANE_COLORS,
)

import os
import pygame

_texture_cache = {}

def _get_texture(size: int):
    if size in _texture_cache:
        return _texture_cache[size]
    path = os.path.join('texture', 'texture_nota.png')
    if os.path.exists(path):
        try:
            tex = load_texture(path)
            tex = pygame.transform.smoothscale(tex, (size * 2, size * 2))
            _texture_cache[size] = tex
            return tex
        except Exception:
            pass
    _texture_cache[size] = None
    return None


DIRECTION_ANGLES = {
    'up':    0,
    'down':  180,
    'left':  270,
    'right': 90,
}


def arrow_poly(cx: float, cy: float, size: int) -> list:
    """Forma base apontando para cima. Rotacione externamente para outras direções."""
    h  = size * 0.52
    sw = size * 0.24
    return [
        (cx,      cy - h),
        (cx + h,  cy),
        (cx + sw, cy),
        (cx + sw, cy + h),
        (cx - sw, cy + h),
        (cx - sw, cy),
        (cx - h,  cy),
    ]


def bake_arrow_surf(direction: str, fill_color: tuple,
                    border_color: tuple, size: int,
                    rotation: float = 0.0) -> pygame.Surface:

    pad  = 6
    dim  = size * 2 + pad * 2
    surf = pygame.Surface((dim, dim), pygame.SRCALPHA)
    cx   = cy = dim // 2

    # Soma o ângulo da direção com a rotação extra
    total_angle = DIRECTION_ANGLES.get(direction, 0) + rotation

    verts = arrow_poly(cx, cy, size)

    if total_angle != 0.0:
        verts = rotate(verts, total_angle, cx, cy)

    tex = _get_texture(size)
    if tex is not None:
        v0 = verts[0]
        for i in range(1, len(verts) - 1):
            p0 = (int(v0[0]),         int(v0[1]))
            p1 = (int(verts[i][0]),   int(verts[i][1]))
            p2 = (int(verts[i+1][0]), int(verts[i+1][1]))
            uv0 = (p0[0] / dim, p0[1] / dim)
            uv1 = (p1[0] / dim, p1[1] / dim)
            uv2 = (p2[0] / dim, p2[1] / dim)
            texture_map_triangle(surf, tex, p0, p1, p2, uv0, uv1, uv2)
        color_overlay = pygame.Surface((dim, dim), pygame.SRCALPHA)
        scanline_fill(color_overlay, verts, (*fill_color, 140))
        surf.blit(color_overlay, (0, 0))
    else:
        scanline_fill(surf, verts, fill_color)

    draw_polygon(surf, verts, border_color)
    return surf


def bake_static_bg(lane_left_x: int) -> pygame.Surface:

    surf = pygame.Surface((W, H))

    strips = 24
    for i in range(strips):
        y0 = int(H * i     / strips)
        y1 = int(H * (i+1) / strips)
        t  = i / strips
        c  = (int(7  + 12*t), int(5 + 6*t), int(18 + 22*t))
        scanline_fill(surf, [(0,y0),(W,y0),(W,y1),(0,y1)], c)

    scanline_fill(surf, [(0,0),(W,0),(W,HUD_H),(0,HUD_H)], (7, 7, 18))
    line_bresenham(surf, 0, HUD_H, W, HUD_H, (45, 45, 92))

    for i in range(LANE_COUNT):
        x0 = lane_left_x + i * LANE_W
        x1 = x0 + LANE_W
        c  = (14, 14, 34) if i % 2 == 0 else (11, 11, 26)
        scanline_fill(surf, [(x0,HUD_H),(x1,HUD_H),(x1,H),(x0,H)], c)

    for i in range(LANE_COUNT + 1):
        x = lane_left_x + i * LANE_W
        line_bresenham(surf, x, HUD_H, x, H, (40, 40, 65))

    for i, d in enumerate(DIRECTIONS):
        x0 = lane_left_x + i * LANE_W
        x1 = x0 + LANE_W
        c  = LANE_COLORS[d]
        for dy in range(-1, 3):
            line_bresenham(surf, x0, TARGET_Y + dy, x1, TARGET_Y + dy, c)

    return surf
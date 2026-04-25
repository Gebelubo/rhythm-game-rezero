from src.lib.cg_lib import (
    scanline_fill,
    draw_polygon,
    line_bresenham,
)
from src.config import (
    W, H, HUD_H,
    LANE_W, LANE_COUNT,
    TARGET_Y,
    DIRECTIONS, LANE_COLORS,
)

import pygame


def arrow_poly(direction: str, cx: float, cy: float, size: int) -> list:
    h  = size * 0.52
    sw = size * 0.24
    if direction == 'up':
        return [(cx,cy-h),(cx+h,cy),(cx+sw,cy),(cx+sw,cy+h),(cx-sw,cy+h),(cx-sw,cy),(cx-h,cy)]
    if direction == 'down':
        return [(cx,cy+h),(cx+h,cy),(cx+sw,cy),(cx+sw,cy-h),(cx-sw,cy-h),(cx-sw,cy),(cx-h,cy)]
    if direction == 'left':
        return [(cx-h,cy),(cx,cy-h),(cx,cy-sw),(cx+h,cy-sw),(cx+h,cy+sw),(cx,cy+sw),(cx,cy+h)]
    return [(cx+h,cy),(cx,cy-h),(cx,cy-sw),(cx-h,cy-sw),(cx-h,cy+sw),(cx,cy+sw),(cx,cy+h)]


def bake_arrow_surf(direction: str, fill_color: tuple,
                    border_color: tuple, size: int) -> pygame.Surface:

    pad  = 6
    dim  = size * 2 + pad * 2
    surf = pygame.Surface((dim, dim), pygame.SRCALPHA)
    cx   = cy = dim // 2
    verts = arrow_poly(direction, cx, cy, size)
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

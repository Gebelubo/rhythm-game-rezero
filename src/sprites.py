import os
import pygame

from src.config import CHAR_SIZE, DIRECTIONS, LANE_COLORS
from src.funcs.cg_lib import (
    set_pixel,
    circle_midpoint,
    scanline_fill,
    draw_polygon,
)
from src.utils.render import arrow_poly


# Cache de surfaces já redimensionadas: (id_surface, new_w, new_h) -> Surface
_resize_cache: dict = {}


def _resize_surface(src: pygame.Surface, new_w: int, new_h: int) -> pygame.Surface:
    if src.get_width() == new_w and src.get_height() == new_h:
        return src

    key = (id(src), new_w, new_h)
    if key in _resize_cache:
        return _resize_cache[key]

    has_alpha = src.get_flags() & pygame.SRCALPHA
    dst = pygame.Surface((new_w, new_h), pygame.SRCALPHA if has_alpha else 0)
    src_w = src.get_width()
    src_h = src.get_height()

    for dy in range(new_h):
        sy = int(dy * (src_h - 1) / max(new_h - 1, 1))
        for dx in range(new_w):
            sx = int(dx * (src_w - 1) / max(new_w - 1, 1))
            dst.set_at((dx, dy), src.get_at((sx, sy)))

    _resize_cache[key] = dst
    return dst


def _blit_alpha(dst: pygame.Surface, src: pygame.Surface, ox: int, oy: int) -> None:
    sw, sh = src.get_width(), src.get_height()
    dw, dh = dst.get_width(), dst.get_height()
    has_alpha = src.get_flags() & pygame.SRCALPHA

    for sy in range(sh):
        dy = oy + sy
        if dy < 0 or dy >= dh:
            continue
        for sx in range(sw):
            dx = ox + sx
            if dx < 0 or dx >= dw:
                continue

            sc = src.get_at((sx, sy))
            sr, sg, sb = sc[0], sc[1], sc[2]
            sa = sc[3] if has_alpha else 255

            if sa == 0:
                continue
            elif sa == 255:
                dst.set_at((dx, dy), (sr, sg, sb))
            else:
                bg = dst.get_at((dx, dy))
                a = sa / 255.0
                r = int(sr * a + bg[0] * (1 - a))
                g = int(sg * a + bg[1] * (1 - a))
                b = int(sb * a + bg[2] * (1 - a))
                dst.set_at((dx, dy), (r, g, b))


def load_sprites(folder: str = 'sprites', size: int = CHAR_SIZE) -> dict:
    """
    Carrega apenas os metadados e as surfaces brutas do disco.
    O redimensionamento acontece lazy no primeiro draw_char.
    """
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
                        # Só carrega — NÃO redimensiona aqui
                        img = pygame.image.load(path).convert_alpha()
                        frames.append(img)
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
                                frames.append(img)
                                break
                            except Exception:
                                pass
                break
        if frames:
            sprites[name] = frames

    return sprites


def draw_char(surface: pygame.Surface, sprites: dict,
              anim: str, cx: int, cy: int, frame: int = 0, size: int = CHAR_SIZE) -> None:

    frames = sprites.get(anim) or sprites.get('idle')

    if frames:
        raw = frames[frame % len(frames)]
        if raw:
            # Redimensiona lazy: só na primeira vez que este frame aparecer
            s = _resize_surface(raw, size, size)
            _blit_alpha(surface, s, cx - size // 2, cy - size // 2)
            return

    # Fallback vetorial
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
        ex, ey = int(r * 0.28), int(r * 0.12)
        er = max(3, int(r * 0.13))
        circle_midpoint(surface, cx - ex, cy - ey, er, (220, 220, 255))
        circle_midpoint(surface, cx + ex, cy - ey, er, (220, 220, 255))
        for dx in range(-int(r * 0.32), int(r * 0.32) + 1):
            sy_off = int((dx / (r * 0.32)) ** 2 * r * 0.18)
            set_pixel(surface, cx + dx, cy + int(r * 0.22) + sy_off, (220, 220, 255))
import math
import random
import pygame
from src.config import CHAR_SIZE_LOBBY

from src.funcs.cg_lib import (
    line_bresenham, scanline_fill, circle_midpoint,
    draw_rectangle, draw_line_viewport, draw_polygon_viewport,
    Window, Viewport, line_bresenham_fast, fill_rectangle_optimized, set_pixel
)
from src.utils.ui import _txt, _draw_btn, draw_coin
from src.music_backend.backend_config import DIFFICULTY_COLORS, DIFFICULTY_NAMES
from src.sprites import draw_char

# ── Constantes do mundo ────────────────────────────────────────────────────────

LOBBY_STAGE_NAMES = [
    'Refazer', 'Entender', 'Reconstruir', 'Lembrar', 'Personalizada'
]
LOBBY_STAGE_COLORS = [
    (62, 108, 62),
    (58,  98, 120),
    (130, 100, 52),
    (110,  58,  90),
    (140, 120,  55),
]

LOBBY_WORLD_XMIN   = -800
LOBBY_WORLD_YMIN   = -600
LOBBY_WORLD_XMAX   =  800
LOBBY_WORLD_YMAX   =  600
LOBBY_GRID_SPACING =  100
LOBBY_VIEW_W       =  620
LOBBY_VIEW_H       =  420
LOBBY_ENTRY_RADIUS =   64

LOBBY_STAGE_POS = [
    (-500,  350),
    ( 500,  350),
    (-500, -350),
    ( 500, -350),
    (   0,    0),
]

_GRASS_COLORS  = [(28,72,28),(35,88,32),(42,102,36),(50,116,40)]
_PATH_COLORS   = [(148,118,82),(160,130,90),(138,108,72)]
_BUSH_COLORS   = [(38,90,38),(48,105,45),(55,120,50)]

_TREE_POSITIONS = [
    (80,80),(1520,80),(80,1120),(1520,1120),
    (400,100),(1200,100),(400,1100),(1200,1100),
    (80,400),(80,800),(1520,400),(1520,800),
    (680,80),(920,80),(680,1120),(920,1120),
    (150,300),(150,900),(1450,300),(1450,900),
    (550,150),(1050,150),(550,1050),(1050,1050),
]

# ── Pixel helpers ──────────────────────────────────────────────────────────────

def _px(surf, x, y, color):
    w, h = surf.get_size()
    if 0 <= x < w and 0 <= y < h:
        surf.set_at((x, y), color)

def _fill_rect(surf, x, y, w, h, color):
    from src.funcs.cg_lib import fill_rectangle
    fill_rectangle(surf, x, y, w, h, color)

def _lerp_color(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def _darken(c, amt):
    return tuple(max(0, v - amt) for v in c)

def _brighten(c, amt):
    return tuple(min(255, v + amt) for v in c)

# ── Gradiente por vértice (scanline com interpolação bilinear) ─────────────────

def _fill_circle_vertex_gradient(surf, cx, cy, radius, color_top, color_bottom,
                                  color_left, color_right):
    """Preenche círculo com gradiente interpolado por vértice (requisito CG)."""
    surf_w, surf_h = surf.get_size()
    for dy in range(-radius, radius + 1):
        ddx_w = int(math.sqrt(max(0, radius * radius - dy * dy)))
        for ddx in range(-ddx_w, ddx_w + 1):
            px_x = cx + ddx
            px_y = cy + dy
            if not (0 <= px_x < surf_w and 0 <= px_y < surf_h):
                continue

            t_y = (dy + radius) / (2 * radius) if radius > 0 else 0.5
            t_x = (ddx + ddx_w) / (2 * ddx_w) if ddx_w > 0 else 0.5

            col_top_row    = _lerp_color(color_left, color_right, t_x)
            col_bot_row    = _lerp_color(
                _lerp_color(color_left,  color_bottom, 0.6),
                _lerp_color(color_right, color_bottom, 0.6),
                t_x
            )
            col_vert       = _lerp_color(color_top, color_bottom, t_y)
            col_horiz      = _lerp_color(color_left, color_right, t_x)

            col = _lerp_color(
                _lerp_color(col_top_row, col_bot_row, t_y),
                _lerp_color(col_vert,    col_horiz,   0.5),
                0.4
            )

            surf.set_at((px_x, px_y), col)

# ── Caminho ────────────────────────────────────────────────────────────────────

def _pixel_path(surf, x, y, w, h, rng):
    tile = 4
    for ty in range(y, y + h, tile):
        for tx in range(x, x + w, tile):
            base = rng.choice(_PATH_COLORS)
            tw = min(tile, x + w - tx)
            th = min(tile, y + h - ty)
            _fill_rect(surf, tx, ty, tw, th, base)
            if rng.random() < 0.12:
                dark = tuple(max(0, c - 20) for c in base)
                _px(surf, tx + 1, ty + 1, dark)
                _px(surf, tx + 2, ty + 1, dark)
                _px(surf, tx + 1, ty + 2, dark)

# ── Arbusto ────────────────────────────────────────────────────────────────────

def _draw_bush(surf, cx, cy, radius, rng):
    for dy in range(-radius, radius + 1):
        row_w = int(math.sqrt(max(0, radius * radius - dy * dy)))
        for dx in range(-row_w, row_w + 1):
            tx = cx + dx * 3
            ty = cy + dy * 3
            col = rng.choice(_BUSH_COLORS)
            _fill_rect(surf, tx - 1, ty - 1, 3, 3, col)
    for angle in range(0, 360, 12):
        rad = math.radians(angle)
        ex = int(cx + (radius * 3 - 2) * math.cos(rad))
        ey = int(cy + (radius * 3 - 2) * math.sin(rad))
        _px(surf, ex, ey, (30, 72, 30))

# ── Árvore ────────────────────────────────────────────────────────────────────

def _draw_tree(surf, cx, cy, rng):
    trunk_c = (100, 68, 35)
    trunk_d = (80, 52, 25)
    for dy in range(0, 18):
        _fill_rect(surf, cx - 3, cy + dy, 6, 1, trunk_c if dy % 2 == 0 else trunk_d)
    layers = [
        (cy - 2,  14, (55, 130, 50)),
        (cy - 10, 18, (62, 148, 55)),
        (cy - 20, 14, (72, 162, 60)),
    ]
    for ly, lw, lc in layers:
        half = lw // 2
        for dy in range(-half // 2, half // 2 + 1):
            row_w = int(math.sqrt(max(0, (lw // 2) ** 2 - dy * dy)))
            _fill_rect(surf, cx - row_w, ly + dy, row_w * 2, 1, lc)
            _px(surf, cx - row_w,     ly + dy, tuple(max(0, c - 20) for c in lc))
            _px(surf, cx + row_w - 1, ly + dy, tuple(max(0, c - 20) for c in lc))
        _px(surf, cx - 2, ly - half // 2 + 1, tuple(min(255, c + 30) for c in lc))
        _px(surf, cx - 1, ly - half // 2,     tuple(min(255, c + 30) for c in lc))

# ── Geração do background ──────────────────────────────────────────────────────

def _world_to_bg(wx, wy):
    return (int(wx - LOBBY_WORLD_XMIN), int(LOBBY_WORLD_YMAX - wy))

def _create_gradient_surface(width: int, height: int) -> pygame.Surface:
    """Cria o gradiente de fundo (céu → chão)"""
    grad = pygame.Surface((width, height))
    sky_top = (18, 38, 88)
    sky_mid = (52, 110, 175)
    horiz = (55, 110, 65)
    gnd_mid = (28, 65, 24)
    gnd_bottom = (14, 38, 12)

    for y in range(height):
        t = y / (height - 1)
        if t < 0.35:
            t2 = t / 0.35
            col = _lerp_color(sky_top, sky_mid, t2)
        elif t < 0.55:
            t2 = (t - 0.35) / 0.20
            col = _lerp_color(sky_mid, horiz, t2)
        elif t < 0.72:
            t2 = (t - 0.55) / 0.17
            col = _lerp_color(horiz, gnd_mid, t2)
        else:
            t2 = (t - 0.72) / 0.28
            col = _lerp_color(gnd_mid, gnd_bottom, t2)
        line_bresenham_fast(grad, 0, y, width - 1, y, col)
    
    return grad


def _add_grass_texture(surf: pygame.Surface, grad: pygame.Surface, width: int, height: int, rng: random.Random):
    """Adiciona textura de grama blendada com o gradiente"""
    tile = 4
    for ty in range(0, height, tile):
        for tx in range(0, width, tile):
            base = rng.choice(_GRASS_COLORS)
            t = ty / (height - 1)
            alpha = 0.55 + 0.42 * t
            bg = grad.get_at((min(tx, width-1), min(ty, height-1)))[:3]
            blended = tuple(int(base[i] * alpha + bg[i] * (1 - alpha)) for i in range(3))
            tw = min(tile, width - tx)
            th = min(tile, height - ty)
            _fill_rect(surf, tx, ty, tw, th, blended)
            
            if rng.random() < 0.20:
                bright = tuple(min(255, c + 14) for c in blended)
                cx2 = tx + tw // 2
                cy2 = ty + th // 2
                _fill_rect(surf, cx2, cy2, 2, 2, bright)


def _draw_paths_between_stages(surf: pygame.Surface, width: int, height: int, rng: random.Random):
    """Desenha os caminhos entre as fases"""
    center_bg = _world_to_bg(0, 0)
    for i in range(4):
        sx, sy = _world_to_bg(*LOBBY_STAGE_POS[i])
        dx = center_bg[0] - sx
        dy = center_bg[1] - sy
        dist = max(1, int(math.hypot(dx, dy)))
        steps = dist // 4
        
        for step in range(steps + 1):
            t = step / max(1, steps)
            px = int(sx + dx * t)
            py = int(sy + dy * t)
            _pixel_path(surf, px - 20, py - 20, 40, 40, rng)
            
            for boff in [(-22, 0), (22, 0), (0, -22), (0, 22)]:
                bx2 = px + boff[0]
                by2 = py + boff[1]
                if 0 <= bx2 < width and 0 <= by2 < height:
                    cur = surf.get_at((bx2, by2))[:3]
                    if cur[0] < 130:
                        darker = tuple(max(0, c - 12) for c in cur)
                        _fill_rect(surf, bx2 - 1, by2 - 1, 3, 3, darker)


def _draw_stage_platform(surf: pygame.Surface, sx: int, sy: int, 
                         radius: int, color: tuple, bright: tuple, dim: tuple):
    """Desenha uma plataforma individual de fase com gradiente por vértice"""
    ring_r = radius + 12
    
    # Sombra no solo
    for shadow_dy in range(-ring_r + 4, ring_r - 4 + 1):
        row_w = int(math.sqrt(max(0, (ring_r-4)*(ring_r-4) - shadow_dy*shadow_dy)))
        shade_c = tuple(max(0, c - 30) for c in surf.get_at((
            min(max(sx, 0), surf.get_width()-1),
            min(max(sy + shadow_dy + 6, 0), surf.get_height()-1)
        ))[:3])
        line_bresenham(surf, sx - row_w + 4, sy + shadow_dy + 6,
                       sx + row_w + 4, sy + shadow_dy + 6, shade_c)
    
    # Anel de grama
    for dy in range(-ring_r, ring_r + 1):
        row_w = int(math.sqrt(max(0, ring_r*ring_r - dy*dy)))
        inner = int(math.sqrt(max(0, radius*radius - dy*dy)))
        t_ring = abs(dy) / ring_r
        ring_c = (
            int(70 + 30 * (1 - t_ring)),
            int(148 + 22 * (1 - t_ring)),
            int(62 + 18 * (1 - t_ring)),
        )
        for ddx in range(-row_w, -inner):
            _px(surf, sx+ddx, sy+dy, ring_c)
        for ddx in range(inner, row_w):
            _px(surf, sx+ddx, sy+dy, ring_c)
    
    # Gradiente por vértice na plataforma
    color_top = bright
    color_bottom = dim
    color_left = tuple(min(255, c + 20) for c in color)
    color_right = tuple(max(0, c - 10) for c in color)
    _fill_circle_vertex_gradient(surf, sx, sy, radius,
                                 color_top, color_bottom,
                                 color_left, color_right)
    
    # Bordas
    circle_midpoint(surf, sx, sy, radius, tuple(min(255, c+50) for c in color))
    circle_midpoint(surf, sx, sy, radius-1, tuple(min(255, c+30) for c in color))
    circle_midpoint(surf, sx, sy, radius-2, tuple(min(255, c+10) for c in color))
    circle_midpoint(surf, sx, sy, radius-10, tuple(max(0, c-30) for c in color))
    
    # Pontos decorativos
    for angle in range(0, 360, 15):
        rad = math.radians(angle)
        ex = int(sx + (radius-3)*math.cos(rad))
        ey = int(sy + (radius-3)*math.sin(rad))
        _px(surf, ex, ey, bright)


def _draw_platform_badge(surf: pygame.Surface,
                         sx: int,
                         sy: int,
                         radius: int,
                         color: tuple,
                         bright: tuple,
                         name: str,
                         abbr: str,
                         fonts):

    f_xl, f_lg, f_md, f_sm = fonts

    # -----------------------------
    # BADGE INFERIOR
    # -----------------------------

    text_scale = 2
    char_w = 5 * text_scale
    spacing = text_scale

    badge_text_w = len(name) * (char_w + spacing)
    badge_w = badge_text_w + 20
    badge_h = 22

    badge_x = sx - badge_w // 2
    badge_y = sy + radius + 10

    # sombra
    _fill_rect(
        surf,
        badge_x + 2,
        badge_y + 2,
        badge_w,
        badge_h,
        (8, 10, 8)
    )

    # fundo
    _fill_rect(
        surf,
        badge_x,
        badge_y,
        badge_w,
        badge_h,
        (18, 22, 18)
    )

    # borda
    draw_rectangle(
        surf,
        badge_x,
        badge_y,
        badge_w,
        badge_h,
        color
    )

    draw_rectangle(
        surf,
        badge_x + 1,
        badge_y + 1,
        badge_w - 2,
        badge_h - 2,
        tuple(min(255, c + 40) for c in color)
    )

    # texto do nome
    _txt(
        surf,
        f_sm,
        name,
        sx,
        badge_y + 6,
        (235, 235, 235),
        center=True,
        scale_size=2
    )

    # -----------------------------
    # TEXTO CENTRAL
    # -----------------------------

    # sombra
    _txt(
        surf,
        f_xl,
        abbr,
        sx + 2,
        sy + 2,
        tuple(max(0, c - 80) for c in color),
        center=True,
        scale_size=5
    )

    # brilho secundário
    _txt(
        surf,
        f_xl,
        abbr,
        sx + 1,
        sy + 1,
        tuple(max(0, c - 40) for c in bright),
        center=True,
        scale_size=5
    )

    # texto principal
    _txt(
        surf,
        f_xl,
        abbr,
        sx,
        sy,
        bright,
        center=True,
        scale_size=5
    )

def build_lobby_background(fonts) -> pygame.Surface:
    """Constrói o fundo completo do lobby"""
    f_xl, f_lg, f_md, f_sm = fonts
    width = LOBBY_WORLD_XMAX - LOBBY_WORLD_XMIN
    height = LOBBY_WORLD_YMAX - LOBBY_WORLD_YMIN
    surf = pygame.Surface((width, height))
    rng = random.Random(42)
    
    # Gradiente base
    grad = _create_gradient_surface(width, height)
    surf.blit(grad, (0, 0))
    
    # Textura de grama
    _add_grass_texture(surf, grad, width, height, rng)
    
    # Caminhos entre fases
    _draw_paths_between_stages(surf, width, height, rng)
    
    # Arbustos
    bush_positions = [
        (180,180), (1420,180), (180,1020), (1420,1020),
        (500,300), (1100,300), (500,900), (1100,900),
        (300,600), (1300,600), (750,200), (850,200),
        (750,1000), (850,1000), (200,480), (200,720),
        (1400,480), (1400,720), (620,300), (980,300),
        (620,900), (980,900), (400,480), (400,720),
        (1200,480), (1200,720),
    ]
    for bx, by in bush_positions:
        _draw_bush(surf, bx, by, rng.randint(5, 9), rng)
    
    # Árvores
    for tx, ty in _TREE_POSITIONS:
        _draw_tree(surf, tx, ty, rng)
    
    # Plataformas das fases
    STAGE_ABBRS = ['Re', 'En', 'Rc', 'Le', 'Ps']
    for i, (wx, wy) in enumerate(LOBBY_STAGE_POS):
        sx, sy = _world_to_bg(wx, wy)
        radius = 44 if i < 4 else 64
        color = LOBBY_STAGE_COLORS[i]
        dim = tuple(max(0, c - 35) for c in color)
        bright = tuple(min(255, c + 45) for c in color)
        
        _draw_stage_platform(surf, sx, sy, radius, color, bright, dim)
        _draw_platform_badge(surf, sx, sy, radius, color, bright,
                            LOBBY_STAGE_NAMES[i], STAGE_ABBRS[i], fonts)
    
    return surf

# ── Helpers de coordenada ──────────────────────────────────────────────────────

def clamp_lobby_player(px, py):
    px = max(LOBBY_WORLD_XMIN + 20, min(LOBBY_WORLD_XMAX - 20, px))
    py = max(LOBBY_WORLD_YMIN + 20, min(LOBBY_WORLD_YMAX - 20, py))
    return px, py

def lobby_difficulty_buttons(W, H):
    gap   = 16
    btn_w = 140
    btn_h = 40
    y     = H - 160
    total_w = len(DIFFICULTY_NAMES) * btn_w + (len(DIFFICULTY_NAMES) - 1) * gap
    start_x = (W - total_w) // 2
    return [
        (name, start_x + i * (btn_w + gap), y, btn_w, btn_h, name)
        for i, name in enumerate(DIFFICULTY_NAMES)
    ]

# ── Update ─────────────────────────────────────────────────────────────────────

def update_lobby(events, dt, game) -> None:
    keys = pygame.key.get_pressed()
    move_x = move_y = 0.0

    if game.lobby_stage_selected is None:
        if keys[pygame.K_w] or keys[pygame.K_UP]:    move_y += 1.0
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  move_y -= 1.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  move_x -= 1.0
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: move_x += 1.0

    if move_x != 0.0 or move_y != 0.0:
        length = math.hypot(move_x, move_y)
        game.lobby_px += game.lobby_speed * dt * move_x / length
        game.lobby_py += game.lobby_speed * dt * move_y / length
        game.lobby_anim_t += dt
        if abs(move_x) > abs(move_y):
            game.lobby_last_move = 'right' if move_x > 0 else 'left'
        else:
            game.lobby_last_move = 'up' if move_y > 0 else 'down'
    else:
        game.lobby_anim_t = 0.0
        game.lobby_last_move = 'idle'

    game.lobby_px, game.lobby_py = clamp_lobby_player(game.lobby_px, game.lobby_py)

    near = None
    for i, (wx, wy) in enumerate(LOBBY_STAGE_POS):
        if math.hypot(game.lobby_px - wx, game.lobby_py - wy) < LOBBY_ENTRY_RADIUS:
            near = i
            break
    game.lobby_entered_stage = near
    if game.lobby_entered_stage is None:
        game.lobby_stage_selected = None

    W, H = game.screen.get_size()

    for ev in events:
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                if game.lobby_stage_selected is not None:
                    game.lobby_stage_selected = None
                else:
                    pygame.mixer.music.stop()
                    pygame.mixer.music.load("musics/openingmenu.mp3")
                    pygame.mixer.music.play(-1)
                    game.state = 'menu'
            elif ev.key == pygame.K_RETURN:
                if game.lobby_stage_selected is None and game.lobby_entered_stage is not None:
                    game.lobby_stage_selected = game.lobby_entered_stage
                elif game.lobby_stage_selected == 4:
                    game._try_start(stage_idx=4)
                elif game.lobby_stage_selected in {0, 1, 2, 3}:
                    game.difficulty_phase = game.difficulty
                    game._try_start(stage_idx=game.lobby_stage_selected, difficulty=game.difficulty)
            elif game.lobby_stage_selected in {0,1,2,3} and ev.key in {pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d}:
                idx = DIFFICULTY_NAMES.index(game.difficulty)
                idx = (idx - 1) % len(DIFFICULTY_NAMES) if ev.key in {pygame.K_LEFT, pygame.K_a} else (idx + 1) % len(DIFFICULTY_NAMES)
                game.difficulty = DIFFICULTY_NAMES[idx]
            elif game.lobby_stage_selected == 4:
                if ev.key == pygame.K_BACKSPACE:
                    game.input_text = game.input_text[:-1]
                elif ev.key in {pygame.K_LEFT, pygame.K_RIGHT}:
                    idx = DIFFICULTY_NAMES.index(game.difficulty)
                    idx = (idx - 1) % len(DIFFICULTY_NAMES) if ev.key == pygame.K_LEFT else (idx + 1) % len(DIFFICULTY_NAMES)
                    game.difficulty = DIFFICULTY_NAMES[idx]
                elif ev.unicode:
                    game.input_text += ev.unicode
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if game.lobby_stage_selected in {0, 1, 2, 3}:
                mx, my = ev.pos
                for lbl, bx, by, bw, bh, name in lobby_difficulty_buttons(W, H):
                    if bx <= mx <= bx+bw and by <= my <= by+bh:
                        game.difficulty_phase = name
                        game._try_start(stage_idx=game.lobby_stage_selected, difficulty=name)
                        break

    game.char_frame_t += dt
    anim_key = game.lobby_last_move if game.lobby_last_move in game.sprites else 'idle'
    frames   = game.sprites.get(anim_key, [None])
    spd      = game.char_frame_spd.get(anim_key, 0.12)
    if game.char_frame_t >= spd:
        game.char_frame_t = 0.0
        game.char_frame   = (game.char_frame + 1) % max(1, len(frames))

# ── Draw ───────────────────────────────────────────────────────────────────────

def draw_lobby(screen, fonts, game, lobby_bg_surf, menu_art) -> None:
    print(f"char: {game.sprite_folder}")
    f_xl, f_lg, f_md, f_sm = fonts
    W, H = screen.get_size()

    screen.blit(menu_art, (0, 0))

    view_x = (W - LOBBY_VIEW_W) // 2
    view_y = 120

    player_bg_x = int(game.lobby_px - LOBBY_WORLD_XMIN)
    player_bg_y = int(LOBBY_WORLD_YMAX - game.lobby_py)

    map_x = min(0, max(LOBBY_VIEW_W - lobby_bg_surf.get_width(),  LOBBY_VIEW_W // 2 - player_bg_x))
    map_y = min(0, max(LOBBY_VIEW_H - lobby_bg_surf.get_height(), LOBBY_VIEW_H // 2 - player_bg_y))

    # ── Tudo no view_surf — clipping automático ───────────────────────────────
    view_surf = pygame.Surface((LOBBY_VIEW_W, LOBBY_VIEW_H))
    view_surf.fill((10, 14, 28))
    view_surf.blit(lobby_bg_surf, (map_x, map_y))

    char_view_x = map_x + player_bg_x
    char_view_y = map_y + player_bg_y

    anim = game.lobby_last_move if game.lobby_last_move in game.sprites else 'idle'

    # Árvores ATRÁS do personagem
    _rng_behind = random.Random(42)
    for _tx, _ty in _TREE_POSITIONS:
        if _ty <= player_bg_y:
            tree_vx = map_x + _tx
            tree_vy = map_y + _ty
            if -40 <= tree_vx <= LOBBY_VIEW_W + 40 and -40 <= tree_vy <= LOBBY_VIEW_H + 40:
                _draw_tree(view_surf, int(tree_vx), int(tree_vy), _rng_behind)

    # Personagem
    draw_char(view_surf, game.sprites_lobby, anim, int(char_view_x), int(char_view_y),
              game.char_frame, size=CHAR_SIZE_LOBBY)

    # Árvores NA FRENTE do personagem
    _rng_front = random.Random(42)
    for _tx, _ty in _TREE_POSITIONS:
        if _ty > player_bg_y:
            tree_vx = map_x + _tx
            tree_vy = map_y + _ty
            if -40 <= tree_vx <= LOBBY_VIEW_W + 40 and -40 <= tree_vy <= LOBBY_VIEW_H + 40:
                _draw_tree(view_surf, int(tree_vx), int(tree_vy), _rng_front)

    screen.blit(view_surf, (view_x, view_y))

    # ── Borda dupla da viewport ────────────────────────────────────────────────
    for off, col in [(0, (185, 185, 210)), (1, (90, 90, 125))]:
        pts = [
            ((view_x - off,               view_y - off),
             (view_x + LOBBY_VIEW_W + off, view_y - off)),
            ((view_x + LOBBY_VIEW_W + off, view_y - off),
             (view_x + LOBBY_VIEW_W + off, view_y + LOBBY_VIEW_H + off)),
            ((view_x + LOBBY_VIEW_W + off, view_y + LOBBY_VIEW_H + off),
             (view_x - off,               view_y + LOBBY_VIEW_H + off)),
            ((view_x - off,               view_y + LOBBY_VIEW_H + off),
             (view_x - off,               view_y - off)),
        ]
        for (x0, y0), (x1, y1) in pts:
            line_bresenham(screen, x0, y0, x1, y1, col)

    # ── Overlay apenas nas faixas de UI (não sobre o mapa) ────────────────────
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
   # Isso NÃO terá transparência - ficará opaco
    fill_rectangle_optimized(overlay, 0, 0, W, view_y, (12, 16, 34))
    y_start = view_y + LOBBY_VIEW_H
    height = H - view_y - LOBBY_VIEW_H
    fill_rectangle_optimized(overlay, 0, y_start, W, height, (12, 16, 34))  # Sem alpha

    screen.blit(overlay, (0, 0))

    # ── UI ────────────────────────────────────────────────────────────────────
    _txt(screen, f_xl, 'LOBBY', W // 2, 40, (245, 245, 255), center=True)
    _txt(screen, f_sm, 'Use WASD / setas para andar e ENTER quando estiver sobre uma fase',
         W // 2, 84, (205, 205, 225), center=True)

    # ── Minimapa ──────────────────────────────────────────────────────────────
    mini_w, mini_h = 220, 140
    mini_x = W - mini_w - 24
    mini_y = 120
    mini_surf = pygame.Surface((mini_w, mini_h))
    mini_surf.fill((10, 14, 20))

    mini_window   = Window(LOBBY_WORLD_XMIN, LOBBY_WORLD_YMIN, LOBBY_WORLD_XMAX, LOBBY_WORLD_YMAX)
    mini_viewport = Viewport(0, mini_h, mini_w, 0)

    draw_line_viewport(mini_surf, -360, 0, 360, 0, (70,70,110), mini_window, mini_viewport)
    draw_line_viewport(mini_surf, 0, -260, 0, 260, (70,70,110), mini_window, mini_viewport)

    for i, (wx, wy) in enumerate(LOBBY_STAGE_POS):
        marker = [(wx-10,wy),(wx,wy+10),(wx+10,wy),(wx,wy-10)]
        draw_polygon_viewport(mini_surf, marker, LOBBY_STAGE_COLORS[i], mini_window, mini_viewport)

    player_marker = [
        (game.lobby_px-8, game.lobby_py),
        (game.lobby_px,   game.lobby_py+8),
        (game.lobby_px+8, game.lobby_py),
        (game.lobby_px,   game.lobby_py-8),
    ]
    draw_polygon_viewport(mini_surf, player_marker, (235,235,100), mini_window, mini_viewport)

    for off in range(2):
        line_bresenham(mini_surf, off, off, mini_w-1-off, off, (140,140,170))
        line_bresenham(mini_surf, mini_w-1-off, off, mini_w-1-off, mini_h-1-off, (140,140,170))
        line_bresenham(mini_surf, mini_w-1-off, mini_h-1-off, off, mini_h-1-off, (140,140,170))
        line_bresenham(mini_surf, off, mini_h-1-off, off, off, (140,140,170))

    screen.blit(mini_surf, (mini_x, mini_y))
    _txt(screen, f_sm, 'MINI VIEWPORT', mini_x + mini_w//2, mini_y-18, (200,200,230), center=True)

    # ── MONEY HUD ─────────────────────────────────────────────

    draw_coin(screen, 40, 40, 14)

    _txt(screen, f_md, f"{game.money}", 65, 30, (255,255,180))


    # ── Painel de seleção ─────────────────────────────────────────────────────
    if game.lobby_stage_selected is not None:
        label = LOBBY_STAGE_NAMES[game.lobby_stage_selected]
        if game.lobby_stage_selected in {0,1,2,3}:
            _txt(screen, f_md, f'{label}: escolha a dificuldade para iniciar',
                 W//2, H-80, (240,220,140), center=True)
            for lbl, bx, by, bw, bh, name in lobby_difficulty_buttons(W, H):
                _draw_btn(screen, bx, by, bw, bh, lbl, f_sm,
                          active=(name == game.difficulty),
                          color=DIFFICULTY_COLORS[name])
            _txt(screen, f_sm, 'Use ←/→ ou A/D para mudar dificuldade e ENTER para começar',
                 W//2, H-182, (190,190,220), center=True)
        else:
            _txt(screen, f_sm, 'Use ← → para mudar dificuldade', W//2, H-220, (190,190,220), center=True)
            for lbl, bx, by, bw, bh, name in lobby_difficulty_buttons(W, H):
                _draw_btn(screen, bx, by, bw, bh, lbl, f_sm,
                          active=(name == game.difficulty),
                          color=DIFFICULTY_COLORS[name])
            msg = ('Digite o nome do arquivo em musics/ (ex: minha.mp3)'
                   if not game.input_text
                   else 'Pressione ENTER para iniciar a fase personalizada')
            _txt(screen, f_md, msg, W//2, H-102, (240,220,140), center=True)

            bx, by, bw, bh = 120, H-90, W-240, 48
            scanline_fill(screen, [(bx,by),(bx+bw,by),(bx+bw,by+bh),(bx,by+bh)], (16,20,36))
            cb = (120,120,190)
            line_bresenham(screen, bx,    by,    bx+bw, by,    cb)
            line_bresenham(screen, bx+bw, by,    bx+bw, by+bh, cb)
            line_bresenham(screen, bx+bw, by+bh, bx,    by+bh, cb)
            line_bresenham(screen, bx,    by+bh, bx,    by,    cb)
            display = game.input_text[-72:] + ('|' if pygame.time.get_ticks() % 1000 < 500 else '')
            _txt(screen, f_sm, display, bx+10, by+12, (235,235,255))

    elif game.lobby_entered_stage is not None:
        label = LOBBY_STAGE_NAMES[game.lobby_entered_stage]
        if game.lobby_entered_stage in {0,1,2,3}:
            _txt(screen, f_md, f'Passe sobre {label} e pressione ENTER para ver as dificuldades',
                 W//2, H-80, (240,220,140), center=True)
        else:
            _txt(screen, f_md, 'Passe pelo centro e pressione ENTER para inserir o nome personalizado',
                 W//2, H-80, (240,220,140), center=True)
    else:
        _txt(screen, f_md, 'Aproxime-se de uma fase para ver o botão de entrada',
             W//2, H-80, (175,175,215), center=True)

    if game.lobby_stage_selected == 4:
        _txt(screen, f_sm, 'ESC = cancelar seleção  |  BACKSPACE apaga o caminho  |  ENTER inicia',
             W//2, H-24, (180,180,210), center=True)
    elif game.lobby_stage_selected is not None:
        _txt(screen, f_sm, 'ESC = cancelar seleção  |  ←/→ ou A/D muda dificuldade  |  ENTER inicia',
             W//2, H-24, (180,180,210), center=True)
    else:
        _txt(screen, f_sm, 'ESC = menu  |  ENTER entra na fase  |  selecione a dificuldade e aperte enter para jogar',
             W//2, H-24, (180,180,210), center=True, scale_size=1)
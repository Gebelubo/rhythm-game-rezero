import os
import math
import pygame
from src.funcs.cg_lib import (
    line_bresenham, circle_midpoint, ellipse_midpoint,
    flood_fill, boundary_fill, scanline_fill, set_pixel,
    draw_rectangle
)
from src.utils.ui import _txt, _draw_btn
from src.music_backend.backend_config import DIFFICULTY_COLORS, DIFFICULTY_NAMES


# ── Splash Screen ──────────────────────────────────────────────────────────────

def build_splash_screen(W, H) -> pygame.Surface:
    surf = pygame.Surface((W, H))
    surf.fill((6, 8, 22))

    cx, cy = W // 2, H // 2

    try:
        font_xl = pygame.font.SysFont('Arial', 54, bold=True)
        font_md = pygame.font.SysFont('Arial', 22)
        font_sm = pygame.font.SysFont('Arial', 16)
    except Exception:
        font_xl = pygame.font.Font(None, 54)
        font_md = pygame.font.Font(None, 22)
        font_sm = pygame.font.Font(None, 16)

    title = font_xl.render('Re:Song', True, (235, 220, 255))
    surf.blit(title, (cx - title.get_width() // 2, cy - 40))

    sub = font_md.render(
        'E mesmo quando tudo der errado, você ainda pode recomeçar do zero',
        True, (160, 145, 200))
    surf.blit(sub, (cx - sub.get_width() // 2, cy + 20))

    hint = font_sm.render(
        'Pressione qualquer tecla ou clique para continuar',
        True, (100, 90, 150))
    surf.blit(hint, (cx - hint.get_width() // 2, H - 38))

    return surf


def draw_splash(screen, splash_surf, alpha: int) -> None:
    """Renderiza a splash screen com fade via alpha (0–255)."""
    s = splash_surf.copy()
    s.set_alpha(alpha)
    screen.fill((6, 8, 22))
    screen.blit(s, (0, 0))


# ── Menu BG ────────────────────────────────────────────────────────────────────

def load_menu_bg_image():
      return None


def _draw_background_from_image(surf, image, W, H):
    src_w, src_h = image.get_width(), image.get_height()
    if src_w == 0 or src_h == 0:
        return
    for y in range(H):
        src_y = int(y * src_h / H)
        if src_y >= src_h:
            src_y = src_h - 1
        for x in range(W):
            src_x = int(x * src_w / W)
            if src_x >= src_w:
                src_x = src_w - 1
            color = image.get_at((src_x, src_y))[:3]
            set_pixel(surf, x, y, color)


def build_menu_art(W, H, menu_bg_image):
    surf = pygame.Surface((W, H))
    surf.fill((12, 14, 36))
    if menu_bg_image:
        _draw_background_from_image(surf, menu_bg_image, W, H)
    return surf


# ── Menu principal ─────────────────────────────────────────────────────────────

def draw_menu(screen, fonts, W, H, alphas, menu_selection, menu_buttons, menu_error, menu_art):
    f_xl, f_lg, f_md, f_sm = fonts
    screen.blit(menu_art, (0, 0))

    a1 = alphas[1]
    _txt(screen, f_xl, 'Re:Song', W // 2, 52,
         (int(245*a1), int(245*a1), int(245*a1)), center=True)
    a2 = alphas[2]
    _txt(screen, f_md, 'E mesmo quando tudo der errado, você ainda pode recomeçar do zero',
         W // 2, 100, (int(225*a2), int(225*a2), int(235*a2)), center=True)

    btn_w, btn_h, gap = 220, 54, 20
    start_x = W // 2 - btn_w // 2
    start_y = 160
    menu_buttons_def = [
        ('JOGAR',         start_x, start_y,                   btn_w, btn_h, 'play',     (95, 180, 255)),
        ('CONFIGURAÇÕES', start_x, start_y + btn_h + gap,     btn_w, btn_h, 'settings', (120, 200, 120)),
        ('TUTORIAL',      start_x, start_y + 2*(btn_h + gap), btn_w, btn_h, 'tutorial', (155, 115, 235)),
        ('SAIR',          start_x, start_y + 3*(btn_h + gap), btn_w, btn_h, 'exit',     (235, 90, 110)),
    ]

    menu_buttons.clear()
    for i, (label, bx, by, bw, bh, action, color) in enumerate(menu_buttons_def):
        a_btn = alphas[i + 3]
        btn_color = (int(color[0]*a_btn), int(color[1]*a_btn), int(color[2]*a_btn))
        _draw_btn(screen, bx, by, bw, bh, label, f_md,
                  active=(i == menu_selection), color=btn_color)
        menu_buttons.append((bx, by, bw, bh, action))

    if menu_error:
        _txt(screen, f_sm, menu_error, W // 2, H - 140, (255, 90, 90), center=True)

    a6 = alphas[6]
    footer_color = (int(185*a6), int(185*a6), int(210*a6))
    _txt(screen, f_sm, 'ESC = sair   |   JOGAR leva ao lobby de fases',
         W // 2, H - 24, footer_color, center=True)


# ── Tutorial ───────────────────────────────────────────────────────────────────

def draw_tutorial(screen, fonts, W, H, menu_art):
    f_xl, f_lg, f_md, f_sm = fonts
    screen.blit(menu_art, (0, 0))

    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((8, 12, 28, 220))
    screen.blit(overlay, (0, 0))

    px, py, pw, ph = 60, 40, W - 120, H - 80
    scanline_fill(screen, [(px,py),(px+pw,py),(px+pw,py+ph),(px,py+ph)], (12, 15, 35))
    bc = (130, 110, 220)
    line_bresenham(screen, px, py, px+pw, py, bc)
    line_bresenham(screen, px, py+ph, px+pw, py+ph, bc)
    line_bresenham(screen, px, py, px, py+ph, bc)
    line_bresenham(screen, px+pw, py, px+pw, py+ph, bc)

    _txt(screen, f_xl, 'Re:Song  —  Como Jogar', W // 2, py + 30, (235, 235, 255), center=True)
    _txt(screen, f_sm, 'Um jogo de ritmo ambientado no universo de Re:Zero',
         W // 2, py + 62, (160, 150, 200), center=True)

    line_bresenham(screen, px + 20, py + 80, px + pw - 20, py + 80, (50, 45, 90))

    col1 = [
        ('NAVEGAÇÃO', ''),
        ('JOGAR',      'Abre o lobby'),
        ('WASD/SETAS', 'Anda pelo lobby'),
        ('ENTER',      'Entra na fase'),
        ('Centro',     'Fase personalizada'),
    ]
    col2 = [
        ('NO JOGO', ''),
        ('← ↓ ↑ →', 'Acerta as notas'),
        ('ESC',      'Volta ao lobby'),
        ('Combo',    'Bonus a cada 10'),
        ('Miss',     'Zera o combo'),
    ]

    c1x = px + 30
    c2x = px + 160
    c3x = px + pw // 2
    c4x = px + pw // 2 + 130

    for i, ((k1, d1), (k2, d2)) in enumerate(zip(col1, col2)):
        iy = py + 100 + i * 34
        color_k = (180, 150, 255) if i == 0 else (220, 210, 255)
        color_d = (140, 135, 175)
        _txt(screen, f_md if i == 0 else f_sm, k1, c1x, iy, color_k)
        _txt(screen, f_md if i == 0 else f_sm, k2, c3x, iy, color_k)
        if d1: _txt(screen, f_sm, d1, c2x, iy, color_d)
        if d2: _txt(screen, f_sm, d2, c4x, iy, color_d)

    line_bresenham(screen, px + 20, py + 268, px + pw - 20, py + 268, (50, 45, 90))

    _txt(screen, f_md, 'JULGAMENTOS', px + 30, py + 278, (180, 150, 255))
    grades = [
        ('PERFECT', '300 pts', (255, 220, 50)),
        ('GOOD',    '150 pts', ( 80, 220, 80)),
        ('OK',      ' 55 pts', ( 80, 170, 255)),
        ('MISS',    '  0 pts', (255,  70, 70)),
    ]
    gw = (pw - 60) // 4
    for i, (name, pts, color) in enumerate(grades):
        gx = px + 30 + i * (gw + 8)
        gy = py + 308
        scanline_fill(screen, [(gx,gy),(gx+gw,gy),(gx+gw,gy+48),(gx,gy+48)],
                      tuple(v // 5 for v in color))
        line_bresenham(screen, gx, gy, gx+gw, gy, tuple(v // 2 for v in color))
        line_bresenham(screen, gx, gy+48, gx+gw, gy+48, tuple(v // 2 for v in color))
        line_bresenham(screen, gx, gy, gx, gy+48, tuple(v // 2 for v in color))
        line_bresenham(screen, gx+gw, gy, gx+gw, gy+48, tuple(v // 2 for v in color))
        _txt(screen, f_sm, name, gx + gw // 2, gy + 10, color, center=True)
        _txt(screen, f_sm, pts,  gx + gw // 2, gy + 28,
             tuple(v // 2 + 80 for v in color), center=True)

    line_bresenham(screen, px + 20, py + 372, px + pw - 20, py + 372, (50, 45, 90))

    quote = '"Mesmo que esqueça tudo, eu não vou me esquecer de nenhum vocês"'
    _txt(screen, f_sm, quote, W // 2, py + 390, (120, 110, 160), center=True)
    _txt(screen, f_sm, 'ESC = voltar ao menu  |  clique para voltar',
         W // 2, py + ph - 18, (90, 85, 130), center=True)


# ── Configurações ──────────────────────────────────────────────────────────────

def draw_settings(screen, fonts, W, H, menu_art, settings):
    f_xl, f_lg, f_md, f_sm = fonts
    screen.blit(menu_art, (0, 0))

    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((8, 12, 28, 220))
    screen.blit(overlay, (0, 0))

    px, py, pw, ph = 80, 60, W - 160, H - 120
    scanline_fill(screen, [(px,py),(px+pw,py),(px+pw,py+ph),(px,py+ph)], (12, 15, 35))
    bc = (130, 110, 220)
    line_bresenham(screen, px, py, px+pw, py, bc)
    line_bresenham(screen, px, py+ph, px+pw, py+ph, bc)
    line_bresenham(screen, px, py, px, py+ph, bc)
    line_bresenham(screen, px+pw, py, px+pw, py+ph, bc)

    _txt(screen, f_xl, 'Configurações', W // 2, py + 30, (235, 235, 255), center=True)
    line_bresenham(screen, px+20, py+70, px+pw-20, py+70, (50, 45, 90))

    settings_buttons = []
    volume_bar = None

    def draw_toggle(x, y, label, key, info=None):
        w, h = 260, 40
        mx, my = pygame.mouse.get_pos()
        active = settings[key]
        base_color = (30, 30, 70) if not active else (60, 40, 120)
        border = (120, 100, 220) if active else (70, 70, 120)
        hover = x <= mx <= x+w and y <= my <= y+h
        if hover:
            border = (180, 160, 255)
        scanline_fill(screen, [(x,y),(x+w,y),(x+w,y+h),(x,y+h)], base_color)
        line_bresenham(screen, x, y, x+w, y, border)
        line_bresenham(screen, x, y+h, x+w, y+h, border)
        line_bresenham(screen, x, y, x, y+h, border)
        line_bresenham(screen, x+w, y, x+w, y+h, border)
        state_txt   = "ON" if active else "OFF"
        state_color = (120, 255, 120) if active else (255, 120, 120)
        _txt(screen, f_sm, label,     x+10,   y+12, (220, 220, 255))
        _txt(screen, f_sm, state_txt, x+w-50, y+12, state_color)
        if info:
            ix, iy = x + w + 10, y + 8
            scanline_fill(screen, [(ix,iy),(ix+24,iy),(ix+24,iy+24),(ix,iy+24)], (20, 20, 50))
            line_bresenham(screen, ix, iy, ix+24, iy, (120,120,200))
            line_bresenham(screen, ix, iy+24, ix+24, iy+24, (120,120,200))
            line_bresenham(screen, ix, iy, ix, iy+24, (120,120,200))
            line_bresenham(screen, ix+24, iy, ix+24, iy+24, (120,120,200))
            _txt(screen, f_sm, "i", ix+12, iy+10, (200, 200, 255), center=True)
            if ix <= mx <= ix+24 and iy <= my <= iy+24:
                _txt(screen, f_sm, info, ix+30, iy+4, (180, 180, 220))
        return (x, y, w, h)

    base_y = py + 100
    gap    = 60
    settings_buttons.append(("adm_mode", draw_toggle(px+40, base_y,
                              "Modo ADM",    "adm_mode",
                              "Permite acessar ferramentas de debug")))
    settings_buttons.append(("show_fps", draw_toggle(px+40, base_y+gap,
                              "Mostrar FPS", "show_fps")))
    settings_buttons.append(("auto_play", draw_toggle(px+40, base_y+gap*2,
                              "Auto Play",   "auto_play",
                              "Joga sozinho (modo debug)")))

    vx, vy = px + pw//2 + 40, base_y
    _txt(screen, f_md, "Volume", vx, vy-30, (200, 180, 255))
    bar_w, bar_h = 220, 10
    vol = settings["volume"]
    scanline_fill(screen,
                  [(vx,vy),(vx+bar_w,vy),(vx+bar_w,vy+bar_h),(vx,vy+bar_h)],
                  (40, 40, 80))
    fill_w = int(bar_w * vol)
    scanline_fill(screen,
                  [(vx,vy),(vx+fill_w,vy),(vx+fill_w,vy+bar_h),(vx,vy+bar_h)],
                  (120, 100, 255))
    line_bresenham(screen, vx, vy, vx+bar_w, vy, (100,100,200))
    line_bresenham(screen, vx, vy+bar_h, vx+bar_w, vy+bar_h, (100,100,200))
    line_bresenham(screen, vx, vy, vx, vy+bar_h, (100,100,200))
    line_bresenham(screen, vx+bar_w, vy, vx+bar_w, vy+bar_h, (100,100,200))
    _txt(screen, f_sm, f"{int(vol*100)}%", vx+bar_w+10, vy-2, (180, 180, 255))
    volume_bar = (vx, vy, bar_w, bar_h)

    _txt(screen, f_sm, "ESC = voltar", W//2, py+ph-20, (100, 100, 150), center=True)

    return settings_buttons, volume_bar
import os
import math
import pygame
from src.funcs.cg_lib import (
    line_bresenham, circle_midpoint, ellipse_midpoint,
    flood_fill, boundary_fill, scanline_fill, set_pixel,
    draw_rectangle, translate, rotate, scale
)
from src.utils.ui import _txt, _draw_btn
from src.music_backend.backend_config import DIFFICULTY_COLORS, DIFFICULTY_NAMES

from src.utils.ui import draw_coin


# ── Splash Screen ──────────────────────────────────────────────────────────────

def build_splash_screen(W, H) -> pygame.Surface:
    surf = pygame.Surface((W, H))

    # fundo
    scanline_fill(
        surf,
        [(0, 0), (W, 0), (W, H), (0, H)],
        (8, 10, 28)
    )

    cx, cy = W // 2, H // 2

    # ─────────────────────────────────────────
    # CÍRCULO (Midpoint Circle)
    # ─────────────────────────────────────────
    circle_midpoint(surf, cx, cy, 120, (120, 100, 255))

    # preenchimento do círculo
    flood_fill(surf, cx, cy, (30, 20, 80))

    # ─────────────────────────────────────────
    # ELIPSE (Midpoint Ellipse)
    # ─────────────────────────────────────────
    ellipse_midpoint(surf, cx, cy, 180, 70, (180, 120, 255))

    # preenchimento da elipse
    boundary_fill(surf, cx, cy - 90, (60, 30, 120), (180, 120, 255))

    # ─────────────────────────────────────────
    # RETAS (Bresenham)
    # ─────────────────────────────────────────
    for i in range(0, 360, 30):
        rad = math.radians(i)

        x2 = int(cx + math.cos(rad) * 220)
        y2 = int(cy + math.sin(rad) * 220)

        line_bresenham(
            surf,
            cx,
            cy,
            x2,
            y2,
            (70, 60, 140)
        )

    # moldura
    margin = 30

    line_bresenham(surf, margin, margin, W-margin, margin, (140,120,255))
    line_bresenham(surf, margin, H-margin, W-margin, H-margin, (140,120,255))
    line_bresenham(surf, margin, margin, margin, H-margin, (140,120,255))
    line_bresenham(surf, W-margin, margin, W-margin, H-margin, (140,120,255))

    # ─────────────────────────────────────────
    # FONTES MELHORES
    # ─────────────────────────────────────────

    font_path = pygame.font.match_font("segoeui")
    title_font = pygame.font.Font(font_path, 64)
    sub_font   = pygame.font.Font(font_path, 24)
    hint_font  = pygame.font.Font(font_path, 18)

    # sombra do título
    shadow = title_font.render("Re:Song", True, (20, 20, 40))
    surf.blit(shadow, (cx - shadow.get_width() // 2 + 3, cy - 45 + 3))

    # título
    title = title_font.render("Re:Song", True, (245, 235, 255))
    surf.blit(title, (cx - title.get_width() // 2, cy - 45))

    # subtítulo
    sub = sub_font.render(
        "E mesmo quando tudo der errado, você ainda pode recomeçar do zero",
        True,
        (190, 180, 230)
    )

    surf.blit(sub, (cx - sub.get_width() // 2, cy + 40))

    # dica
    hint = hint_font.render(
        "Pressione qualquer tecla para continuar",
        True,
        (120, 110, 180)
    )

    surf.blit(hint, (cx - hint.get_width() // 2, H - 50))

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

    # ─────────────────────────────────────────
    # FUNDO
    # ─────────────────────────────────────────

    scanline_fill(
        surf,
        [(0,0),(W,0),(W,H),(0,H)],
        (10, 12, 32)
    )

    # ─────────────────────────────────────────
    # GRADIENTE MANUAL
    # ─────────────────────────────────────────

    for y in range(H):

        t = y / H

        r = int(10 + 25 * t)
        g = int(12 + 18 * t)
        b = int(32 + 50 * t)

        line_bresenham(
            surf,
            0,
            y,
            W,
            y,
            (r, g, b)
        )

    cx = W // 2
    cy = H // 2

    # ─────────────────────────────────────────
    # CÍRCULO CENTRAL
    # ─────────────────────────────────────────

    circle_midpoint(
        surf,
        cx,
        cy,
        180,
        (110, 90, 240)
    )

    flood_fill(
        surf,
        cx,
        cy,
        (30, 20, 70)
    )

    # ─────────────────────────────────────────
    # ELIPSES DECORATIVAS
    # ─────────────────────────────────────────

    ellipse_midpoint(
        surf,
        cx,
        cy,
        260,
        100,
        (180, 120, 255)
    )

    ellipse_midpoint(
        surf,
        cx,
        cy,
        320,
        140,
        (90, 70, 180)
    )

    boundary_fill(
        surf,
        cx,
        cy - 120,
        (45, 25, 90),
        (180, 120, 255)
    )

    # ─────────────────────────────────────────
    # LINHAS RADIAIS
    # ─────────────────────────────────────────

    for angle in range(0, 360, 15):

        rad = math.radians(angle)

        x2 = int(cx + math.cos(rad) * 340)
        y2 = int(cy + math.sin(rad) * 340)

        line_bresenham(
            surf,
            cx,
            cy,
            x2,
            y2,
            (60, 50, 120)
        )

    # ─────────────────────────────────────────
    # GRID RETRÔ
    # ─────────────────────────────────────────

    for x in range(0, W, 40):

        line_bresenham(
            surf,
            x,
            0,
            x,
            H,
            (18, 20, 45)
        )

    for y in range(0, H, 40):

        line_bresenham(
            surf,
            0,
            y,
            W,
            y,
            (18, 20, 45)
        )

    # ─────────────────────────────────────────
    # MOLDURA
    # ─────────────────────────────────────────

    margin = 20

    line_bresenham(
        surf,
        margin,
        margin,
        W-margin,
        margin,
        (150,120,255)
    )

    line_bresenham(
        surf,
        margin,
        H-margin,
        W-margin,
        H-margin,
        (150,120,255)
    )

    line_bresenham(
        surf,
        margin,
        margin,
        margin,
        H-margin,
        (150,120,255)
    )

    line_bresenham(
        surf,
        W-margin,
        margin,
        W-margin,
        H-margin,
        (150,120,255)
    )

    # ─────────────────────────────────────────
    # ESTRELAS PIXELADAS
    # ─────────────────────────────────────────

    for _ in range(120):

        sx = int((math.sin(_) * 99999) % W)
        sy = int((math.cos(_) * 99999) % H)

        set_pixel(surf, sx, sy, (255,255,255))

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
        ('SHOP',          start_x, start_y + 3*(btn_h + gap), btn_w, btn_h, 'shop',     (255, 180, 90)),
        ('PERSONAGENS',    start_x, start_y + 4*(btn_h + gap), btn_w, btn_h, 'character_select', (255, 180, 90)),
        ('SAIR',          start_x, start_y + 5*(btn_h + gap), btn_w, btn_h, 'exit',     (235, 90, 110)),
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

    # ─────────────────────────────────────────
    # OVERLAY ESCURO
    # ─────────────────────────────────────────

    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((5, 8, 20, 210))
    screen.blit(overlay, (0, 0))

    # ─────────────────────────────────────────
    # PAINEL PRINCIPAL
    # ─────────────────────────────────────────

    px, py = 90, 55
    pw, ph = W - 180, H - 110

    # sombra
    scanline_fill(
        screen,
        [
            (px+8, py+8),
            (px+pw+8, py+8),
            (px+pw+8, py+ph+8),
            (px+8, py+ph+8)
        ],
        (0,0,0)
    )

    # painel
    scanline_fill(
        screen,
        [
            (px, py),
            (px+pw, py),
            (px+pw, py+ph),
            (px, py+ph)
        ],
        (14, 18, 40)
    )

    # bordas duplas
    border1 = (120, 100, 220)
    border2 = (70, 60, 140)

    draw_rectangle(screen, px, py, pw, ph, border1)
    draw_rectangle(screen, px+3, py+3, pw-6, ph-6, border2)

    # ─────────────────────────────────────────
    # CÍRCULO DECORATIVO
    # ─────────────────────────────────────────

    cx = px + pw - 130
    cy = py + 110

    circle_midpoint(screen, cx, cy, 58, (90, 70, 180))
    circle_midpoint(screen, cx, cy, 48, (130, 100, 255))

    ellipse_midpoint(screen, cx, cy, 80, 26, (70, 50, 150))

    for a in range(0, 360, 30):

        rad = math.radians(a)

        x2 = int(cx + math.cos(rad) * 70)
        y2 = int(cy + math.sin(rad) * 70)

        line_bresenham(
            screen,
            cx,
            cy,
            x2,
            y2,
            (60, 50, 120)
        )

    # ─────────────────────────────────────────
    # TÍTULO
    # ─────────────────────────────────────────

    _txt(
        screen,
        f_xl,
        "COMO JOGAR",
        px + 40,
        py + 36,
        (240,240,255)
    )

    _txt(
        screen,
        f_sm,
        "Rhythm Game inspirado em Re:Zero",
        px + 42,
        py + 72,
        (150,140,190)
    )

    line_bresenham(
        screen,
        px + 40,
        py + 95,
        px + pw - 40,
        py + 95,
        (55, 50, 100)
    )

    # ─────────────────────────────────────────
    # COLUNA ESQUERDA
    # ─────────────────────────────────────────

    left_x = px + 50
    top_y  = py + 130

    _txt(screen, f_md, "NAVEGACAO", left_x, top_y, (190,160,255))

    controls = [
        ("WASD", "Mover personagem"),
        ("ENTER", "Entrar na fase"),
        ("ESC", "Voltar ao menu"),
    ]

    for i, (k, d) in enumerate(controls):

        iy = top_y + 45 + i*50

        # tecla decorativa
        scanline_fill(
            screen,
            [
                (left_x, iy),
                (left_x+90, iy),
                (left_x+90, iy+30),
                (left_x, iy+30)
            ],
            (28,30,60)
        )

        draw_rectangle(
            screen,
            left_x,
            iy,
            90,
            30,
            (90,80,170)
        )

        _txt(
            screen,
            f_sm,
            k,
            left_x + 18,
            iy + 8,
            (240,240,255)
        )

        _txt(
            screen,
            f_sm,
            d,
            left_x + 120,
            iy + 8,
            (170,170,210)
        )

    # ─────────────────────────────────────────
    # COLUNA DIREITA
    # ─────────────────────────────────────────

    rx = px + pw//2 + 20

    _txt(screen, f_md, "JULGAMENTOS", rx, top_y, (190,160,255))

    grades = [
        ("PERFECT", "300", (255,220,90)),
        ("GOOD",    "150", (80,220,120)),
        ("OK",      "55",  (80,170,255)),
        ("MISS",    "0",   (255,90,90)),
    ]

    for i, (name, pts, color) in enumerate(grades):

        gy = top_y + 45 + i*48

        scanline_fill(
            screen,
            [
                (rx, gy),
                (rx+180, gy),
                (rx+180, gy+34),
                (rx, gy+34)
            ],
            tuple(v//5 for v in color)
        )

        draw_rectangle(
            screen,
            rx,
            gy,
            180,
            34,
            tuple(v//2 for v in color)
        )

        _txt(screen, f_sm, name, rx+14, gy+8, color)

        _txt(
            screen,
            f_sm,
            pts + " pts",
            rx+110,
            gy+8,
            tuple(min(255, c+40) for c in color)
        )

    # ─────────────────────────────────────────
    # QUOTE
    # ─────────────────────────────────────────

    qy = py + ph - 90

    line_bresenham(
        screen,
        px + 40,
        qy - 20,
        px + pw - 40,
        qy - 20,
        (50,45,90)
    )

    _txt(
        screen,
        f_sm,
        '"Mesmo que tudo se repita..."',
        W//2,
        qy,
        (130,120,170),
        center=True
    )

    _txt(
        screen,
        f_sm,
        'ESC para voltar',
        W//2,
        py + ph - 34,
        (90,85,130),
        center=True
    )

# ── Configurações ──────────────────────────────────────────────────────────────

def draw_settings(screen, fonts, W, H, menu_art, settings):
    f_xl, f_lg, f_md, f_sm = fonts
    screen.blit(menu_art, (0, 0))

    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((8, 12, 28, 220))
    screen.blit(overlay, (0, 0))

    px, py, pw, ph = 80, 60, W - 160, H - 120

    # painel
    scanline_fill(
        screen,
        [(px,py),(px+pw,py),(px+pw,py+ph),(px,py+ph)],
        (12, 15, 35)
    )

    bc = (130, 110, 220)

    line_bresenham(screen, px, py, px+pw, py, bc)
    line_bresenham(screen, px, py+ph, px+pw, py+ph, bc)
    line_bresenham(screen, px, py, px, py+ph, bc)
    line_bresenham(screen, px+pw, py, px+pw, py+ph, bc)

    # linhas internas suaves
    line_bresenham(screen, px+20, py+70, px+pw-20, py+70, (50, 45, 90))
    line_bresenham(screen, px+pw//2, py+90, px+pw//2, py+ph-40, (40, 38, 70))

    # título
    _txt(
        screen,
        f_xl,
        'Configurações',
        W // 2,
        py + 32,
        (235, 235, 255),
        center=True
    )

    # ─────────────────────────────────────────────
    # ELEMENTO VISUAL COM TRANSFORMAÇÕES
    # ─────────────────────────────────────────────

    t = pygame.time.get_ticks() * 0.05

    cx = px + pw - 190
    cy = py + 20

    diamond = [
        (cx, cy - 24),
        (cx + 24, cy),
        (cx, cy + 24),
        (cx - 24, cy),
    ]

    # escala animada
    scale_factor = 1.0 + math.sin(math.radians(t * 2)) * 0.18
    diamond = scale(
        diamond,
        scale_factor,
        scale_factor,
        cx,
        cy
    )

    # rotação animada
    diamond = rotate(
        diamond,
        t,
        cx,
        cy
    )

    # pequena translação flutuando
    diamond = translate(
        diamond,
        0,
        math.sin(math.radians(t * 3)) * 4
    )

    # preenchimento
    scanline_fill(screen, diamond, (45, 30, 95))

    # borda
    for i in range(len(diamond)):
        x1, y1 = diamond[i]
        x2, y2 = diamond[(i + 1) % len(diamond)]

        line_bresenham(
            screen,
            int(x1), int(y1),
            int(x2), int(y2),
            (170, 140, 255)
        )

    # brilho central
    circle_midpoint(screen, int(cx), int(cy), 6, (210, 180, 255))
    flood_fill(screen, int(cx), int(cy), (140, 90, 255))

    settings_buttons = []
    volume_bar = None

    def draw_toggle(x, y, label, key, info=None):
        w, h = 260, 40

        mx, my = pygame.mouse.get_pos()

        active = settings[key]

        base_color = (30, 30, 70) if not active else (60, 40, 120)
        border     = (80, 80, 130) if not active else (150, 120, 255)

        hover = x <= mx <= x+w and y <= my <= y+h

        if hover:
            border = (210, 190, 255)

        # fundo
        scanline_fill(
            screen,
            [(x,y),(x+w,y),(x+w,y+h),(x,y+h)],
            base_color
        )

        # bordas
        line_bresenham(screen, x,   y,   x+w, y,   border)
        line_bresenham(screen, x,   y+h, x+w, y+h, border)
        line_bresenham(screen, x,   y,   x,   y+h, border)
        line_bresenham(screen, x+w, y,   x+w, y+h, border)

        # indicador
        state_txt   = "ON" if active else "OFF"
        state_color = (120, 255, 140) if active else (255, 120, 120)

        # bolinha estado
        circle_midpoint(screen, x + 18, y + 20, 6, state_color)
        flood_fill(screen, x + 18, y + 20, tuple(v // 2 for v in state_color))

        _txt(
            screen,
            f_sm,
            label,
            x + 34,
            y + 12,
            (225, 225, 245)
        )

        _txt(
            screen,
            f_sm,
            state_txt,
            x + w - 50,
            y + 12,
            state_color
        )

        # info
        if info:
            ix, iy = x + w + 10, y + 3

            scanline_fill(
                screen,
                [(ix,iy),(ix+24,iy),(ix+24,iy+24),(ix,iy+24)],
                (20, 20, 50)
            )

            line_bresenham(screen, ix, iy, ix+24, iy, (120,120,200))
            line_bresenham(screen, ix, iy+24, ix+24, iy+24, (120,120,200))
            line_bresenham(screen, ix, iy, ix, iy+24, (120,120,200))
            line_bresenham(screen, ix+24, iy, ix+24, iy+24, (120,120,200))

            _txt(
                screen,
                f_sm,
                "i",
                ix+12,
                iy+12,
                (200, 200, 255),
                center=True
            )

            if ix <= mx <= ix+24 and iy <= my <= iy+24:
                _txt(
                    screen,
                    f_sm,
                    info,
                    ix - 254,
                    iy + 50,
                    (180, 180, 220)
                )

        return (x, y, w, h)

    # ─────────────────────────────────────────────
    # TOGGLES
    # ─────────────────────────────────────────────

    base_y = py + 110
    gap    = 60

    settings_buttons.append((
        "adm_mode",
        draw_toggle(
            px + 40,
            base_y,
            "Modo ADM",
            "adm_mode",
            "Permite criar suas proprias fases"
        )
    ))

    # ─────────────────────────────────────────────
    # VOLUME
    # ─────────────────────────────────────────────

    vx, vy = px + pw//2 + 40, base_y + 10

    _txt(
        screen,
        f_md,
        "Volume",
        vx,
        vy - 36,
        (210, 190, 255)
    )

    bar_w, bar_h = 240, 12

    vol = settings["volume"]

    # fundo barra
    scanline_fill(
        screen,
        [(vx,vy),(vx+bar_w,vy),(vx+bar_w,vy+bar_h),(vx,vy+bar_h)],
        (36, 36, 70)
    )

    fill_w = int(bar_w * vol)

    # preenchimento
    if fill_w > 0:
        scanline_fill(
            screen,
            [(vx,vy),(vx+fill_w,vy),(vx+fill_w,vy+bar_h),(vx,vy+bar_h)],
            (130, 110, 255)
        )

    # bordas
    line_bresenham(screen, vx, vy, vx+bar_w, vy, (100,100,200))
    line_bresenham(screen, vx, vy+bar_h, vx+bar_w, vy+bar_h, (100,100,200))
    line_bresenham(screen, vx, vy, vx, vy+bar_h, (100,100,200))
    line_bresenham(screen, vx+bar_w, vy, vx+bar_w, vy+bar_h, (100,100,200))

    # knob
    knob_x = vx + fill_w

    circle_midpoint(
        screen,
        knob_x,
        vy + bar_h // 2,
        7,
        (220, 210, 255)
    )

    flood_fill(
        screen,
        knob_x,
        vy + bar_h // 2,
        (170, 150, 255)
    )

    _txt(
        screen,
        f_sm,
        f"{int(vol*100)}%",
        vx + bar_w + 14,
        vy - 2,
        (190, 190, 255)
    )

    volume_bar = (vx, vy, bar_w, bar_h)

    # rodapé
    _txt(
        screen,
        f_sm,
        "ESC = voltar",
        W // 2,
        py + ph - 20,
        (100, 100, 150),
        center=True
    )

    

    return settings_buttons, volume_bar

def draw_character_selector(screen, fonts, W, H, menu_art, game):

    import os

    f_xl, f_lg, f_md, f_sm = fonts

    screen.blit(menu_art, (0, 0))

    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((8, 12, 28, 230))
    screen.blit(overlay, (0, 0))

    # painel principal
    px, py, pw, ph = 70, 50, W - 140, H - 100

    scanline_fill(
        screen,
        [(px,py),(px+pw,py),(px+pw,py+ph),(px,py+ph)],
        (12, 15, 35)
    )

    bc = (130, 110, 220)

    line_bresenham(screen, px, py, px+pw, py, bc)
    line_bresenham(screen, px, py+ph, px+pw, py+ph, bc)
    line_bresenham(screen, px, py, px, py+ph, bc)
    line_bresenham(screen, px+pw, py, px+pw, py+ph, bc)

    # título
    _txt(
        screen,
        f_xl,
        "SELETOR DE PERSONAGEM",
        W // 2,
        py + 30,
        (240,240,255),
        center=True
    )

    line_bresenham(
        screen,
        px + 20,
        py + 70,
        px + pw - 20,
        py + 70,
        (50,45,90)
    )

    # grid de personagens
    char_buttons = []

    start_x = px + 40
    start_y = py + 110

    cols = 3

    btn_w = 220
    btn_h = 140

    gap_x = 28
    gap_y = 28

    current_character = game.selected_character

    for i, char in enumerate(game.unlocked_characters):

        row = i // cols
        col = i % cols

        bx = start_x + col * (btn_w + gap_x)
        by = start_y + row * (btn_h + gap_y)

        active = (char == current_character)

        base_col = (26, 28, 58)
        border   = (80, 80, 140)

        if active:
            base_col = (60, 40, 120)
            border   = (190, 150, 255)

        # hover
        mx, my = pygame.mouse.get_pos()

        hover = bx <= mx <= bx+btn_w and by <= my <= by+btn_h

        if hover:
            border = (230, 210, 255)

        # fundo
        scanline_fill(
            screen,
            [(bx,by),(bx+btn_w,by),(bx+btn_w,by+btn_h),(bx,by+btn_h)],
            base_col
        )

        selected_by_keyboard = (
            hasattr(game, "character_select_index")
            and game.character_select_index == i
        )

        if selected_by_keyboard:

            glow = (255, 240, 120)

            line_bresenham(
                screen,
                bx-2,
                by-2,
                bx+btn_w+2,
                by-2,
                glow
            )

            line_bresenham(
                screen,
                bx-2,
                by+btn_h+2,
                bx+btn_w+2,
                by+btn_h+2,
                glow
            )

            line_bresenham(
                screen,
                bx-2,
                by-2,
                bx-2,
                by+btn_h+2,
                glow
            )

            line_bresenham(
                screen,
                bx+btn_w+2,
                by-2,
                bx+btn_w+2,
                by+btn_h+2,
                glow
            )

        # ─────────────────────────────────────
        # PREVIEW DO SPRITE
        # ─────────────────────────────────────

        preview_x = bx + btn_w // 2
        preview_y = by + 52

        try:

            sprite_dir = f"sprites/{char.sprites_folder}"

            files = sorted([
                f for f in os.listdir(sprite_dir)
                if f.endswith(".png")
            ])

            if files:

                sprite_path = os.path.join(sprite_dir, files[0])

                sprite = pygame.image.load(sprite_path).convert_alpha()

                sprite = pygame.transform.scale(sprite, (64, 64))

                sprite_rect = sprite.get_rect(center=(preview_x, preview_y))

                # sombra
                shadow = sprite.copy()
                shadow.fill((0,0,0,120), special_flags=pygame.BLEND_RGBA_MULT)

                screen.blit(shadow, (sprite_rect.x + 3, sprite_rect.y + 3))

                screen.blit(sprite, sprite_rect)

            else:

                circle_midpoint(
                    screen,
                    preview_x,
                    preview_y,
                    24,
                    border
                )

        except:

            circle_midpoint(
                screen,
                preview_x,
                preview_y,
                24,
                border
            )

        # nome
        _txt(
            screen,
            f_md,
            char.name,
            bx + btn_w//2,
            by + 98,
            (235,235,255),
            center=True
        )

        # status
        if active:

            _txt(
                screen,
                f_sm,
                "EM USO",
                bx + btn_w//2,
                by + 118,
                (120,255,140),
                center=True,
                scale_size=1
            )

        else:

            _txt(
                screen,
                f_sm,
                "Clique para selecionar",
                bx + btn_w//2,
                by + 118,
                (170,170,220),
                center=True,
                scale_size=1
            )

        char_buttons.append(
            (bx, by, btn_w, btn_h, char)
        )

    

    # footer
    _txt(
        screen,
        f_sm,
        "ESC = voltar",
        W//2,
        py + ph - 22,
        (120,120,170),
        center=True
    )

    return char_buttons

def draw_shop(screen, fonts, W, H, menu_art, game):

    import os

    f_xl, f_lg, f_md, f_sm = fonts

    screen.blit(menu_art, (0, 0))

    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((8, 12, 28, 230))
    screen.blit(overlay, (0, 0))

    px, py, pw, ph = 70, 50, W - 140, H - 100

    # painel
    scanline_fill(
        screen,
        [(px,py),(px+pw,py),(px+pw,py+ph),(px,py+ph)],
        (12, 15, 35)
    )

    bc = (130, 110, 220)

    line_bresenham(screen, px, py, px+pw, py, bc)
    line_bresenham(screen, px, py+ph, px+pw, py+ph, bc)
    line_bresenham(screen, px, py, px, py+ph, bc)
    line_bresenham(screen, px+pw, py, px+pw, py+ph, bc)

    # título
    _txt(
        screen,
        f_xl,
        "LOJA DE PERSONAGENS",
        W // 2,
        py + 30,
        (240,240,255),
        center=True
    )


    coin_x = px + pw - 120
    coin_y = py + 40

    draw_coin(screen, coin_x, coin_y, 14)

    # dinheiro
    _txt(
        screen,
        f_md,
        f"{game.money}",
        coin_x + 28,
        coin_y - 10,
        (255, 220, 120)
    )
    line_bresenham(
        screen,
        px + 20,
        py + 70,
        px + pw - 20,
        py + 70,
        (50,45,90)
    )

    # chars da loja
    shop_buttons = []

    start_x = px + 40
    start_y = py + 110

    cols = 3

    btn_w = 220
    btn_h = 180

    gap_x = 28
    gap_y = 28

    # exemplo:
    # game.shop_characters = [
    #     (Character(...), 100),
    #     (Character(...), 250),
    # ]

    for i, (char, price) in enumerate(game.shop_characters):

        row = i // cols
        col = i % cols

        bx = start_x + col * (btn_w + gap_x)
        by = start_y + row * (btn_h + gap_y)

        owned = char in game.unlocked_characters

        selected_by_keyboard = (
            hasattr(game, "shop_select_index")
            and game.shop_select_index == i
        )

        base_col = (26, 28, 58)
        border   = (80, 80, 140)

        if owned:
            base_col = (40, 70, 40)
            border   = (120, 255, 140)

        # hover
        mx, my = pygame.mouse.get_pos()

        hover = bx <= mx <= bx+btn_w and by <= my <= by+btn_h

        if hover:
            border = (230, 210, 255)

        # fundo
        scanline_fill(
            screen,
            [(bx,by),(bx+btn_w,by),(bx+btn_w,by+btn_h),(bx,by+btn_h)],
            base_col
        )

        # glow teclado
        if selected_by_keyboard:

            glow = (255, 240, 120)

            line_bresenham(screen, bx-2, by-2, bx+btn_w+2, by-2, glow)
            line_bresenham(screen, bx-2, by+btn_h+2, bx+btn_w+2, by+btn_h+2, glow)
            line_bresenham(screen, bx-2, by-2, bx-2, by+btn_h+2, glow)
            line_bresenham(screen, bx+btn_w+2, by-2, bx+btn_w+2, by+btn_h+2, glow)

        # borda
        line_bresenham(screen, bx, by, bx+btn_w, by, border)
        line_bresenham(screen, bx, by+btn_h, bx+btn_w, by+btn_h, border)
        line_bresenham(screen, bx, by, bx, by+btn_h, border)
        line_bresenham(screen, bx+btn_w, by, bx+btn_w, by+btn_h, border)

        # sprite preview
        preview_x = bx + btn_w // 2
        preview_y = by + 52

        try:

            sprite_dir = f"sprites/{char.sprites_folder}"

            files = sorted([
                f for f in os.listdir(sprite_dir)
                if f.endswith(".png")
            ])

            if files:

                sprite_path = os.path.join(sprite_dir, files[0])

                sprite = pygame.image.load(sprite_path).convert_alpha()

                sprite = pygame.transform.scale(sprite, (64, 64))

                rect = sprite.get_rect(center=(preview_x, preview_y))

                screen.blit(sprite, rect)

        except:
            pass

        # nome
        _txt(
            screen,
            f_md,
            char.name,
            bx + btn_w//2,
            by + 98,
            (235,235,255),
            center=True
        )

        # preço
        if owned:

            status = "COMPRADO"
            color  = (120,255,140)

        else:

            status = f"{price} moedas"
            color  = (255,220,120)

        _txt(
            screen,
            f_sm,
            status,
            bx + btn_w//2,
            by + 125,
            color,
            center=True,
            scale_size=1
        )

        if not owned:

            _txt(
                screen,
                f_sm,
                "ENTER / Clique para comprar",
                bx + btn_w//2,
                by + 148,
                (180,180,220),
                center=True,
                scale_size=1
            )

        shop_buttons.append(
            (bx, by, btn_w, btn_h, char, price)
        )

    # footer
    _txt(
        screen,
        f_sm,
        "ESC = voltar",
        W//2,
        py + ph - 22,
        (120,120,170),
        center=True
    )

    return shop_buttons
import pygame

from src.funcs.cg_lib import (
    line_bresenham, scanline_fill, fill_rectangle
)
from src.utils.ui import _txt, _draw_btn
from src.music_backend.backend_config import DIFFICULTY_COLORS, DIFFICULTY_NAMES
from src.sprites import draw_char
from src.screens.lobby import LOBBY_STAGE_NAMES, LOBBY_STAGE_COLORS
from src.config import (
    W, H, LANE_W, LANE_COUNT, TARGET_Y, SPAWN_OFFSET,
    HUD_H, DIRECTIONS, LANE_COLORS, LANE_DIM, NOTE_SIZE, WIN_OK
)


def update_playing(game, dt: float) -> str | None:
    mt = game.music_time()

    for n in game.notes:
        if n.active and not n.hit and not n.missed:
            if mt > n.beat_time + WIN_OK:
                n.missed    = True
                n.active    = False
                game.combo  = 0
                game.misses += 1
                game.fb_text  = 'MISS'
                game.fb_timer = 0.38
                game.fb_color = (255, 55, 55)
                game.char_anim  = 'game_miss'
                game.char_timer = 0.38

    game.fb_timer   = max(0.0, game.fb_timer   - dt)
    game.char_timer = max(0.0, game.char_timer - dt)
    if game.char_timer <= 0:
        game.char_anim = 'game_idle'
    for d in DIRECTIONS:
        game.lane_flash[d] = max(0.0, game.lane_flash[d] - dt)

    if not pygame.mixer.music.get_busy():
        return 'results'

    game.char_frame_t += dt
    frames = game.sprites.get(game.char_anim, [None])
    if game.char_frame_t >= game.char_frame_spd.get(game.char_anim, 0.12):
        game.char_frame_t = 0.0
        game.char_frame   = (game.char_frame + 1) % max(1, len(frames))

    return None


def draw_playing(screen, fonts, game) -> None:
    f_xl, f_lg, f_md, f_sm = fonts

    screen.blit(game.bg_surf, (0, 0))

    if 0 <= game.stage_idx < len(LOBBY_STAGE_COLORS):
        theme   = LOBBY_STAGE_COLORS[game.stage_idx]
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((theme[0], theme[1], theme[2], 24))
        screen.blit(overlay, (0, 0))

    intensity = game._current_intensity()
    if intensity > 0.30:
        t     = min(1.0, (intensity - 0.30) / 0.70)
        r     = int(40  + 180 * t)
        g     = int(10  +  20 * (1 - t))
        b     = int(80  -  60 * t)
        alpha = int(18  +  55 * t)
        lane_w_total = LANE_W * LANE_COUNT
        ov = pygame.Surface((lane_w_total, H - HUD_H), pygame.SRCALPHA)
        ov.fill((r, g, b, alpha))
        screen.blit(ov, (game.lane_left, HUD_H))

    # Barra de intensidade
    ib_x  = game.lane_left - 22
    ib_y0 = HUD_H + 10
    ib_h  = H - HUD_H - 20
    ib_w  = 10
    scanline_fill(screen,
        [(ib_x, ib_y0), (ib_x+ib_w, ib_y0),
         (ib_x+ib_w, ib_y0+ib_h), (ib_x, ib_y0+ib_h)],
        (18, 18, 40))
    fill_h = int(ib_h * intensity)
    if fill_h > 2:
        fy0 = ib_y0 + ib_h - fill_h
        t2  = intensity
        rc  = int(30 + 210 * t2)
        gc  = int(200 - 160 * t2)
        bc  = int(80  -  60 * t2)
        scanline_fill(screen,
            [(ib_x, fy0), (ib_x+ib_w, fy0),
             (ib_x+ib_w, ib_y0+ib_h), (ib_x, ib_y0+ib_h)],
            (rc, gc, bc))
    line_bresenham(screen, ib_x,      ib_y0,      ib_x+ib_w, ib_y0,      (60, 60, 120))
    line_bresenham(screen, ib_x,      ib_y0+ib_h, ib_x+ib_w, ib_y0+ib_h, (60, 60, 120))
    line_bresenham(screen, ib_x,      ib_y0,      ib_x,      ib_y0+ib_h, (60, 60, 120))
    line_bresenham(screen, ib_x+ib_w, ib_y0,      ib_x+ib_w, ib_y0+ib_h, (60, 60, 120))
    _txt(screen, f_sm, 'INT', ib_x - 1, ib_y0 - 16, (90, 90, 160))

    # Receptores e flash
    for i, d in enumerate(DIRECTIONS):
        rs = game.recv_surfs[d]
        rx = game.lane_xs[i] - rs.get_width()  // 2
        ry = TARGET_Y        - rs.get_height() // 2
        screen.blit(rs, (rx, ry))

        fl = game.lane_flash[d]
        if fl > 0:
            alpha = int(min(255, fl / 0.22 * 210))
            fs = game._flash_surfs[d]
            fs.set_alpha(alpha)
            screen.blit(fs, (game.lane_left + i * LANE_W,
                             TARGET_Y - fs.get_height() // 2))
            ns = game.note_surfs[d]
            screen.blit(ns, (game.lane_xs[i] - ns.get_width()  // 2,
                             TARGET_Y         - ns.get_height() // 2))

    # Notas
    mt  = game.music_time()
    top = TARGET_Y - SPAWN_OFFSET - 60
    bot = H + 60
    for note in game.notes:
        if not note.active:
            continue
        y = note.y_pos(mt)
        if y < top or y > bot:
            continue
        ns = game.note_surfs[note.direction]
        screen.blit(ns, (note.lane_x - ns.get_width()  // 2,
                         int(y)       - ns.get_height() // 2))

    # HUD
    _txt(screen, f_lg, f'SCORE  {game.score:07d}', 16, 12, (220, 220, 255))
    _txt(screen, f_md, f'COMBO  {game.combo}×',    16, 48, (160, 160, 255))
    stage_name = LOBBY_STAGE_NAMES[game.stage_idx] if 0 <= game.stage_idx < len(LOBBY_STAGE_NAMES) else 'Fase'
    _txt(screen, f_sm, f'FASE  {stage_name}',      16, 78, (180, 180, 255))

    intensity = game._current_intensity()
    if   intensity < 0.35: mood, mc = 'calmo',    (100, 180, 255)
    elif intensity < 0.65: mood, mc = 'animado',   (130, 255, 130)
    else:                  mood, mc = 'INTENSO!',  (255, 110,  60)
    _txt(screen, f_sm, f'{game.bpm:.0f} BPM  |  {mood}', W - 220, 12, mc)

    # Barra de progresso
    mt2 = game.music_time()
    if game.duration > 0:
        prog = min(1.0, mt2 / game.duration)
        bx, by, bw, bh = W - 310, 24, 288, 12
        scanline_fill(screen, [(bx,by),(bx+bw,by),(bx+bw,by+bh),(bx,by+bh)], (26, 26, 56))
        fw = int(bw * prog)
        if fw > 1:
            scanline_fill(screen, [(bx,by),(bx+fw,by),(bx+fw,by+bh),(bx,by+bh)], (85, 85, 205))
        line_bresenham(screen, bx,    by,    bx+bw, by,    (65, 65, 155))
        line_bresenham(screen, bx,    by+bh, bx+bw, by+bh, (65, 65, 155))

        rem  = max(0.0, game.duration - mt2)
        mins = int(rem) // 60
        secs = int(rem) % 60
        _txt(screen, f_sm, f'{mins}:{secs:02d}', W - 47, 42, (130, 130, 190))

    # Feedback
    if game.fb_timer > 0:
        alpha   = min(1.0, game.fb_timer / 0.22)
        fc      = tuple(int(v * alpha) for v in game.fb_color)
        lane_cx = game.lane_left + (LANE_W * LANE_COUNT) // 2
        _txt(screen, f_lg, game.fb_text, lane_cx, TARGET_Y - 95, fc, center=True)

    draw_char(screen, game.sprites, game.char_anim, game.char_cx, game.char_cy, game.char_frame)

    hint = '  ←  ↓  ↑  →      ESC: menu'
    _txt(screen, f_sm, hint, game.lane_left, H - 22, (70, 70, 110))


def draw_results(screen, fonts, game) -> None:
    f_xl, f_lg, f_md, f_sm = fonts

    screen.blit(game.bg_surf, (0, 0))

    total = game.perfects + game.goods + game.oks + game.misses
    acc   = (game.perfects + game.goods * 0.67 + game.oks * 0.33) / max(1, total)

    if   acc >= 0.95: grade, gc = 'S', (255, 215,   0)
    elif acc >= 0.85: grade, gc = 'A', (180, 255, 100)
    elif acc >= 0.70: grade, gc = 'B', (100, 200, 255)
    elif acc >= 0.50: grade, gc = 'C', (200, 200, 255)
    else:             grade, gc = 'D', (255, 100, 100)

    px, py, pw, ph = 80, 65, W - 160, H - 130
    scanline_fill(screen, [(px,py),(px+pw,py),(px+pw,py+ph),(px,py+ph)], (10, 10, 28))
    bc = (78, 55, 178)
    line_bresenham(screen, px,    py,    px+pw, py,    bc)
    line_bresenham(screen, px,    py+ph, px+pw, py+ph, bc)
    line_bresenham(screen, px,    py,    px,    py+ph, bc)
    line_bresenham(screen, px+pw, py,    px+pw, py+ph, bc)

    dc = DIFFICULTY_COLORS[game.difficulty]
    _txt(screen, f_lg, f'── RESULTADO  [{game.difficulty}] ──', W // 2, py + 20, dc, center=True)

    rows = [
        (f'PONTUAÇÃO    {game.score:07d}',  (220, 220, 255)),
        (f'COMBO MÁX    {game.max_combo}×', (180, 180, 255)),
        ('',                                 None),
        (f'PERFEITOS    {game.perfects}',   (255, 235,  55)),
        (f'BONS         {game.goods}',       ( 55, 235,  55)),
        (f'OKs          {game.oks}',         ( 55, 180, 255)),
        (f'ERROS        {game.misses}',      (255,  65,  65)),
        ('',                                 None),
        (f'ACURÁCIA     {acc * 100:.1f}%',  (200, 200, 255)),
    ]
    for i, (t, c) in enumerate(rows):
        if c:
            _txt(screen, f_md, t, px + 70, py + 60 + i * 38, c)

    _txt(screen, f_xl, grade, px + pw - 95, py + ph // 2 - 35, gc)

    n_diff   = len(DIFFICULTY_NAMES)
    btn_w    = 140
    gap      = 10
    total_bw = n_diff * btn_w + (n_diff - 1) * gap
    start_x  = (W - total_bw) // 2
    ry       = py + ph - 72

    _txt(screen, f_sm, 'Jogar novamente em:', W // 2, ry - 14, (120, 120, 180), center=True)

    res_diff_btns = []
    for i, name in enumerate(DIFFICULTY_NAMES):
        bx2 = start_x + i * (btn_w + gap)
        col = DIFFICULTY_COLORS[name]
        _draw_btn(screen, bx2, ry, btn_w, 36, name, f_sm,
                  active=(name == game.difficulty), color=col)
        res_diff_btns.append((bx2, ry, btn_w, 36, name))

    _txt(screen, f_sm,
         '←/→ ou A/D muda dificuldade   ENTER: repetir mesmo nível   ESC: menu   Q: sair',
         W // 2, py + ph - 22, (110, 110, 175), center=True)

    return res_diff_btns
import pygame
import os
import sys
import math
import random
import json

LOBBY_STAGE_NAMES = [
    'Refazer', 'Entender', 'Reconstruir', 'Lembrar', 'Personalizada'
]

LOBBY_STAGE_COLORS = [
    (95, 170, 95),
    (95, 155, 205),
    (220, 165, 90),
    (200, 95, 175),
    (255, 200, 110),
]

_GRASS_COLORS = [
    (52,  110, 52),
    (60,  124, 55),
    (72,  138, 60),
    (80,  148, 65),
]
_PATH_COLORS = [
    (148, 118, 82),
    (160, 130, 90),
    (138, 108, 72),
]
_FLOWER_COLORS = [
    (255, 80,  120),
    (255, 220, 60),
    (200, 120, 255),
    (255, 160, 60),
    (255, 255, 255),
]
_BUSH_COLORS = [
    (38,  90,  38),
    (48, 105,  45),
    (55, 120,  50),
]

LOBBY_WORLD_XMIN = -800
LOBBY_WORLD_YMIN = -600
LOBBY_WORLD_XMAX = 800
LOBBY_WORLD_YMAX = 600
LOBBY_GRID_SPACING = 100
LOBBY_VIEW_W = 620
LOBBY_VIEW_H = 420

LOBBY_STAGE_POS = [
    (-500, 350),  # Refazer (Superior Esquerda)
    (500, 350),   # Entender (Superior Direita)
    (-500, -350), # Reconstruir (Inferior Esquerda)
    (500, -350),  # Lembrar (Inferior Direita)
    (0, 0),       # Personalizada (Centro)
]

LOBBY_ENTRY_RADIUS = 64

from src.config import (
    W, H, LANE_W, LANE_COUNT, TARGET_Y, SPAWN_OFFSET, FALL_TIME,
    CHAR_SIZE, CHAR_SIZE_LOBBY, DIRECTIONS, LANE_COLORS, LANE_DIM, NOTE_SIZE, WIN_GOOD, WIN_OK, WIN_PERFECT, HUD_H, KEY_MAP
)
from src.music_backend.note import Note
from src.music_backend.difficulty import apply_difficulty
from src.music_backend.utils import (
    detect_beats,
    load_beatmap
)

from src.utils.render import (
    bake_static_bg, bake_arrow_surf
)

from src.sprites import draw_char, load_sprites

from src.music_backend.backend_config import (
    DIFFICULTY_COLORS, DIFFICULTY_NAMES, STAGE_MUSIC_PATHS
)

from src.funcs.cg_lib import (
    Window, Viewport, boundary_fill, circle_midpoint, cohen_sutherland_clip,
    draw_line_clipped, draw_line_viewport, draw_polygon, draw_polygon_viewport,
    ellipse_midpoint, flood_fill, line_bresenham, scanline_fill, set_pixel, draw_rectangle, fill_rectangle
)

from src.utils.render import bake_static_bg, bake_arrow_surf, DIRECTION_ANGLES

# Funções de desenho pixel a pixel para detalhes como grama, caminhos, flores e arbustos.
def _px(surf, x, y, color):
    w, h = surf.get_size()
    if 0 <= x < w and 0 <= y < h:
        surf.set_at((x, y), color)

def _fill_rect(surf, x, y, w, h, color):
    fill_rectangle(surf, x, y, w, h, color)

def _pixel_grass(surf, x, y, w, h, rng):
    tile = 4
    for ty in range(y, y + h, tile):
        for tx in range(x, x + w, tile):
            base = rng.choice(_GRASS_COLORS)
            tw = min(tile, x + w - tx)
            th = min(tile, y + h - ty)
            _fill_rect(surf, tx, ty, tw, th, base)
            if rng.random() < 0.35:
                bright = tuple(min(255, c + 22) for c in base)
                _px(surf, tx, ty, bright)

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

def _draw_flower(surf, cx, cy, color, rng):
    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
        _px(surf, cx + dx, cy + dy, color)
    center_c = (255, 240, 80) if color != (255, 220, 60) else (255, 120, 40)
    _px(surf, cx, cy, center_c)
    stem = (48, 100, 40)
    _px(surf, cx, cy + 1, stem)
    _px(surf, cx, cy + 2, stem)

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

class RhythmGame:

    def __init__(self):
        pygame.init()
        pygame.mixer.init(44100, -16, 2, 512)

        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Re:Song")
        self.clock  = pygame.time.Clock()

        self.f_xl = pygame.font.SysFont('monospace', 42, bold=True)
        self.f_lg = pygame.font.SysFont('monospace', 28, bold=True)
        self.f_md = pygame.font.SysFont('monospace', 20)
        self.f_sm = pygame.font.SysFont('monospace', 15)

        total_lane_w   = LANE_W * LANE_COUNT
        self.lane_left = (W - total_lane_w) // 2 - 85
        self.lane_xs   = [self.lane_left + i * LANE_W + LANE_W // 2
                          for i in range(LANE_COUNT)]

        self.char_cx = self.lane_left + total_lane_w + 150
        self.char_cy = TARGET_Y - 20

        self.bg_surf   = bake_static_bg(self.lane_left)
        self.note_surfs = {}
        self.recv_surfs = {}
        for d in DIRECTIONS:
            c   = LANE_COLORS[d]
            cd  = LANE_DIM[d]
            brt = tuple(min(255, v + 68) for v in c)
            brd = tuple(min(255, v + 28) for v in cd)
            self.note_surfs[d] = bake_arrow_surf(d, c,  brt, NOTE_SIZE)
            self.recv_surfs[d] = bake_arrow_surf(d, cd, brd, NOTE_SIZE)

        fw = LANE_W
        fh = NOTE_SIZE * 2 + 16
        self._flash_surfs = {}
        for d in DIRECTIONS:
            fs = pygame.Surface((fw, fh))
            fs.fill(LANE_COLORS[d])
            self._flash_surfs[d] = fs

        self.sprites = load_sprites('sprites', size=CHAR_SIZE)
        self.sprites_lobby = load_sprites('sprites', size=CHAR_SIZE_LOBBY)

        self.menu_bg_image = self._load_menu_bg_image()
        self.menu_art = self._build_menu_art()
        self._lobby_bg_surf = self._build_lobby_background()
        self.menu_page = 'main'
        self._menu_buttons = []
        self._lobby_buttons = []
        self._settings_buttons = []
        self._exit_requested = False

        self.state          = 'menu'
        self.menu_selection = 0
        self.music_path     = None
        self.input_text     = sys.argv[1] if len(sys.argv) > 1 else ''
        self.menu_error     = ''
        self.difficulty     = 'Normal'
        self.stage_idx      = 0
        self.selected_stage = None
        self._raw_events = []

        self.lobby_px   = 0.0
        self.lobby_py   = 0.0
        self.lobby_speed= 180.0
        self.lobby_anim_t = 0.0
        self.lobby_entered_stage = None
        self.lobby_stage_selected = None
        self.lobby_last_move = 'idle'

        self.notes:     list[Note] = []
        self.score      = 0
        self.combo      = 0
        self.max_combo  = 0
        self.perfects   = self.goods = self.oks = self.misses = 0
        self.duration   = 0.0
        self.bpm        = 120.0

        self.fb_text    = ''
        self.fb_timer   = 0.0
        self.fb_color   = (255, 255, 255)

        self.char_anim  = 'game_idle'
        self.char_timer = 0.0
        self.char_frame     = 0
        self.char_frame_t   = 0.0
        self.char_frame_spd = {
            'idle':  0.12,
            'left':  0.12,
            'right': 0.30,
            'up':    0.12,
            'down':  0.12,
        }
        self.lane_flash = {d: 0.0 for d in DIRECTIONS}

        self.intensity_map: list = []
        self._intensity_surf = pygame.Surface((W, H), pygame.SRCALPHA)

        self.menu_alpha = 0.0
        self.fade_speed = 0.5 

        self.music_delay_timer = 2.0
        self.music_started = False

        try:
            path_opening = "musics/openingmenu.mp3"
            pygame.mixer.music.load(path_opening)
            pygame.mixer.music.set_volume(0.4)
        except pygame.error:
            print(f"Erro ao carregar música de abertura: {path_opening}")

        self.menu_timer = 0.0
        self.fade_speed = 0.7

        # Alphas: [0: Fundo, 1: Título, 2: Frase, 3: Botão JOGAR, 4: TUTORIAL, 5: SAIR, 6: Rodapé]
        self.alphas = [0.0] * 7

        # Delays (em segundos) - eles vão aparecendo em escadinha
        self.delays = [0.0, 2, 2.4, 2.8, 3.2, 3.6, 4.0]

        self.settings = {
                "adm_mode": False,
                "show_fps": False,
                "auto_play": False,
                "volume": 0.5
            }


    def music_time(self) -> float:
        pos = pygame.mixer.music.get_pos()
        return pos / 1000.0 if pos >= 0 else self.duration + 10.0


    def load_song(self, path: str, reuse_raw: bool = False, stage_idx: int = 0, pre_defined: bool = False) -> None:
        self.stage_idx = stage_idx if stage_idx is not None else 0
        d2x = {d: self.lane_xs[i] for i, d in enumerate(DIRECTIONS)}

        if pre_defined==False:

            duration = self.duration
            if not reuse_raw or not self._raw_events:
                self.screen.blit(self.bg_surf, (0, 0))
                diff_c = DIFFICULTY_COLORS[self.difficulty]
                self._txt(self.f_lg, '♪  Analisando batidas…  ♪', W // 2, H // 2 - 24,
                        (185, 145, 255), center=True)
                self._txt(self.f_md, f'Dificuldade: {self.difficulty}', W // 2, H // 2 + 18,
                        diff_c, center=True)
                pygame.display.flip()

                try:
                    raw_events, bpm, duration = detect_beats(path)
                except Exception as e:
                    self.menu_error = f'Erro ao analisar: {str(e)[:60]}'
                    return

                self._raw_events = raw_events
                self.duration    = duration
                self.bpm         = bpm
                self.music_path  = path
            else:
                raw_events = self._raw_events

        else:
            try:
                raw_events, bpm, duration = load_beatmap(path)
            except Exception as e:
                self.menu_error = f'Erro ao analisar: {str(e)[:60]}'
                return

            self._raw_events = raw_events
            self.duration    = duration
            self.bpm         = bpm
            self.music_path  = path



        notes_raw = apply_difficulty(raw_events, self.duration, self.difficulty)

        self.notes = [Note(t, d, d2x[d]) for t, d in notes_raw]

        self.score = self.combo = self.max_combo = 0
        self.perfects = self.goods = self.oks = self.misses = 0
        self.fb_text = ''
        self.char_anim  = 'idle'
        self.char_timer = 0.0
        self.lane_flash = {d: 0.0 for d in DIRECTIONS}


        window = 3.0
        step   = 0.25
        t_max  = duration
        self.intensity_map = []
        if t_max > 0:
            t = 0.0
            while t < t_max:
                count = sum(1 for n in self.notes
                            if abs(n.beat_time - t) < window / 2)
                self.intensity_map.append((t, count))
                t += step
            # Normaliza
            peak = max((e for _, e in self.intensity_map), default=1)
            if peak > 0:
                self.intensity_map = [(t, e / peak) for t, e in self.intensity_map]

        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        self.state = 'playing'

    
    def load_song_recording_mode(self, path: str, stage_idx: int = 0) -> None:
        self.stage_idx = stage_idx if stage_idx is not None else 0

        # Estado base
        self._raw_events = []
        self.recorded_events = []  # <- NOVO: onde vamos salvar

        self.duration = 0.0
        self.bpm = 0.0
        self.music_path = path

        # UI inicial
        self.screen.blit(self.bg_surf, (0, 0))
        self._txt(self.f_lg, '● MODO GRAVAÇÃO ●', W // 2, H // 2 - 24,
                (255, 120, 120), center=True)
        self._txt(self.f_md, 'Pressione as teclas no ritmo!', W // 2, H // 2 + 18,
                (200, 200, 200), center=True)
        pygame.display.flip()

        # Carrega duração
        try:
            snd = pygame.mixer.Sound(path)
            self.duration = snd.get_length()
            del snd
        except Exception:
            self.duration = 240.0  # fallback

        # Zera estado do jogo
        self.notes = []
        self.score = self.combo = self.max_combo = 0
        self.perfects = self.goods = self.oks = self.misses = 0
        self.fb_text = ''

        self.char_anim  = 'idle'
        self.char_timer = 0.0
        self.lane_flash = {d: 0.0 for d in DIRECTIONS}

        # Controle de tempo
        self.recording_start_time = None
        self.is_recording = True

        # Toca música
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()

        self.state = 'recording'


    def _current_intensity(self) -> float:
        mt = self.music_time()
        if not self.intensity_map:
            return 0.0
        for i in range(len(self.intensity_map) - 1):
            t0, e0 = self.intensity_map[i]
            t1, e1 = self.intensity_map[i + 1]
            if t0 <= mt <= t1:
                alpha = (mt - t0) / (t1 - t0) if t1 > t0 else 0.0
                return e0 + alpha * (e1 - e0)
        return self.intensity_map[-1][1]


    def press_key(self, direction: str) -> None:
        mt       = self.music_time()
        best     = None
        best_dt  = 999.0

        for n in self.notes:
            if n.direction != direction or not n.active or n.hit:
                continue
            dt = abs(mt - n.beat_time)
            if dt < best_dt:
                best, best_dt = n, dt

        if best is None or best_dt > WIN_OK:
            return

        best.hit    = True
        best.active = False

        if best_dt <= WIN_PERFECT:
            grade, pts, col = 'PERFECT!', 300, (255, 238, 60)
            self.perfects += 1
        elif best_dt <= WIN_GOOD:
            grade, pts, col = 'GOOD',    150, ( 60, 235, 60)
            self.goods   += 1
        else:
            grade, pts, col = 'OK',       55, ( 60, 180, 255)
            self.oks     += 1

        self.combo    += 1
        self.max_combo = max(self.max_combo, self.combo)
        bonus          = 1 + self.combo // 10
        self.score    += pts * bonus

        self.fb_text   = grade
        self.fb_timer  = 0.55
        self.fb_color  = col

        self.char_anim  = f'game_{direction}'
        self.char_timer = 0.30
        self.lane_flash[direction] = 0.22

    def update(self, dt: float) -> None:
        mt = self.music_time()

        for n in self.notes:
            if n.active and not n.hit and not n.missed:
                if mt > n.beat_time + WIN_OK:
                    n.missed   = True
                    n.active   = False
                    self.combo = 0
                    self.misses += 1
                    self.fb_text  = 'MISS'
                    self.fb_timer = 0.38
                    self.fb_color = (255, 55, 55)
                    self.char_anim  = 'game_miss'
                    self.char_timer = 0.38

        self.fb_timer   = max(0.0, self.fb_timer   - dt)
        self.char_timer = max(0.0, self.char_timer - dt)
        if self.char_timer <= 0:
            self.char_anim = 'game_idle'
        for d in DIRECTIONS:
            self.lane_flash[d] = max(0.0, self.lane_flash[d] - dt)

        if not pygame.mixer.music.get_busy():
            self.state = 'results'

        self.char_frame_t += dt
        frames = self.sprites.get(self.char_anim, [None])
        if self.char_frame_t >= self.char_frame_spd.get(self.char_anim, 0.12):
            self.char_frame_t = 0.0
            self.char_frame = (self.char_frame + 1) % max(1, len(frames))

    def _txt(self, font, text, x, y, color=(255,255,255), center=False):
        """Renderiza texto com a fonte pygame e blit (como Button da lib)."""
        surf = font.render(text, True, color)
        if center:
            x -= surf.get_width()  // 2
            y -= surf.get_height() // 2
        self.screen.blit(surf, (x, y))

    def _default_stage_music_path(self) -> str:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'musics', 'music.mp3'))

    def _draw_playing(self) -> None:
        scr = self.screen

        scr.blit(self.bg_surf, (0, 0))

        if 0 <= self.stage_idx < len(LOBBY_STAGE_COLORS):
            theme = LOBBY_STAGE_COLORS[self.stage_idx]
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((theme[0], theme[1], theme[2], 24))
            scr.blit(overlay, (0, 0))

        intensity = self._current_intensity()
        if intensity > 0.30:
            t    = min(1.0, (intensity - 0.30) / 0.70)
            r    = int(40  + 180 * t)
            g    = int(10  +  20 * (1 - t))
            b    = int(80  -  60 * t)
            alpha = int(18 +  55 * t)
            lane_w_total = LANE_W * LANE_COUNT
            ov = pygame.Surface((lane_w_total, H - HUD_H), pygame.SRCALPHA)
            ov.fill((r, g, b, alpha))
            scr.blit(ov, (self.lane_left, HUD_H))

        intensity = self._current_intensity()
        ib_x  = self.lane_left - 22
        ib_y0 = HUD_H + 10
        ib_h  = H - HUD_H - 20
        ib_w  = 10
        scanline_fill(scr,
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
            scanline_fill(scr,
                [(ib_x, fy0), (ib_x+ib_w, fy0),
                 (ib_x+ib_w, ib_y0+ib_h), (ib_x, ib_y0+ib_h)],
                (rc, gc, bc))
        line_bresenham(scr, ib_x, ib_y0, ib_x+ib_w, ib_y0, (60,60,120))
        line_bresenham(scr, ib_x, ib_y0+ib_h, ib_x+ib_w, ib_y0+ib_h, (60,60,120))
        line_bresenham(scr, ib_x, ib_y0, ib_x, ib_y0+ib_h, (60,60,120))
        line_bresenham(scr, ib_x+ib_w, ib_y0, ib_x+ib_w, ib_y0+ib_h, (60,60,120))
        self._txt(self.f_sm, 'INT', ib_x - 1, ib_y0 - 16, (90, 90, 160))

        for i, d in enumerate(DIRECTIONS):
            rs = self.recv_surfs[d]
            rx = self.lane_xs[i] - rs.get_width()  // 2
            ry = TARGET_Y        - rs.get_height() // 2
            scr.blit(rs, (rx, ry))

            fl = self.lane_flash[d]
            if fl > 0:
                alpha = int(min(255, fl / 0.22 * 210))
                fs = self._flash_surfs[d]
                fs.set_alpha(alpha)
                scr.blit(fs, (self.lane_left + i * LANE_W,
                              TARGET_Y - fs.get_height() // 2))
                ns = self.note_surfs[d]
                scr.blit(ns, (self.lane_xs[i] - ns.get_width()  // 2,
                              TARGET_Y        - ns.get_height() // 2))

        mt  = self.music_time()
        top = TARGET_Y - SPAWN_OFFSET - 60
        bot = H + 60
        for note in self.notes:
            if not note.active:
                continue
            y = note.y_pos(mt)
            if y < top or y > bot:
                continue
            ns = self.note_surfs[note.direction]
            scr.blit(ns, (note.lane_x - ns.get_width()  // 2,
                          int(y)       - ns.get_height() // 2))

        self._txt(self.f_lg, f'SCORE  {self.score:07d}', 16, 12, (220, 220, 255))
        self._txt(self.f_md, f'COMBO  {self.combo}×',    16, 48, (160, 160, 255))
        stage_name = LOBBY_STAGE_NAMES[self.stage_idx] if 0 <= self.stage_idx < len(LOBBY_STAGE_NAMES) else 'Fase'
        self._txt(self.f_sm, f'FASE  {stage_name}',      16, 78, (180, 180, 255))

        intensity = self._current_intensity()
        if   intensity < 0.35: mood, mc = 'calmo',   (100, 180, 255)
        elif intensity < 0.65: mood, mc = 'animado',  (130, 255, 130)
        else:                  mood, mc = 'INTENSO!', (255, 110,  60)
        self._txt(self.f_sm, f'{self.bpm:.0f} BPM  |  {mood}',
                  W - 220, 12, mc)

        mt2 = self.music_time()
        if self.duration > 0:
            prog = min(1.0, mt2 / self.duration)
            bx, by, bw, bh = W - 310, 24, 288, 12
            scanline_fill(scr, [(bx,by),(bx+bw,by),(bx+bw,by+bh),(bx,by+bh)],
                          (26, 26, 56))
            fw = int(bw * prog)
            if fw > 1:
                scanline_fill(scr, [(bx,by),(bx+fw,by),(bx+fw,by+bh),(bx,by+bh)],
                              (85, 85, 205))
            line_bresenham(scr, bx,    by,    bx+bw, by,    (65, 65, 155))
            line_bresenham(scr, bx,    by+bh, bx+bw, by+bh, (65, 65, 155))

            rem  = max(0.0, self.duration - mt2)
            mins = int(rem) // 60
            secs = int(rem) % 60
            self._txt(self.f_sm, f'{mins}:{secs:02d}', W - 47, 42, (130, 130, 190))

        if self.fb_timer > 0:
            alpha = min(1.0, self.fb_timer / 0.22)
            fc    = tuple(int(v * alpha) for v in self.fb_color)
            lane_cx = self.lane_left + (LANE_W * LANE_COUNT) // 2
            self._txt(self.f_lg, self.fb_text, lane_cx, TARGET_Y - 95, fc, center=True)

        draw_char(scr, self.sprites, self.char_anim, self.char_cx, self.char_cy, self.char_frame)

        hint = '  ←  ↓  ↑  →      ESC: menu'
        self._txt(self.f_sm, hint, self.lane_left, H - 22, (70, 70, 110))


    def _load_menu_bg_image(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        screens_dir = os.path.join(base_dir, 'screens')
        if not os.path.isdir(screens_dir):
            return None

        candidates = [
            os.path.join(screens_dir, fn)
            for fn in sorted(os.listdir(screens_dir))
            if fn.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp'))
        ]
        for img_path in candidates:
            try:
                return pygame.image.load(img_path).convert()
            except Exception:
                continue
        return None


    def _draw_background_from_image(self, surf, image):
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


    def _build_menu_art(self):
        surf = pygame.Surface((W, H))
        surf.fill((12, 14, 36))

        if self.menu_bg_image:
            self._draw_background_from_image(surf, self.menu_bg_image)


        return surf


    def _draw_btn(self, scr, bx, by, bw, bh, label, font,
                  active=False, color=(115,75,250)):
        bg  = tuple(min(255, c // 2 + (30 if active else 0)) for c in color)
        brd = color if active else tuple(c // 2 for c in color)
        scanline_fill(scr, [(bx,by),(bx+bw,by),(bx+bw,by+bh),(bx,by+bh)], bg)
        for off in range(2 if active else 1):
            o = off
            line_bresenham(scr, bx+o,    by+o,    bx+bw-o, by+o,    brd)
            line_bresenham(scr, bx+bw-o, by+o,    bx+bw-o, by+bh-o, brd)
            line_bresenham(scr, bx+bw-o, by+bh-o, bx+o,    by+bh-o, brd)
            line_bresenham(scr, bx+o,    by+bh-o, bx+o,    by+o,    brd)
        tc = (255, 255, 255) if active else (180, 180, 210)
        self._txt(font, label, bx + bw // 2, by + bh // 2, tc, center=True)

    def _draw_menu(self) -> None:
        scr = self.screen
        scr.blit(self.menu_art, (0, 0))

        a1 = self.alphas[1]
        self._txt(self.f_xl, 'Re:Song', W // 2, 52, (int(245*a1), int(245*a1), int(245*a1)), center=True)
        a2 = self.alphas[2]
        self._txt(self.f_md, 'E mesmo quando tudo der errado, você ainda pode recomeçar do zero',
                  W // 2, 100, (int(225*a2), int(225*a2), int(235*a2)), center=True)

        btn_w, btn_h, gap = 220, 54, 20
        start_x = W // 2 - btn_w // 2
        start_y = 160
        menu_buttons = [
            ('JOGAR', start_x, start_y, btn_w, btn_h, 'play', (95, 180, 255)),
            ('CONFIGURAÇÕES', start_x, start_y + btn_h + gap, btn_w, btn_h, 'settings', (120, 200, 120)),
            ('TUTORIAL', start_x, start_y + 2 * (btn_h + gap), btn_w, btn_h, 'tutorial', (155, 115, 235)),
            ('SAIR', start_x, start_y + 3 * (btn_h + gap), btn_w, btn_h, 'exit', (235, 90, 110)),
        ]

        self._menu_buttons = []
        for i, (label, bx, by, bw, bh, action, color) in enumerate(menu_buttons):
            a_btn = self.alphas[i + 3]
            btn_color = (int(color[0] * a_btn), int(color[1] * a_btn), int(color[2] * a_btn))

            self._draw_btn(scr, bx, by, bw, bh, label, self.f_md,
                           active=(i == self.menu_selection), color=btn_color)
            self._menu_buttons.append((bx, by, bw, bh, action))

        if self.menu_error:
            self._txt(self.f_sm, self.menu_error, W // 2, H - 140, (255, 90, 90), center=True)

        a6 = self.alphas[6]
        footer_color = (int(185*a6), int(185*a6), int(210*a6))
        self._txt(self.f_sm, 'ESC = sair   |   JOGAR leva ao lobby de fases',
                  W // 2, H - 24, footer_color, center=True)

    def _world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        return (int(W // 2 + (wx - self.lobby_px)), int(H // 2 - (wy - self.lobby_py)))

    def _clamp_lobby_player(self) -> None:
        lim = 320
        self.lobby_px = max(LOBBY_WORLD_XMIN + 20, min(LOBBY_WORLD_XMAX - 20, self.lobby_px))
        self.lobby_py = max(LOBBY_WORLD_YMIN + 20, min(LOBBY_WORLD_YMAX - 20, self.lobby_py))

    def _world_to_bg(self, wx: float, wy: float) -> tuple[int, int]:
        return (int(wx - LOBBY_WORLD_XMIN), int(LOBBY_WORLD_YMAX - wy))

    def _build_lobby_background(self) -> pygame.Surface:
        width  = LOBBY_WORLD_XMAX - LOBBY_WORLD_XMIN
        height = LOBBY_WORLD_YMAX - LOBBY_WORLD_YMIN
        surf   = pygame.Surface((width, height))
        rng    = random.Random(42)

        _pixel_grass(surf, 0, 0, width, height, rng)

        center_bg = self._world_to_bg(0, 0)
        for i in range(4):
            sx, sy = self._world_to_bg(*LOBBY_STAGE_POS[i])
            dx = center_bg[0] - sx
            dy = center_bg[1] - sy
            dist  = max(1, int(math.hypot(dx, dy)))
            steps = dist // 6
            for step in range(steps + 1):
                t  = step / max(1, steps)
                px = int(sx + dx * t)
                py = int(sy + dy * t)
                _pixel_path(surf, px - 14, py - 14, 28, 28, rng)
      
        bush_positions = [
            (180,180),(1420,180),(180,1020),(1420,1020),
            (500,300),(1100,300),(500,900),(1100,900),
            (300,600),(1300,600),
            (750,200),(850,200),(750,1000),(850,1000),
            (200,480),(200,720),(1400,480),(1400,720),
        ]

        path_w = 40
        for bx, by in bush_positions:
            _draw_bush(surf, bx, by, rng.randint(4, 7), rng)

        for _ in range(320):
            fx = rng.randint(10, width - 10)
            fy = rng.randint(10, height - 10)
            if abs(fy - height//2) < path_w+30 or abs(fx - width//2) < path_w+30:
                continue
            _draw_flower(surf, fx, fy, rng.choice(_FLOWER_COLORS), rng)

        tree_positions = [
            (80,80),(1520,80),(80,1120),(1520,1120),
            (400,100),(1200,100),(400,1100),(1200,1100),
            (80,400),(80,800),(1520,400),(1520,800),
            (680,80),(920,80),(680,1120),(920,1120),
        ]
        for tx, ty in tree_positions:
            _draw_tree(surf, tx, ty, rng)

        for i, (wx, wy) in enumerate(LOBBY_STAGE_POS):
            sx, sy = self._world_to_bg(wx, wy)
            radius = 60 if i < 4 else 88
            color  = LOBBY_STAGE_COLORS[i]
            dim    = tuple(max(0, c - 50) for c in color)
            bright = tuple(min(255, c + 80) for c in color)
            ring_r = radius + 14

            # Anel externo
            for dy in range(-ring_r, ring_r + 1):
                row_w = int(math.sqrt(max(0, ring_r*ring_r - dy*dy)))
                inner = int(math.sqrt(max(0, radius*radius - dy*dy)))
                for dx in range(-row_w, -inner):
                    _px(surf, sx+dx, sy+dy, (88, 160, 72))
                for dx in range(inner, row_w):
                    _px(surf, sx+dx, sy+dy, (88, 160, 72))

            for dy in range(-radius+2, radius):
                dx = int(math.sqrt(max(0, (radius-2)**2 - dy*dy)))
                line_bresenham(
                    surf,
                    sx - dx + 5, sy + dy + 5,
                    sx + dx + 5, sy + dy + 5,
                    (20, 28, 18)
                )

            # Preenchimento com shading
            for dy in range(-radius, radius+1):
                dx = int(math.sqrt(max(0, radius*radius - dy*dy)))
                t  = abs(dy) / radius
                shade = tuple(int(dim[c] + (color[c]-dim[c])*(1 - t*0.4)) for c in range(3))

                line_bresenham(
                    surf,
                    sx - dx, sy + dy,
                    sx + dx, sy + dy,
                    shade
                )

            circle_midpoint(surf, sx, sy, radius,     tuple(min(255, c+40) for c in color))
            circle_midpoint(surf, sx, sy, radius-1,   tuple(min(255, c+20) for c in color))
            circle_midpoint(surf, sx, sy, radius-8,   tuple(max(0,   c-20) for c in color))

            for angle in range(0, 360, 18):
                rad = math.radians(angle)
                ex = int(sx + (radius-4)*math.cos(rad))
                ey = int(sy + (radius-4)*math.sin(rad))
                _px(surf, ex, ey, bright)
            
            # Badge com nome embaixo do círculo
            name_surf = self.f_sm.render(LOBBY_STAGE_NAMES[i], True, (235, 235, 235))
            badge_w = name_surf.get_width() + 16
            badge_h = name_surf.get_height() + 8
            badge_x = sx - badge_w // 2
            badge_y = sy + radius + 8

            # fundo escuro semitransparente simulado (cor sólida)
            badge_bg = tuple(max(0, c // 4) for c in color) 
            _fill_rect(surf, badge_x, badge_y, badge_w, badge_h, (18, 22, 18))
            # borda colorida
            draw_rectangle(surf, badge_x, badge_y, badge_w, badge_h, color)
            surf.blit(name_surf, (badge_x + 8, badge_y + 4))

            # Inicial estilizada no centro do círculo
            STAGE_ABBRS = ['Re', 'En', 'Rc', 'Le', 'Ps']
            abbr = STAGE_ABBRS[i]
            abbr_surf   = self.f_xl.render(abbr, True, bright)
            shadow_surf = self.f_xl.render(abbr, True, (20, 28, 18))
            surf.blit(shadow_surf, (sx - abbr_surf.get_width()//2 + 2, sy - abbr_surf.get_height()//2 + 2))
            surf.blit(abbr_surf,   (sx - abbr_surf.get_width()//2,     sy - abbr_surf.get_height()//2))

        return surf



    def _lobby_difficulty_buttons(self):
        gap = 16
        btn_w = 140
        btn_h = 40
        y = H - 160
        total_w = len(DIFFICULTY_NAMES) * btn_w + (len(DIFFICULTY_NAMES) - 1) * gap
        start_x = (W - total_w) // 2
        return [
            (name, start_x + i * (btn_w + gap), y, btn_w, btn_h, name)
            for i, name in enumerate(DIFFICULTY_NAMES)
        ]

    def _update_lobby(self, events, dt: float) -> None:
        keys = pygame.key.get_pressed()
        move_x = move_y = 0.0
        if self.lobby_stage_selected is None:
            if keys[pygame.K_w] or keys[pygame.K_UP]:    move_y += 1.0
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:  move_y -= 1.0
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:  move_x -= 1.0
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]: move_x += 1.0

        if move_x != 0.0 or move_y != 0.0:
            length = math.hypot(move_x, move_y)
            self.lobby_px += self.lobby_speed * dt * move_x / length
            self.lobby_py += self.lobby_speed * dt * move_y / length
            self.lobby_anim_t += dt

            if abs(move_x) > abs(move_y):
                self.lobby_last_move = 'right' if move_x > 0 else 'left'
            else:
                self.lobby_last_move = 'up' if move_y > 0 else 'down'
        else:
            self.lobby_anim_t = 0.0
            self.lobby_last_move = 'idle'

        self._clamp_lobby_player()

        near = None
        for i, (wx, wy) in enumerate(LOBBY_STAGE_POS):
            dist = math.hypot(self.lobby_px - wx, self.lobby_py - wy)
            if dist < LOBBY_ENTRY_RADIUS:
                near = i
                break
        self.lobby_entered_stage = near
        if self.lobby_entered_stage is None:
            self.lobby_stage_selected = None

        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if self.lobby_stage_selected is not None:
                        self.lobby_stage_selected = None
                    else:
                        pygame.mixer.music.stop()
                        pygame.mixer.music.load("musics/openingmenu.mp3") 
                        pygame.mixer.music.play(-1)
                        self.state = 'menu'
                elif ev.key == pygame.K_RETURN:
                    if self.lobby_stage_selected is None and self.lobby_entered_stage is not None:
                        self.lobby_stage_selected = self.lobby_entered_stage
                    elif self.lobby_stage_selected == 4:
                        self._try_start(stage_idx=4)
                    elif self.lobby_stage_selected in {0, 1, 2, 3}:
                        self._try_start(stage_idx=self.lobby_stage_selected, difficulty=self.difficulty)
                elif self.lobby_stage_selected in {0, 1, 2, 3} and ev.key in {pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d}:
                    idx = DIFFICULTY_NAMES.index(self.difficulty)
                    if ev.key in {pygame.K_LEFT, pygame.K_a}:
                        idx = (idx - 1) % len(DIFFICULTY_NAMES)
                    else:
                        idx = (idx + 1) % len(DIFFICULTY_NAMES)
                    self.difficulty = DIFFICULTY_NAMES[idx]
                elif self.lobby_stage_selected == 4:
                    if ev.key == pygame.K_BACKSPACE:
                        self.input_text = self.input_text[:-1]
                    elif ev.key in {pygame.K_LEFT, pygame.K_RIGHT}:
                        idx = DIFFICULTY_NAMES.index(self.difficulty)
                        if ev.key == pygame.K_LEFT:
                            idx = (idx - 1) % len(DIFFICULTY_NAMES)
                        else:
                            idx = (idx + 1) % len(DIFFICULTY_NAMES)
                        self.difficulty = DIFFICULTY_NAMES[idx]
                    elif ev.unicode:
                        self.input_text += ev.unicode
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self.lobby_stage_selected in {0, 1, 2, 3}:
                    mx, my = ev.pos
                    for lbl, bx, by, bw, bh, name in self._lobby_difficulty_buttons():
                        if bx <= mx <= bx + bw and by <= my <= by + bh:
                            self._try_start(stage_idx=self.lobby_stage_selected, difficulty=name)
                            break
        self.char_frame_t += dt
        frames = self.sprites.get(self.lobby_last_move if self.lobby_last_move in self.sprites else 'idle', [None])
        anim_key = self.lobby_last_move if self.lobby_last_move in self.sprites else 'idle'
        if self.char_frame_t >= self.char_frame_spd.get(anim_key, 0.12):
            self.char_frame_t = 0.0
            self.char_frame = (self.char_frame + 1) % max(1, len(frames))

    def _draw_lobby(self) -> None:
        scr = self.screen
        scr.blit(self.menu_art, (0, 0))

        view_x = (W - LOBBY_VIEW_W) // 2
        view_y = 120

        player_bg_x = int(self.lobby_px - LOBBY_WORLD_XMIN)
        player_bg_y = int(LOBBY_WORLD_YMAX - self.lobby_py)

        map_x = LOBBY_VIEW_W // 2 - player_bg_x
        map_y = LOBBY_VIEW_H // 2 - player_bg_y

        map_x = max(LOBBY_VIEW_W - self._lobby_bg_surf.get_width(), min(0, map_x))
        map_y = max(LOBBY_VIEW_H - self._lobby_bg_surf.get_height(), min(0, map_y))

        map_x = min(0, max(map_x, LOBBY_VIEW_W - self._lobby_bg_surf.get_width()))
        map_y = min(0, max(map_y, LOBBY_VIEW_H - self._lobby_bg_surf.get_height()))

        view_surf = pygame.Surface((LOBBY_VIEW_W, LOBBY_VIEW_H))
        view_surf.fill((10, 14, 28))
        view_surf.blit(self._lobby_bg_surf, (map_x, map_y))
        scr.blit(view_surf, (view_x, view_y))
        line_bresenham(scr, view_x, view_y, view_x + LOBBY_VIEW_W, view_y, (185, 185, 210))
        line_bresenham(scr, view_x + LOBBY_VIEW_W, view_y, view_x + LOBBY_VIEW_W, view_y + LOBBY_VIEW_H, (185, 185, 210))
        line_bresenham(scr, view_x + LOBBY_VIEW_W, view_y + LOBBY_VIEW_H, view_x, view_y + LOBBY_VIEW_H, (185, 185, 210))
        line_bresenham(scr, view_x, view_y + LOBBY_VIEW_H, view_x, view_y, (185, 185, 210))

        final_char_x = view_x + (player_bg_x + map_x)
        final_char_y = view_y + (player_bg_y + map_y)

        anim = self.lobby_last_move if self.lobby_last_move in self.sprites else 'idle'
        draw_char(scr, self.sprites_lobby, anim, int(final_char_x), int(final_char_y), self.char_frame, size=CHAR_SIZE_LOBBY)

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((12, 16, 34, 100))
        scr.blit(overlay, (0, 0))

        self._txt(self.f_xl, 'LOBBY', W // 2, 40, (245, 245, 255), center=True)
        self._txt(self.f_sm,
                  'Use WASD / setas para andar e ENTER quando estiver sobre uma fase',
                  W // 2, 84, (205, 205, 225), center=True)

        anim = self.lobby_last_move if self.lobby_last_move in self.sprites else 'idle'
        player_rel_x = self.lobby_px - LOBBY_WORLD_XMIN
        player_rel_y = LOBBY_WORLD_YMAX - self.lobby_py

        # Somando com o offset do mapa na tela para o boneco ficar em cima do cenário correto
        final_char_x = view_x + map_x + player_rel_x
        final_char_y = view_y + map_y + player_rel_y

        draw_char(scr, self.sprites_lobby, anim, int(final_char_x), int(final_char_y), self.char_frame, size=CHAR_SIZE_LOBBY)

        mini_w, mini_h = 220, 140
        mini_x = W - mini_w - 24
        mini_y = 120
        mini_surf = pygame.Surface((mini_w, mini_h))
        mini_surf.fill((10, 14, 20))

        mini_window = Window(LOBBY_WORLD_XMIN, LOBBY_WORLD_YMIN,
                             LOBBY_WORLD_XMAX, LOBBY_WORLD_YMAX)
        mini_viewport = Viewport(0, mini_h, mini_w, 0)

        draw_line_viewport(mini_surf, -360, 0, 360, 0, (70, 70, 110), mini_window, mini_viewport)
        draw_line_viewport(mini_surf, 0, -260, 0, 260, (70, 70, 110), mini_window, mini_viewport)

        for i, (wx, wy) in enumerate(LOBBY_STAGE_POS):
            marker = [(wx - 10, wy), (wx, wy + 10), (wx + 10, wy), (wx, wy - 10)]
            draw_polygon_viewport(mini_surf, marker, LOBBY_STAGE_COLORS[i], mini_window, mini_viewport)

        player_marker = [
            (self.lobby_px - 8, self.lobby_py),
            (self.lobby_px, self.lobby_py + 8),
            (self.lobby_px + 8, self.lobby_py),
            (self.lobby_px, self.lobby_py - 8),
        ]
        draw_polygon_viewport(mini_surf, player_marker, (235, 235, 100), mini_window, mini_viewport)

        for off in range(2):
            line_bresenham(mini_surf, off, off, mini_w - 1 - off, off, (140, 140, 170))
            line_bresenham(mini_surf, mini_w - 1 - off, off, mini_w - 1 - off, mini_h - 1 - off, (140, 140, 170))
            line_bresenham(mini_surf, mini_w - 1 - off, mini_h - 1 - off, off, mini_h - 1 - off, (140, 140, 170))
            line_bresenham(mini_surf, off, mini_h - 1 - off, off, off, (140, 140, 170))

        scr.blit(mini_surf, (mini_x, mini_y))
        self._txt(self.f_sm, 'MINI VIEWPORT', mini_x + mini_w // 2, mini_y - 18, (200, 200, 230), center=True)

        if self.lobby_stage_selected is not None:
            label = LOBBY_STAGE_NAMES[self.lobby_stage_selected]
            if self.lobby_stage_selected in {0, 1, 2, 3}:
                self._txt(self.f_md,
                          f'{label}: escolha a dificuldade para iniciar',
                          W // 2, H - 80, (240, 220, 140), center=True)
                for lbl, bx, by, bw, bh, name in self._lobby_difficulty_buttons():
                    self._draw_btn(scr, bx, by, bw, bh, lbl, self.f_sm,
                                   active=(name == self.difficulty),
                                   color=DIFFICULTY_COLORS[name])
                self._txt(self.f_sm,
                          'Use ←/→ ou A/D para mudar dificuldade e ENTER para começar',
                          W // 2, H - 182, (190, 190, 220), center=True)
            else:
                self._txt(self.f_sm,
                          'Use ← → para mudar dificuldade',
                          W // 2, H - 220, (190, 190, 220), center=True)
                for lbl, bx, by, bw, bh, name in self._lobby_difficulty_buttons():
                     self._draw_btn(scr, bx, by, bw, bh, lbl, self.f_sm,
                                    active=(name == self.difficulty),
                                    color=DIFFICULTY_COLORS[name])
                msg = 'Digite o nome do arquivo em musics/ (ex: minha.mp3)' if not self.input_text else 'Pressione ENTER para iniciar a fase personalizada'
                self._txt(self.f_md, msg, W // 2, H - 102, (240, 220, 140), center=True)
               
                bx, by, bw, bh = 120, H - 90, W - 240, 48
                scanline_fill(scr, [(bx,by),(bx+bw,by),(bx+bw,by+bh),(bx,by+bh)], (16, 20, 36))
                cb = (120, 120, 190)
                line_bresenham(scr, bx,    by,    bx+bw, by,    cb)
                line_bresenham(scr, bx+bw, by,    bx+bw, by+bh, cb)
                line_bresenham(scr, bx+bw, by+bh, bx,    by+bh, cb)
                line_bresenham(scr, bx,    by+bh, bx,    by,    cb)
                display = self.input_text[-72:] + ('|' if pygame.time.get_ticks() % 1000 < 500 else '')
                self._txt(self.f_sm, display, bx + 10, by + 12, (235, 235, 255))
        elif self.lobby_entered_stage is not None:
            label = LOBBY_STAGE_NAMES[self.lobby_entered_stage]
            if self.lobby_entered_stage in {0, 1, 2, 3}:
                self._txt(self.f_md,
                          f'Passe sobre {label} e pressione ENTER para ver as dificuldades',
                          W // 2, H - 80, (240, 220, 140), center=True)
            else:
                self._txt(self.f_md,
                          'Passe pelo centro e pressione ENTER para inserir o nome personalizado',
                          W // 2, H - 80, (240, 220, 140), center=True)
        else:
            self._txt(self.f_md,
                      'Aproxime-se de uma fase para ver o botão de entrada',
                      W // 2, H - 80, (175, 175, 215), center=True)

        if self.lobby_stage_selected == 4:
            self._txt(self.f_sm,
                      'ESC = cancelar seleção  |  BACKSPACE apaga o caminho  |  ENTER inicia',
                      W // 2, H - 24, (180, 180, 210), center=True)
        elif self.lobby_stage_selected is not None:
            self._txt(self.f_sm,
                      'ESC = cancelar seleção  |  ←/→ ou A/D muda dificuldade  |  ENTER inicia',
                      W // 2, H - 24, (180, 180, 210), center=True)
        else:
            self._txt(self.f_sm,
                      'ESC = menu  |  ENTER entra na fase  |  selecione a dificuldade e aperte enter para jogar',
                      W // 2, H - 24, (180, 180, 210), center=True)


    def _draw_tutorial(self) -> None:
        scr = self.screen
        scr.blit(self.menu_art, (0, 0))

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((8, 12, 28, 220))
        scr.blit(overlay, (0, 0))

        px, py, pw, ph = 60, 40, W - 120, H - 80
        scanline_fill(scr, [(px,py),(px+pw,py),(px+pw,py+ph),(px,py+ph)], (12, 15, 35))
        bc = (130, 110, 220)
        line_bresenham(scr, px, py, px+pw, py, bc)
        line_bresenham(scr, px, py+ph, px+pw, py+ph, bc)
        line_bresenham(scr, px, py, px, py+ph, bc)
        line_bresenham(scr, px+pw, py, px+pw, py+ph, bc)

        self._txt(self.f_xl, 'Re:Song  —  Como Jogar', W // 2, py + 30, (235, 235, 255), center=True)
        self._txt(self.f_sm, 'Um jogo de ritmo ambientado no universo de Re:Zero', W // 2, py + 62, (160, 150, 200), center=True)

        line_bresenham(scr, px + 20, py + 80, px + pw - 20, py + 80, (50, 45, 90))

        col1 = [
            ('NAVEGAÇÃO', ''),
            ('JOGAR',   'Abre o lobby'),
            ('WASD/SETAS',    'Anda pelo lobby'),
            ('ENTER',   'Entra na fase'),
            ('Centro',  'Fase personalizada'),
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
            self._txt(self.f_md if i == 0 else self.f_sm, k1, c1x, iy, color_k)
            self._txt(self.f_md if i == 0 else self.f_sm, k2, c3x, iy, color_k)
            if d1: self._txt(self.f_sm, d1, c2x, iy, color_d)
            if d2: self._txt(self.f_sm, d2, c4x, iy, color_d)

        line_bresenham(scr, px + 20, py + 268, px + pw - 20, py + 268, (50, 45, 90))

        self._txt(self.f_md, 'JULGAMENTOS', px + 30, py + 278, (180, 150, 255))
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
            scanline_fill(scr, [(gx,gy),(gx+gw,gy),(gx+gw,gy+48),(gx,gy+48)],
                        tuple(v // 5 for v in color))
            line_bresenham(scr, gx, gy, gx+gw, gy, tuple(v // 2 for v in color))
            line_bresenham(scr, gx, gy+48, gx+gw, gy+48, tuple(v // 2 for v in color))
            line_bresenham(scr, gx, gy, gx, gy+48, tuple(v // 2 for v in color))
            line_bresenham(scr, gx+gw, gy, gx+gw, gy+48, tuple(v // 2 for v in color))
            self._txt(self.f_sm, name, gx + gw // 2, gy + 10, color, center=True)
            self._txt(self.f_sm, pts,  gx + gw // 2, gy + 28, tuple(v // 2 + 80 for v in color), center=True)

        line_bresenham(scr, px + 20, py + 372, px + pw - 20, py + 372, (50, 45, 90))

        quote = '"Mesmo que esqueça tudo, eu não vou me esquecer de nenhum vocês"'
        self._txt(self.f_sm, quote, W // 2, py + 390, (120, 110, 160), center=True)

        self._txt(self.f_sm, 'ESC = voltar ao menu  |  clique para voltar',
                W // 2, py + ph - 18, (90, 85, 130), center=True)

    def _draw_settings(self) -> None:
        scr = self.screen
        scr.blit(self.menu_art, (0, 0))

        # Overlay
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((8, 12, 28, 220))
        scr.blit(overlay, (0, 0))

        px, py, pw, ph = 80, 60, W - 160, H - 120

        # Fundo
        scanline_fill(scr, [(px,py),(px+pw,py),(px+pw,py+ph),(px,py+ph)], (12, 15, 35))
        bc = (130, 110, 220)
        line_bresenham(scr, px, py, px+pw, py, bc)
        line_bresenham(scr, px, py+ph, px+pw, py+ph, bc)
        line_bresenham(scr, px, py, px, py+ph, bc)
        line_bresenham(scr, px+pw, py, px+pw, py+ph, bc)

        # Título
        self._txt(self.f_xl, 'Configurações', W // 2, py + 30, (235,235,255), center=True)

        line_bresenham(scr, px+20, py+70, px+pw-20, py+70, (50,45,90))

        # ========================
        # CONFIGS (estado)
        # ========================
        if not hasattr(self, "settings"):
            self.settings = {
                "adm_mode": False,
                "show_fps": False,
                "auto_play": False,
                "volume": 0.5
            }

        # ========================
        # FUNÇÃO BOTÃO
        # ========================
        def draw_toggle(x, y, label, key, info=None):
            w, h = 260, 40
            mx, my = pygame.mouse.get_pos()

            active = self.settings[key]

            base_color = (30, 30, 70) if not active else (60, 40, 120)
            border = (120, 100, 220) if active else (70, 70, 120)

            hover = x <= mx <= x+w and y <= my <= y+h
            if hover:
                border = (180, 160, 255)

            # fundo
            scanline_fill(scr, [(x,y),(x+w,y),(x+w,y+h),(x,y+h)], base_color)

            # borda
            line_bresenham(scr, x,y, x+w,y, border)
            line_bresenham(scr, x,y+h, x+w,y+h, border)
            line_bresenham(scr, x,y, x,y+h, border)
            line_bresenham(scr, x+w,y, x+w,y+h, border)

            # texto
            state_txt = "ON" if active else "OFF"
            state_color = (120,255,120) if active else (255,120,120)

            self._txt(self.f_sm, label, x+10, y+12, (220,220,255))
            self._txt(self.f_sm, state_txt, x+w-50, y+12, state_color)

            # botão info (i)
            if info:
                ix = x + w + 10
                iy = y + 8

                scanline_fill(scr, [(ix,iy),(ix+24,iy),(ix+24,iy+24),(ix,iy+24)], (20,20,50))
                line_bresenham(scr, ix,iy, ix+24,iy, (120,120,200))
                line_bresenham(scr, ix,iy+24, ix+24,iy+24, (120,120,200))
                line_bresenham(scr, ix,iy, ix,iy+24, (120,120,200))
                line_bresenham(scr, ix+24,iy, ix+24,iy+24, (120,120,200))

                self._txt(self.f_sm, "i", ix+12, iy+10, (200,200,255), center=True)

                if ix <= mx <= ix+24 and iy <= my <= iy+24:
                    self._txt(self.f_sm, info, ix+30, iy+4, (180,180,220))

            return (x, y, w, h)

        # ========================
        # DESENHO
        # ========================
        base_y = py + 100
        gap = 60

        self._settings_buttons = []

        self._settings_buttons.append(("adm_mode", draw_toggle(px+40, base_y, "Modo ADM", "adm_mode",
            "Permite acessar ferramentas de debug")))

        self._settings_buttons.append(("show_fps", draw_toggle(px+40, base_y+gap, "Mostrar FPS", "show_fps")))

        self._settings_buttons.append(("auto_play", draw_toggle(px+40, base_y+gap*2, "Auto Play", "auto_play",
            "Joga sozinho (modo debug)")))

        # ========================
        # VOLUME (slider fake)
        # ========================
        vx = px + pw//2 + 40
        vy = base_y

        self._txt(self.f_md, "Volume", vx, vy-30, (200,180,255))

        bar_w = 220
        bar_h = 10

        vol = self.settings["volume"]

        # fundo barra
        scanline_fill(scr, [(vx,vy),(vx+bar_w,vy),(vx+bar_w,vy+bar_h),(vx,vy+bar_h)], (40,40,80))

        # preenchimento
        fill_w = int(bar_w * vol)
        scanline_fill(scr, [(vx,vy),(vx+fill_w,vy),(vx+fill_w,vy+bar_h),(vx,vy+bar_h)], (120,100,255))

        # borda
        line_bresenham(scr, vx,vy, vx+bar_w,vy, (100,100,200))
        line_bresenham(scr, vx,vy+bar_h, vx+bar_w,vy+bar_h, (100,100,200))
        line_bresenham(scr, vx,vy, vx,vy+bar_h, (100,100,200))
        line_bresenham(scr, vx+bar_w,vy, vx+bar_w,vy+bar_h, (100,100,200))

        self._txt(self.f_sm, f"{int(vol*100)}%", vx+bar_w+10, vy-2, (180,180,255))

        self._volume_bar = (vx, vy, bar_w, bar_h)

        # Footer
        self._txt(self.f_sm, "ESC = voltar", W//2, py+ph-20, (100,100,150), center=True)

    def _draw_results(self) -> None:
        scr = self.screen
        scr.blit(self.bg_surf, (0, 0))

        total = self.perfects + self.goods + self.oks + self.misses
        acc   = (self.perfects + self.goods * 0.67 + self.oks * 0.33) / max(1, total)

        if   acc >= 0.95: grade, gc = 'S', (255, 215,   0)
        elif acc >= 0.85: grade, gc = 'A', (180, 255, 100)
        elif acc >= 0.70: grade, gc = 'B', (100, 200, 255)
        elif acc >= 0.50: grade, gc = 'C', (200, 200, 255)
        else:             grade, gc = 'D', (255, 100, 100)

        px, py, pw, ph = 80, 65, W - 160, H - 130
        scanline_fill(scr, [(px,py),(px+pw,py),(px+pw,py+ph),(px,py+ph)], (10, 10, 28))
        bc = (78, 55, 178)
        line_bresenham(scr, px,    py,    px+pw, py,    bc)
        line_bresenham(scr, px,    py+ph, px+pw, py+ph, bc)
        line_bresenham(scr, px,    py,    px,    py+ph, bc)
        line_bresenham(scr, px+pw, py,    px+pw, py+ph, bc)

        dc = DIFFICULTY_COLORS[self.difficulty]
        self._txt(self.f_lg, f'── RESULTADO  [{self.difficulty}] ──', W // 2, py + 20,
                  dc, center=True)

        rows = [
            (f'PONTUAÇÃO    {self.score:07d}',  (220, 220, 255)),
            (f'COMBO MÁX    {self.max_combo}×', (180, 180, 255)),
            ('',                                 None),
            (f'PERFEITOS    {self.perfects}',   (255, 235,  55)),
            (f'BONS         {self.goods}',       ( 55, 235,  55)),
            (f'OKs          {self.oks}',         ( 55, 180, 255)),
            (f'ERROS        {self.misses}',      (255,  65,  65)),
            ('',                                 None),
            (f'ACURÁCIA     {acc * 100:.1f}%',  (200, 200, 255)),
        ]
        for i, (t, c) in enumerate(rows):
            if c:
                self._txt(self.f_md, t, px + 70, py + 60 + i * 38, c)

        self._txt(self.f_xl, grade, px + pw - 95, py + ph // 2 - 35, gc)

        n_diff   = len(DIFFICULTY_NAMES)
        btn_w    = 140
        gap      = 10
        total_bw = n_diff * btn_w + (n_diff - 1) * gap
        start_x  = (W - total_bw) // 2
        ry       = py + ph - 72
        self._txt(self.f_sm, 'Jogar novamente em:', W // 2, ry - 14, (120,120,180), center=True)
        self._res_diff_btns = []
        for i, name in enumerate(DIFFICULTY_NAMES):
            bx2 = start_x + i * (btn_w + gap)
            col = DIFFICULTY_COLORS[name]
            is_sel = (name == self.difficulty)
            self._draw_btn(scr, bx2, ry, btn_w, 36, name, self.f_sm,
                           active=is_sel, color=col)
            self._res_diff_btns.append((bx2, ry, btn_w, 36, name))

        self._txt(self.f_sm,
                  '←/→ ou A/D muda dificuldade   ENTER: repetir mesmo nível   ESC: menu   Q: sair',
                  W // 2, py + ph - 22, (110, 110, 175), center=True)


    def _try_start(self, stage_idx: int = 0, difficulty: str | None = None) -> None:
        self.stage_idx = stage_idx if stage_idx is not None else 0
        if difficulty is not None:
            self.difficulty = difficulty
        path = self.input_text.strip().strip('"\'')

        if self.stage_idx in {0, 1, 2, 3}:
            music_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', STAGE_MUSIC_PATHS[self.stage_idx])
            )
            if not os.path.exists(music_path):
                self.menu_error = f'Música não encontrada: {STAGE_MUSIC_PATHS[self.stage_idx]}'
                return
            self.menu_error = ''
            if self.settings.get("adm_mode", False):
                self.load_song_recording_mode(music_path, stage_idx=stage_idx)
            else:
                self.load_song(music_path, stage_idx=stage_idx, pre_defined=True)
            return
        if not path:
            self.menu_error = 'Digite o nome da música personalizada.'
            return
        music_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', 'musics', path)
        )
        if not os.path.exists(music_path):
            self.menu_error = f'Não encontrado em musics/: {path[:55]}'
            return
        ext = os.path.splitext(path)[1].lower()
        if ext not in {'.mp3', '.ogg', '.wav', '.flac', '.m4a', '.opus'}:
            self.menu_error = 'Formato inválido. Use .mp3, .ogg, .wav ou .flac'
            return
        self.menu_error = ''
        self.load_song(music_path, stage_idx=4, pre_defined=False)

    def save_recorded_map(self):
        if not self.recorded_events:
            print("Nenhum evento gravado.")
            return

        self.recorded_events.sort(key=lambda x: x[0])

        name = os.path.splitext(os.path.basename(self.music_path))[0]

        data = {
            "music": name,
            "duration": self.duration,
            "bpm": self.bpm,
            "events": [
                {
                    "time": t,
                    "direction": d,
                    "strength": s,
                    "energy": e
                }
                for (t, d, s, e) in self.recorded_events
            ]
        }

        os.makedirs("src/beatmap", exist_ok=True)
        out_path = f"src/beatmap/{name}.json"

        with open(out_path, "w") as f:
            json.dump(data, f, indent=4)

        print(f"[REC] Beatmap salvo em: {out_path}")

    def update_recording(self):
        if self.state != 'recording':
            return

        if not pygame.mixer.music.get_busy():
            print("[REC] Música terminou, salvando mapa...")
            self.save_recorded_map()
            self.is_recording = False
            self.state = 'menu'  # ou outro estado

    def handle_recording_input(self, event):
        if self.state != 'recording':
            return

        if event.type == pygame.KEYDOWN:
            key_map = {
                pygame.K_UP: 'up',
                pygame.K_DOWN: 'down',
                pygame.K_LEFT: 'left',
                pygame.K_RIGHT: 'right',
            }

            if event.key in key_map:
                t = pygame.mixer.music.get_pos() / 1000.0  # ms → s
                d = key_map[event.key]

                print(f"[REC] {t:.3f}s -> {d}")

                self.recorded_events.append((t, d, 1.0, 0.5))

    def run(self) -> None:
        running = True
        while running:
            dt =  self.clock.tick(60) / 1000.0
            events = pygame.event.get()

            if self.state == 'menu':
                self.menu_timer += dt
                for i in range(len(self.alphas)):
                    if self.menu_timer > self.delays[i]:
                        if self.alphas[i] < 1.0:
                            self.alphas[i] = min(1.0, self.alphas[i] + self.fade_speed * dt)

            if (self.state == 'menu' or self.state == 'lobby') and not self.music_started:
                if self.music_delay_timer > 0:
                    self.music_delay_timer -= dt
                else:
                    pygame.mixer.music.play(-1) 
                    self.music_started = True

            for ev in events:
                if ev.type == pygame.QUIT:
                    running = False

            if self.state == 'menu':
                for ev in events:
                    if ev.type == pygame.KEYDOWN:
                        if ev.key == pygame.K_ESCAPE:
                            running = False
                        elif ev.key in {pygame.K_UP, pygame.K_w}:
                            self.menu_selection = (self.menu_selection - 1) % len(self._menu_buttons)
                        elif ev.key in {pygame.K_DOWN, pygame.K_s}:
                            self.menu_selection = (self.menu_selection + 1) % len(self._menu_buttons)
                        elif ev.key == pygame.K_RETURN:
                            _, _, _, _, action = list(self._menu_buttons)[self.menu_selection]
                            if action == 'play':
                                pygame.mixer.music.stop()
                                self.music_started = True
                                self.state = 'lobby'
                            elif action == 'tutorial':
                                self.state = 'tutorial'
                            elif action == 'settings':
                                self.state = 'settings'
                            elif action == 'exit':
                                self._exit_requested = True
                    elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                        mx, my = ev.pos
                        for idx, (bx2, by2, bw2, bh2, action) in enumerate(getattr(self, '_menu_buttons', [])):
                            if bx2 <= mx <= bx2+bw2 and by2 <= my <= by2+bh2:
                                self.menu_selection = idx
                                if action == 'play':
                                    self.music_started = True
                                    self.state = 'lobby'
                                elif action == 'tutorial':
                                    self.state = 'tutorial'
                                elif action == 'settings':
                                    self.state = 'settings'
                                elif action == 'exit':
                                    self._exit_requested = True
                        if self._exit_requested:
                            running = False
                self._draw_menu()

            elif self.state == 'lobby':
                self._update_lobby(events, dt)
                self._draw_lobby()

            elif self.state == 'tutorial':
                for ev in events:
                    if ev.type == pygame.KEYDOWN:
                        if ev.key == pygame.K_ESCAPE:
                            self.state = 'menu'
                    elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                        self.state = 'menu'
                self._draw_tutorial()

            elif self.state == 'settings':
                for ev in events:
                    if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                        self.state = 'menu'

                    elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                        mx, my = ev.pos

                        # toggles
                        for key, (x,y,w,h) in self._settings_buttons:
                            if x <= mx <= x+w and y <= my <= y+h:
                                self.settings[key] = not self.settings[key]
                                print(f"{key} -> {self.settings[key]}")

                        # volume
                        vx, vy, vw, vh = self._volume_bar
                        if vx <= mx <= vx+vw and vy <= my <= vy+vh:
                            rel = (mx - vx) / vw
                            self.settings["volume"] = max(0.0, min(1.0, rel))
                            pygame.mixer.music.set_volume(self.settings["volume"])

                self._draw_settings()


            elif self.state == 'playing':
                for ev in events:
                    if ev.type == pygame.KEYDOWN:
                        k = ev.key
                        if k == pygame.K_ESCAPE:
                            pygame.mixer.music.stop()
                            self.state = 'lobby'
                        elif k in KEY_MAP:
                            self.press_key(KEY_MAP[k])
                self.update(dt)
                self._draw_playing()

            elif self.state == 'results':
                for ev in events:
                    if ev.type == pygame.KEYDOWN:
                        k = ev.key
                        if k == pygame.K_ESCAPE:
                            self.state = 'lobby'
                        elif k == pygame.K_RETURN and self.music_path:
                            self.load_song(self.music_path, reuse_raw=True)
                        elif k in {pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d}:
                            idx = DIFFICULTY_NAMES.index(self.difficulty)
                            if k in {pygame.K_LEFT, pygame.K_a}:
                                idx = (idx - 1) % len(DIFFICULTY_NAMES)
                            else:
                                idx = (idx + 1) % len(DIFFICULTY_NAMES)
                            self.difficulty = DIFFICULTY_NAMES[idx]
                        elif k == pygame.K_q:
                            running = False
                    elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                        mx, my = ev.pos
                        for bx2, by2, bw2, bh2, dname in getattr(self, '_res_diff_btns', []):
                            if bx2 <= mx <= bx2+bw2 and by2 <= my <= by2+bh2:
                                self.difficulty = dname
                self._draw_results()

            elif self.state == 'recording':
                for ev in events:
                    if ev.type == pygame.KEYDOWN:
                        if ev.key == pygame.K_ESCAPE:
                            print("[REC] Cancelado")
                            pygame.mixer.music.stop()
                            self.state = 'menu'
                        else:
                            self.handle_recording_input(ev)

                self.update_recording()
                self._draw_playing()  # pode reaproveitar o draw

                

            if self._exit_requested:
                running = False

            pygame.display.flip()

        pygame.quit()

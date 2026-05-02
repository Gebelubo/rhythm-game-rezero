import pygame
import os
import sys
import math

LOBBY_STAGE_NAMES = [
    'Floresta', 'Cidade', 'Templo', 'Vórtex', 'Personalizada'
]

LOBBY_STAGE_COLORS = [
    (95, 170, 95),
    (95, 155, 205),
    (220, 165, 90),
    (200, 95, 175),
    (255, 200, 110),
]

LOBBY_WORLD_XMIN = -800
LOBBY_WORLD_YMIN = -600
LOBBY_WORLD_XMAX = 800
LOBBY_WORLD_YMAX = 600
LOBBY_GRID_SPACING = 100
LOBBY_VIEW_W = 620
LOBBY_VIEW_H = 420

LOBBY_STAGE_POS = [
    (-500, 350),  # Floresta (Superior Esquerda)
    (500, 350),   # Cidade (Superior Direita)
    (-500, -350), # Templo (Inferior Esquerda)
    (500, -350),  # Vórtex (Inferior Direita)
    (0, 0),       # Personalizada (Centro)
]

LOBBY_ENTRY_RADIUS = 64

from src.config import (
    W, H, LANE_W, LANE_COUNT, TARGET_Y, SPAWN_OFFSET, FALL_TIME,
    CHAR_SIZE, DIRECTIONS, LANE_COLORS, LANE_DIM, NOTE_SIZE, WIN_GOOD, WIN_OK, WIN_PERFECT, HUD_H, KEY_MAP
)
from src.music_backend.note import Note
from src.music_backend.difficulty import apply_difficulty
from src.music_backend.utils import (
    detect_beats,
)

from src.utils.render import (
    bake_static_bg, bake_arrow_surf
)

from src.sprites import draw_char, load_sprites

from src.music_backend.backend_config import (
    DIFFICULTY_COLORS, DIFFICULTY_NAMES
)

from src.lib.cg_lib import (
    Window, Viewport, boundary_fill, circle_midpoint, cohen_sutherland_clip,
    draw_line_clipped, draw_line_viewport, draw_polygon, draw_polygon_viewport,
    ellipse_midpoint, flood_fill, line_bresenham, scanline_fill, set_pixel
)

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

        self.char_cx = self.lane_left + total_lane_w + 95
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

        self.sprites = load_sprites()

        self.menu_bg_image = self._load_menu_bg_image()
        self.menu_art = self._build_menu_art()
        self._lobby_bg_surf = self._build_lobby_background()
        self.menu_page = 'main'
        self._menu_buttons = []
        self._lobby_buttons = []
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

        self.char_anim  = 'idle'
        self.char_timer = 0.0
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


    def music_time(self) -> float:
        pos = pygame.mixer.music.get_pos()
        return pos / 1000.0 if pos >= 0 else self.duration + 10.0


    def load_song(self, path: str, reuse_raw: bool = False, stage_idx: int = 0) -> None:
        self.stage_idx = stage_idx if stage_idx is not None else 0
        d2x = {d: self.lane_xs[i] for i, d in enumerate(DIRECTIONS)}

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

        self.char_anim  = direction
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

        self.fb_timer   = max(0.0, self.fb_timer   - dt)
        self.char_timer = max(0.0, self.char_timer - dt)
        if self.char_timer <= 0:
            self.char_anim = 'idle'
        for d in DIRECTIONS:
            self.lane_flash[d] = max(0.0, self.lane_flash[d] - dt)

        if not pygame.mixer.music.get_busy():
            self.state = 'results'


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

        draw_char(scr, self.sprites, self.char_anim, self.char_cx, self.char_cy)

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
            ('TUTORIAL', start_x, start_y + btn_h + gap, btn_w, btn_h, 'tutorial', (155, 115, 235)),
            ('SAIR', start_x, start_y + 2 * (btn_h + gap), btn_w, btn_h, 'exit', (235, 90, 110)),
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
        width = LOBBY_WORLD_XMAX - LOBBY_WORLD_XMIN
        height = LOBBY_WORLD_YMAX - LOBBY_WORLD_YMIN
        surf = pygame.Surface((width, height))
        surf.fill((14, 18, 34))

        for gx in range(LOBBY_WORLD_XMIN + 20, LOBBY_WORLD_XMAX, LOBBY_GRID_SPACING):
            x = gx - LOBBY_WORLD_XMIN
            line_bresenham(surf, x, 0, x, height, (30, 30, 55))
        for gy in range(LOBBY_WORLD_YMIN + 20, LOBBY_WORLD_YMAX, LOBBY_GRID_SPACING):
            y = LOBBY_WORLD_YMAX - gy
            line_bresenham(surf, 0, y, width, y, (30, 30, 55))

        for i, (wx, wy) in enumerate(LOBBY_STAGE_POS):
            sx, sy = self._world_to_bg(wx, wy)
            radius = 60 if i < 4 else 88
            circle_midpoint(surf, sx, sy, radius, LOBBY_STAGE_COLORS[i])
            flood_fill(surf, sx, sy, tuple(min(255, c + 30) for c in LOBBY_STAGE_COLORS[i]))
            poly = [
                self._world_to_bg(wx + radius * math.cos(a), wy + radius * math.sin(a))
                for a in [k * math.pi / 3 for k in range(6)]
            ]
            draw_polygon(surf, poly, (255, 255, 255))
            label = self.f_md.render(LOBBY_STAGE_NAMES[i], True, (235, 235, 235))
            surf.blit(label, (sx - label.get_width() // 2, sy - radius - 24))

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
                        if self.lobby_stage_selected == 4:
                            self.input_text = ''
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
                    elif ev.unicode:
                        self.input_text += ev.unicode
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self.lobby_stage_selected in {0, 1, 2, 3}:
                    mx, my = ev.pos
                    for lbl, bx, by, bw, bh, name in self._lobby_difficulty_buttons():
                        if bx <= mx <= bx + bw and by <= my <= by + bh:
                            self._try_start(stage_idx=self.lobby_stage_selected, difficulty=name)
                            break

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
        draw_char(scr, self.sprites, anim, int(final_char_x), int(final_char_y))

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

        draw_char(scr, self.sprites, anim, int(final_char_x), int(final_char_y))

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
                msg = 'Digite o caminho para a fase personalizada' if not self.input_text else 'Pressione ENTER para iniciar a fase personalizada'
                self._txt(self.f_md, msg, W // 2, H - 118, (240, 220, 140), center=True)
                bx, by, bw, bh = 120, H - 150, W - 240, 48
                scanline_fill(scr, [(bx,by),(bx+bw,by),(bx+bw,by+bh),(bx,by+bh)], (16, 20, 36))
                cb = (120, 120, 190)
                line_bresenham(scr, bx,    by,    bx+bw, by,    cb)
                line_bresenham(scr, bx+bw, by,    bx+bw, by+bh, cb)
                line_bresenham(scr, bx+bw, by+bh, bx,    by+bh, cb)
                line_bresenham(scr, bx,    by+bh, bx,    by,    cb)
                display = self.input_text[-72:] + ('|' if pygame.time.get_ticks() % 1000 < 500 else '')
                self._txt(self.f_sm, display, bx + 10, by + 12, (235, 235, 255))
                self._txt(self.f_sm,
                          'Digite o caminho da música personalizada e pressione ENTER',
                          W // 2, by - 24, (210, 210, 230), center=True)
        elif self.lobby_entered_stage is not None:
            label = LOBBY_STAGE_NAMES[self.lobby_entered_stage]
            if self.lobby_entered_stage in {0, 1, 2, 3}:
                self._txt(self.f_md,
                          f'Passe sobre {label} e pressione ENTER para ver as dificuldades',
                          W // 2, H - 80, (240, 220, 140), center=True)
            else:
                self._txt(self.f_md,
                          'Passe pelo centro e pressione ENTER para inserir o caminho personalizado',
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

        px, py, pw, ph = 70, 60, W - 140, H - 120
        scanline_fill(scr, [(px,py),(px+pw,py),(px+pw,py+ph),(px,py+ph)], (15, 18, 40))
        line_bresenham(scr, px, py, px+pw, py, (130, 110, 220))
        line_bresenham(scr, px, py+ph, px+pw, py+ph, (130, 110, 220))
        line_bresenham(scr, px, py, px, py+ph, (130, 110, 220))
        line_bresenham(scr, px+pw, py, px+pw, py+ph, (130, 110, 220))

        self._txt(self.f_xl, 'TUTORIAL', W // 2, 90, (235, 235, 255), center=True)
        lines = [
            'Esta tela inicial usa reta, circunferência, elipse e preenchimento',
            'com Flood Fill / Boundary Fill para construir a arte de abertura.',
            '',
            'JOGAR: leva ao lobby de fases, onde você escolhe o canto ou a fase central.',
            'TUTORIAL: volta para esta tela de instruções.',
            'SAIR: fecha o jogo.',
            '',
            'Durante o jogo, use as teclas ← ↓ ↑ → para acertar as notas.',
            'A tela de resultados mostra pontuação, combo e precisão.',
            '',
            'Pressione ESC para voltar ao menu principal.',
        ]
        for i, line in enumerate(lines):
            self._txt(self.f_sm, line, W // 2, 150 + i * 32, (200, 200, 230), center=True)


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
            self.menu_error = ''
            self.load_song(self._default_stage_music_path(), stage_idx=stage_idx)
            return
        if not path:
            self.menu_error = 'Digite o caminho para a fase personalizada.'
            return
        if not os.path.exists(path):
            self.menu_error = f'Arquivo não encontrado: {path[:55]}'
            return
        ext = os.path.splitext(path)[1].lower()
        if ext not in {'.mp3', '.ogg', '.wav', '.flac', '.m4a', '.opus'}:
            self.menu_error = 'Formato inválido. Use .mp3, .ogg, .wav ou .flac'
            return
        self.menu_error = ''
        self.load_song(path, stage_idx=stage_idx)

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
                                self.state = 'lobby'
                            elif action == 'tutorial':
                                self.state = 'tutorial'
                            elif action == 'exit':
                                self._exit_requested = True
                    elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                        mx, my = ev.pos
                        for idx, (bx2, by2, bw2, bh2, action) in enumerate(getattr(self, '_menu_buttons', [])):
                            if bx2 <= mx <= bx2+bw2 and by2 <= my <= by2+bh2:
                                self.menu_selection = idx
                                if action == 'play':
                                    self.state = 'lobby'
                                elif action == 'tutorial':
                                    self.state = 'tutorial'
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

            if self._exit_requested:
                running = False

            pygame.display.flip()

        pygame.quit()

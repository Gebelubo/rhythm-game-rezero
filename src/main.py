import pygame
import os
import sys

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
    line_bresenham, scanline_fill
)
class RhythmGame:

    def __init__(self):
        pygame.init()
        pygame.mixer.init(44100, -16, 2, 512)

        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("RhythmPy ♪")
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

        self.state      = 'menu'
        self.music_path = None
        self.input_text = sys.argv[1] if len(sys.argv) > 1 else ''
        self.menu_error = ''
        self.difficulty  = 'Normal'
        self._raw_events = []

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


    def music_time(self) -> float:
        pos = pygame.mixer.music.get_pos()
        return pos / 1000.0 if pos >= 0 else self.duration + 10.0


    def load_song(self, path: str, reuse_raw: bool = False) -> None:
        d2x = {d: self.lane_xs[i] for i, d in enumerate(DIRECTIONS)}

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


    def _draw_playing(self) -> None:
        scr = self.screen

        scr.blit(self.bg_surf, (0, 0))

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
        scr.blit(self.bg_surf, (0, 0))

        self._txt(self.f_xl, '♪  RhythmPy  ♪', W // 2, 55,
                  (188, 148, 255), center=True)
        self._txt(self.f_sm, 'Pressione as setas no momento certo para acertar as notas!',
                  W // 2, 105, (150, 150, 210), center=True)
        self._txt(self.f_sm, 'Cole o caminho do arquivo de música abaixo:',
                  W // 2, 135, (175, 175, 240), center=True)

        bx, by, bw, bh = 55, 162, W - 110, 42
        scanline_fill(scr, [(bx,by),(bx+bw,by),(bx+bw,by+bh),(bx,by+bh)], (20, 20, 50))
        cb = (105, 105, 255)
        line_bresenham(scr, bx,    by,    bx+bw, by,    cb)
        line_bresenham(scr, bx+bw, by,    bx+bw, by+bh, cb)
        line_bresenham(scr, bx+bw, by+bh, bx,    by+bh, cb)
        line_bresenham(scr, bx,    by+bh, bx,    by,    cb)
        display = self.input_text[-72:] + '|'
        self._txt(self.f_sm, display, bx + 10, by + 12, (215, 215, 255))

        self._txt(self.f_md, 'Dificuldade:', W // 2, 222, (180, 180, 240), center=True)

        n_diff   = len(DIFFICULTY_NAMES)
        btn_w    = 170
        gap      = 14
        total_bw = n_diff * btn_w + (n_diff - 1) * gap
        start_x  = (W - total_bw) // 2
        btn_h    = 44

        self._diff_btns = []
        for i, name in enumerate(DIFFICULTY_NAMES):
            bx2 = start_x + i * (btn_w + gap)
            by2 = 244
            col = DIFFICULTY_COLORS[name]
            is_sel = (name == self.difficulty)
            self._draw_btn(scr, bx2, by2, btn_w, btn_h, name, self.f_md,
                           active=is_sel, color=col)
            desc = {'Fácil': '~2 notas/s', 'Normal': '~4 notas/s',
                    'Difícil': '~6 notas/s', 'Expert': '~9 notas/s'}[name]
            dc = col if is_sel else (90, 90, 120)
            self._txt(self.f_sm, desc, bx2 + btn_w // 2, by2 + btn_h + 8, dc, center=True)
            self._diff_btns.append((bx2, by2, btn_w, btn_h + 22, name))

        hints = {
            'Fácil':   'Apenas os beats principais. Ideal para iniciantes.',
            'Normal':  'Beats + onsets fortes. Bom equilíbrio.',
            'Difícil': 'Maioria dos onsets + acordes nos picos de intensidade.',
            'Expert':  'Quase todos os onsets. Acordes frequentes. Boa sorte!',
        }
        hc = DIFFICULTY_COLORS[self.difficulty]
        self._txt(self.f_sm, hints[self.difficulty], W // 2, 318, hc, center=True)

        self._btnx, self._btny = W // 2 - 130, 340
        self._btnw, self._btnh = 260, 52
        bx2, by2, bw2, bh2 = self._btnx, self._btny, self._btnw, self._btnh
        self._draw_btn(scr, bx2, by2, bw2, bh2, '▶  INICIAR', self.f_lg,
                       active=True, color=(115, 75, 250))

        if self.menu_error:
            self._txt(self.f_sm, self.menu_error, W // 2, 405, (255, 85, 85), center=True)

        try:
            import librosa
            st, sc = 'librosa ✓  análise espectral por banda de frequência', (80, 200, 80)
        except ImportError:
            st, sc = 'librosa não instalado → BPM fixo 120.  pip install librosa', (200, 150, 70)
        self._txt(self.f_sm, st, W // 2, H - 40, sc, center=True)
        self._txt(self.f_sm,
                  '← ↓ ↑ →  acertar notas     ESC  sair     Sprites: pasta sprites/',
                  W // 2, H - 20, (78, 78, 125), center=True)


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
                  'ENTER: repetir mesmo nível     ESC: menu     Q: sair',
                  W // 2, py + ph - 22, (110, 110, 175), center=True)


    def _try_start(self) -> None:
        path = self.input_text.strip().strip('"\'')
        if not os.path.exists(path):
            self.menu_error = f'Arquivo não encontrado: {path[:55]}'
            return
        ext = os.path.splitext(path)[1].lower()
        if ext not in {'.mp3', '.ogg', '.wav', '.flac', '.m4a', '.opus'}:
            self.menu_error = 'Formato inválido. Use .mp3, .ogg, .wav ou .flac'
            return
        self.menu_error = ''
        self.load_song(path)

    def run(self) -> None:
        running = True
        while running:
            dt     = self.clock.tick(60) / 1000.0
            events = pygame.event.get()

            for ev in events:
                if ev.type == pygame.QUIT:
                    running = False

            if self.state == 'menu':
                for ev in events:
                    if ev.type == pygame.KEYDOWN:
                        k = ev.key
                        if   k == pygame.K_ESCAPE:    running = False
                        elif k == pygame.K_RETURN:    self._try_start()
                        elif k == pygame.K_BACKSPACE: self.input_text = self.input_text[:-1]
                        else:                         self.input_text += ev.unicode
                    elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                        mx, my = ev.pos
                        for dbx, dby, dbw, dbh, dname in getattr(self, '_diff_btns', []):
                            if dbx <= mx <= dbx+dbw and dby <= my <= dby+dbh:
                                self.difficulty = dname
                                self.menu_error = ''
                        bx2 = getattr(self, '_btnx', W//2-130)
                        by2 = getattr(self, '_btny', 340)
                        bw2 = getattr(self, '_btnw', 260)
                        bh2 = getattr(self, '_btnh', 52)
                        if bx2 <= mx <= bx2+bw2 and by2 <= my <= by2+bh2:
                            self._try_start()
                self._draw_menu()

            elif self.state == 'playing':
                for ev in events:
                    if ev.type == pygame.KEYDOWN:
                        k = ev.key
                        if k == pygame.K_ESCAPE:
                            pygame.mixer.music.stop()
                            self.state = 'menu'
                        elif k in KEY_MAP:
                            self.press_key(KEY_MAP[k])
                self.update(dt)
                self._draw_playing()

            elif self.state == 'results':
                for ev in events:
                    if ev.type == pygame.KEYDOWN:
                        k = ev.key
                        if k == pygame.K_ESCAPE:
                            self.state = 'menu'
                        elif k == pygame.K_RETURN and self.music_path:
                            self.load_song(self.music_path, reuse_raw=True)
                        elif k == pygame.K_q:
                            running = False
                    elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                        mx, my = ev.pos
                        for bx2, by2, bw2, bh2, dname in getattr(self, '_res_diff_btns', []):
                            if bx2 <= mx <= bx2+bw2 and by2 <= my <= by2+bh2:
                                self.difficulty = dname
                                if self.music_path:
                                    self.load_song(self.music_path, reuse_raw=True)
                self._draw_results()

            pygame.display.flip()

        pygame.quit()

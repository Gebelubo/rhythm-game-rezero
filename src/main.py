import pygame
import os
import sys
import json

from src.config import (
    W, H, LANE_W, LANE_COUNT, TARGET_Y, SPAWN_OFFSET, FALL_TIME,
    CHAR_SIZE, CHAR_SIZE_LOBBY, DIRECTIONS, LANE_COLORS, LANE_DIM,
    NOTE_SIZE, WIN_GOOD, WIN_OK, WIN_PERFECT, HUD_H, KEY_MAP
)
from src.music_backend.note import Note
from src.music_backend.difficulty import apply_difficulty
from src.music_backend.utils import detect_beats, load_beatmap
from src.music_backend.backend_config import DIFFICULTY_COLORS, DIFFICULTY_NAMES, STAGE_MUSIC_PATHS

from src.utils.render import bake_static_bg, bake_arrow_surf, DIRECTION_ANGLES
from src.utils.ui import _txt, _draw_btn
from src.sprites import draw_char, load_sprites

from src.entities.char import Character

from src.music_backend.utils import calc_acc, calc_reward

from src.funcs.cg_lib import (
    Window, Viewport, boundary_fill, circle_midpoint, cohen_sutherland_clip,
    draw_line_clipped, draw_line_viewport, draw_polygon, draw_polygon_viewport,
    ellipse_midpoint, flood_fill, line_bresenham, scanline_fill,
    set_pixel, draw_rectangle, fill_rectangle
)

from src.screens.menu import (
    load_menu_bg_image, build_menu_art,
    draw_menu, draw_tutorial, draw_settings,
    build_splash_screen, draw_splash, draw_character_selector, draw_shop
)
from src.screens.lobby import (
    build_lobby_background, update_lobby, draw_lobby,
    LOBBY_STAGE_NAMES, LOBBY_STAGE_COLORS, LOBBY_STAGE_POS,
    LOBBY_WORLD_XMIN, LOBBY_WORLD_XMAX, LOBBY_WORLD_YMIN, LOBBY_WORLD_YMAX,
    LOBBY_VIEW_W, LOBBY_VIEW_H, LOBBY_ENTRY_RADIUS, LOBBY_GRID_SPACING
)
from src.screens.playing import update_playing, draw_playing, draw_results


class RhythmGame:

    def __init__(self):
        pygame.init()
        pygame.mixer.init(44100, -16, 2, 512)

        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Re:Song")
        self.clock  = pygame.time.Clock()

        self.f_xl = pygame.font.SysFont('Segoe UI', 42, bold=True)        # Moderna, limpa
        self.f_lg = pygame.font.SysFont('Segoe UI', 28, bold=True)
        self.f_md = pygame.font.SysFont('Segoe UI', 20)
        self.f_sm = pygame.font.SysFont('Segoe UI', 15)

        total_lane_w   = LANE_W * LANE_COUNT
        self.lane_left = (W - total_lane_w) // 2 - 85
        self.lane_xs   = [self.lane_left + i * LANE_W + LANE_W // 2
                          for i in range(LANE_COUNT)]

        self.char_cx = self.lane_left + total_lane_w + 150
        self.char_cy = TARGET_Y - 20

        self.bg_surf    = bake_static_bg(self.lane_left)
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

        # SISTEMA MONETARIO
        self.money = 0.0
        self.money_changed = False

        # SKINS
        self.unlocked_characters = [Character("Emilia", "sprites_1")]
        self.shop_characters = [(Character("GB", "sprites_2"), 250), (Character("Vesuvio", "sprites_3"), 350)]
        self.selected_character = self.unlocked_characters[0]
        self.sprite_folder = "sprites_1"
        self.shop_select_index = 0

        self.sprites       = load_sprites(self.sprite_folder, size=CHAR_SIZE)
        self.sprites_lobby = load_sprites(self.sprite_folder, size=CHAR_SIZE_LOBBY)

        fonts = (self.f_xl, self.f_lg, self.f_md, self.f_sm)
        self.menu_bg_image  = load_menu_bg_image()
        self.menu_art       = build_menu_art(W, H, self.menu_bg_image)
        self._lobby_bg_surf = build_lobby_background(fonts)

        # ── Splash screen ──────────────────────────────────────────────────────
        self.splash_surf    = build_splash_screen(W, H)
        self.splash_alpha   = 0.0        # 0–255, controla fade
        self.splash_timer   = 0.0        # tempo total na splash
        self.splash_fade_in = 1.2        # segundos para aparecer
        self.splash_hold    = 3.0        # segundos visível (após fade-in)
        self.splash_fade_out= 0.8        # segundos para sumir
        self._splash_done   = False      # já saiu da splash?

        self.menu_page        = 'main'
        self._menu_buttons    = []
        self._lobby_buttons   = []
        self._settings_buttons = []
        self._volume_bar      = None
        self._res_diff_btns   = []
        self._exit_requested  = False

        # Começa na splash, não no menu
        self.state          = 'splash'
        self.menu_selection = 0
        self.music_path     = None
        self.input_text     = sys.argv[1] if len(sys.argv) > 1 else ''
        self.menu_error     = ''
        self.difficulty     = 'Normal'
        self.difficulty_phase = 'Normal'
        self.stage_idx      = 0
        self.selected_stage = None
        self._raw_events    = []

        self.lobby_px            = 0.0
        self.lobby_py            = 0.0
        self.lobby_speed         = 180.0
        self.lobby_anim_t        = 0.0
        self.lobby_entered_stage = None
        self.lobby_stage_selected = None
        self.lobby_last_move     = 'idle'

        self.notes:    list[Note] = []
        self.score     = 0
        self.combo     = 0
        self.max_combo = 0
        self.perfects  = self.goods = self.oks = self.misses = 0
        self.duration  = 0.0
        self.bpm       = 120.0

        self.reward = 0

        self.fb_text  = ''
        self.fb_timer = 0.0
        self.fb_color = (255, 255, 255)

        self.char_anim      = 'game_idle'
        self.char_timer     = 0.0
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

        self.intensity_map   = []
        self._intensity_surf = pygame.Surface((W, H), pygame.SRCALPHA)

        self.menu_alpha       = 0.0
        self.fade_speed       = 0.7
        self.music_delay_timer = 2.0
        self.music_started    = False

        try:
            pygame.mixer.music.load("musics/openingmenu.mp3")
            pygame.mixer.music.set_volume(0.4)
        except pygame.error as e:
            print(f"Erro ao carregar música de abertura: {e}")

        self.menu_timer = 0.0
        self.alphas  = [0.0] * 9
        self.delays = [
            0.0,  # fundo
            2.0,  # título
            2.4,  # subtítulo

            2.8,  # jogar
            3.2,  # configurações
            3.6,  # tutorial
            4.0,  # personagens
            4.4,  # sair

            4.8,  # footer
        ]

        self.settings = {
            "adm_mode": False,
            "show_fps":  False,
            "auto_play": False,
            "volume":    0.5
        }

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _enter_menu(self):
        """Transição da splash para o menu."""
        self.state      = 'menu'
        self.menu_timer = 0.0
        self.alphas     = [0.0] * 9

    def music_time(self) -> float:
        pos = pygame.mixer.music.get_pos()
        return pos / 1000.0 if pos >= 0 else self.duration + 10.0

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
    
    def update_sprites_folder(self):
        self.sprites       = load_sprites(self.sprite_folder, size=CHAR_SIZE)
        self.sprites_lobby = load_sprites(self.sprite_folder, size=CHAR_SIZE_LOBBY)

    def press_key(self, direction: str) -> None:
        mt      = self.music_time()
        best    = None
        best_dt = 999.0

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

        self.combo     += 1
        self.max_combo  = max(self.max_combo, self.combo)
        bonus           = 1 + self.combo // 10
        self.score     += pts * bonus

        self.fb_text  = grade
        self.fb_timer = 0.55
        self.fb_color = col

        self.char_anim  = f'game_{direction}'
        self.char_timer = 0.30
        self.lane_flash[direction] = 0.22

    def _flash_lane(self, direction: str) -> None:
        """Efeito visual/animacional quando uma seta é ativada (usado em recording)."""
        if direction not in self.lane_flash:
            return
        self.char_anim  = f'game_{direction}'
        self.char_timer = 0.30
        self.lane_flash[direction] = 0.22

    def _tick_timers(self, dt: float) -> None:
        """Atualiza timers que afetam a renderização (fade do brilho, char_timer, fb_timer)."""
        # decai o brilho das lanes
        for d in list(self.lane_flash.keys()):
            if self.lane_flash[d] > 0.0:
                self.lane_flash[d] = max(0.0, self.lane_flash[d] - dt)

        # decai timer da animação do personagem
        if self.char_timer > 0.0:
            self.char_timer = max(0.0, self.char_timer - dt)
            if self.char_timer == 0.0:
                # volta para idle quando acabar o timer
                self.char_anim = 'game_idle'

        # feedback text timer
        if self.fb_timer > 0.0:
            self.fb_timer = max(0.0, self.fb_timer - dt)

    def load_song(self, path: str, reuse_raw: bool = False,
                  stage_idx: int = 0, pre_defined: bool = False) -> None:
        self.stage_idx = stage_idx if stage_idx is not None else 0
        d2x = {d: self.lane_xs[i] for i, d in enumerate(DIRECTIONS)}
        fonts = (self.f_xl, self.f_lg, self.f_md, self.f_sm)

        if not pre_defined:
            duration = self.duration
            if not reuse_raw or not self._raw_events:
                self.screen.blit(self.bg_surf, (0, 0))
                diff_c = DIFFICULTY_COLORS[self.difficulty]
                _txt(self.screen, self.f_lg, '♪  Analisando batidas…  ♪',
                     W // 2, H // 2 - 24, (185, 145, 255), center=True)
                _txt(self.screen, self.f_md, f'Dificuldade: {self.difficulty}',
                     W // 2, H // 2 + 18, diff_c, center=True)
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

        notes_raw   = apply_difficulty(raw_events, self.duration, self.difficulty)
        self.notes  = [Note(t, d, d2x[d]) for t, d in notes_raw]

        self.score = self.combo = self.max_combo = 0
        self.perfects = self.goods = self.oks = self.misses = 0
        self.fb_text    = ''
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
            peak = max((e for _, e in self.intensity_map), default=1)
            if peak > 0:
                self.intensity_map = [(t, e / peak) for t, e in self.intensity_map]

        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        self.state = 'playing'

    def load_song_recording_mode(self, path: str, stage_idx: int = 0) -> None:
        self.stage_idx      = stage_idx if stage_idx is not None else 0
        self._raw_events    = []
        self.recorded_events = []
        self.duration       = 0.0
        self.bpm            = 0.0
        self.music_path     = path

        self.screen.blit(self.bg_surf, (0, 0))
        _txt(self.screen, self.f_lg, '● MODO GRAVAÇÃO ●',
             W // 2, H // 2 - 24, (255, 120, 120), center=True)
        _txt(self.screen, self.f_md, 'Pressione as teclas no ritmo!',
             W // 2, H // 2 + 18, (200, 200, 200), center=True)
        pygame.display.flip()

        try:
            snd = pygame.mixer.Sound(path)
            self.duration = snd.get_length()
            del snd
        except Exception:
            self.duration = 240.0

        self.notes    = []
        self.score    = self.combo = self.max_combo = 0
        self.perfects = self.goods = self.oks = self.misses = 0
        self.fb_text    = ''
        self.char_anim  = 'idle'
        self.char_timer = 0.0
        self.lane_flash = {d: 0.0 for d in DIRECTIONS}

        self.recording_start_time = None
        self.is_recording = True

        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        self.state = 'recording'

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

    def save_recorded_map(self) -> None:
        if not self.recorded_events:
            print("Nenhum evento gravado.")
            return

        self.recorded_events.sort(key=lambda x: x[0])
        name = os.path.splitext(os.path.basename(self.music_path))[0]
        data = {
            "music":    name,
            "duration": self.duration,
            "bpm":      self.bpm,
            "events": [
                {"time": t, "direction": d, "strength": s, "energy": e}
                for (t, d, s, e) in self.recorded_events
            ]
        }
        os.makedirs("src/beatmap", exist_ok=True)
        out_path = f"src/beatmap/{name}.json"
        with open(out_path, "w") as f:
            json.dump(data, f, indent=4)
        print(f"[REC] Beatmap salvo em: {out_path}")

    def update_recording(self) -> None:
        if not pygame.mixer.music.get_busy():
            print("[REC] Música terminou, salvando mapa...")
            self.save_recorded_map()
            self.is_recording = False
            self.state = 'menu'

    def handle_recording_input(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            key_map = {
                pygame.K_UP:    'up',
                pygame.K_DOWN:  'down',
                pygame.K_LEFT:  'left',
                pygame.K_RIGHT: 'right',
            }
            if event.key in key_map:
                t = pygame.mixer.music.get_pos() / 1000.0
                d = key_map[event.key]
                print(f"[REC] {t:.3f}s -> {d}")
                self.recorded_events.append((t, d, 1.0, 0.5))
                self._flash_lane(d)

    def add_money(self, value:float):
        if not self.money_changed:
            self.money += value
            self.money_changed = True


    # ── Loop principal ─────────────────────────────────────────────────────────

    def run(self) -> None:
        fonts   = (self.f_xl, self.f_lg, self.f_md, self.f_sm)
        running = True

        while running:
            dt     = self.clock.tick(60) / 1000.0
            events = pygame.event.get()

            for ev in events:
                if ev.type == pygame.QUIT:
                    running = False

            # ── SPLASH ────────────────────────────────────────────────────────
            if self.state == 'splash':
                self.splash_timer += dt
                t = self.splash_timer
                fi = self.splash_fade_in
                ho = self.splash_hold
                fo = self.splash_fade_out
                total = fi + ho + fo

                if t <= fi:
                    self.splash_alpha = (t / fi) * 255
                elif t <= fi + ho:
                    self.splash_alpha = 255
                elif t <= total:
                    self.splash_alpha = (1.0 - (t - fi - ho) / fo) * 255
                else:
                    self._enter_menu()

                # Qualquer tecla ou clique pula a splash
                for ev in events:
                    if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                        self._enter_menu()

                if self.state == 'splash':
                    draw_splash(self.screen, self.splash_surf, int(self.splash_alpha))

            # ── MENU ──────────────────────────────────────────────────────────
            elif self.state == 'menu':
                self.menu_timer += dt
                for i in range(len(self.alphas)):
                    if self.menu_timer > self.delays[i] and self.alphas[i] < 1.0:
                        self.alphas[i] = min(1.0, self.alphas[i] + self.fade_speed * dt)

                if not self.music_started:
                    if self.music_delay_timer > 0:
                        self.music_delay_timer -= dt
                    else:
                        pygame.mixer.music.play(-1)
                        self.music_started = True

                for ev in events:
                    if ev.type == pygame.KEYDOWN:
                        if ev.key == pygame.K_ESCAPE:
                            running = False
                        elif ev.key in {pygame.K_UP, pygame.K_w}:
                            self.menu_selection = (self.menu_selection - 1) % max(1, len(self._menu_buttons))
                        elif ev.key in {pygame.K_DOWN, pygame.K_s}:
                            self.menu_selection = (self.menu_selection + 1) % max(1, len(self._menu_buttons))
                        elif ev.key == pygame.K_RETURN and self._menu_buttons:
                            _, _, _, _, action = self._menu_buttons[self.menu_selection]
                            if action == 'play':
                                pygame.mixer.music.stop()
                                self.music_started = True
                                self.state = 'lobby'
                            elif action == 'tutorial':
                                self.state = 'tutorial'
                            elif action == 'settings':
                                self.state = 'settings'
                            elif action == 'character_select':
                                self.state = 'character_select'
                            elif action == 'shop':
                                self.state = 'shop'
                            elif action == 'exit':
                                self._exit_requested = True
                    elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                        mx, my = ev.pos
                        for idx, (bx, by, bw, bh, action) in enumerate(self._menu_buttons):
                            if bx <= mx <= bx+bw and by <= my <= by+bh:
                                self.menu_selection = idx
                                if action == 'play':
                                    self.music_started = True
                                    self.state = 'lobby'
                                elif action == 'tutorial':
                                    self.state = 'tutorial'
                                elif action == 'settings':
                                    self.state = 'settings'
                                elif action == 'character_select':
                                    self.state = 'character_select'
                                elif action == 'shop':
                                    self.state = 'shop'
                                elif action == 'exit':
                                    self._exit_requested = True

                draw_menu(self.screen, fonts, W, H,
                          self.alphas, self.menu_selection,
                          self._menu_buttons, self.menu_error, self.menu_art)

            # ── LOBBY ─────────────────────────────────────────────────────────
            elif self.state == 'lobby':
                if not self.music_started:
                    if self.music_delay_timer > 0:
                        self.music_delay_timer -= dt
                    else:
                        pygame.mixer.music.play(-1)
                        self.music_started = True

                update_lobby(events, dt, self)
                draw_lobby(self.screen, fonts, self, self._lobby_bg_surf, self.menu_art)
                self.money_changed = False

            # ── TUTORIAL ──────────────────────────────────────────────────────
            elif self.state == 'tutorial':
                for ev in events:
                    if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                        self.state = 'menu'
                    elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                        self.state = 'menu'
                draw_tutorial(self.screen, fonts, W, H, self.menu_art)

            # ── SETTINGS ──────────────────────────────────────────────────────
            elif self.state == 'settings':
                for ev in events:
                    if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                        self.state = 'menu'
                    elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                        mx, my = ev.pos
                        for key, (x, y, w, h) in self._settings_buttons:
                            if x <= mx <= x+w and y <= my <= y+h:
                                self.settings[key] = not self.settings[key]
                        if self._volume_bar:
                            vx, vy, vw, vh = self._volume_bar
                            if vx <= mx <= vx+vw and vy <= my <= vy+vh:
                                self.settings["volume"] = max(0.0, min(1.0, (mx - vx) / vw))
                                pygame.mixer.music.set_volume(self.settings["volume"])

                self._settings_buttons, self._volume_bar = draw_settings(
                    self.screen, fonts, W, H, self.menu_art, self.settings
                )

            # ── PLAYING ───────────────────────────────────────────────────────
            elif self.state == 'playing':
                for ev in events:
                    if ev.type == pygame.KEYDOWN:
                        if ev.key == pygame.K_ESCAPE:
                            pygame.mixer.music.stop()
                            self.state = 'lobby'
                        elif ev.key in KEY_MAP:
                            self.press_key(KEY_MAP[ev.key])

                next_state = update_playing(self, dt)
                if next_state:
                    self.state = next_state
                draw_playing(self.screen, fonts, self)

            # ── RESULTS ───────────────────────────────────────────────────────
            elif self.state == 'results':
                self.reward = calc_reward(calc_acc(self), self.difficulty_phase)
                for ev in events:
                    if ev.type == pygame.KEYDOWN:
                        k = ev.key
                        if k == pygame.K_ESCAPE:
                            self.state = 'lobby'
                            self.add_money(self.reward)
                        elif k == pygame.K_RETURN and self.music_path:
                            self.load_song(self.music_path, reuse_raw=True)
                        elif k in {pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d}:
                            idx = DIFFICULTY_NAMES.index(self.difficulty)
                            idx = (idx - 1) % len(DIFFICULTY_NAMES) if k in {pygame.K_LEFT, pygame.K_a} else (idx + 1) % len(DIFFICULTY_NAMES)
                            self.difficulty = DIFFICULTY_NAMES[idx]
                        elif k == pygame.K_q:
                            running = False
                    elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                        mx, my = ev.pos
                        for bx, by, bw, bh, dname in self._res_diff_btns:
                            if bx <= mx <= bx+bw and by <= my <= by+bh:
                                self.difficulty = dname

                self._res_diff_btns = draw_results(self.screen, fonts, self)

            # ── RECORDING ─────────────────────────────────────────────────────
            elif self.state == 'recording':
                for ev in events:
                    if ev.type == pygame.KEYDOWN:
                        if ev.key == pygame.K_ESCAPE:
                            print("[REC] Cancelado")
                            self.recorded_events = []
                            pygame.mixer.music.stop()
                            self.state = 'menu'
                        else:
                            self.handle_recording_input(ev)

                self.update_recording()
                self._tick_timers(dt)
                draw_playing(self.screen, fonts, self)

            elif self.state == "character_select":

                char_buttons = draw_character_selector(
                    self.screen,
                    fonts,
                    W,
                    H,
                    self.menu_art,
                    self
                )

                # índice selecionado por teclado
                if not hasattr(self, "character_select_index"):
                    self.character_select_index = 0

                total_chars = len(self.unlocked_characters)
                cols = 3

                for ev in events:

                    if ev.type == pygame.KEYDOWN:

                        # sair
                        if ev.key == pygame.K_ESCAPE:
                            self.state = "menu"

                        # mover seleção
                        elif ev.key in (pygame.K_LEFT, pygame.K_a):

                            self.character_select_index -= 1

                            if self.character_select_index < 0:
                                self.character_select_index = total_chars - 1

                        elif ev.key in (pygame.K_RIGHT, pygame.K_d):

                            self.character_select_index += 1

                            if self.character_select_index >= total_chars:
                                self.character_select_index = 0

                        elif ev.key in (pygame.K_UP, pygame.K_w):

                            self.character_select_index -= cols

                            if self.character_select_index < 0:
                                self.character_select_index = max(0, total_chars - 1)

                        elif ev.key in (pygame.K_DOWN, pygame.K_s):

                            self.character_select_index += cols

                            if self.character_select_index >= total_chars:
                                self.character_select_index = total_chars - 1

                        # selecionar personagem
                        elif ev.key == pygame.K_RETURN:

                            char = self.unlocked_characters[self.character_select_index]

                            self.selected_character = char
                            self.sprite_folder = char.sprites_folder

                            self.update_sprites_folder()

                    # mouse
                    elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:

                        mx, my = ev.pos

                        for i, (bx, by, bw, bh, char) in enumerate(char_buttons):

                            if bx <= mx <= bx+bw and by <= my <= by+bh:

                                self.character_select_index = i

                                self.selected_character = char
                                self.sprite_folder = char.sprites_folder

                                self.update_sprites_folder()

            elif self.state == "shop":

                shop_buttons = draw_shop(
                    self.screen,
                    fonts,
                    W,
                    H,
                    self.menu_art,
                    self
                )

                for ev in events:

                    if ev.type == pygame.KEYDOWN:

                        if ev.key == pygame.K_ESCAPE:
                            self.state = "menu"

                        elif ev.key == pygame.K_RIGHT:
                            self.shop_select_index = min(
                                self.shop_select_index + 1,
                                len(self.shop_characters) - 1
                            )

                        elif ev.key == pygame.K_LEFT:
                            self.shop_select_index = max(
                                self.shop_select_index - 1,
                                0
                            )

                        elif ev.key == pygame.K_DOWN:
                            self.shop_select_index = min(
                                self.shop_select_index + 3,
                                len(self.shop_characters) - 1
                            )

                        elif ev.key == pygame.K_UP:
                            self.shop_select_index = max(
                                self.shop_select_index - 3,
                                0
                            )

                        elif ev.key == pygame.K_RETURN:

                            char, price = self.shop_characters[self.shop_select_index]

                            if (
                                char not in self.unlocked_characters
                                and self.money >= price
                            ):

                                self.money -= price
                                self.unlocked_characters.append(char)

                    elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:

                        mx, my = ev.pos

                        for bx, by, bw, bh, char, price in shop_buttons:

                            if bx <= mx <= bx+bw and by <= my <= by+bh:

                                if (
                                    char not in self.unlocked_characters
                                    and self.money >= price
                                ):

                                    self.money -= price
                                    self.unlocked_characters.append(char)

            if self._exit_requested:
                running = False

            pygame.display.flip()

        pygame.quit()
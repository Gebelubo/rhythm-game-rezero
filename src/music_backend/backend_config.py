BAND_DIR = ['left', 'down', 'up', 'right']
BAND_HZ  = [(20, 200), (200, 800), (800, 3500), (3500, 11025)]

DIFFICULTIES = {
    'Fácil': dict(
        onset_thr_base = 0.72,
        onset_thr_k    = 0.30,
        min_gap_ms     = 580,
        chord_energy   = None,
        chord_max      = 1,
        keep_ratio     = 0.45,
    ),
    'Normal': dict(
        onset_thr_base = 0.52,
        onset_thr_k    = 0.28,
        min_gap_ms     = 220,
        chord_energy   = None,
        chord_max      = 1,
        keep_ratio     = 0.72,
    ),
    'Difícil': dict(
        onset_thr_base = 0.38,
        onset_thr_k    = 0.25,
        min_gap_ms     = 140,
        chord_energy   = 0.72,
        chord_max      = 2,
        keep_ratio     = 0.82,
    ),
    'Expert': dict(
        onset_thr_base = 0.22,
        onset_thr_k    = 0.20,
        min_gap_ms     = 100,
        chord_energy   = 0.58,
        chord_max      = 2,
        keep_ratio     = 0.90,
    ),
}
DIFFICULTY_NAMES  = ['Fácil', 'Normal', 'Difícil', 'Expert']
DIFFICULTY_COLORS = {
    'Fácil':   ( 80, 200,  80),
    'Normal':  ( 80, 160, 255),
    'Difícil': (255, 165,  40),
    'Expert':  (255,  60,  60),
}

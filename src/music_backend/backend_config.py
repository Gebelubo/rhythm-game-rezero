BAND_DIR = ['left', 'down', 'up', 'right']
BAND_HZ  = [(20, 200), (200, 800), (800, 3500), (3500, 11025)]

DIFFICULTIES= {
    "Fácil": {
        "remove_chance": 0.75,
        "add_chance": 0.00,
        "min_gap": 0.42,
    },

    "Normal": {
        "remove_chance": 0.00,
        "add_chance": 0.00,
        "min_gap": 0.30,
    },

    "Difícil": {
        "remove_chance": 0.00,
        "add_chance": 0.42,
        "min_gap": 0.20,
    },

    "Expert": {
        "remove_chance": 0.00,
        "add_chance": 0.82,
        "min_gap": 0.1,
    }
}

DIFFICULTY_NAMES  = ['Fácil', 'Normal', 'Difícil', 'Expert']
DIFFICULTY_COLORS = {
    'Fácil':   ( 80, 200,  80),
    'Normal':  ( 80, 160, 255),
    'Difícil': (255, 165,  40),
    'Expert':  (255,  60,  60),
}

STAGE_MUSIC_PATHS = [
    'musics/refazer.mp3',
    'musics/entender.mp3',
    'musics/reconstruir.mp3',
    'musics/lembrar.mp3',
]

DIFFICULTY_MONEY = {
    "Fácil":   40,
    "Normal": 70,
    "Difícil":   110,
    "Expert": 170,
}
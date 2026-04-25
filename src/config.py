import pygame

W,  H           = 920, 660
LANE_W          = 116
LANE_COUNT      = 4
HUD_H           = 76
NOTE_SIZE       = 44
TARGET_Y        = 555
SPAWN_OFFSET    = 690
FALL_TIME       = 1.90

CHAR_SIZE       = 100

DIRECTIONS      = ['left', 'down', 'up', 'right']
KEY_MAP = {
    pygame.K_LEFT:  'left',
    pygame.K_DOWN:  'down',
    pygame.K_UP:    'up',
    pygame.K_RIGHT: 'right',
}

WIN_PERFECT     = 0.050
WIN_GOOD        = 0.100
WIN_OK          = 0.160

LANE_COLORS = {
    'left':  (220,  65,  65),
    'down':  ( 55, 140, 220),
    'up':    ( 55, 215,  80),
    'right': (220, 190,  45),
}
LANE_DIM = {
    'left':  ( 62,  17,  17),
    'down':  ( 16,  42,  65),
    'up':    ( 16,  62,  23),
    'right': ( 65,  57,  10),
}

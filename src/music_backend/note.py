from src.config import (
    TARGET_Y, SPAWN_OFFSET, FALL_TIME,
)
class Note:
    __slots__ = ('beat_time', 'direction', 'lane_x', 'active', 'hit', 'missed')

    def __init__(self, beat_time: float, direction: str, lane_x: int):
        self.beat_time = beat_time
        self.direction = direction
        self.lane_x    = lane_x
        self.active    = True
        self.hit       = False
        self.missed    = False

    def y_pos(self, music_t: float) -> float:
        frac   = 1.0 - (self.beat_time - music_t) / FALL_TIME
        spawn  = TARGET_Y - SPAWN_OFFSET
        return spawn + (TARGET_Y - spawn) * frac

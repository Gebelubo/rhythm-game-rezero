from src.music_backend.backend_config import (
    BAND_HZ, BAND_DIR,
)

import math

import pygame

from src.music_backend.backend_config import DIFFICULTY_MONEY

def _hz_to_bin(hz: float, sr: int, n_fft: int) -> int:
    return int(hz / (sr / 2) * (n_fft // 2 + 1))


def _smooth(arr, w=5):
    import numpy as np
    kernel = np.ones(w) / w
    return np.convolve(arr, kernel, mode='same')


def _local_energy_map(y, sr, hop=512, window_sec=1.5):

    import numpy as np
    import librosa
    rms    = librosa.feature.rms(y=y, hop_length=hop)[0]
    n_win  = max(1, int(window_sec * sr / hop))
    local  = np.array([rms[max(0, i-n_win):i+n_win].mean()
                       for i in range(len(rms))])
    mn, mx = local.min(), local.max()
    return (local - mn) / (mx - mn + 1e-9)


def detect_beats(path: str):
    duration = 240.0
    try:
        snd = pygame.mixer.Sound(path)
        duration = snd.get_length()
        del snd
    except Exception:
        pass

    try:
        import librosa
        import numpy as np

        SR    = 22050
        HOP   = 512
        N_FFT = 2048

        y, sr = librosa.load(path, sr=SR, mono=True)
        duration = len(y) / sr

        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, trim=False)
        bpm = float(np.atleast_1d(tempo)[0])

        D   = np.abs(librosa.stft(y, n_fft=N_FFT, hop_length=HOP))
        n_f = D.shape[0]

        energy = _local_energy_map(y, sr, hop=HOP, window_sec=1.8)
        n_stft = D.shape[1]
        if len(energy) != n_stft:
            xp = np.linspace(0, 1, len(energy))
            xi = np.linspace(0, 1, n_stft)
            energy = np.interp(xi, xp, energy)


        raw_events = []
        for band_idx, (f_lo, f_hi) in enumerate(BAND_HZ):
            b_lo = _hz_to_bin(f_lo, SR, N_FFT)
            b_hi = _hz_to_bin(min(f_hi, SR // 2), SR, N_FFT)
            b_lo = min(b_lo, n_f - 1)
            b_hi = min(b_hi, n_f)
            if b_lo >= b_hi:
                continue

            D_band = D[b_lo:b_hi, :]

            flux = np.diff(D_band, axis=1, prepend=D_band[:, :1])
            flux = np.maximum(flux, 0).sum(axis=0)
            flux = _smooth(flux, w=3)

            band_max = flux.max()
            if band_max < 1e-6:
                continue
            flux_norm = flux / band_max

            onset_frames = librosa.onset.onset_detect(
                onset_envelope=flux_norm,
                sr=SR,
                hop_length=HOP,
                backtrack=False,
                delta=0.07,
                wait=int(SR / HOP * 0.10)
            )

            direction = BAND_DIR[band_idx]
            for fr in onset_frames:
                t        = librosa.frames_to_time(fr, sr=SR, hop_length=HOP)
                strength = float(flux_norm[min(fr, len(flux_norm) - 1)])
                e_local  = float(energy[min(fr, len(energy) - 1)])
                if 1.0 <= t <= duration - 1.5:
                    raw_events.append((t, direction, strength, e_local))

        raw_events.sort(key=lambda x: x[0])

        if not raw_events:
            beat_times = librosa.frames_to_time(beat_frames, sr=SR, hop_length=HOP)
            raw_events = [
                (float(t), BAND_DIR[i % 4], 0.8, 0.5)
                for i, t in enumerate(beat_times)
                if 1.0 <= t <= duration - 1.5
            ]

        return raw_events, bpm, duration

    except ImportError:
        pass

    bpm      = 120.0
    interval = 60.0 / bpm
    total    = int((duration - 2.0) / interval)

    raw_events = []
    for i in range(total):
        t        = 1.0 + i * interval
        block    = (i // 16) % 4
        e_local  = {0: 0.2, 1: 0.5, 2: 0.85, 3: 0.5}[block]
        strength = 0.4 + 0.6 * abs(math.sin(i * 0.7))
        d = BAND_DIR[i % 4]
        raw_events.append((t, d, strength, e_local))
        if block == 2 and i % 4 == 0:
            d2 = BAND_DIR[(i + 2) % 4]
            raw_events.append((t, d2, strength * 0.75, e_local))

    raw_events.sort(key=lambda x: x[0])
    return raw_events, bpm, duration

import json
import os
BEATMAP_DIR = 'src/beatmap/'

def load_beatmap(path: str):

    name = os.path.splitext(os.path.basename(path))[0] + ".json"

    complete_path = os.path.join(BEATMAP_DIR, name)
    if not os.path.exists(complete_path):
        print(f"[LOAD] Beatmap não encontrado: {complete_path}")
        return [], 120.0, 0.0

    with open(complete_path, 'r') as f:
        data = json.load(f)

    raw_events = []

    events = data.get("events", [])
    for ev in events:
        t = float(ev.get("time", 0.0))
        d = ev.get("direction", "up")
        strength = float(ev.get("strength", 0.8))
        e_local  = float(ev.get("energy", 0.5))

        raw_events.append((t, d, strength, e_local))

    # Ordena por segurança
    raw_events.sort(key=lambda x: x[0])

    bpm = float(data.get("bpm", 120.0))
    duration = float(data.get("duration", 0.0))

    # fallback caso duration não exista
    if duration <= 0 and raw_events:
        duration = raw_events[-1][0] + 2.0

    print(f"[LOAD] {len(raw_events)} eventos carregados")
    print(f"[LOAD] BPM: {bpm}, Duração: {duration:.2f}s")

    return raw_events, bpm, duration

def calc_reward(acc: float, difficulty: str) -> int:

    base = DIFFICULTY_MONEY.get(difficulty, 70)

    # curva forte de recompensa
    # accuracy baixa destrói o valor
    acc_curve = acc ** 2.2

    # bônus extra para full combo/quase perfeito
    bonus = 1.0

    if acc >= 0.98:
        bonus = 1.35
    elif acc >= 0.95:
        bonus = 1.20
    elif acc >= 0.90:
        bonus = 1.10

    reward = int(base * acc_curve * bonus)

    # mínimo simbólico
    if acc >= 0.30:
        reward = max(5, reward)
    else:
        reward = 0

    return reward

def calc_acc(game):
    total = game.perfects + game.goods + game.oks + game.misses
    return (game.perfects + game.goods * 0.67 + game.oks * 0.33) / max(1, total)


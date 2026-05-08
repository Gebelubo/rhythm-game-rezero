from src.music_backend.backend_config import (
    DIFFICULTIES,
)
from src.config import (
    DIRECTIONS,
)
import random
import random


def apply_difficulty(raw_events: list,
                     duration: float,
                     diff_name: str = "Normal") -> list:
    
    cfg = DIFFICULTIES.get(
        diff_name,
        DIFFICULTIES["Normal"]
    )

    remove_chance = cfg["remove_chance"]
    add_chance    = cfg["add_chance"]
    min_gap       = cfg["min_gap"]

    rng = random.Random()

    # ─────────────────────────────────────────
    # Converte formato do mapa
    # ─────────────────────────────────────────
    notes = []

    for ev in raw_events:

        t = float(ev[0])
        d = ev[1]

        notes.append((t, d))

    notes.sort(key=lambda x: x[0])

    # ─────────────────────────────────────────
    # REMOVE notas (dificuldade baixa)
    # ─────────────────────────────────────────
    filtered = []

    last_per_dir = {
        d: -999.0
        for d in DIRECTIONS
    }

    for t, d in notes:

        # evita spam
        if t - last_per_dir[d] < min_gap:
            continue

        last_per_dir[d] = t

        # remover aleatoriamente
        if rng.random() < remove_chance:
            continue

        filtered.append((t, d))

    # ─────────────────────────────────────────
    # ADICIONA notas (dificuldade alta)
    # ─────────────────────────────────────────
    extra_notes = []

    for i in range(len(filtered) - 1):

        t1, d1 = filtered[i]
        t2, d2 = filtered[i + 1]

        gap = t2 - t1

        # espaço muito pequeno
        if gap < min_gap * 1.5:
            continue

        # chance de adicionar nota
        if rng.random() > add_chance:
            continue

        # tempo da nova nota
        nt = round(
            rng.uniform(
                t1 + min_gap * 0.6,
                t2 - min_gap * 0.6
            ),
            3
        )

        # direção diferente
        possible_dirs = [
            d for d in DIRECTIONS
            if d != d1
        ]

        nd = rng.choice(possible_dirs)

        extra_notes.append((nt, nd))

        # chance pequena de chord
        if diff_name in ("Hard", "Insane"):

            if rng.random() < 0.18:

                chord_dirs = [
                    d for d in DIRECTIONS
                    if d != nd
                ]

                cd = rng.choice(chord_dirs)

                extra_notes.append((nt, cd))

    # ─────────────────────────────────────────
    # Junta tudo
    # ─────────────────────────────────────────
    final = filtered + extra_notes

    final.sort(key=lambda x: x[0])

    # ─────────────────────────────────────────
    # Remove colisões finais
    # ─────────────────────────────────────────
    cleaned = []

    last_dir_time = {
        d: -999.0
        for d in DIRECTIONS
    }

    for t, d in final:

        if t - last_dir_time[d] < min_gap:
            continue

        cleaned.append((t, d))

        last_dir_time[d] = t

    # ─────────────────────────────────────────
    # Garantia mínima
    # ─────────────────────────────────────────
    if len(cleaned) < 8:

        beat_gap = max(0.35, duration / 24)

        cleaned = []

        t = 2.0

        while t < duration - 2.0:

            cleaned.append((
                round(t, 3),
                rng.choice(DIRECTIONS)
            ))

            t += beat_gap

    return cleaned
from src.music_backend.backend_config import (
    DIFFICULTIES,
)
from src.config import (
    DIRECTIONS,
)
import random
def apply_difficulty(raw_events: list, duration: float,
                     diff_name: str = 'Normal') -> list:

    cfg = DIFFICULTIES[diff_name]
    thr_base   = cfg['onset_thr_base']
    thr_k      = cfg['onset_thr_k']
    min_gap    = cfg['min_gap_ms'] / 1000.0
    chord_nrg  = cfg['chord_energy']
    chord_max  = cfg['chord_max']
    keep_ratio = cfg['keep_ratio']

    candidates = []
    for t, d, strength, e_local in raw_events:
        thr = thr_base - thr_k * e_local
        if strength >= thr:
            candidates.append((t, d, strength, e_local))

    candidates.sort(key=lambda x: x[0])
    last_t_per_dir = {d: -999.0 for d in DIRECTIONS}
    after_gap = []
    for t, d, strength, e_local in candidates:
        if t - last_t_per_dir[d] >= min_gap:
            after_gap.append((t, d, strength, e_local))
            last_t_per_dir[d] = t

    CHORD_WIN = 0.025
    groups = []
    for item in after_gap:
        if groups and item[0] - groups[-1][0][0] < CHORD_WIN:
            groups[-1].append(item)
        else:
            groups.append([item])

    notes_pool = []
    for grp in groups:
        e_local = grp[0][3]
        if chord_nrg is not None and e_local >= chord_nrg and len(grp) > 1:
            grp_sorted = sorted(grp, key=lambda x: -x[2])
            seen, count = set(), 0
            for t, d, s, e in grp_sorted:
                if d not in seen and count < chord_max:
                    notes_pool.append((t, d, s))
                    seen.add(d)
                    count += 1
        else:
            best = max(grp, key=lambda x: x[2])
            notes_pool.append((best[0], best[1], best[2]))


    final = []
    for t, d, strength in notes_pool:
        p_keep = keep_ratio + (1.0 - keep_ratio) * strength
        if random.random() < p_keep:
            final.append((t, d))

    final.sort(key=lambda x: x[0])

    if not final and notes_pool:
        final = [(t, d) for t, d, _ in notes_pool]
        final.sort(key=lambda x: x[0])

    return final

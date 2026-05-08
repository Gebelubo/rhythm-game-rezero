# Beatmaps (`src/beatmap/*.json`)

Este documento descreve como os beatmaps funcionam no **Re:Song** e como criar/editar mapas.

## Onde ficam e como são carregados

- Diretório: `src/beatmap/`
- Para as **fases fixas**, o jogo deriva o nome do beatmap pelo basename da música:
  - `musics/entender.mp3` → `src/beatmap/entender.json`
- O carregamento é feito por `src/music_backend/utils.py` (`load_beatmap`).

## Schema do JSON

Um beatmap é um JSON com este formato:

```json
{
  "music": "entender",
  "duration": 123.45,
  "bpm": 120.0,
  "events": [
    { "time": 1.234, "direction": "left",  "strength": 0.8, "energy": 0.5 },
    { "time": 1.567, "direction": "down",  "strength": 0.7, "energy": 0.6 },
    { "time": 1.890, "direction": "up",    "strength": 0.9, "energy": 0.8 },
    { "time": 2.100, "direction": "right", "strength": 0.6, "energy": 0.4 }
  ]
}
```

### Campos

- **`music`**: string (nome/label)
- **`duration`**: float (segundos)
- **`bpm`**: float (pode ser 0.0; o jogo não depende estritamente dele)
- **`events`**: lista de eventos; cada evento tem:
  - **`time`**: float (segundos)
  - **`direction`**: `"left" | "down" | "up" | "right"`
  - **`strength`**: float (metadado; hoje é carregado, mas a dificuldade converte o evento para `(time, direction)`)
  - **`energy`**: float (metadado; carregado como energia local)

## Dificuldade e densidade de notas

Após carregar os eventos, o jogo aplica dificuldade em `src/music_backend/difficulty.py` (`apply_difficulty`):

- Converte eventos para `[(time, direction), ...]`
- Remove notas com base em `remove_chance` (ex.: Fácil)
- Adiciona notas com base em `add_chance` (ex.: Difícil/Expert)
- Aplica `min_gap` por direção para evitar spam

As configs por dificuldade ficam em `src/music_backend/backend_config.py` (`DIFFICULTIES`).

## Criando um beatmap manualmente (modo gravação)

O jogo tem um modo de gravação que salva automaticamente o JSON:

- Ative **ADM mode** em **Settings/Configurações**.
- Inicie uma fase fixa.
- Pressione **← ↓ ↑ →** no ritmo durante a música.
- Ao terminar, ele salva em `src/beatmap/<nome_da_musica>.json`.

O salvamento fica em `src/main.py` (`save_recorded_map`).

## Boas práticas

- **Ordene** os eventos por `time` (o loader ordena por segurança).
- Evite notas muito coladas. O `min_gap` por direção já ajuda, mas mapas muito densos podem ficar injogáveis.
- Se `duration` estiver errado ou 0, o loader tenta um fallback baseado no último evento.

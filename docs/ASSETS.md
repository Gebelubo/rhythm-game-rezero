# Assets (músicas, sprites e textura)

Este projeto depende de alguns assets em pastas específicas. Quando algum asset está ausente, o jogo tenta usar **fallbacks** (ex.: personagem vetorial, setas sem textura), mas as fases fixas precisam das músicas.

## Músicas (`musics/`)

Pasta: `musics/`

### Fases fixas

As fases 0–3 usam os paths definidos em `src/music_backend/backend_config.py` (`STAGE_MUSIC_PATHS`):

- `musics/refazer.mp3`
- `musics/entender.mp3`
- `musics/reconstruir.mp3`
- `musics/lembrar.mp3`

Para cada música, deve existir um beatmap correspondente em `src/beatmap/` com o mesmo basename (veja `docs/BEATMAPS.md`).

### Música do menu

- `musics/openingmenu.mp3`

### Música personalizada

Na fase “Personalizada” você informa o nome do arquivo dentro de `musics/`.

- Extensões aceitas (validadas em `src/main.py`): `.mp3`, `.ogg`, `.wav`, `.flac`, `.m4a`, `.opus`

## Sprites (`sprites/`)

Pasta: `sprites/`

Os packs ficam em subpastas (ex.: `sprites/sprites_1/`, `sprites/sprites_2/`, ...). O jogo escolhe o pack pelo atributo `sprites_folder` do personagem.

### Convenção de nomes

O loader `src/sprites.py` (`load_sprites`) detecta animações e frames por nomes:

- Animação com frames: `nome_0.png`, `nome_1.png`, ...
- Animação com um único arquivo: `nome.png`

Ele procura frames de `0..63` e para ao encontrar o primeiro frame ausente (sequência deve ser contínua a partir do 0).

### Animações usadas pelo jogo

Recomendado fornecer:

- **Lobby/menu**: `idle`, `left`, `right`, `up`, `down`
- **Gameplay**: `game_idle`, `game_left`, `game_right`, `game_up`, `game_down`, `game_miss`

Se uma animação não existir, o jogo tenta cair em `idle` e, se necessário, usa um **personagem vetorial** (desenhado por primitivas).

## Texturas (`texture/`)

Pasta: `texture/`

- `texture/texture_nota.png` (opcional)

Se a textura não existir ou falhar ao carregar, o jogo desenha as setas em cores sólidas automaticamente.

## Checklist rápido

- [ ] `musics/openingmenu.mp3` existe (menu)
- [ ] As músicas de fase em `musics/` existem
- [ ] Os beatmaps correspondentes em `src/beatmap/*.json` existem (fases fixas)
- [ ] O pack de sprites selecionado existe em `sprites/<pack>/` (opcional)
- [ ] `texture/texture_nota.png` (opcional)

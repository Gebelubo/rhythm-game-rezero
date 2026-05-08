# Re:Song — Rhythm Game (Computação Gráfica)

**Re:Song** é um jogo de ritmo feito em **Python + Pygame**. Você escolhe uma fase/música e acerta as setas **← ↓ ↑ →** conforme as notas caem nas 4 lanes, dentro de janelas de timing (**Perfect/Good/OK**). O projeto também tem **lobby com seleção de fases**, **dificuldades**, **resultados**, **seleção/loja de personagens (skins)** e um **modo de gravação** para gerar beatmaps.

## Rodando o jogo

### Requisitos

- **Python**: recomendado **3.10+**
- **Dependência obrigatória**: `pygame`
- **Dependências opcionais (para detecção automática de batidas em música personalizada)**: `librosa`, `numpy`

### Executar

Na raiz do repositório:

```bash
python -m run
```

ou 

```bash
python3 run.py
```

O entrypoint `run.py` instancia `RhythmGame` em `src/main.py`.

## Vídeos de documentação

[![Visão geral (Re:Song)](https://img.youtube.com/vi/CzqVb_gcgOo/hqdefault.jpg)](https://youtu.be/CzqVb_gcgOo)

[![Como rodar (Re:Song)](https://img.youtube.com/vi/SHFaxm7ecAQ/hqdefault.jpg)](https://youtu.be/SHFaxm7ecAQ)

[![Customização (Re:Song)](https://img.youtube.com/vi/O4iYjhTcY0A/hqdefault.jpg)](https://youtu.be/O4iYjhTcY0A)

## Controles

- **Gameplay**: **← ↓ ↑ →** (setas do teclado)
- **Lobby** (mapa do mundo):
  - mover: **WASD** ou **setas**
  - interagir/confirmar: **ENTER**
  - voltar: **ESC**
- **Menu / telas**: navegação varia (teclado e mouse são suportados)

## Fases e dificuldades

### Fases “fixas”

As fases 0–3 usam músicas e beatmaps pré-definidos:

- `musics/refazer.mp3` → `src/beatmap/refazer.json`
- `musics/entender.mp3` → `src/beatmap/entender.json`
- `musics/reconstruir.mp3` → `src/beatmap/reconstruir.json`
- `musics/lembrar.mp3` → `src/beatmap/lembrar.json`

Os paths das músicas estão em `src/music_backend/backend_config.py` (`STAGE_MUSIC_PATHS`).

### Dificuldades

As dificuldades disponíveis são:

- **Fácil**
- **Normal**
- **Difícil**
- **Expert**

Elas ajustam a densidade do mapa (removendo/adicionando notas e aplicando `min_gap`). Configuração em `src/music_backend/backend_config.py` (`DIFFICULTIES`) e lógica em `src/music_backend/difficulty.py` (`apply_difficulty`).

## Música personalizada (fase “Personalizada”)

No lobby, existe uma fase “**Personalizada**”. Ao selecioná-la, você pode digitar o **nome do arquivo** que está dentro de `musics/` (ex.: `minha_musica.mp3`) e apertar **ENTER**.

- **Formatos aceitos**: `.mp3`, `.ogg`, `.wav`, `.flac`, `.m4a`, `.opus`
- Se `librosa`/`numpy` estiverem instalados, o jogo tenta **detectar batidas**.
- Se não estiverem, o jogo usa um **fallback** (um padrão sintético) — ainda dá para jogar.

## Modo gravação de beatmap (ADM)

O projeto tem um modo para **gravar um beatmap manualmente**: você toca a música e pressiona **← ↓ ↑ →** no ritmo; no fim, o jogo salva um JSON em `src/beatmap/<nome_da_musica>.json`.

Como usar:

- Abra **Settings/Configurações** no menu e ative **ADM mode**.
- No lobby, selecione uma das fases fixas e inicie normalmente.
- No modo gravação:
  - **← ↓ ↑ →**: grava eventos
  - **ESC**: cancela
  - Ao terminar a música, salva automaticamente em `src/beatmap/`.

> Dica: o nome do beatmap é derivado do basename do arquivo de música (ex.: `musics/entender.mp3` → `src/beatmap/entender.json`).

## Assets (músicas, sprites e textura)

### Músicas

- Pasta: `musics/`
- Necessárias para as fases fixas e para o menu (ex.: `openingmenu.mp3`)

### Sprites de personagem (skins)

Os packs ficam em `sprites/` (ex.: `sprites/sprites_1/`, `sprites/sprites_2/`, ...).

O loader (`src/sprites.py`) reconhece animações por arquivos no formato:

- `idle_0.png`, `idle_1.png`, ...
- `game_left_0.png`, `game_left_1.png`, ...
- (também aceita arquivo único como `idle.png`)

Animações que o jogo tenta usar com frequência:

- Lobby/menu: `idle`, `left`, `right`, `up`, `down`
- Gameplay: `game_idle`, `game_left`, `game_right`, `game_up`, `game_down`, `game_miss`

Se o sprite não existir, o jogo usa um **fallback vetorial** (desenha o personagem com primitivas).

### Textura da nota (opcional)

Se existir `texture/texture_nota.png`, ela pode ser usada no desenho das setas. Se faltar, o jogo renderiza setas sólidas automaticamente.

## Estrutura do projeto (visão rápida)

- **Entrypoint**: `run.py`
- **Loop/estado do jogo**: `src/main.py` (`RhythmGame`)
- **Config (resolução, timing windows, teclas)**: `src/config.py`
- **Telas**: `src/screens/` (`menu.py`, `lobby.py`, `playing.py`)
- **Backend de música/beatmaps**: `src/music_backend/`
- **Sprites**: `src/sprites.py`
- **Render/UI**: `src/utils/`
- **Primitivas de CG (disciplina)**: `src/funcs/cg_lib.py`

## Documentação detalhada

Para detalhes de formato e manutenção:

- `docs/BEATMAPS.md` — schema do JSON, como criar/validar beatmaps e dicas de sincronização
- `docs/ASSETS.md` — convenções de arquivos (músicas, sprites, textura) e checklist
- `docs/ARCHITECTURE.md` — arquitetura do loop, estados e responsabilidades dos módulos
- `docs/REQUIREMENTS_MAP.md` — mapeamento dos requisitos da disciplina (CG) → arquivos e linhas do código

## Troubleshooting (problemas comuns)

- **`ModuleNotFoundError: pygame`**: instale `pygame` no seu ambiente Python.
- **Erro ao inicializar áudio (mixer)**: em Linux, pode ajudar testar `SDL_AUDIODRIVER=pulse` ou `SDL_AUDIODRIVER=alsa` (ou `dummy` para rodar sem som).
- **Música/beatmap não encontrado**: confira se o arquivo existe em `musics/` e, para fases fixas, se existe o JSON correspondente em `src/beatmap/`.

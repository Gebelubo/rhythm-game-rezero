# Arquitetura (visão técnica)

Este documento descreve como o Re:Song está organizado: loop principal, estados e responsabilidades dos módulos.

## Entrypoint

- `run.py`: instancia `RhythmGame` e chama `run()`.
- `src/main.py`: contém a classe `RhythmGame`, que centraliza o loop principal e o gerenciamento de estados.

## Estados do jogo

O jogo usa uma máquina de estados simples (string em `self.state`) dentro de `RhythmGame.run()`:

- `splash`
- `menu`
- `lobby`
- `tutorial`
- `settings`
- `playing`
- `results`
- `recording` (modo gravação de beatmap)
- `character_select`
- `shop`

Cada estado:

- consome eventos do Pygame (teclado/mouse)
- atualiza o estado do jogo
- desenha a tela correspondente

## Telas (`src/screens/`)

- `src/screens/menu.py`: desenho e interação do menu principal, tutorial, settings, seleção de personagem e shop.
- `src/screens/lobby.py`: “mundo”/mapa com movimentação, seleção de fases e botões de dificuldade.
- `src/screens/playing.py`: lógica de update/draw do gameplay e tela de resultados.

## Backend de música e notas (`src/music_backend/`)

- `utils.py`
  - `detect_beats(path)`: detecção de batidas (usa `librosa`/`numpy` se existirem; caso contrário, fallback).
  - `load_beatmap(path)`: carrega `src/beatmap/<basename>.json` para fases fixas.
  - `calc_acc(game)`, `calc_reward(acc, difficulty)`: cálculo de precisão e recompensa (moeda).
- `difficulty.py`
  - `apply_difficulty(raw_events, duration, diff_name)`: ajusta a densidade de notas.
- `note.py`
  - `Note`: representa uma nota e sua posição ao longo do tempo (`FALL_TIME` em `src/config.py`).
- `backend_config.py`
  - dificuldades, cores, paths de músicas e mapeamento de bandas de frequência → direção.

## Render/UI

- `src/utils/render.py`: superfícies pré-bake (background e setas) e desenho com/sem textura.
- `src/utils/ui.py` e `src/utils/fonts.py`: UI “pixel font”, botões e HUD (inclui moeda).

## Sprites / personagens

- `src/entities/char.py`: entidade `Character(name, sprites_folder)`.
- `src/sprites.py`: loader de sprites e `draw_char` (com cache de resize e fallback vetorial).

## Primitivas de CG (`src/funcs/cg_lib.py`)

Implementa rotinas típicas de computação gráfica (ex.: Bresenham, scanline fill, viewport/window, clipping etc.) e é reutilizada por telas e render helpers.

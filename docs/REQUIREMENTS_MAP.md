# Mapeamento dos requisitos (CG) → código

Este documento aponta **onde** cada requisito do trabalho está implementado no código, com **arquivo + linhas**.

> Convenção: quando fizer sentido, eu separo **Implementação (biblioteca CG)** vs **Uso no jogo (telas/loop)**.

## Abertura (splash) com reta + circunferência + elipse e preenchimento

- **Splash screen** (usa **reta (Bresenham)**, **círculo (midpoint)**, **elipse (midpoint)** e preenche com **Flood Fill** e **Boundary Fill**)  
  - `src/screens/menu.py` **L17–L106**

## a) Set Pixel

- **Implementação**
  - `src/funcs/cg_lib.py` **L10–L20** (`set_pixel`, `get_pixel`)

- **Uso (exemplos)**
  - `src/utils/ui.py` **L8–L62** (texto “pixel font” desenhado com `set_pixel`)
  - `src/screens/menu.py` **L122–L136** (desenha fundo a partir de imagem usando `set_pixel`)

## b) Primitivas de rasterização (Linha, Círculo e Elipse)

- **Implementação**
  - **Linha (Bresenham)**: `src/funcs/cg_lib.py` **L27–L45** (`line_bresenham`)
  - **Círculo (ponto médio)**: `src/funcs/cg_lib.py` **L73–L95** (`circle_midpoint`)
  - **Elipse (ponto médio)**: `src/funcs/cg_lib.py` **L97–L138** (`ellipse_midpoint`)

- **Uso (exemplos)**
  - Splash: `src/screens/menu.py` **L17–L106**
  - UI/menus (múltiplas telas): `src/screens/menu.py` (várias ocorrências; ex.: bordas e decorações)

## c) Preenchimento de regiões (Flood Fill / Boundary Fill e Scanline)

- **Implementação**
  - **Flood Fill**: `src/funcs/cg_lib.py` **L144–L165**
  - **Boundary Fill**: `src/funcs/cg_lib.py` **L167–L187**
  - **Scanline Fill**: `src/funcs/cg_lib.py` **L208–L230**

- **Uso (exemplos)**
  - Flood/Boundary: splash e menu art em `src/screens/menu.py` **L17–L106** e **L176–L223**
  - Scanline (polígonos/retângulos UI): `src/utils/ui.py` **L64–L76** e `src/screens/playing.py` **L80–L98**, **L147–L156**, **L190–L196**
  - Scanline (setas/notas como polígonos): `src/utils/render.py` **L61–L96** (`scanline_fill` em `bake_arrow_surf`)

## d) Transformações geométricas (Rotação, Translação e Escala)

- **Implementação**
  - **Translação**: `src/funcs/cg_lib.py` **L245–L247** (`translate`)
  - **Escala**: `src/funcs/cg_lib.py` **L250–L255** (`scale`)
  - **Rotação**: `src/funcs/cg_lib.py` **L258–L269** (`rotate`)

- **Uso (exemplos)**
  - **Elemento com transformações animadas** (escala + rotação + translação num polígono preenchido por scanline):
    - `src/screens/menu.py` **L666–L724**
  - **Rotação do polígono da seta** (setas em `bake_arrow_surf`):
    - `src/utils/render.py` **L61–L96** (chama `rotate(...)` em **L75–L77**)

## e) Animação 2D

- **Splash com fade-in/hold/fade-out** (animação por tempo):
  - `src/main.py` **L509–L534** (evolução de `splash_alpha` e transição de estado)

- **Animação por frames do personagem (gameplay)**
  - `src/screens/playing.py` **L43–L48** (avança `char_frame` no tempo)

- **Animação por frames do personagem (lobby)**
  - `src/screens/lobby.py` **L565–L571** (avança frame conforme movimento/tempo)

- **Animação via transformações (ex.: diamante “flutuando”)**
  - `src/screens/menu.py` **L666–L724**

## f) Janela e Viewport (mapeamento mundo → dispositivo) + translação/escala (zoom)

- **Implementação (Window/Viewport + mapeamento)**
  - `src/funcs/cg_lib.py` **L286–L324**
    - `Window` (L286–L293)
    - `Viewport` (L295–L302)
    - `world_to_viewport` (L304–L310) — inclui o **fator de escala** \(sx, sy\)
    - `draw_line_viewport` / `draw_polygon_viewport` (L313–L324)

- **Uso (exemplo: minimapa com viewport)**
  - `src/screens/lobby.py` **L655–L686**
    - cria `Window(...)` e `Viewport(...)` (L661–L662)
    - desenha eixos e marcadores mapeados (L664–L677)

> Observação: “zoom” pode ser obtido alterando dinamicamente os limites da `Window` (ex.: reduzir/ampliar `x_min/x_max/y_min/y_max`). No código atual, o mapeamento com escala está implementado e usado; o ajuste dinâmico de zoom não aparece como interação explícita.

## g) Recorte de Cohen‑Sutherland (clipping)

- **Implementação**
  - `src/funcs/cg_lib.py` **L330–L391**
    - `cohen_sutherland_clip` (L350–L384)
    - helper `draw_line_clipped` (L386–L391)

> Observação: aqui está a implementação completa; se você quiser, dá para integrar o `draw_line_clipped` em algum elemento visual (ex.: HUD/minimapa) para ficar “visivelmente” demonstrado durante a execução.

## h) Mapeamento de textura

- **Implementação (retângulo e triângulo)**
  - `src/funcs/cg_lib.py` **L397–L450**
    - `texture_map_rect` (L402–L416)
    - `texture_map_triangle` (L418–L450)

- **Uso no jogo (textura aplicada em polígonos das setas)**
  - `src/utils/render.py` **L22–L96**
    - carrega e escala `texture/texture_nota.png` (L22–L35)
    - aplica textura por triângulos (fan) via `texture_map_triangle` (L78–L91)
    - faz overlay de cor com `scanline_fill` (L89–L91)

## i) Input (teclado e/ou mouse) + menu interativo

- **Mapa de teclas do gameplay (setas)**
  - `src/config.py` **L15–L21** (`KEY_MAP`)

- **Loop principal e estados com input de teclado/mouse**
  - `src/main.py` **L501–L707** (e continua abaixo; menu/settings/playing/results/recording etc.)
    - Splash: “qualquer tecla/clique pula” (L527–L531)
    - Menu: teclado + mouse (L549–L591)
    - Settings: mouse (L619–L636)
    - Playing: teclado (L639–L647)
    - Results: teclado + mouse (L654–L676)
    - Recording: teclado (L679–L689)

- **Lobby com teclado (movimento/seleção) e entrada de texto**
  - `src/screens/lobby.py` **L489–L563** (movimento e seleção)  
  - `src/screens/lobby.py` **L547–L555** (fase personalizada: BACKSPACE e `ev.unicode` para digitar)

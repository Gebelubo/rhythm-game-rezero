import math
import pygame
 
# a) SET PIXEL

 
def set_pixel(surface: pygame.Surface, x: int, y: int, color: tuple) -> None:
    # Escreve um pixel diretamente no frame buffer
    x, y = int(round(x)), int(round(y))
    if 0 <= x < surface.get_width() and 0 <= y < surface.get_height():
        surface.set_at((x, y), color)
 
 
def get_pixel(surface: pygame.Surface, x: int, y: int) -> tuple:
    # Lê a cor de um pixel do frame buffer
    x, y = int(round(x)), int(round(y))
    if 0 <= x < surface.get_width() and 0 <= y < surface.get_height():
        return surface.get_at((x, y))[:3]
    return (-1, -1, -1)
 
 
# b) PRIMITIVAS DE RASTERIZAÇÃO
 
def line_bresenham(surface: pygame.Surface,
                   x0: int, y0: int, x1: int, y1: int,
                   color: tuple) -> None:
    # Rasteriza um segmento de reta usando o algoritmo de Bresenham, funciona para qualquer octante
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
 
    while True:
        set_pixel(surface, x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
 
 
def _plot8(surface, xc, yc, x, y, color):
    # Plota os 8 pontos simétricos de um círculo
    for px, py in [
        (xc + x, yc + y), (xc - x, yc + y),
        (xc + x, yc - y), (xc - x, yc - y),
        (xc + y, yc + x), (xc - y, yc + x),
        (xc + y, yc - x), (xc - y, yc - x),
    ]:
        set_pixel(surface, px, py, color)
 
 
def circle_midpoint(surface: pygame.Surface,
                    xc: int, yc: int, r: int,
                    color: tuple) -> None:
    # Rasteriza uma circunferência usando o algoritmo do Ponto Médio, explora a simetria de 8 octantes
    x, y = 0, r
    d = 1 - r
    _plot8(surface, xc, yc, x, y, color)
    while x < y:
        if d < 0:
            d += 2 * x + 3
        else:
            d += 2 * (x - y) + 5
            y -= 1
        x += 1
        _plot8(surface, xc, yc, x, y, color)
 
 
def ellipse_midpoint(surface: pygame.Surface,
                     xc: int, yc: int,
                     a: int, b: int,
                     color: tuple) -> None:
    # Rasteriza uma elipse usando o algoritmo do Ponto Médio
    # Divide o cálculo em duas regiões (região 1: |slope| < 1; região 2: |slope| > 1).
    a2, b2 = a * a, b * b
    x, y = 0, b
 
    # Região 1
    d1 = b2 - a2 * b + 0.25 * a2
    dx = 2 * b2 * x
    dy = 2 * a2 * y
 
    def plot4(x, y):
        for px, py in [(xc + x, yc + y), (xc - x, yc + y),
                       (xc + x, yc - y), (xc - x, yc - y)]:
            set_pixel(surface, px, py, color)
 
    while dx < dy:
        plot4(x, y)
        if d1 < 0:
            x += 1
            dx += 2 * b2
            d1 += dx + b2
        else:
            x += 1
            y -= 1
            dx += 2 * b2
            dy -= 2 * a2
            d1 += dx - dy + b2
 
    # Região 2
    d2 = b2 * (x + 0.5) ** 2 + a2 * (y - 1) ** 2 - a2 * b2
    while y >= 0:
        plot4(x, y)
        if d2 > 0:
            y -= 1
            dy -= 2 * a2
            d2 += a2 - dy
        else:
            y -= 1
            x += 1
            dx += 2 * b2
            dy -= 2 * a2
            d2 += dx - dy + a2
 

# c) PREENCHIMENTO DE REGIÕES
 
def boundary_fill(surface: pygame.Surface,
                  x: int, y: int,
                  fill_color: tuple,
                  border_color: tuple) -> None:
    # Preenchimento por fronteira (Boundary Fill) iterativo (pilha manual)
    # Começa na semente (x, y) e pinta vizinhos 4-conectados até encontrar a cor de borda
    x, y = int(round(x)), int(round(y))
    w, h = surface.get_width(), surface.get_height()
    stack = [(x, y)]
    visited = set()
 
    while stack:
        cx, cy = stack.pop()
        if (cx, cy) in visited:
            continue
        if not (0 <= cx < w and 0 <= cy < h):
            continue
        cur = surface.get_at((cx, cy))[:3]
        if cur == border_color or cur == fill_color:
            continue
        visited.add((cx, cy))
        set_pixel(surface, cx, cy, fill_color)
        stack.extend([(cx + 1, cy), (cx - 1, cy),
                      (cx, cy + 1), (cx, cy - 1)])
 
 
def flood_fill(surface: pygame.Surface,
               x: int, y: int,
               fill_color: tuple) -> None:
    # Flood Fill iterativo: substitui a cor original do ponto semente por fill_color em toda a região 4-conectada de mesma cor
    
    x, y = int(round(x)), int(round(y))
    w, h = surface.get_width(), surface.get_height()
    if not (0 <= x < w and 0 <= y < h):
        return
    target_color = surface.get_at((x, y))[:3]
    if target_color == fill_color:
        return
    stack = [(x, y)]
    visited = set()
 
    while stack:
        cx, cy = stack.pop()
        if (cx, cy) in visited:
            continue
        if not (0 <= cx < w and 0 <= cy < h):
            continue
        if surface.get_at((cx, cy))[:3] != target_color:
            continue
        visited.add((cx, cy))
        set_pixel(surface, cx, cy, fill_color)
        stack.extend([(cx + 1, cy), (cx - 1, cy),
                      (cx, cy + 1), (cx, cy - 1)])
 
 
def _build_edge_table(vertices: list) -> dict:
    # Monta a Edge Table (ET) para o algoritmo Scanline, retorna dict: {y_min: [(y_max, x_at_ymin, 1/m), ...]}

    et = {}
    n = len(vertices)
    for i in range(n):
        x0, y0 = vertices[i]
        x1, y1 = vertices[(i + 1) % n]
        if y0 == y1: # aresta horizontal: ignorar
            continue
        if y0 > y1: # garante y0 < y1
            x0, y0, x1, y1 = x1, y1, x0, y0
        inv_m = (x1 - x0) / (y1 - y0)
        et.setdefault(int(math.ceil(y0)), []).append(
            [int(math.ceil(y1)), x0 + inv_m * (math.ceil(y0) - y0), inv_m]
        )
    return et
 
 
def scanline_fill(surface: pygame.Surface,
                  vertices: list,
                  color: tuple) -> None:
    # Preenche um polígono convexo ou côncavo usando Scanline (varredura), vértices: lista de tuplas (x, y).
    if len(vertices) < 3:
        return
    et = _build_edge_table(vertices)
    if not et:
        return
 
    y_min = min(et.keys())
    y_max = max(int(math.ceil(v[1])) for v in vertices)
 
    active = []  # Active Edge Table
 
    for y in range(y_min, y_max):
        # Adiciona novas arestas
        if y in et:
            active.extend(et[y])
 
        # Remove arestas com y_max <= y
        active = [e for e in active if e[0] > y]
 
        # Ordena por X atual
        active.sort(key=lambda e: e[1])
 
        # Pinta pixels entre pares
        for i in range(0, len(active) - 1, 2):
            x_start = int(math.ceil(active[i][1]))
            x_end   = int(math.floor(active[i + 1][1]))
            for x in range(x_start, x_end + 1):
                set_pixel(surface, x, y, color)
 
        # Avança X de cada aresta
        for e in active:
            e[1] += e[2]
 
 
def scanline_fill_gradient(surface: pygame.Surface,
                           vertices: list,
                           colors: list) -> None:
   # Scanline com interpolação de cor por vértice (gradiente Gouraud simplificado)
   # vértices: [(x, y), ...]   colors: [(r, g, b), ...]  (mesma ordem)

    if len(vertices) < 3:
        return
 
    n = len(vertices)
 
    # Determina y_min e y_max
    ys = [v[1] for v in vertices]
    y_min = int(math.ceil(min(ys)))
    y_max = int(math.floor(max(ys)))
 
    for y in range(y_min, y_max + 1):
        # Encontra interseções com arestas + interpola cor
        intersections = []
        for i in range(n):
            x0, y0 = vertices[i]
            x1, y1 = vertices[(i + 1) % n]
            c0 = colors[i]
            c1 = colors[(i + 1) % n]
            if y0 == y1:
                continue
            if not (min(y0, y1) <= y < max(y0, y1)):
                continue
            t = (y - y0) / (y1 - y0)
            xi = x0 + t * (x1 - x0)
            ci = tuple(int(c0[k] + t * (c1[k] - c0[k])) for k in range(3))
            intersections.append((xi, ci))
 
        intersections.sort(key=lambda p: p[0])
 
        for i in range(0, len(intersections) - 1, 2):
            x_left,  c_left  = intersections[i]
            x_right, c_right = intersections[i + 1]
            x_start = int(math.ceil(x_left))
            x_end   = int(math.floor(x_right))
            span = x_right - x_left
            for x in range(x_start, x_end + 1):
                t = (x - x_left) / span if span != 0 else 0
                c = tuple(int(c_left[k] + t * (c_right[k] - c_left[k])) for k in range(3))
                set_pixel(surface, x, y, c)
 
 
def scanline_fill_texture(surface: pygame.Surface,
                          vertices: list,
                          uv_coords: list,
                          texture: pygame.Surface) -> None:

    # Scanline com mapeamento de textura por interpolação de coordenadas UV
    # vertices: [(x, y), ...]   em coordenadas de tela
    # uv_coords: [(u, v), ...]   em [0,1] x [0,1]
    # texture: pygame.Surface carregada (use pygame.image.load)
   
    if len(vertices) < 3:
        return
 
    tw, th = texture.get_width(), texture.get_height()
    n = len(vertices)
    ys = [v[1] for v in vertices]
    y_min = int(math.ceil(min(ys)))
    y_max = int(math.floor(max(ys)))
 
    for y in range(y_min, y_max + 1):
        intersections = []
        for i in range(n):
            x0, y0 = vertices[i]
            x1, y1 = vertices[(i + 1) % n]
            u0, v0 = uv_coords[i]
            u1, v1 = uv_coords[(i + 1) % n]
            if y0 == y1:
                continue
            if not (min(y0, y1) <= y < max(y0, y1)):
                continue
            t  = (y - y0) / (y1 - y0)
            xi = x0 + t * (x1 - x0)
            ui = u0 + t * (u1 - u0)
            vi = v0 + t * (v1 - v0)
            intersections.append((xi, ui, vi))
 
        intersections.sort(key=lambda p: p[0])
 
        for i in range(0, len(intersections) - 1, 2):
            x_left,  u_left,  v_left  = intersections[i]
            x_right, u_right, v_right = intersections[i + 1]
            x_start = int(math.ceil(x_left))
            x_end   = int(math.floor(x_right))
            span = x_right - x_left
            for x in range(x_start, x_end + 1):
                t  = (x - x_left) / span if span != 0 else 0
                u  = u_left + t * (u_right - u_left)
                v  = v_left + t * (v_right - v_left)
                tx = int(u * (tw - 1)) % tw
                ty = int(v * (th - 1)) % th
                c  = texture.get_at((tx, ty))[:3]
                set_pixel(surface, x, y, c)
 
 

# d) TRANSFORMAÇÕES GEOMÉTRICAS (coordenadas homogêneas 3×3)
 
def mat_mul(A: list, B: list) -> list:
    # Multiplica duas matrizes 3×3
    return [
        [sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)]
        for i in range(3)
    ]
 
 
def mat_vec(M: list, x: float, y: float) -> tuple:
    # Aplica a matriz 3×3 M ao ponto homogêneo (x, y, 1)
    xp = M[0][0] * x + M[0][1] * y + M[0][2]
    yp = M[1][0] * x + M[1][1] * y + M[1][2]
    w  = M[2][0] * x + M[2][1] * y + M[2][2]
    if w != 0:
        return xp / w, yp / w
    return xp, yp
 
 
def translation(tx: float, ty: float) -> list:
    return [[1, 0, tx],
            [0, 1, ty],
            [0, 0,  1]]
 
 
def scaling(sx: float, sy: float) -> list:
    return [[sx,  0, 0],
            [ 0, sy, 0],
            [ 0,  0, 1]]
 
 
def rotation(theta: float) -> list:
    c, s = math.cos(theta), math.sin(theta)
    return [[ c, -s, 0],
            [ s,  c, 0],
            [ 0,  0, 1]]
 
 
def rotation_around(theta: float, cx: float, cy: float) -> list:
    # Rotação em torno do ponto (cx, cy)
    T1 = translation(-cx, -cy)
    R  = rotation(theta)
    T2 = translation(cx, cy)
    return mat_mul(T2, mat_mul(R, T1))
 
 
def apply_transform(M: list, vertices: list) -> list:
    # Aplica a matriz M a uma lista de vértices (x, y)
    return [mat_vec(M, x, y) for x, y in vertices]
 
 
# f) JANELA E VIEWPORT
 
class Window:
    # Define a janela de visualização no espaço do mundo.
    # Permite translação (pan) e escala (zoom).

    def __init__(self, x_min: float, y_min: float,
                 x_max: float, y_max: float):
        self.x_min = x_min
        self.y_min = y_min
        self.x_max = x_max
        self.y_max = y_max
 
    def pan(self, dx: float, dy: float) -> None:
        self.x_min += dx; self.x_max += dx
        self.y_min += dy; self.y_max += dy
 
    def zoom(self, factor: float,
             cx: float = None, cy: float = None) -> None:
        # Zoom centrado em (cx, cy). Se None, usa o centro da janela
        if cx is None:
            cx = (self.x_min + self.x_max) / 2
        if cy is None:
            cy = (self.y_min + self.y_max) / 2
        hw = (self.x_max - self.x_min) / 2 / factor
        hh = (self.y_max - self.y_min) / 2 / factor
        self.x_min = cx - hw; self.x_max = cx + hw
        self.y_min = cy - hh; self.y_max = cy + hh
 
 
class Viewport:
    # Define a viewport em coordenadas de dispositivo (pixels).
    def __init__(self, u_min: int, v_min: int,
                 u_max: int, v_max: int):
        self.u_min = u_min
        self.v_min = v_min
        self.u_max = u_max
        self.v_max = v_max
 
 
def world_to_viewport(x: float, y: float,
                      win: Window, vp: Viewport) -> tuple:
    # Mapeia (x, y) do espaço do mundo para coordenadas de dispositivo
    # Dentro da viewport, com y invertido (origem no topo na tela)

    u = vp.u_min + (x - win.x_min) / (win.x_max - win.x_min) * (vp.u_max - vp.u_min)
    v = vp.v_max - (y - win.y_min) / (win.y_max - win.y_min) * (vp.v_max - vp.v_min)
    return u, v
 
 
def world_to_viewport_transform(win: Window, vp: Viewport) -> list:

    # Retorna a matriz 3×3 de transformação Mundo→Viewport (composição)
    # Equivalente a: T(vp.u_min, vp.v_max) · S(sx, -sy) · T(-win.x_min, -win.y_min)
    
    sx = (vp.u_max - vp.u_min) / (win.x_max - win.x_min)
    sy = (vp.v_max - vp.v_min) / (win.y_max - win.y_min)
    T1 = translation(-win.x_min, -win.y_min)
    S  = scaling(sx, -sy) # y negativo: invertemos o eixo
    T2 = translation(vp.u_min, vp.v_max)
    return mat_mul(T2, mat_mul(S, T1))
 
 
def apply_viewport_transform(vertices: list,
                              win: Window,
                              vp: Viewport) -> list:
    # Transforma uma lista de vértices do mundo para a viewport
    M = world_to_viewport_transform(win, vp)
    return apply_transform(M, vertices)
 

# g) RECORTE DE COHEN-SUTHERLAND
 
# Códigos de região
_CS_INSIDE = 0b0000
_CS_LEFT   = 0b0001
_CS_RIGHT  = 0b0010
_CS_BOTTOM = 0b0100  # y < y_min  (eixo y positivo para cima no mundo)
_CS_TOP    = 0b1000  # y > y_max
 
 
def _compute_code(x: float, y: float,
                  x_min: float, y_min: float,
                  x_max: float, y_max: float) -> int:
    code = _CS_INSIDE
    if x < x_min:
        code |= _CS_LEFT
    elif x > x_max:
        code |= _CS_RIGHT
    if y < y_min:
        code |= _CS_BOTTOM
    elif y > y_max:
        code |= _CS_TOP
    return code
 
 
def cohen_sutherland(x0: float, y0: float,
                     x1: float, y1: float,
                     x_min: float, y_min: float,
                     x_max: float, y_max: float
                     ) -> tuple:

    # Recorta o segmento (x0,y0)-(x1,y1) pela janela [x_min,x_max]×[y_min,y_max].
    # Retorna (x0, y0, x1, y1, accepted: bool).
   
    code0 = _compute_code(x0, y0, x_min, y_min, x_max, y_max)
    code1 = _compute_code(x1, y1, x_min, y_min, x_max, y_max)
 
    while True:
        if not (code0 | code1): # ambos dentro → aceita
            return x0, y0, x1, y1, True
        if code0 & code1: # ambos fora do mesmo lado → rejeita
            return x0, y0, x1, y1, False
 
        # Escolhe um ponto exterior
        code_out = code0 if code0 else code1
 
        # Calcula interseção
        dx = x1 - x0
        dy = y1 - y0
        if code_out & _CS_TOP:
            x = x0 + dx * (y_max - y0) / dy
            y = y_max
        elif code_out & _CS_BOTTOM:
            x = x0 + dx * (y_min - y0) / dy
            y = y_min
        elif code_out & _CS_RIGHT:
            y = y0 + dy * (x_max - x0) / dx
            x = x_max
        else:  # LEFT
            y = y0 + dy * (x_min - x0) / dx
            x = x_min
 
        if code_out == code0:
            x0, y0 = x, y
            code0 = _compute_code(x0, y0, x_min, y_min, x_max, y_max)
        else:
            x1, y1 = x, y
            code1 = _compute_code(x1, y1, x_min, y_min, x_max, y_max)
 
 
def draw_line_clipped(surface: pygame.Surface,
                      x0: float, y0: float,
                      x1: float, y1: float,
                      win: Window,
                      vp: Viewport,
                      color: tuple) -> None:
 
    # Recorta a linha pelo Cohen-Sutherland, converte para viewport e rasteriza com Bresenham.
    
    rx0, ry0, rx1, ry1, accepted = cohen_sutherland(
        x0, y0, x1, y1,
        win.x_min, win.y_min, win.x_max, win.y_max
    )
    if not accepted:
        return
    ux0, vy0 = world_to_viewport(rx0, ry0, win, vp)
    ux1, vy1 = world_to_viewport(rx1, ry1, win, vp)
    line_bresenham(surface,
                   int(round(ux0)), int(round(vy0)),
                   int(round(ux1)), int(round(vy1)),
                   color)
 
 
# h) MAPEAMENTO DE TEXTURA E GRADIENTE  (ver scanline acima)
 
def load_texture(path: str) -> pygame.Surface:
    # Carrega uma imagem como textura (Surface do Pygame)
    return pygame.image.load(path).convert()
 
 
# i) INPUT — Helpers de teclado e mouse
 
def key_held(key: int) -> bool:
    # Retorna True se a tecla estiver sendo pressionada no frame atual
    return pygame.key.get_pressed()[key]
 
 
def mouse_pos() -> tuple:
    # Retorna (x, y) do cursor do mouse
    return pygame.mouse.get_pos()
 
 
def mouse_button(btn: int = 1) -> bool:
    # Retorna True se o botão do mouse estiver pressionado
    return pygame.mouse.get_pressed()[btn - 1]
 

# j) MENU INTERATIVO — Picking por Bounding Box

 
class Button:
    # Botão simples desenhado com primitivas próprias.
    # Usa Bresenham para a borda e set_pixel para o preenchimento.
    
    def __init__(self, x: int, y: int, w: int, h: int,
                 label: str,
                 bg_color:     tuple = (40,  40,  80),
                 hover_color:  tuple = (70,  70, 140),
                 border_color: tuple = (120, 120, 255),
                 text_color:   tuple = (255, 255, 255),
                 font: pygame.font.Font = None):
        self.rect   = pygame.Rect(x, y, w, h)
        self.label  = label
        self.bg     = bg_color
        self.hover  = hover_color
        self.border = border_color
        self.text_c = text_color
        self.font   = font or pygame.font.SysFont("monospace", 18)
        self._hovered = False
 
    def _fill_rect(self, surface: pygame.Surface, color: tuple) -> None:
        # Preenche o retângulo do botão pixel a pixel
        x0, y0 = self.rect.topleft
        for y in range(self.rect.height):
            for x in range(self.rect.width):
                set_pixel(surface, x0 + x, y0 + y, color)
 
    def _draw_border(self, surface: pygame.Surface) -> None:
        # Desenha a borda do botão com Bresenham
        x0, y0 = self.rect.left,  self.rect.top
        x1, y1 = self.rect.right - 1, self.rect.bottom - 1
        line_bresenham(surface, x0, y0, x1, y0, self.border)
        line_bresenham(surface, x1, y0, x1, y1, self.border)
        line_bresenham(surface, x1, y1, x0, y1, self.border)
        line_bresenham(surface, x0, y1, x0, y0, self.border)
 
    def update(self, events: list) -> bool:
       # Atualiza o estado hover e retorna True se o botão foi clicado.

        mx, my = pygame.mouse.get_pos()
        self._hovered = self.rect.collidepoint(mx, my)
        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self.rect.collidepoint(ev.pos):
                    return True
        return False
 
    def draw(self, surface: pygame.Surface) -> None:
        color = self.hover if self._hovered else self.bg
        self._fill_rect(surface, color)
        self._draw_border(surface)
        # Texto via Pygame (apenas renderização de bitmap; não é "desenho")
        txt = self.font.render(self.label, True, self.text_c)
        tw, th = txt.get_size()
        tx = self.rect.x + (self.rect.width  - tw) // 2
        ty = self.rect.y + (self.rect.height - th) // 2
        surface.blit(txt, (tx, ty))
 
 
class Menu:
    # Menu vertical de botões com picking por bounding box.
    def __init__(self, x: int, y: int, w: int,
                 items: list,
                 gap: int = 8,
                 font: pygame.font.Font = None):
        self.buttons: list[Button] = []
        self.callbacks: dict[str, callable] = {}
        btn_h = 40
        for i, (label, callback) in enumerate(items):
            b = Button(x, y + i * (btn_h + gap), w, btn_h,
                       label, font=font)
            self.buttons.append(b)
            self.callbacks[label] = callback
 
    def update(self, events: list) -> None:
        for b in self.buttons:
            if b.update(events):
                fn = self.callbacks.get(b.label)
                if fn:
                    fn()
 
    def draw(self, surface: pygame.Surface) -> None:
        for b in self.buttons:
            b.draw(surface)
 
 
# UTILITÁRIOS GERAIS
 
def draw_polygon(surface: pygame.Surface,
                 vertices: list,
                 color: tuple) -> None:
    # Desenha o contorno de um polígono com Bresenham
    n = len(vertices)
    for i in range(n):
        x0, y0 = vertices[i]
        x1, y1 = vertices[(i + 1) % n]
        line_bresenham(surface,
                       int(round(x0)), int(round(y0)),
                       int(round(x1)), int(round(y1)),
                       color)
 
 
def draw_polygon_world(surface: pygame.Surface,
                       vertices: list,
                       win: Window,
                       vp: Viewport,
                       color: tuple,
                       clip: bool = True) -> None:

    # Desenha o contorno de um polígono no espaço do mundo com recorte opcional por Cohen-Sutherland.
    
    n = len(vertices)
    for i in range(n):
        x0, y0 = vertices[i]
        x1, y1 = vertices[(i + 1) % n]
        if clip:
            draw_line_clipped(surface, x0, y0, x1, y1, win, vp, color)
        else:
            ux0, vy0 = world_to_viewport(x0, y0, win, vp)
            ux1, vy1 = world_to_viewport(x1, y1, win, vp)
            line_bresenham(surface,
                           int(round(ux0)), int(round(vy0)),
                           int(round(ux1)), int(round(vy1)),
                           color)
 
 
def regular_polygon(cx: float, cy: float,
                    r: float, n: int,
                    start_angle: float = 0.0) -> list:
    # Gera vértices de um polígono regular de n lados
    return [
        (cx + r * math.cos(start_angle + 2 * math.pi * i / n),
         cy + r * math.sin(start_angle + 2 * math.pi * i / n))
        for i in range(n)
    ]
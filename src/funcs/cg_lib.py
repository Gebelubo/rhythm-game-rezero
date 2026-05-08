import math
import pygame
from collections import deque


# ──────────────────────────────────────────────
# a) SET PIXEL
# ──────────────────────────────────────────────

def set_pixel(surface, x, y, color):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < surface.get_width() and 0 <= y < surface.get_height():
        surface.set_at((x, y), color)


def get_pixel(surface, x, y):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < surface.get_width() and 0 <= y < surface.get_height():
        return surface.get_at((x, y))[:3]
    return (-1, -1, -1)


# ──────────────────────────────────────────────
# b) PRIMITIVAS DE RASTERIZAÇÃO
# ──────────────────────────────────────────────

def line_bresenham(surface, x0, y0, x1, y1, color):
    """Rasterização de linha pelo algoritmo de Bresenham."""
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    dx, dy = abs(x1 - x0), abs(y1 - y0)
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


def line_bresenham_fast(surface, x0, y0, x1, y1, color):
    """Versão otimizada sem verificações redundantes"""
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    
    w, h = surface.get_width(), surface.get_height()
    
    while True:
        # Verificação de limites UNA vez por pixel
        if 0 <= x0 < w and 0 <= y0 < h:
            surface.set_at((x0, y0), color)
        
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def circle_midpoint(surface, xc, yc, r, color):
    """Rasterização de círculo pelo algoritmo do ponto médio."""
    x, y = 0, r
    d = 1 - r
    set_pixel(surface, xc, yc + r, color)
    set_pixel(surface, xc, yc - r, color)
    set_pixel(surface, xc + r, yc, color)
    set_pixel(surface, xc - r, yc, color)
    while x < y:
        if d < 0:
            d += 2 * x + 3
        else:
            d += 2 * (x - y) + 5
            y -= 1
        x += 1
        for px, py in [
            (xc + x, yc + y), (xc - x, yc + y),
            (xc + x, yc - y), (xc - x, yc - y),
            (xc + y, yc + x), (xc - y, yc + x),
            (xc + y, yc - x), (xc - y, yc - x),
        ]:
            set_pixel(surface, px, py, color)


def ellipse_midpoint(surface, xc, yc, rx, ry, color):
    """Rasterização de elipse pelo algoritmo do ponto médio."""
    x, y = 0, ry
    rx2, ry2 = rx * rx, ry * ry

    def plot4(x, y):
        set_pixel(surface, xc + x, yc + y, color)
        set_pixel(surface, xc - x, yc + y, color)
        set_pixel(surface, xc + x, yc - y, color)
        set_pixel(surface, xc - x, yc - y, color)

    # Região 1
    d1 = ry2 - rx2 * ry + 0.25 * rx2
    dx, dy = 2 * ry2 * x, 2 * rx2 * y
    while dx < dy:
        plot4(x, y)
        if d1 < 0:
            x += 1
            dx += 2 * ry2
            d1 += dx + ry2
        else:
            x += 1
            y -= 1
            dx += 2 * ry2
            dy -= 2 * rx2
            d1 += dx - dy + ry2

    # Região 2
    d2 = ry2 * (x + 0.5) ** 2 + rx2 * (y - 1) ** 2 - rx2 * ry2
    while y >= 0:
        plot4(x, y)
        if d2 > 0:
            y -= 1
            dy -= 2 * rx2
            d2 += rx2 - dy
        else:
            y -= 1
            x += 1
            dx += 2 * ry2
            dy -= 2 * rx2
            d2 += dx - dy + rx2


# ──────────────────────────────────────────────
# c) PREENCHIMENTO DE REGIÕES
# ──────────────────────────────────────────────

def flood_fill(surface, x, y, fill_color):
    """Flood Fill (4-conectado) a partir do ponto (x, y)."""
    x, y = int(round(x)), int(round(y))
    target_color = get_pixel(surface, x, y)
    fill_color = tuple(fill_color[:3])
    if target_color == fill_color or target_color == (-1, -1, -1):
        return
    queue = deque([(x, y)])
    w, h = surface.get_width(), surface.get_height()
    visited = set()
    while queue:
        cx, cy = queue.popleft()
        if (cx, cy) in visited:
            continue
        if not (0 <= cx < w and 0 <= cy < h):
            continue
        if get_pixel(surface, cx, cy) != target_color:
            continue
        visited.add((cx, cy))
        set_pixel(surface, cx, cy, fill_color)
        queue.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])


def boundary_fill(surface, x, y, fill_color, boundary_color):
    """Boundary Fill (4-conectado) usando cor de borda como limite."""
    x, y = int(round(x)), int(round(y))
    fill_color = tuple(fill_color[:3])
    boundary_color = tuple(boundary_color[:3])
    w, h = surface.get_width(), surface.get_height()
    queue = deque([(x, y)])
    visited = set()
    while queue:
        cx, cy = queue.popleft()
        if (cx, cy) in visited:
            continue
        if not (0 <= cx < w and 0 <= cy < h):
            continue
        current = get_pixel(surface, cx, cy)
        if current == boundary_color or current == fill_color:
            continue
        visited.add((cx, cy))
        set_pixel(surface, cx, cy, fill_color)
        queue.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])


def _build_edge_table(vertices):
    et = {}
    n = len(vertices)
    for i in range(n):
        x0, y0 = vertices[i]
        x1, y1 = vertices[(i + 1) % n]
        if y0 == y1:
            continue
        if y0 > y1:
            x0, y0, x1, y1 = x1, y1, x0, y0
        inv_m = (x1 - x0) / (y1 - y0)
        et.setdefault(int(math.ceil(y0)), []).append([
            int(math.ceil(y1)),
            x0 + inv_m * (math.ceil(y0) - y0),
            inv_m,
        ])
    return et


def scanline_fill(surface, vertices, color):
    """Preenchimento por varredura (Scanline Fill)."""
    if len(vertices) < 3:
        return
    et = _build_edge_table(vertices)
    if not et:
        return
    y_min = min(et.keys())
    y_max = max(int(math.ceil(v[1])) for v in vertices)
    active = []
    for y in range(y_min, y_max):
        if y in et:
            active.extend(et[y])
        active = [e for e in active if e[0] > y]
        active.sort(key=lambda e: e[1])
        for i in range(0, len(active) - 1, 2):
            x_start = int(math.ceil(active[i][1]))
            x_end = int(math.floor(active[i + 1][1]))
            for x in range(x_start, x_end + 1):
                set_pixel(surface, x, y, color)
        for e in active:
            e[1] += e[2]


def draw_polygon(surface, vertices, color):
    """Desenha o contorno de um polígono."""
    n = len(vertices)
    for i in range(n):
        x0, y0 = vertices[i]
        x1, y1 = vertices[(i + 1) % n]
        line_bresenham(surface, int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1)), color)


# ──────────────────────────────────────────────
# d) TRANSFORMAÇÕES GEOMÉTRICAS
# ──────────────────────────────────────────────

def translate(vertices, tx, ty):
    """Translação: desloca cada vértice por (tx, ty)."""
    return [(x + tx, y + ty) for x, y in vertices]


def scale(vertices, sx, sy, cx=0, cy=0):
    """Escala em relação ao ponto central (cx, cy)."""
    return [
        (cx + (x - cx) * sx, cy + (y - cy) * sy)
        for x, y in vertices
    ]


def rotate(vertices, angle_deg, cx=0, cy=0):
    """Rotação em torno do ponto (cx, cy) por angle_deg graus."""
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    result = []
    for x, y in vertices:
        x -= cx
        y -= cy
        nx = x * cos_a - y * sin_a
        ny = x * sin_a + y * cos_a
        result.append((nx + cx, ny + cy))
    return result


def reflect_x(vertices):
    """Reflexão em relação ao eixo X."""
    return [(x, -y) for x, y in vertices]


def reflect_y(vertices):
    """Reflexão em relação ao eixo Y."""
    return [(-x, y) for x, y in vertices]


# ──────────────────────────────────────────────
# f) JANELA E VIEWPORT
# ──────────────────────────────────────────────

class Window:
    """Define a janela do mundo (coordenadas do mundo)."""
    def __init__(self, x_min, y_min, x_max, y_max):
        self.x_min = x_min
        self.y_min = y_min
        self.x_max = x_max
        self.y_max = y_max


class Viewport:
    """Define a viewport (coordenadas de dispositivo/tela)."""
    def __init__(self, x_min, y_min, x_max, y_max):
        self.x_min = x_min
        self.y_min = y_min
        self.x_max = x_max
        self.y_max = y_max


def world_to_viewport(x, y, window: Window, viewport: Viewport):
    """Mapeia um ponto do espaço do mundo para a viewport."""
    sx = (viewport.x_max - viewport.x_min) / (window.x_max - window.x_min)
    sy = (viewport.y_max - viewport.y_min) / (window.y_max - window.y_min)
    vx = viewport.x_min + (x - window.x_min) * sx
    vy = viewport.y_min + (y - window.y_min) * sy
    return vx, vy


def draw_line_viewport(surface, x0, y0, x1, y1, color, window: Window, viewport: Viewport):
    """Desenha uma linha com mapeamento janela→viewport."""
    vx0, vy0 = world_to_viewport(x0, y0, window, viewport)
    vx1, vy1 = world_to_viewport(x1, y1, window, viewport)
    line_bresenham(surface, vx0, vy0, vx1, vy1, color)


def draw_polygon_viewport(surface, vertices, color, window: Window, viewport: Viewport):
    """Desenha polígono com mapeamento janela→viewport."""
    mapped = [world_to_viewport(x, y, window, viewport) for x, y in vertices]
    draw_polygon(surface, mapped, color)


# ──────────────────────────────────────────────
# g) RECORTE DE COHEN-SUTHERLAND (CLIPPING)
# ──────────────────────────────────────────────

INSIDE = 0b0000
LEFT   = 0b0001
RIGHT  = 0b0010
BOTTOM = 0b0100
TOP    = 0b1000


def _compute_code(x, y, x_min, y_min, x_max, y_max):
    code = INSIDE
    if x < x_min:
        code |= LEFT
    elif x > x_max:
        code |= RIGHT
    if y < y_min:
        code |= BOTTOM
    elif y > y_max:
        code |= TOP
    return code


def cohen_sutherland_clip(x0, y0, x1, y1, x_min, y_min, x_max, y_max):
    """
    Recorte de Cohen-Sutherland.
    Retorna (x0, y0, x1, y1) recortados, ou None se o segmento for rejeitado.
    """
    code0 = _compute_code(x0, y0, x_min, y_min, x_max, y_max)
    code1 = _compute_code(x1, y1, x_min, y_min, x_max, y_max)

    while True:
        if not (code0 | code1):       # Trivialmente aceito
            return x0, y0, x1, y1
        elif code0 & code1:           # Trivialmente rejeitado
            return None
        else:
            code_out = code0 if code0 else code1
            if code_out & TOP:
                x = x0 + (x1 - x0) * (y_max - y0) / (y1 - y0)
                y = y_max
            elif code_out & BOTTOM:
                x = x0 + (x1 - x0) * (y_min - y0) / (y1 - y0)
                y = y_min
            elif code_out & RIGHT:
                y = y0 + (y1 - y0) * (x_max - x0) / (x1 - x0)
                x = x_max
            else:  # LEFT
                y = y0 + (y1 - y0) * (x_min - x0) / (x1 - x0)
                x = x_min

            if code_out == code0:
                x0, y0 = x, y
                code0 = _compute_code(x0, y0, x_min, y_min, x_max, y_max)
            else:
                x1, y1 = x, y
                code1 = _compute_code(x1, y1, x_min, y_min, x_max, y_max)


def draw_line_clipped(surface, x0, y0, x1, y1, color, x_min, y_min, x_max, y_max):
    """Desenha linha com recorte de Cohen-Sutherland aplicado."""
    result = cohen_sutherland_clip(x0, y0, x1, y1, x_min, y_min, x_max, y_max)
    if result:
        line_bresenham(surface, *result, color)


# ──────────────────────────────────────────────
# h) MAPEAMENTO DE TEXTURA
# ──────────────────────────────────────────────

def load_texture(path):
    """Carrega uma imagem como textura."""
    return pygame.image.load(path).convert()


def texture_map_rect(surface, texture, x, y, w, h):
    """
    Mapeia textura sobre um retângulo (x, y, w, h).
    A textura é escalada para preencher o retângulo.
    """
    tw, th = texture.get_width(), texture.get_height()
    for px in range(int(w)):
        for py in range(int(h)):
            u = px / w
            v = py / h
            tx = int(u * (tw - 1))
            ty = int(v * (th - 1))
            color = texture.get_at((tx, ty))[:3]
            set_pixel(surface, x + px, y + py, color)


def texture_map_triangle(surface, texture, p0, p1, p2, uv0, uv1, uv2):
    """
    Mapeamento de textura affine sobre um triângulo.
    p0, p1, p2 — coordenadas (x, y) dos vértices na tela.
    uv0, uv1, uv2 — coordenadas (u, v) em [0,1] correspondentes.
    """
    tw, th = texture.get_width() - 1, texture.get_height() - 1
    xs = [p0[0], p1[0], p2[0]]
    ys = [p0[1], p1[1], p2[1]]
    x_min, x_max = int(math.floor(min(xs))), int(math.ceil(max(xs)))
    y_min, y_max = int(math.floor(min(ys))), int(math.ceil(max(ys)))

    ax, ay = p1[0] - p0[0], p1[1] - p0[1]
    bx, by = p2[0] - p0[0], p2[1] - p0[1]
    denom = ax * by - ay * bx
    if denom == 0:
        return

    for py in range(y_min, y_max + 1):
        for px in range(x_min, x_max + 1):
            wx, wy = px - p0[0], py - p0[1]
            s = (wx * by - wy * bx) / denom
            t = (ax * wy - ay * wx) / denom
            if s >= 0 and t >= 0 and s + t <= 1:
                u = uv0[0] + s * (uv1[0] - uv0[0]) + t * (uv2[0] - uv0[0])
                v = uv0[1] + s * (uv1[1] - uv0[1]) + t * (uv2[1] - uv0[1])
                tx = int(round(u * tw))
                ty = int(round(v * th))
                tx = max(0, min(tx, tw))
                ty = max(0, min(ty, th))
                color = texture.get_at((tx, ty))[:3]
                set_pixel(surface, px, py, color)


# ──────────────────────────────────────────────
# e) ANIMAÇÃO 2D  +  i) INPUT  +  j) MENU
# ──────────────────────────────────────────────

# A biblioteca de computação gráfica fornece primitivas, transformações,
# preenchimentos, clipping, viewport e mapeamento de textura.
# Animação, entrada e menus devem ser tratados na aplicação principal.


def draw_rectangle(surface, x, y, w, h, color):
    """Desenha o contorno de um retângulo."""
    x0, y0 = int(round(x)), int(round(y))
    x1, y1 = int(round(x + w)), int(round(y + h))

    # Topo
    line_bresenham(surface, x0, y0, x1, y0, color)
    # Base
    line_bresenham(surface, x0, y1, x1, y1, color)
    # Esquerda
    line_bresenham(surface, x0, y0, x0, y1, color)
    # Direita
    line_bresenham(surface, x1, y0, x1, y1, color)

def fill_rectangle(surface, x, y, w, h, color):
    """Desenha um retângulo preenchido."""
    x0, y0 = int(round(x)), int(round(y))
    x1, y1 = int(round(x + w)), int(round(y + h))

    for y in range(y0, y1 + 1):
        line_bresenham(surface, x0, y, x1, y, color)

def fill_rectangle_optimized(surface, x, y, w, h, color):
    """Versão otimizada - preenche linha por linha diretamente"""
    x0, y0 = int(round(x)), int(round(y))
    x1, y1 = int(round(x + w)), int(round(y + h))
    
    w, h = surface.get_width(), surface.get_height()
    
    # Garantir limites
    x0 = max(0, min(x0, w - 1))
    x1 = max(0, min(x1, w - 1))
    y0 = max(0, min(y0, h - 1))
    y1 = max(0, min(y1, h - 1))
    
    if x0 > x1:
        x0, x1 = x1, x0
    
    for y in range(y0, y1 + 1):
        # Desenha a linha inteira de uma vez
        for x in range(x0, x1 + 1):
            surface.set_at((x, y), color)

def scale_texture(texture, new_w, new_h):
    """Escala imagem manualmente (nearest neighbor)."""
    src_w, src_h = texture.get_width(), texture.get_height()
    scaled = pygame.Surface((new_w, new_h))

    for y in range(new_h):
        for x in range(new_w):
            u = x / new_w
            v = y / new_h
            sx = int(u * (src_w - 1))
            sy = int(v * (src_h - 1))
            color = texture.get_at((sx, sy))
            scaled.set_at((x, y), color)

    return scaled
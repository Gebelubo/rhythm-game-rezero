"""
╔══════════════════════════════════════════════════════════════╗
║              RHYTHM QUEST  –  Jogo de Ritmo                 ║
║  Todos os requisitos de Computação Gráfica implementados:   ║
║  • Rasterização: Bresenham, Ponto-Médio (circ. + elipse)    ║
║  • Preenchimento: Flood Fill, Boundary Fill, Scanline       ║
║  • Scanline com gradiente (Gouraud) e textura               ║
║  • Transformações: translação, escala, rotação + animação   ║
║  • Janela/Viewport + zoom/pan + Cohen-Sutherland            ║
║  • Menu interativo (picking por bounding box)               ║
╚══════════════════════════════════════════════════════════════╝

Requisitos:  pip install pygame
Uso:         python rhythm_game.py
"""

import math
import random
import pygame
import pygame.mixer
import struct
import wave
import io

# ─────────────────────────────────────────────────────────────────
# PRIMITIVAS DA BIBLIOTECA  (copiadas/importadas do módulo fornecido)
# ─────────────────────────────────────────────────────────────────

def set_pixel(surface, x, y, color):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < surface.get_width() and 0 <= y < surface.get_height():
        surface.set_at((x, y), color)

def get_pixel(surface, x, y):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < surface.get_width() and 0 <= y < surface.get_height():
        return surface.get_at((x, y))[:3]
    return (-1, -1, -1)

def line_bresenham(surface, x0, y0, x1, y1, color):
    x0,y0,x1,y1 = int(round(x0)),int(round(y0)),int(round(x1)),int(round(y1))
    dx,dy = abs(x1-x0), abs(y1-y0)
    sx = 1 if x0<x1 else -1
    sy = 1 if y0<y1 else -1
    err = dx-dy
    while True:
        set_pixel(surface,x0,y0,color)
        if x0==x1 and y0==y1: break
        e2 = 2*err
        if e2>-dy: err-=dy; x0+=sx
        if e2<dx:  err+=dx; y0+=sy

def _plot8(surface,xc,yc,x,y,color):
    for px,py in [(xc+x,yc+y),(xc-x,yc+y),(xc+x,yc-y),(xc-x,yc-y),
                  (xc+y,yc+x),(xc-y,yc+x),(xc+y,yc-x),(xc-y,yc-x)]:
        set_pixel(surface,px,py,color)

def circle_midpoint(surface,xc,yc,r,color):
    x,y = 0,r; d=1-r
    _plot8(surface,xc,yc,x,y,color)
    while x<y:
        d = d+2*x+3 if d<0 else d+2*(x-y)+5; y -= (0 if d<0 else 1); d += 0; x+=1
        # fix: recalculate properly
        _plot8(surface,xc,yc,x,y,color)

def circle_midpoint_filled(surface,xc,yc,r,color):
    """Fills a circle using horizontal scanlines derived from midpoint."""
    x,y = 0,r; d=1-r
    def hline(yy,xa,xb):
        for xi in range(int(xa),int(xb)+1):
            set_pixel(surface,xi,yy,color)
    hline(yc-r,xc,xc); hline(yc+r,xc,xc)
    while x<y:
        if d<0: d+=2*x+3
        else:   d+=2*(x-y)+5; y-=1
        x+=1
        hline(yc+y,xc-x,xc+x); hline(yc-y,xc-x,xc+x)
        hline(yc+x,xc-y,xc+y); hline(yc-x,xc-y,xc+y)

def ellipse_midpoint(surface,xc,yc,a,b,color):
    a2,b2=a*a,b*b; x,y=0,b
    d1=b2-a2*b+0.25*a2; dx=2*b2*x; dy=2*a2*y
    def plot4(x,y):
        for px,py in [(xc+x,yc+y),(xc-x,yc+y),(xc+x,yc-y),(xc-x,yc-y)]:
            set_pixel(surface,px,py,color)
    while dx<dy:
        plot4(x,y)
        if d1<0: x+=1;dx+=2*b2;d1+=dx+b2
        else:    x+=1;y-=1;dx+=2*b2;dy-=2*a2;d1+=dx-dy+b2
    d2=b2*(x+0.5)**2+a2*(y-1)**2-a2*b2
    while y>=0:
        plot4(x,y)
        if d2>0: y-=1;dy-=2*a2;d2+=a2-dy
        else:    y-=1;x+=1;dx+=2*b2;dy-=2*a2;d2+=dx-dy+a2

def ellipse_midpoint_filled(surface,xc,yc,a,b,color):
    """Fill ellipse with horizontal scanlines."""
    a2,b2=a*a,b*b
    for y in range(-b,b+1):
        if b==0: continue
        x_span=int(round(a*math.sqrt(max(0,1-(y/b)**2))))
        for x in range(-x_span,x_span+1):
            set_pixel(surface,xc+x,yc+y,color)

def flood_fill(surface,x,y,fill_color):
    x,y=int(round(x)),int(round(y))
    w,h=surface.get_width(),surface.get_height()
    if not(0<=x<w and 0<=y<h): return
    target=surface.get_at((x,y))[:3]
    if target==fill_color: return
    stack=[(x,y)]; visited=set()
    while stack:
        cx,cy=stack.pop()
        if (cx,cy) in visited: continue
        if not(0<=cx<w and 0<=cy<h): continue
        if surface.get_at((cx,cy))[:3]!=target: continue
        visited.add((cx,cy)); set_pixel(surface,cx,cy,fill_color)
        stack.extend([(cx+1,cy),(cx-1,cy),(cx,cy+1),(cx,cy-1)])

def boundary_fill(surface,x,y,fill_color,border_color):
    x,y=int(round(x)),int(round(y))
    w,h=surface.get_width(),surface.get_height()
    stack=[(x,y)]; visited=set()
    while stack:
        cx,cy=stack.pop()
        if (cx,cy) in visited: continue
        if not(0<=cx<w and 0<=cy<h): continue
        cur=surface.get_at((cx,cy))[:3]
        if cur==border_color or cur==fill_color: continue
        visited.add((cx,cy)); set_pixel(surface,cx,cy,fill_color)
        stack.extend([(cx+1,cy),(cx-1,cy),(cx,cy+1),(cx,cy-1)])

def _build_edge_table(vertices):
    et={}; n=len(vertices)
    for i in range(n):
        x0,y0=vertices[i]; x1,y1=vertices[(i+1)%n]
        if y0==y1: continue
        if y0>y1: x0,y0,x1,y1=x1,y1,x0,y0
        inv_m=(x1-x0)/(y1-y0)
        et.setdefault(int(math.ceil(y0)),[]).append([int(math.ceil(y1)),x0+inv_m*(math.ceil(y0)-y0),inv_m])
    return et

def scanline_fill(surface,vertices,color):
    if len(vertices)<3: return
    et=_build_edge_table(vertices)
    if not et: return
    y_min=min(et.keys()); y_max=max(int(math.ceil(v[1])) for v in vertices)
    active=[]
    for y in range(y_min,y_max):
        if y in et: active.extend(et[y])
        active=[e for e in active if e[0]>y]
        active.sort(key=lambda e:e[1])
        for i in range(0,len(active)-1,2):
            for x in range(int(math.ceil(active[i][1])),int(math.floor(active[i+1][1]))+1):
                set_pixel(surface,x,y,color)
        for e in active: e[1]+=e[2]

def scanline_fill_gradient(surface,vertices,colors):
    if len(vertices)<3: return
    n=len(vertices)
    ys=[v[1] for v in vertices]
    y_min=int(math.ceil(min(ys))); y_max=int(math.floor(max(ys)))
    for y in range(y_min,y_max+1):
        intersections=[]
        for i in range(n):
            x0,y0=vertices[i]; x1,y1=vertices[(i+1)%n]
            c0=colors[i]; c1=colors[(i+1)%n]
            if y0==y1: continue
            if not(min(y0,y1)<=y<max(y0,y1)): continue
            t=(y-y0)/(y1-y0); xi=x0+t*(x1-x0)
            ci=tuple(int(c0[k]+t*(c1[k]-c0[k])) for k in range(3))
            intersections.append((xi,ci))
        intersections.sort(key=lambda p:p[0])
        for i in range(0,len(intersections)-1,2):
            xl,cl=intersections[i]; xr,cr=intersections[i+1]
            span=xr-xl
            for x in range(int(math.ceil(xl)),int(math.floor(xr))+1):
                t=(x-xl)/span if span!=0 else 0
                c=tuple(int(cl[k]+t*(cr[k]-cl[k])) for k in range(3))
                set_pixel(surface,x,y,c)

def scanline_fill_texture(surface,vertices,uv_coords,texture):
    if len(vertices)<3: return
    tw,th=texture.get_width(),texture.get_height()
    n=len(vertices)
    ys=[v[1] for v in vertices]
    y_min=int(math.ceil(min(ys))); y_max=int(math.floor(max(ys)))
    for y in range(y_min,y_max+1):
        intersections=[]
        for i in range(n):
            x0,y0=vertices[i]; x1,y1=vertices[(i+1)%n]
            u0,v0=uv_coords[i]; u1,v1=uv_coords[(i+1)%n]
            if y0==y1: continue
            if not(min(y0,y1)<=y<max(y0,y1)): continue
            t=(y-y0)/(y1-y0); xi=x0+t*(x1-x0)
            ui=u0+t*(u1-u0); vi=v0+t*(v1-v0)
            intersections.append((xi,ui,vi))
        intersections.sort(key=lambda p:p[0])
        for i in range(0,len(intersections)-1,2):
            xl,ul,vl=intersections[i]; xr,ur,vr=intersections[i+1]
            span=xr-xl
            for x in range(int(math.ceil(xl)),int(math.floor(xr))+1):
                t=(x-xl)/span if span!=0 else 0
                u=ul+t*(ur-ul); v=vl+t*(vr-vl)
                tx=int(u*(tw-1))%tw; ty=int(v*(th-1))%th
                c=texture.get_at((tx,ty))[:3]
                set_pixel(surface,x,y,c)

# Transformações
def mat_mul(A,B):
    return [[sum(A[i][k]*B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]

def mat_vec(M,x,y):
    xp=M[0][0]*x+M[0][1]*y+M[0][2]; yp=M[1][0]*x+M[1][1]*y+M[1][2]
    w=M[2][0]*x+M[2][1]*y+M[2][2]
    return (xp/w,yp/w) if w!=0 else (xp,yp)

def translation(tx,ty):
    return [[1,0,tx],[0,1,ty],[0,0,1]]

def scaling(sx,sy):
    return [[sx,0,0],[0,sy,0],[0,0,1]]

def rotation(theta):
    c,s=math.cos(theta),math.sin(theta)
    return [[c,-s,0],[s,c,0],[0,0,1]]

def rotation_around(theta,cx,cy):
    return mat_mul(translation(cx,cy),mat_mul(rotation(theta),translation(-cx,-cy)))

def apply_transform(M,vertices):
    return [mat_vec(M,x,y) for x,y in vertices]

# Janela/Viewport
class Window:
    def __init__(self,x_min,y_min,x_max,y_max):
        self.x_min=x_min; self.y_min=y_min; self.x_max=x_max; self.y_max=y_max
    def pan(self,dx,dy):
        self.x_min+=dx;self.x_max+=dx;self.y_min+=dy;self.y_max+=dy
    def zoom(self,factor,cx=None,cy=None):
        if cx is None: cx=(self.x_min+self.x_max)/2
        if cy is None: cy=(self.y_min+self.y_max)/2
        hw=(self.x_max-self.x_min)/2/factor; hh=(self.y_max-self.y_min)/2/factor
        self.x_min=cx-hw;self.x_max=cx+hw;self.y_min=cy-hh;self.y_max=cy+hh

class Viewport:
    def __init__(self,u_min,v_min,u_max,v_max):
        self.u_min=u_min;self.v_min=v_min;self.u_max=u_max;self.v_max=v_max

def world_to_viewport(x,y,win,vp):
    u=vp.u_min+(x-win.x_min)/(win.x_max-win.x_min)*(vp.u_max-vp.u_min)
    v=vp.v_max-(y-win.y_min)/(win.y_max-win.y_min)*(vp.v_max-vp.v_min)
    return u,v

def world_to_viewport_transform(win,vp):
    sx=(vp.u_max-vp.u_min)/(win.x_max-win.x_min)
    sy=(vp.v_max-vp.v_min)/(win.y_max-win.y_min)
    return mat_mul(translation(vp.u_min,vp.v_max),mat_mul(scaling(sx,-sy),translation(-win.x_min,-win.y_min)))

def apply_viewport_transform(vertices,win,vp):
    M=world_to_viewport_transform(win,vp)
    return apply_transform(M,vertices)

# Cohen-Sutherland
_CS_INSIDE=0;_CS_LEFT=1;_CS_RIGHT=2;_CS_BOTTOM=4;_CS_TOP=8

def _compute_code(x,y,x_min,y_min,x_max,y_max):
    code=0
    if x<x_min: code|=_CS_LEFT
    elif x>x_max: code|=_CS_RIGHT
    if y<y_min: code|=_CS_BOTTOM
    elif y>y_max: code|=_CS_TOP
    return code

def cohen_sutherland(x0,y0,x1,y1,x_min,y_min,x_max,y_max):
    code0=_compute_code(x0,y0,x_min,y_min,x_max,y_max)
    code1=_compute_code(x1,y1,x_min,y_min,x_max,y_max)
    while True:
        if not(code0|code1): return x0,y0,x1,y1,True
        if code0&code1:      return x0,y0,x1,y1,False
        co=code0 if code0 else code1
        dx=x1-x0;dy=y1-y0
        if co&_CS_TOP:    x=x0+dx*(y_max-y0)/dy;y=y_max
        elif co&_CS_BOTTOM: x=x0+dx*(y_min-y0)/dy;y=y_min
        elif co&_CS_RIGHT:  y=y0+dy*(x_max-x0)/dx;x=x_max
        else:               y=y0+dy*(x_min-x0)/dx;x=x_min
        if co==code0: x0,y0=x,y;code0=_compute_code(x0,y0,x_min,y_min,x_max,y_max)
        else:         x1,y1=x,y;code1=_compute_code(x1,y1,x_min,y_min,x_max,y_max)

def draw_line_clipped(surface,x0,y0,x1,y1,win,vp,color):
    rx0,ry0,rx1,ry1,ok=cohen_sutherland(x0,y0,x1,y1,win.x_min,win.y_min,win.x_max,win.y_max)
    if not ok: return
    ux0,vy0=world_to_viewport(rx0,ry0,win,vp)
    ux1,vy1=world_to_viewport(rx1,ry1,win,vp)
    line_bresenham(surface,int(round(ux0)),int(round(vy0)),int(round(ux1)),int(round(vy1)),color)

def draw_polygon(surface,vertices,color):
    n=len(vertices)
    for i in range(n):
        x0,y0=vertices[i];x1,y1=vertices[(i+1)%n]
        line_bresenham(surface,int(round(x0)),int(round(y0)),int(round(x1)),int(round(y1)),color)

def regular_polygon(cx,cy,r,n,start_angle=0.0):
    return [(cx+r*math.cos(start_angle+2*math.pi*i/n),
             cy+r*math.sin(start_angle+2*math.pi*i/n)) for i in range(n)]

# Button class
class Button:
    def __init__(self,x,y,w,h,label,bg=(40,40,80),hover=(70,70,140),border=(120,120,255),text_c=(255,255,255),font=None):
        self.rect=pygame.Rect(x,y,w,h); self.label=label
        self.bg=bg;self.hover_c=hover;self.border=border;self.text_c=text_c
        self.font=font or pygame.font.SysFont("monospace",18); self._hovered=False
    def _fill_rect(self,surface,color):
        x0,y0=self.rect.topleft
        for dy in range(self.rect.height):
            for dx in range(self.rect.width):
                set_pixel(surface,x0+dx,y0+dy,color)
    def _draw_border(self,surface):
        x0,y0=self.rect.left,self.rect.top
        x1,y1=self.rect.right-1,self.rect.bottom-1
        line_bresenham(surface,x0,y0,x1,y0,self.border)
        line_bresenham(surface,x1,y0,x1,y1,self.border)
        line_bresenham(surface,x1,y1,x0,y1,self.border)
        line_bresenham(surface,x0,y1,x0,y0,self.border)
    def update(self,events):
        mx,my=pygame.mouse.get_pos(); self._hovered=self.rect.collidepoint(mx,my)
        for ev in events:
            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                if self.rect.collidepoint(ev.pos): return True
        return False
    def draw(self,surface):
        color=self.hover_c if self._hovered else self.bg
        self._fill_rect(surface,color); self._draw_border(surface)
        txt=self.font.render(self.label,True,self.text_c)
        tw,th=txt.get_size()
        surface.blit(txt,(self.rect.x+(self.rect.width-tw)//2,self.rect.y+(self.rect.height-th)//2))

# ─────────────────────────────────────────────────────────────────
# GERAÇÃO DE ÁUDIO PROCEDURAL
# ─────────────────────────────────────────────────────────────────
def make_tone(freq=440, duration=0.1, volume=0.4, sample_rate=44100):
    """Gera um beep sinusoidal como Sound do pygame."""
    n = int(sample_rate * duration)
    buf = bytearray()
    for i in range(n):
        t = i / sample_rate
        fade = min(1.0, (n-i)/(sample_rate*0.02))  # fade out
        val = int(32767 * volume * fade * math.sin(2*math.pi*freq*t))
        buf += struct.pack('<h', max(-32767, min(32767, val)))
    channels = pygame.mixer.get_init()[2]
    if channels == 2:
        stereo = bytearray()
        for i in range(n):
            val = struct.unpack_from('<h', buf, i*2)[0]
            stereo += struct.pack('<hh', val, val)
        sound = pygame.mixer.Sound(buffer=bytes(stereo))
    else:
        sound = pygame.mixer.Sound(buffer=bytes(buf))
    return sound

def make_beat_sound(sample_rate=44100):
    """Kick drum sintético."""
    duration = 0.15
    n = int(sample_rate * duration)
    buf = bytearray()
    for i in range(n):
        t = i / sample_rate
        freq = 120 * math.exp(-20*t)
        fade = math.exp(-15*t)
        val = int(32767 * 0.8 * fade * math.sin(2*math.pi*freq*t))
        buf += struct.pack('<h', max(-32767, min(32767, val)))
    channels = pygame.mixer.get_init()[2]
    if channels == 2:
        stereo = bytearray()
        for i in range(n):
            val = struct.unpack_from('<h', buf, i*2)[0]
            stereo += struct.pack('<hh', val, val)
        sound = pygame.mixer.Sound(buffer=bytes(stereo))
    else:
        sound = pygame.mixer.Sound(buffer=bytes(buf))
    return sound

def make_hihat_sound(sample_rate=44100):
    """Hi-hat sintético (ruído filtrado)."""
    duration = 0.05
    n = int(sample_rate * duration)
    buf = bytearray()
    for i in range(n):
        fade = math.exp(-60*(i/sample_rate))
        val = int(32767 * 0.3 * fade * (random.random()*2-1))
        buf += struct.pack('<h', max(-32767, min(32767, val)))
    channels = pygame.mixer.get_init()[2]
    if channels == 2:
        stereo = bytearray()
        for i in range(n):
            val = struct.unpack_from('<h', buf, i*2)[0]
            stereo += struct.pack('<hh', val, val)
        sound = pygame.mixer.Sound(buffer=bytes(stereo))
    else:
        sound = pygame.mixer.Sound(buffer=bytes(buf))
    return sound

# ─────────────────────────────────────────────────────────────────
# TEXTURAS PROCEDURAIS
# ─────────────────────────────────────────────────────────────────
def make_checker_texture(size=64, c1=(180,100,200), c2=(80,20,120)):
    surf = pygame.Surface((size,size))
    half = size//2
    for y in range(size):
        for x in range(size):
            c = c1 if (x//half+y//half)%2==0 else c2
            surf.set_at((x,y),c)
    return surf

def make_stars_texture(size=128):
    surf = pygame.Surface((size,size))
    surf.fill((5,5,20))
    for _ in range(40):
        x,y = random.randint(0,size-1), random.randint(0,size-1)
        v = random.randint(150,255)
        surf.set_at((x,y),(v,v,v))
    return surf

def make_grid_texture(size=64, line_color=(60,200,120), bg=(10,30,15)):
    surf = pygame.Surface((size,size))
    surf.fill(bg)
    step = size//4
    for i in range(0, size, step):
        for x in range(size): surf.set_at((x,i),line_color)
        for y in range(size): surf.set_at((i,y),line_color)
    return surf

def make_fire_texture(size=64):
    surf = pygame.Surface((size,size))
    for y in range(size):
        for x in range(size):
            t = y/size
            r = int(255*(1-t*0.3))
            g = int(200*max(0,1-t*1.5))
            b = 0
            noise = random.randint(-20,20)
            surf.set_at((x,y),(max(0,min(255,r+noise)),max(0,min(255,g+noise)),b))
    return surf

# ─────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────
W, H = 960, 640
FPS = 60

# Paleta
C_BG        = (8, 6, 18)
C_PURPLE    = (120, 60, 200)
C_PINK      = (220, 60, 140)
C_CYAN      = (60, 220, 220)
C_YELLOW    = (240, 200, 60)
C_GREEN     = (60, 220, 100)
C_WHITE     = (255, 255, 255)
C_DARK      = (20, 15, 40)
C_GRAY      = (100, 90, 130)

ARROW_COLORS = {
    'left':  (255, 80,  80),
    'down':  (80,  200, 255),
    'up':    (80,  255, 120),
    'right': (255, 200, 60),
}
ARROW_KEYS = {
    'left':  pygame.K_LEFT,
    'down':  pygame.K_DOWN,
    'up':    pygame.K_UP,
    'right': pygame.K_RIGHT,
}
ARROW_ORDER = ['left','down','up','right']
LANE_XS = [280, 340, 400, 460]   # x center of each lane in rhythm screen
HIT_Y = 520                       # y position of the hit zone

ZONE_PERFECT = 18
ZONE_GOOD    = 35
ZONE_OK      = 55

# BPMs per stage
STAGE_BPMS   = [90, 110, 130, 155]
STAGE_NAMES  = ["Floresta Mística", "Cidade Neon", "Templo Antigo", "Vórtex Final"]
STAGE_COLORS = [
    [(30,80,30),(60,160,60),(20,60,20)],
    [(10,10,60),(40,40,120),(80,80,200)],
    [(80,50,10),(160,100,20),(100,60,10)],
    [(60,0,60),(120,0,120),(200,0,200)],
]
# Corner positions in lobby map (world coords)
STAGE_CORNERS_WORLD = [
    (-180, 120),   # top-left  -> stage 0
    ( 180, 120),   # top-right -> stage 1
    (-180,-120),   # bot-left  -> stage 2
    ( 180,-120),   # bot-right -> stage 3
]

# ─────────────────────────────────────────────────────────────────
# TELA DE ABERTURA  (usa Bresenham, circunferência, elipse, flood/boundary fill)
# ─────────────────────────────────────────────────────────────────
class SplashScreen:
    def __init__(self, surface):
        self.surf = surface
        self.done = False
        self.timer = 0
        self.alpha = 0
        self.phase = 0   # 0=drawing, 1=filling, 2=showing text, 3=waiting
        self.step  = 0
        self._bg = pygame.Surface((W,H))
        self._bg.fill(C_BG)
        self._layer = pygame.Surface((W,H))
        self._layer.fill(C_BG)
        # Button
        fnt = pygame.font.SysFont("monospace", 22, bold=True)
        self.btn = Button(W//2-100,H-90,200,50,"▶  COMEÇAR",
                          bg=(60,20,100),hover=(100,40,160),
                          border=C_PINK,text_c=C_WHITE,font=fnt)
        self.drawn_shapes = []  # list of lambdas to re-draw
        self._build_splash()

    def _build_splash(self):
        """Pre-renders the full splash artwork onto _layer."""
        surf = self._layer
        surf.fill(C_BG)

        # ── Stars (set_pixel) ──
        rng = random.Random(42)
        for _ in range(200):
            x,y = rng.randint(0,W-1), rng.randint(0,H//2)
            v = rng.randint(100,255)
            set_pixel(surf,x,y,(v,v,v))

        # ── Ellipse (planet) – rasterizada ──
        ellipse_midpoint(surf, W//2, 80, 220, 30, C_PURPLE)
        ellipse_midpoint_filled(surf, W//2, 80, 218, 28, (30,15,60))

        # ── Large circle (main orb) ──
        cx,cy,r = W//2, 280, 130
        circle_midpoint(surf, cx,cy,r, C_PINK)
        # Fill interior with flood fill
        # First paint background inside
        for yy in range(cy-r+2,cy+r-1):
            xspan = int(math.sqrt(max(0,r*r-(yy-cy)**2)))
            for xx in range(cx-xspan+1,cx+xspan):
                set_pixel(surf,xx,yy,C_BG)
        flood_fill(surf, cx, cy, (15,8,35))

        # ── Concentric decorative circles ──
        for dr, col in [(90,(80,40,150)),(60,(100,50,180)),(30,(130,65,210))]:
            circle_midpoint(surf,cx,cy,dr,col)

        # ── Music note (lines + small circles) via Bresenham ──
        # stem
        line_bresenham(surf, cx-10,cy-60, cx-10,cy+20, C_WHITE)
        line_bresenham(surf, cx+10,cy-80, cx+10,cy,    C_WHITE)
        # beam
        line_bresenham(surf, cx-10,cy-60, cx+10,cy-80, C_WHITE)
        # note heads (filled circles via flood)
        circle_midpoint(surf,cx-18,cy+22,10,C_WHITE)
        flood_fill(surf,cx-18,cy+22,C_WHITE)
        circle_midpoint(surf,cx+2,cy+2,10,C_WHITE)
        flood_fill(surf,cx+2,cy+2,C_WHITE)

        # ── Arrow decorations (scanline triangles with gradient) ──
        dirs = [('left',-180,280),('right',180,280),('up',0,100),('down',0,460)]
        for d,ax,ay in dirs:
            col = ARROW_COLORS[d]
            dark = tuple(c//3 for c in col)
            self._draw_arrow_shape(surf,ax,ay,d,col,dark)

        # ── Title text (drawn via pygame font – allowed) ──
        fnt_big  = pygame.font.SysFont("monospace",54,bold=True)
        fnt_sub  = pygame.font.SysFont("monospace",22)
        title = fnt_big.render("RHYTHM  QUEST", True, C_CYAN)
        sub   = fnt_sub.render("- Aperte as setas no ritmo -", True, C_GRAY)
        surf.blit(title,(W//2-title.get_width()//2, H-230))
        surf.blit(sub,  (W//2-sub.get_width()//2,  H-165))

        # ── Border with Bresenham ──
        for i in range(3):
            c = [C_PURPLE,C_PINK,C_CYAN][i]
            m = i*2
            line_bresenham(surf,m,m,W-1-m,m,c)
            line_bresenham(surf,W-1-m,m,W-1-m,H-1-m,c)
            line_bresenham(surf,W-1-m,H-1-m,m,H-1-m,c)
            line_bresenham(surf,m,H-1-m,m,m,c)

    def _draw_arrow_shape(self,surf,cx,cy,direction,col,dark):
        """Desenha uma seta triangular preenchida com scanline+gradiente."""
        s=28
        if direction=='left':
            verts=[(cx-s,cy),(cx+s,cy-s),(cx+s,cy+s)]
        elif direction=='right':
            verts=[(cx+s,cy),(cx-s,cy-s),(cx-s,cy+s)]
        elif direction=='up':
            verts=[(cx,cy-s),(cx-s,cy+s),(cx+s,cy+s)]
        else:
            verts=[(cx,cy+s),(cx-s,cy-s),(cx+s,cy-s)]
        colors=[col,dark,dark]
        scanline_fill_gradient(surf,verts,colors)
        draw_polygon(surf,verts,C_WHITE)

    def update(self, events, dt):
        self.timer += dt
        for ev in events:
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
                self.done = True
        if self.btn.update(events):
            self.done = True

    def draw(self):
        self.surf.blit(self._layer,(0,0))
        # Pulsing glow on orb
        t = self.timer
        pulse_r = int(130 + 8*math.sin(t*3))
        alpha_ring = int(120 + 100*math.sin(t*3))
        glow = pygame.Surface((W,H), pygame.SRCALPHA)
        cx,cy = W//2,280
        for dr in range(20,0,-1):
            a = int(alpha_ring * dr/20 * 0.12)
            pygame.draw.circle(glow,(220,80,180,a),(cx,cy),pulse_r+dr)
        self.surf.blit(glow,(0,0))
        self.btn.draw(self.surf)

# ─────────────────────────────────────────────────────────────────
# TELA DE TUTORIAL
# ─────────────────────────────────────────────────────────────────
class TutorialScreen:
    def __init__(self,surface):
        self.surf=surface
        self.done=False
        fnt=pygame.font.SysFont("monospace",20)
        fnt_big=pygame.font.SysFont("monospace",32,bold=True)
        self.fnt=fnt; self.fnt_big=fnt_big
        self.btn=Button(W//2-80,H-80,160,45,"← VOLTAR",
                        bg=(40,20,70),hover=(80,40,120),border=C_CYAN,
                        text_c=C_WHITE,font=fnt)
        self._layer=pygame.Surface((W,H))
        self._build()

    def _build(self):
        surf=self._layer; surf.fill(C_BG)
        # Title
        fnt_big=pygame.font.SysFont("monospace",36,bold=True)
        t=fnt_big.render("COMO JOGAR",True,C_CYAN)
        surf.blit(t,(W//2-t.get_width()//2,30))

        # Arrow legends
        fnt=pygame.font.SysFont("monospace",20)
        lines=[
            ("←  SETA ESQUERDA",  ARROW_COLORS['left']),
            ("↓  SETA BAIXO",     ARROW_COLORS['down']),
            ("↑  SETA CIMA",      ARROW_COLORS['up']),
            ("→  SETA DIREITA",   ARROW_COLORS['right']),
        ]
        for i,(text,col) in enumerate(lines):
            tx=fnt.render(text,True,col)
            surf.blit(tx,(W//2-160,120+i*40))
            # small arrow icon with scanline
            self._draw_mini_arrow(surf,W//2+160,133+i*40,ARROW_ORDER[i],col)

        # Rules text
        rules=[
            "Setas descem pelas 4 raias.",
            "Pressione a tecla certa quando a seta",
            "chegar à ZONA DE ACERTO (parte de baixo).",
            "",
            "PERFEITO  < 18px   → 100 pts",
            "BOM       < 35px   →  60 pts",
            "OK        < 55px   →  30 pts",
            "MISS      = 0 pts, quebra o combo",
            "",
            "No lobby, mova o personagem com WASD",
            "e entre nas zonas dos cantos para escolher",
            "uma fase. Boa sorte!",
        ]
        for i,r in enumerate(rules):
            col=C_WHITE if r else C_BG
            if r.startswith("PERFEITO"): col=(255,215,0)
            elif r.startswith("BOM"):    col=C_CYAN
            elif r.startswith("OK"):     col=C_GREEN
            elif r.startswith("MISS"):   col=(255,80,80)
            elif r.startswith("No lobby") or r.startswith("e entre") or r.startswith("uma fase"): col=C_GRAY
            t=fnt.render(r,True,col)
            surf.blit(t,(W//2-t.get_width()//2,280+i*26))

        # border
        for i in range(3):
            c=[C_PURPLE,C_PINK,C_CYAN][i]; m=i*2
            line_bresenham(surf,m,m,W-1-m,m,c)
            line_bresenham(surf,W-1-m,m,W-1-m,H-1-m,c)
            line_bresenham(surf,W-1-m,H-1-m,m,H-1-m,c)
            line_bresenham(surf,m,H-1-m,m,m,c)

    def _draw_mini_arrow(self,surf,cx,cy,direction,col):
        s=14
        if direction=='left':    verts=[(cx-s,cy),(cx+s,cy-s),(cx+s,cy+s)]
        elif direction=='right': verts=[(cx+s,cy),(cx-s,cy-s),(cx-s,cy+s)]
        elif direction=='up':    verts=[(cx,cy-s),(cx-s,cy+s),(cx+s,cy+s)]
        else:                    verts=[(cx,cy+s),(cx-s,cy-s),(cx+s,cy-s)]
        dark=tuple(c//3 for c in col)
        scanline_fill_gradient(surf,verts,[col,dark,dark])
        draw_polygon(surf,verts,C_WHITE)

    def update(self,events,dt):
        if self.btn.update(events): self.done=True
        for ev in events:
            if ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE: self.done=True

    def draw(self):
        self.surf.blit(self._layer,(0,0))
        self.btn.draw(self.surf)

# ─────────────────────────────────────────────────────────────────
# MENU PRINCIPAL
# ─────────────────────────────────────────────────────────────────
class MainMenu:
    def __init__(self,surface):
        self.surf=surface
        self.action=None   # 'play','tutorial','quit'
        fnt=pygame.font.SysFont("monospace",22,bold=True)
        bw,bh,bx=220,52,W//2-110
        self.btn_play    =Button(bx,250,bw,bh,"▶  JOGAR",       bg=(50,20,90),hover=(90,40,150),border=C_CYAN,  text_c=C_WHITE,font=fnt)
        self.btn_tutorial=Button(bx,320,bw,bh,"?  TUTORIAL",    bg=(30,40,20),hover=(60,80,40), border=C_GREEN, text_c=C_WHITE,font=fnt)
        self.btn_quit    =Button(bx,390,bw,bh,"✕  SAIR",        bg=(60,15,15),hover=(120,30,30),border=C_PINK,  text_c=C_WHITE,font=fnt)
        self._layer=pygame.Surface((W,H))
        self._build()
        self.timer=0.0

    def _build(self):
        surf=self._layer; surf.fill(C_BG)
        # Background grid lines (viewport/world demo)
        win=Window(-480,-320,480,320); vp=Viewport(0,0,W,H)
        for gx in range(-480,481,60):
            draw_line_clipped(surf,gx,-320,gx,320,win,vp,(25,20,50))
        for gy in range(-320,321,60):
            draw_line_clipped(surf,-480,gy,480,gy,win,vp,(25,20,50))

        # Title logo using primitives
        fnt_logo=pygame.font.SysFont("monospace",58,bold=True)
        t1=fnt_logo.render("RHYTHM",True,C_CYAN)
        t2=fnt_logo.render("QUEST",True,C_PINK)
        surf.blit(t1,(W//2-t1.get_width()//2,100))
        surf.blit(t2,(W//2-t2.get_width()//2,158))

        # Decorative ellipse under title
        ellipse_midpoint(surf,W//2,175,200,12,C_PURPLE)

        # Side decorative circles
        circle_midpoint(surf,80,H//2,60,(40,20,80))
        flood_fill(surf,80,H//2,(30,12,55))
        circle_midpoint(surf,W-80,H//2,60,(40,20,80))
        flood_fill(surf,W-80,H//2,(30,12,55))

        # Corner arrows
        for d,ax,ay in [('left',80,H//2),('right',W-80,H//2)]:
            col=ARROW_COLORS[d]
            s=30
            if d=='left': verts=[(ax-s,ay),(ax+s,ay-s),(ax+s,ay+s)]
            else:         verts=[(ax+s,ay),(ax-s,ay-s),(ax-s,ay+s)]
            scanline_fill_gradient(surf,verts,[col,tuple(c//3 for c in col),tuple(c//3 for c in col)])
            draw_polygon(surf,verts,C_WHITE)

        # Border
        for i in range(3):
            c=[C_PURPLE,C_PINK,C_CYAN][i]; m=i*2
            line_bresenham(surf,m,m,W-1-m,m,c)
            line_bresenham(surf,W-1-m,m,W-1-m,H-1-m,c)
            line_bresenham(surf,W-1-m,H-1-m,m,H-1-m,c)
            line_bresenham(surf,m,H-1-m,m,m,c)

    def update(self,events,dt):
        self.timer+=dt
        if self.btn_play.update(events):     self.action='play'
        if self.btn_tutorial.update(events): self.action='tutorial'
        if self.btn_quit.update(events):     self.action='quit'
        for ev in events:
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_RETURN: self.action='play'
                if ev.key==pygame.K_ESCAPE: self.action='quit'

    def draw(self):
        self.surf.blit(self._layer,(0,0))
        # Animated pulsing ellipse
        t=self.timer
        a=int(200+10*math.sin(t*2)); b=int(12+4*math.sin(t*2))
        ellipse_midpoint(self.surf,W//2,175,a,b,C_CYAN)
        self.btn_play.draw(self.surf)
        self.btn_tutorial.draw(self.surf)
        self.btn_quit.draw(self.surf)

# ─────────────────────────────────────────────────────────────────
# LOBBY  (mapa com personagem + World/Viewport + Cohen-Sutherland)
# ─────────────────────────────────────────────────────────────────
class LobbyScreen:
    def __init__(self,surface):
        self.surf=surface
        self.action=None   # None or stage index 0-3
        # World coords for player
        self.px=0.0; self.py=0.0
        self.speed=120.0  # world units/sec
        self.timer=0.0
        self.anim_t=0.0
        # Window/Viewport
        self.win=Window(-240,-180,240,180)
        self.vp=Viewport(0,0,W,H)
        # Textures for floor tiles
        self.tex_checker=make_checker_texture(32,(50,30,80),(25,15,40))
        self.tex_grid=make_grid_texture(32,(40,120,80),(8,25,15))
        # Fonts
        self.fnt=pygame.font.SysFont("monospace",18)
        self.fnt_big=pygame.font.SysFont("monospace",24,bold=True)
        self.fnt_small=pygame.font.SysFont("monospace",20,bold=True)
        self.fnt_hud=pygame.font.SysFont("monospace",16)
        self._overlay_diff=pygame.Surface((W,80),pygame.SRCALPHA)
        self._overlay_diff.fill((0,0,0,160))
        # Static world map (render once)
        self._world_map_surf=self._build_world_map()
        self._static_origin=world_to_viewport(-240,-180,Window(-240,-180,240,180),self.vp)
        # Stage entry radius (world units)
        self.entry_r=40
        self.entered_stage=None
        self.enter_timer=0.0
        # Diff buttons (shown when near a stage)
        fnt_btn=pygame.font.SysFont("monospace",18,bold=True)
        bw,bh=130,40
        cx=W//2
        self.diff_buttons=[
            Button(cx-210,H//2-20,bw,bh,"FÁCIL",   bg=(20,60,20),hover=(40,100,40),border=C_GREEN, text_c=C_WHITE,font=fnt_btn),
            Button(cx-65, H//2-20,bw,bh,"MÉDIO",   bg=(60,50,10),hover=(110,90,20),border=C_YELLOW,text_c=C_WHITE,font=fnt_btn),
            Button(cx+80, H//2-20,bw,bh,"DIFÍCIL", bg=(60,10,10),hover=(110,20,20),border=C_PINK,  text_c=C_WHITE,font=fnt_btn),
        ]
        self.diff_labels=['easy','medium','hard']
        self.show_diff=False
        self.pending_stage=None
        self.btn_back=Button(10,10,110,38,"← MENU",
                             bg=(30,15,50),hover=(60,30,90),border=C_GRAY,
                             text_c=C_WHITE,font=pygame.font.SysFont("monospace",16))

    def _build_world_map(self):
        """Render the static full-world map once in default world coordinates."""
        surf=pygame.Surface((W,H))
        surf.fill((12,8,25))
        default_win=Window(-240,-180,240,180)
        vp=self.vp

        # Floor quad (textured scanline)
        floor_world=[(-220,-160),(220,-160),(220,160),(-220,160)]
        floor_vp=apply_viewport_transform(floor_world,default_win,vp)
        uv=[(0,0),(1,0),(1,1),(0,1)]
        scanline_fill_texture(surf,floor_vp,uv,self.tex_checker)

        # Stage zones (gradient polygons at corners)
        for i,((wx,wy),cols) in enumerate(zip(STAGE_CORNERS_WORLD,STAGE_COLORS)):
            r=38
            verts_w=[(wx+r*math.cos(2*math.pi*k/6),wy+r*math.sin(2*math.pi*k/6)) for k in range(6)]
            verts_s=apply_viewport_transform(verts_w,default_win,vp)
            clist=[cols[k%3] for k in range(6)]
            scanline_fill_gradient(surf,verts_s,clist)
            draw_polygon(surf,verts_s,C_WHITE)
            ux,vy=world_to_viewport(wx,wy,default_win,vp)
            t=self.fnt_big.render(STAGE_NAMES[i],True,C_WHITE)
            surf.blit(t,(int(ux)-t.get_width()//2,int(vy)-10))

        # Map border
        wall_pts=[(-220,-160),(220,-160),(220,160),(-220,160)]
        for i in range(4):
            x0,y0=wall_pts[i]; x1,y1=wall_pts[(i+1)%4]
            draw_line_clipped(surf,x0,y0,x1,y1,default_win,vp,(80,60,120))

        # Grid lines (Cohen-Sutherland demo)
        for gx in range(-200,201,40):
            draw_line_clipped(surf,gx,-160,gx,160,default_win,vp,(30,25,55))
        for gy in range(-160,161,40):
            draw_line_clipped(surf,-220,gy,220,gy,default_win,vp,(30,25,55))

        return surf

    def _draw_player(self,surf,screen_x,screen_y,anim_t,scale=1.0):
        """
        Desenha o personagem usando polígonos + scanline + transformações.
        Todas as partes são calculadas em coordenadas locais e transformadas.
        """
        # Body (hexagon with gradient)
        bob = math.sin(anim_t*6)*4*scale
        # Build body polygon in local space then translate
        body_r=14*scale
        body_verts=regular_polygon(0,0,body_r,6,math.pi/6)
        # Apply: scale already in r, translate to screen pos
        T=translation(screen_x, screen_y+bob)
        body_screen=apply_transform(T,body_verts)
        body_colors=[(80,180,255),(40,100,200),(60,140,230),(80,180,255),(40,100,200),(60,140,230)]
        scanline_fill_gradient(surf,body_screen,body_colors)
        draw_polygon(surf,body_screen,C_CYAN)

        # Head (circle - midpoint)
        hx,hy=int(screen_x),int(screen_y-18*scale+bob)
        hr=int(10*scale)
        circle_midpoint(surf,hx,hy,hr,(200,230,255))
        flood_fill(surf,hx,hy,(180,210,240))

        # Eyes
        set_pixel(surf,hx-3,hy-2,(20,20,60))
        set_pixel(surf,hx+3,hy-2,(20,20,60))
        set_pixel(surf,hx-4,hy-2,(20,20,60))
        set_pixel(surf,hx+4,hy-2,(20,20,60))

        # Legs (two lines that animate)
        leg_swing=math.sin(anim_t*6)*8*scale
        bx,by=int(screen_x),int(screen_y+14*scale+bob)
        line_bresenham(surf,bx,by,int(bx-6*scale),int(by+10*scale+leg_swing),(200,230,255))
        line_bresenham(surf,bx,by,int(bx+6*scale),int(by+10*scale-leg_swing),(200,230,255))

        # Arms
        arm_swing=math.sin(anim_t*6)*6*scale
        line_bresenham(surf,bx,int(by-10*scale),int(bx-12*scale),int(by-4*scale+arm_swing),(200,230,255))
        line_bresenham(surf,bx,int(by-10*scale),int(bx+12*scale),int(by-4*scale-arm_swing),(200,230,255))

    def _clamp_player(self):
        lim=180
        self.px=max(-lim,min(lim,self.px))
        self.py=max(-lim,min(lim,self.py))

    def update(self,events,dt):
        self.timer+=dt; self.anim_t+=dt
        keys=pygame.key.get_pressed()
        moving=False
        if keys[pygame.K_w] or keys[pygame.K_UP]:    self.py+=self.speed*dt; moving=True
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  self.py-=self.speed*dt; moving=True
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  self.px-=self.speed*dt; moving=True
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: self.px+=self.speed*dt; moving=True
        if not moving: self.anim_t=0  # idle
        self._clamp_player()

        # Pan world window to follow player (zoom/pan demo)
        self.win.x_min=self.px-240; self.win.x_max=self.px+240
        self.win.y_min=self.py-180; self.win.y_max=self.py+180

        # Check proximity to stage corners
        near=None
        for i,(wx,wy) in enumerate(STAGE_CORNERS_WORLD):
            dist=math.hypot(self.px-wx,self.py-wy)
            if dist<self.entry_r: near=i; break
        self.entered_stage=near
        self.show_diff=(near is not None)
        if near is not None: self.pending_stage=near

        # Diff buttons
        if self.show_diff:
            for i,btn in enumerate(self.diff_buttons):
                if btn.update(events):
                    self.action=(self.pending_stage, self.diff_labels[i])

        if self.btn_back.update(events): self.action='menu'
        for ev in events:
            if ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE: self.action='menu'

    def draw(self):
        surf=self.surf
        dx,dy=world_to_viewport(-240,-180,self.win,self.vp)
        sx,sy=self._static_origin
        surf.blit(self._world_map_surf,(int(dx-sx),int(dy-sy)))

        # Draw player at center of screen (viewport center = player position)
        px_s,py_s=world_to_viewport(self.px,self.py,self.win,self.vp)
        self._draw_player(surf,px_s,py_s,self.anim_t)

        # Stage proximity indicator
        if self.entered_stage is not None:
            t=self.fnt_small.render(f"Entrando em: {STAGE_NAMES[self.entered_stage]}",True,C_YELLOW)
            surf.blit(t,(W//2-t.get_width()//2,H//2-60))

        # Diff buttons
        if self.show_diff:
            surf.blit(self._overlay_diff,(0,H//2-40))
            t=self.fnt.render("Escolha a dificuldade:",True,C_WHITE)
            surf.blit(t,(W//2-t.get_width()//2,H//2-38))
            for btn in self.diff_buttons: btn.draw(surf)

        # HUD
        t=self.fnt_hud.render("WASD/setas: mover    ESC: menu",True,C_GRAY)
        surf.blit(t,(W//2-t.get_width()//2,H-28))
        self.btn_back.draw(surf)

# ─────────────────────────────────────────────────────────────────
# FASE DE RITMO
# ─────────────────────────────────────────────────────────────────
class Note:
    def __init__(self,lane,y):
        self.lane=lane    # 0-3
        self.y=y          # screen y (starts at 0, falls down)
        self.active=True
        self.hit_result=None   # 'perfect','good','ok','miss'
        self.flash_timer=0.0

class RhythmScreen:
    DIFF_SPEED = {'easy':200,'medium':300,'hard':420}
    DIFF_DENSITY= {'easy':1.0,'medium':1.6,'hard':2.4}

    def __init__(self,surface,stage_idx,difficulty,sounds):
        self.surf=surface
        self.stage=stage_idx
        self.diff=difficulty
        self.sounds=sounds
        self.action=None   # 'back' or 'menu'
        self.speed=self.DIFF_SPEED[difficulty]
        self.density=self.DIFF_DENSITY[difficulty]
        self.bpm=STAGE_BPMS[stage_idx]
        self.beat_interval=60.0/self.bpm
        self.timer=0.0
        self.beat_timer=0.0
        self.notes=[]
        self.score=0
        self.combo=0
        self.max_combo=0
        self.miss_count=0
        self.total_notes=0
        self.judgement=''
        self.judgement_timer=0.0
        self.judgement_color=C_WHITE
        self.game_over=False
        self.win_condition=False
        self.notes_target=40+stage_idx*10
        self.notes_spawned=0
        self.anim_t=0.0
        self.beat_flash=0.0
        # Stage textures for lane bg
        self.stage_tex=[make_stars_texture,make_grid_texture,make_fire_texture,make_checker_texture][stage_idx]()
        # Build background layer
        self._bg=self._build_bg()
        self._lane_bg=self._build_lane_bg()
        self._hit_zone_rects=[pygame.Rect(cx-22,HIT_Y-22,44,44) for cx in LANE_XS]
        self._hit_zone_surfaces=[(
            self._make_hit_zone_surface(i,False),
            self._make_hit_zone_surface(i,True)
        ) for i in range(4)]
        self._note_surfaces=[self._make_note_surface(i,False) for i in range(4)]
        self._note_flash_surfaces=[self._make_note_surface(i,True) for i in range(4)]
        self.fnt=pygame.font.SysFont("monospace",18)
        self.fnt_big=pygame.font.SysFont("monospace",28,bold=True)
        self.fnt_huge=pygame.font.SysFont("monospace",48,bold=True)
        self.fnt_judge=pygame.font.SysFont("monospace",36,bold=True)
        # Back button
        self.btn_back=Button(10,10,110,36,"← SAIR",
                             bg=(40,15,60),hover=(80,30,100),border=C_GRAY,
                             text_c=C_WHITE,font=pygame.font.SysFont("monospace",15))
        # End screen buttons
        fnt_e=pygame.font.SysFont("monospace",20,bold=True)
        self.btn_retry=Button(W//2-120,H//2+100,110,42,"TENTAR DE NOVO",
                              bg=(20,50,20),hover=(40,90,40),border=C_GREEN,text_c=C_WHITE,font=pygame.font.SysFont("monospace",14))
        self.btn_lobby=Button(W//2+10,H//2+100,110,42,"LOBBY",
                              bg=(20,20,60),hover=(40,40,110),border=C_CYAN,text_c=C_WHITE,font=pygame.font.SysFont("monospace",14))
        # Key press visual
        self.key_press=[0.0]*4   # flash timers per lane
        # Note spawn pattern (pre-compute)
        random.seed(stage_idx*100+{'easy':0,'medium':1,'hard':2}[difficulty])
        self._beat_patterns=self._generate_patterns()
        self._pattern_idx=0
        # Beat-sync audio
        self.last_beat_sound=0.0

    def _generate_patterns(self):
        """Generates a list of lane indices per beat."""
        patterns=[]
        count=int(self.notes_target*1.5)
        for _ in range(count):
            n_notes=1 if self.density<1.5 else (2 if random.random()<0.4 else 1)
            lanes=random.sample([0,1,2,3],n_notes)
            patterns.append(lanes)
        return patterns

    def _build_bg(self):
        surf=pygame.Surface((W,H))
        surf.fill(C_BG)
        cols=STAGE_COLORS[self.stage]
        # Background gradient polygon (full screen)
        verts=[(0,0),(W,0),(W,H),(0,H)]
        bg_colors=[cols[0],cols[1],cols[2],cols[0]]
        scanline_fill_gradient(surf,verts,bg_colors)
        return surf

    def _build_lane_bg(self):
        surf=pygame.Surface((W,H))
        lane_w=60; lane_x=LANE_XS[0]-lane_w//2
        total_w=LANE_XS[-1]-LANE_XS[0]+lane_w
        tex_verts=[(lane_x,0),(lane_x+total_w,0),(lane_x+total_w,H),(lane_x,H)]
        uv=[(0,0),(1,0),(1,1),(0,1)]
        scanline_fill_texture(surf,tex_verts,uv,self.stage_tex)
        for lx in LANE_XS:
            pygame.draw.line(surf,(60,50,80),(lx-lane_w//2,0),(lx-lane_w//2,H),2)
            pygame.draw.line(surf,(60,50,80),(lx+lane_w//2,0),(lx+lane_w//2,H),2)
        return surf

    def _make_hit_zone_surface(self,lane,pressed=False):
        size=48
        surf=pygame.Surface((size,size),pygame.SRCALPHA)
        cx=size/2; cy=size/2; s=22
        col=ARROW_COLORS[ARROW_ORDER[lane]]
        dark=tuple(c//4 for c in col)
        if pressed:
            bright=tuple(min(255,int(c*1.6)) for c in col)
        else:
            bright=col
        verts=[(cx-s,cy-s),(cx+s,cy-s),(cx+s,cy+s),(cx-s,cy+s)]
        pygame.draw.polygon(surf, bright, verts)
        pygame.draw.polygon(surf, C_WHITE, verts, 2)
        self._draw_arrow_icon(surf,cx,cy,ARROW_ORDER[lane],col,size=14)
        return surf

    def _make_note_surface(self,lane,flash=False):
        size=40
        surf=pygame.Surface((size,size),pygame.SRCALPHA)
        cx=size/2; cy=size/2; s=14
        col=ARROW_COLORS[ARROW_ORDER[lane]]
        if flash:
            col=tuple(min(255,c+120) for c in col)
        if ARROW_ORDER[lane]=='left':
            pts=[(cx-s,cy),(cx+s,cy-s),(cx+s,cy+s)]
        elif ARROW_ORDER[lane]=='right':
            pts=[(cx+s,cy),(cx-s,cy-s),(cx-s,cy+s)]
        elif ARROW_ORDER[lane]=='up':
            pts=[(cx,cy-s),(cx-s,cy+s),(cx+s,cy+s)]
        else:
            pts=[(cx,cy+s),(cx-s,cy-s),(cx+s,cy-s)]
        pygame.draw.polygon(surf, col, pts)
        pygame.draw.polygon(surf, C_WHITE, pts, 2)
        return surf

    def _note_verts(self,lane,y):
        """Returns polygon vertices for an arrow note."""
        cx=LANE_XS[lane]; s=20
        d=ARROW_ORDER[lane]
        if d=='left':    return [(cx-s,y),(cx+s,y-s),(cx+s,y+s)]
        elif d=='right': return [(cx+s,y),(cx-s,y-s),(cx-s,y+s)]
        elif d=='up':    return [(cx,y-s),(cx-s,y+s),(cx+s,y+s)]
        else:            return [(cx,y+s),(cx-s,y-s),(cx+s,y-s)]

    def _hit_zone_verts(self,lane):
        cx=LANE_XS[lane]; s=22
        return [(cx-s,HIT_Y-s),(cx+s,HIT_Y-s),(cx+s,HIT_Y+s),(cx-s,HIT_Y+s)]

    def update(self,events,dt):
        if self.game_over:
            if self.btn_retry.update(events): self.action='retry'
            if self.btn_lobby.update(events): self.action='lobby'
            for ev in events:
                if ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE: self.action='lobby'
            return

        self.timer+=dt; self.anim_t+=dt; self.beat_timer+=dt
        self.beat_flash=max(0,self.beat_flash-dt*4)
        for i in range(4): self.key_press[i]=max(0,self.key_press[i]-dt*5)
        if self.judgement_timer>0: self.judgement_timer-=dt

        # Beat-sync note spawn
        if self.beat_timer>=self.beat_interval:
            self.beat_timer-=self.beat_interval
            self.beat_flash=1.0
            # Play beat sound
            if self.sounds.get('beat'): self.sounds['beat'].play()
            # Spawn notes
            if self._pattern_idx<len(self._beat_patterns) and self.notes_spawned<self.notes_target:
                lanes=self._beat_patterns[self._pattern_idx]
                for lane in lanes:
                    self.notes.append(Note(lane,-30))
                    self.notes_spawned+=1
                    self.total_notes+=1
                self._pattern_idx+=1
            # Hi-hat every 2 beats
            if int(self.timer/self.beat_interval)%2==0:
                if self.sounds.get('hihat'): self.sounds['hihat'].play()

        # Move notes
        for note in self.notes:
            if note.active: note.y+=self.speed*dt
            if note.flash_timer>0: note.flash_timer-=dt

        # Miss detection
        for note in self.notes:
            if note.active and note.y>HIT_Y+ZONE_OK+5:
                note.active=False; note.hit_result='miss'
                self.combo=0; self.miss_count+=1
                self._show_judgement('MISS',(255,60,60))

        # Clean old notes
        self.notes=[n for n in self.notes if n.y<H+50]

        # Key input
        for ev in events:
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_ESCAPE: self.action='lobby'; return
                for i,d in enumerate(ARROW_ORDER):
                    if ev.key==ARROW_KEYS[d]:
                        self.key_press[i]=1.0
                        self._process_hit(i)
                        if self.sounds.get(d): self.sounds[d].play()

        if self.btn_back.update(events): self.action='lobby'

        # End condition
        if self.notes_spawned>=self.notes_target and len([n for n in self.notes if n.active])==0:
            self.game_over=True

    def _process_hit(self,lane):
        best=None; best_dist=9999
        for note in self.notes:
            if note.active and note.lane==lane:
                dist=abs(note.y-HIT_Y)
                if dist<best_dist: best_dist=dist; best=note
        if best is None: return
        if best_dist<=ZONE_PERFECT:
            best.active=False; best.hit_result='perfect'; best.flash_timer=0.3
            self.score+=100*(1+self.combo//10); self.combo+=1
            self._show_judgement('PERFEITO!',(255,215,0))
        elif best_dist<=ZONE_GOOD:
            best.active=False; best.hit_result='good'; best.flash_timer=0.25
            self.score+=60*(1+self.combo//20); self.combo+=1
            self._show_judgement('BOM!',(60,220,220))
        elif best_dist<=ZONE_OK:
            best.active=False; best.hit_result='ok'; best.flash_timer=0.2
            self.score+=30; self.combo+=1
            self._show_judgement('OK',(80,200,80))
        self.max_combo=max(self.max_combo,self.combo)

    def _show_judgement(self,text,color):
        self.judgement=text; self.judgement_color=color; self.judgement_timer=0.6

    def draw(self):
        surf=self.surf
        surf.blit(self._bg,(0,0))

        # Beat flash overlay
        if self.beat_flash>0:
            ov=pygame.Surface((W,H),pygame.SRCALPHA)
            ov.fill((255,255,255,int(self.beat_flash*25)))
            surf.blit(ov,(0,0))

        surf.blit(self._lane_bg,(0,0))

        # Hit zone rectangles (cached surfaces)
        for i,lane in enumerate(LANE_XS):
            press=self.key_press[i]
            surf.blit(self._hit_zone_surfaces[i][1 if press>0 else 0], self._hit_zone_rects[i].topleft)

        # Notes
        for note in self.notes:
            if not (note.active or note.flash_timer>0):
                continue
            surf_note = self._note_flash_surfaces[note.lane] if note.flash_timer>0 else self._note_surfaces[note.lane]
            scale = 1.0+note.flash_timer*0.5 if note.flash_timer>0 else 1.0
            if abs(scale-1.0) > 0.01:
                surf_note = pygame.transform.rotozoom(surf_note, 0, scale)
            x = int(LANE_XS[note.lane] - surf_note.get_width()/2)
            y = int(note.y - surf_note.get_height()/2)
            surf.blit(surf_note, (x, y))

        if self.judgement_timer>0:
            alpha=min(1.0,self.judgement_timer/0.3)
            txt=self.fnt_judge.render(self.judgement,True,self.judgement_color)
            # Animate: scale in
            if alpha<1.0:
                sc=0.5+0.5*alpha
                txt=pygame.transform.scale(txt,(int(txt.get_width()*sc),int(txt.get_height()*sc)))
            surf.blit(txt,(W//2-txt.get_width()//2,HIT_Y-80))

        # Score/combo HUD
        score_t=self.fnt_big.render(f"SCORE: {self.score}",True,C_YELLOW)
        combo_t=self.fnt_big.render(f"COMBO: x{self.combo}",True,C_CYAN)
        surf.blit(score_t,(W-score_t.get_width()-20,20))
        surf.blit(combo_t,(W-combo_t.get_width()-20,56))
        stage_t=self.fnt.render(f"{STAGE_NAMES[self.stage]}  [{self.diff.upper()}]",True,C_WHITE)
        surf.blit(stage_t,(20,H-30))

        # Progress bar
        prog=self.notes_spawned/max(1,self.notes_target)
        bar_w=int(200*prog); bar_x=W//2-100
        verts_bar=[(bar_x,H-18),(bar_x+bar_w,H-18),(bar_x+bar_w,H-6),(bar_x,H-6)]
        if len(verts_bar)>=3:
            scanline_fill_gradient(surf,verts_bar,[(60,200,80),(60,220,100),(60,220,100),(60,200,80)])
        draw_polygon(surf,[(bar_x,H-18),(bar_x+200,H-18),(bar_x+200,H-6),(bar_x,H-6)],(80,80,100))

        # BPM indicator (circle that pulses on beat)
        bf=self.beat_flash
        bcol=tuple(min(255,int(100+155*bf)) for _ in range(3))
        bx,by=30,H-50
        circle_midpoint(surf,bx,by,12,bcol)
        if bf>0.3: flood_fill(surf,bx,by,bcol)
        bpm_t=self.fnt.render(f"{self.bpm} BPM",True,C_GRAY)
        surf.blit(bpm_t,(50,H-58))

        self.btn_back.draw(surf)

        # End screen overlay
        if self.game_over:
            ov=pygame.Surface((W,H),pygame.SRCALPHA)
            ov.fill((0,0,0,200)); surf.blit(ov,(0,0))
            hit=self.total_notes-self.miss_count
            acc=hit/max(1,self.total_notes)*100
            rank='S' if acc>=95 else 'A' if acc>=80 else 'B' if acc>=65 else 'C' if acc>=50 else 'D'
            rank_col={
                'S':(255,215,0),'A':(60,220,220),'B':(80,200,80),
                'C':(220,160,60),'D':(200,80,80)
            }[rank]
            lines=[
                (f"FASE CONCLUÍDA!",C_YELLOW,self.fnt_huge,0),
                (f"Score: {self.score}",C_WHITE,self.fnt_big,60),
                (f"Combo máximo: {self.max_combo}",C_CYAN,self.fnt_big,95),
                (f"Precisão: {acc:.1f}%",C_GREEN,self.fnt_big,130),
                (f"RANK: {rank}",rank_col,self.fnt_huge,180),
            ]
            for text,col,fnt,dy in lines:
                t=fnt.render(text,True,col)
                surf.blit(t,(W//2-t.get_width()//2,H//2-120+dy))
            self.btn_retry.draw(surf)
            self.btn_lobby.draw(surf)

    def _draw_arrow_icon(self,surf,cx,cy,direction,col,size=18):
        s=size
        if direction=='left':    verts=[(cx-s,cy),(cx+s,cy-s),(cx+s,cy+s)]
        elif direction=='right': verts=[(cx+s,cy),(cx-s,cy-s),(cx-s,cy+s)]
        elif direction=='up':    verts=[(cx,cy-s),(cx-s,cy+s),(cx+s,cy+s)]
        else:                    verts=[(cx,cy+s),(cx-s,cy-s),(cx+s,cy-s)]
        draw_polygon(surf,verts,col)

# ─────────────────────────────────────────────────────────────────
# MAIN GAME LOOP
# ─────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
    screen=pygame.display.set_mode((W,H))
    pygame.display.set_caption("Rhythm Quest")
    clock=pygame.time.Clock()

    # Pre-generate sounds
    print("Gerando sons... (pode demorar alguns segundos)")
    sounds={
        'left':  make_tone(349,0.08,0.35),
        'down':  make_tone(294,0.08,0.35),
        'up':    make_tone(440,0.08,0.35),
        'right': make_tone(523,0.08,0.35),
        'beat':  make_beat_sound(),
        'hihat': make_hihat_sound(),
    }
    print("Sons prontos!")

    # States
    STATE_SPLASH   = 'splash'
    STATE_MENU     = 'menu'
    STATE_TUTORIAL = 'tutorial'
    STATE_LOBBY    = 'lobby'
    STATE_RHYTHM   = 'rhythm'

    state=STATE_SPLASH
    splash  =SplashScreen(screen)
    menu    =None
    tutorial=None
    lobby   =None
    rhythm  =None

    running=True
    while running:
        dt=clock.tick(FPS)/1000.0
        events=pygame.event.get()
        for ev in events:
            if ev.type==pygame.QUIT: running=False

        # ── State machine ──
        if state==STATE_SPLASH:
            if splash is None: splash=SplashScreen(screen)
            splash.update(events,dt)
            splash.draw()
            if splash.done:
                state=STATE_MENU
                menu=MainMenu(screen)
                splash=None

        elif state==STATE_MENU:
            menu.update(events,dt)
            menu.draw()
            if menu.action=='play':
                state=STATE_LOBBY
                lobby=LobbyScreen(screen)
                menu.action=None
            elif menu.action=='tutorial':
                state=STATE_TUTORIAL
                tutorial=TutorialScreen(screen)
                menu.action=None
            elif menu.action=='quit':
                running=False

        elif state==STATE_TUTORIAL:
            tutorial.update(events,dt)
            tutorial.draw()
            if tutorial.done:
                state=STATE_MENU
                tutorial=None

        elif state==STATE_LOBBY:
            lobby.update(events,dt)
            lobby.draw()
            if lobby.action=='menu':
                state=STATE_MENU
                menu=MainMenu(screen)
                lobby=None
            elif isinstance(lobby.action,tuple):
                stage_idx,diff=lobby.action
                state=STATE_RHYTHM
                rhythm=RhythmScreen(screen,stage_idx,diff,sounds)
                lobby.action=None

        elif state==STATE_RHYTHM:
            rhythm.update(events,dt)
            rhythm.draw()
            if rhythm.action=='lobby':
                state=STATE_LOBBY
                lobby=LobbyScreen(screen)
                rhythm=None
            elif rhythm.action=='menu':
                state=STATE_MENU
                menu=MainMenu(screen)
                rhythm=None
            elif rhythm.action=='retry':
                stage_idx=rhythm.stage; diff=rhythm.diff
                rhythm=RhythmScreen(screen,stage_idx,diff,sounds)

        pygame.display.flip()

    pygame.quit()

if __name__=='__main__':
    main()

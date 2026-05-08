from src.funcs.cg_lib import line_bresenham, scanline_fill

def _txt(screen, font, text, x, y, color=(255,255,255), center=False):
        # Renderiza texto com a fonte pygame e blit (como Button da lib)
        surf = font.render(text, True, color)
        if center:
            x -= surf.get_width()  // 2
            y -= surf.get_height() // 2
        screen.blit(surf, (x, y))

def _draw_btn(screen, bx, by, bw, bh, label, font,
                  active=False, color=(115,75,250)):
        bg  = tuple(min(255, c // 2 + (30 if active else 0)) for c in color)
        brd = color if active else tuple(c // 2 for c in color)
        scanline_fill(screen, [(bx,by),(bx+bw,by),(bx+bw,by+bh),(bx,by+bh)], bg)
        for off in range(2 if active else 1):
            o = off
            line_bresenham(screen, bx+o,    by+o,    bx+bw-o, by+o,    brd)
            line_bresenham(screen, bx+bw-o, by+o,    bx+bw-o, by+bh-o, brd)
            line_bresenham(screen, bx+bw-o, by+bh-o, bx+o,    by+bh-o, brd)
            line_bresenham(screen, bx+o,    by+bh-o, bx+o,    by+o,    brd)
        tc = (255, 255, 255) if active else (180, 180, 210)
        _txt(screen, font, label, bx + bw // 2, by + bh // 2, tc, center=True)
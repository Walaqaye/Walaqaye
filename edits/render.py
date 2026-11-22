import numpy as np, subprocess, math, sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
FPS = 30000 / 1001
SRC = sys.argv[1]
OUT = sys.argv[2]
STILLS = [float(x) for x in sys.argv[3:]]

FB = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
FXB = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
FSB = '/usr/share/fonts/opentype/inter/Inter-SemiBold.otf'
FMD = '/usr/share/fonts/opentype/inter/Inter-Medium.otf'
FSERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FMONO = '/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf'
_fc = {}
def F(p, s):
    k = (p, int(s))
    if k not in _fc: _fc[k] = ImageFont.truetype(p, int(s))
    return _fc[k]

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def lerp(a, b, t): return a + (b - a) * t
def prog(t, a, d): return clamp((t - a) / d)
def eout(x): return 1 - (1 - x) ** 3
def ein(x): return x ** 3
def eio(x): return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def eback(x, s=1.9):
    x -= 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2

def tsize(font, text):
    b = font.getbbox(text)
    return b[2] - b[0], b[3] - b[1], b

def fit(path, text, maxw, start):
    s = start
    while s > 14 and tsize(F(path, s), text)[0] > maxw: s -= 2
    return F(path, s)

def rrect(w, h, r, fill, outline=None, width=0):
    im = Image.new('RGBA', (int(w), int(h)), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=fill, outline=outline, width=width)
    return im

def with_shadow(img, blur=22, off=(0, 14), op=110):
    pad = blur * 2 + max(abs(off[0]), abs(off[1]))
    w, h = img.size
    out = Image.new('RGBA', (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    a = img.split()[3].point(lambda v: v * op // 255)
    sh = Image.new('RGBA', img.size, (0, 0, 0, 255)); sh.putalpha(a)
    out.alpha_composite(sh, (pad + off[0], pad + off[1]))
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(img, (pad, pad))
    return out

def place(canvas, img, cx, cy, scale=1.0, angle=0.0, alpha=1.0):
    if alpha <= 0.003 or scale <= 0.01: return
    im = img
    if abs(scale - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if abs(angle) > 0.05:
        im = im.rotate(angle, Image.BICUBIC, expand=True)
    if alpha < 0.999:
        a = im.split()[3].point(lambda v: int(v * alpha))
        im = im.copy(); im.putalpha(a)
    x, y = int(cx - im.width / 2), int(cy - im.height / 2)
    canvas.alpha_composite(im, (0, 0), (max(0, -x), max(0, -y))) if False else None
    # manual clipped composite
    sx, sy = max(0, -x), max(0, -y)
    dx, dy = max(0, x), max(0, y)
    w = min(im.width - sx, canvas.width - dx); h = min(im.height - sy, canvas.height - dy)
    if w <= 0 or h <= 0: return
    canvas.alpha_composite(im.crop((sx, sy, sx + w, sy + h)), (dx, dy))

def cam(frame, z, cx, cy, dx=0, dy=0):
    z = max(z, 1.0)
    if abs(dx) + abs(dy) > 0.2: z = max(z, 1.05)
    if z <= 1.0005: return frame
    cw, ch = W / z, H / z
    x0 = clamp(cx * W - cw / 2 + dx / z, 0, W - cw); y0 = clamp(cy * H - ch / 2 + dy / z, 0, H - ch)
    return frame.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))

def pixelate(img, b):
    b = int(b)
    if b <= 1: return img
    return img.resize((max(1, W // b), max(1, H // b)), Image.BILINEAR).resize((W, H), Image.NEAREST)

def shake(t, hits, amp=26, dur=0.45):
    dx = dy = 0.0
    for h in hits:
        u = t - h
        if 0 <= u < dur:
            k = amp * math.exp(-u * 9)
            dx += k * math.sin(u * 95); dy += k * math.cos(u * 77)
    return dx, dy

def star(d, cx, cy, r, fill):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)

def check(d, x, y, s, fill, width, p=1.0):
    a, b, c = (x + s * .18, y + s * .52), (x + s * .42, y + s * .76), (x + s * .84, y + s * .26)
    if p <= 0: return
    p1 = min(p / .4, 1)
    d.line([a, (lerp(a[0], b[0], p1), lerp(a[1], b[1], p1))], fill=fill, width=width, joint='curve')
    if p > .4:
        p2 = (p - .4) / .6
        d.line([b, (lerp(b[0], c[0], p2), lerp(b[1], c[1], p2))], fill=fill, width=width, joint='curve')

# ---------------------------------------------------------------- 1. HEADLINE WALL
HL = [
    (0.15, 'ASALAAMU CALAYKUM', 'kicker', .355, -4),
    (2.70, 'QALAB CIYAAREED CUSUB', 'paper', .46, 3),
    (3.90, 'TAYO SARE!', 'red', .555, -2.5),
    (5.00, 'WAXAAD RABTO WAA YAAL', 'paper', .65, 3.5),
    (5.90, 'KABO • BOORSOOYIN • QALAB', 'black', .745, -3),
    (6.40, 'LA SOCO!', 'yellow', .845, 2),
]
def headline_img(text, style, maxw=940):
    if style == 'paper':
        f = fit(FSERIF, text, maxw - 80, 96)
        tw, th, bb = tsize(f, text)
        w, h = tw + 80, th + 110
        im = Image.new('RGBA', (w, h), (244, 238, 224, 255)); d = ImageDraw.Draw(im)
        d.text((40 - bb[0], 62 - bb[1]), text, font=f, fill=(18, 18, 18))
        d.line([30, 22, w - 30, 22], fill=(18, 18, 18), width=3); d.line([30, 30, w - 30, 30], fill=(18, 18, 18), width=1)
        d.text((30, 36), 'WARKA MAANTA  •  2026', font=F(FMONO, 18), fill=(90, 80, 70))
        d.line([30, h - 22, w - 30, h - 22], fill=(18, 18, 18), width=2)
        return with_shadow(im, 14, (0, 10), 140)
    bgc, fg = {'red': ((222, 28, 40), (255, 255, 255)), 'black': ((14, 14, 16), (255, 255, 255)),
               'yellow': ((255, 214, 0), (14, 14, 16)), 'kicker': ((14, 14, 16), (255, 255, 255))}[style]
    tagw = 150 if style == 'kicker' else 0
    f = fit(FB, text, maxw - 80 - tagw, 110 if style in ('red', 'yellow') else 84)
    tw, th, bb = tsize(f, text)
    w, h = tw + 80 + tagw, th + 64
    im = Image.new('RGBA', (w, h), bgc + (255,)); d = ImageDraw.Draw(im)
    if tagw:
        d.rectangle([0, 0, tagw - 10, h], fill=(222, 28, 40))
        d.ellipse([22, h / 2 - 9, 40, h / 2 + 9], fill=(255, 255, 255))
        d.text((50, h / 2), 'TOOS', font=F(FB, 34), fill=(255, 255, 255), anchor='lm')
    d.text((40 + tagw - bb[0], 32 - bb[1]), text, font=f, fill=fg)
    return with_shadow(im, 14, (0, 10), 150)
HL_IMG = [headline_img(t, s) for _, t, s, _, _ in HL]

def fx_headlines(t, base):
    if t > 7.35: return base, None
    hits = [h[0] for h in HL]
    dx, dy = shake(t, hits)
    fr = cam(base, 1.0, .5, .5, dx, dy)
    n = sum(1 for h in hits if t >= h)
    exitp = eio(prog(t, 6.95, 0.38))
    dim = 0.06 * n * (1 - exitp)
    ov = Image.new('RGBA', (W, H), (0, 0, 0, int(255 * dim)))
    for i, (t0, txt, st, y, ang) in enumerate(HL):
        if t < t0: continue
        p = prog(t, t0, 0.22)
        side = -1 if i % 2 == 0 else 1
        x = W / 2 + side * (1 - eout(p)) * 900
        sc = lerp(1.35, 1.0, eback(p, 1.4))
        ex = exitp
        x += -side * ex * 1300
        place(ov, HL_IMG[i], x, y * H + ex * (i - 2.5) * 60, sc, ang + side * 8 * (1 - p), 1 - ex * 0.3)
    # impact flash
    for h in hits:
        u = t - h
        if 0 <= u < 0.08:
            ov.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(70 * (1 - u / .08)))))
    return fr, ov

# ---------------------------------------------------------------- 2. CHAT TAKEOVER
MSGS = [
    (7.35, 'c', 'Walaal, alaabtii aad noo ballan qaadday?'),
    (8.45, 's', 'Haa! Maanta ayaan idin tusaynaa'),
    (9.60, 'c', 'Maxaa cusub?'),
    (10.45, 's', 'Qalab jirkaaga ilaaliya'),
    (11.40, 'c', 'Ciyaarta ma ku habboon yihiin?'),
    (12.40, 's', 'Haa, si aad nabad ugu ciyaarto'),
    (13.35, 'c', 'Hadda na tus!'),
    (13.95, 's', 'Bal daawo...'),
]
def wrap(text, font, maxw):
    words, lines, cur = text.split(), [], ''
    for w_ in words:
        tryl = (cur + ' ' + w_).strip()
        if tsize(font, tryl)[0] <= maxw: cur = tryl
        else: lines.append(cur); cur = w_
    lines.append(cur); return lines

def bubble(text, who, k):
    fs = int(46 * (1 + 0.07 * k))
    f = F(FSB, fs)
    lines = wrap(text, f, int(660 * (1 + .05 * k)))
    lh = int(fs * 1.28)
    tw = max(tsize(f, l)[0] for l in lines)
    w, h = tw + 72, lh * len(lines) + 46
    bg = (255, 255, 255, 255) if who == 'c' else (20, 132, 255, 255)
    fg = (20, 20, 24) if who == 'c' else (255, 255, 255)
    im = Image.new('RGBA', (w + 20, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ox = 20 if who == 'c' else 0
    d.rounded_rectangle([ox, 0, ox + w - 1, h - 1], 40, fill=bg)
    if who == 'c': d.polygon([(ox + 6, h - 34), (0, h - 2), (ox + 40, h - 10)], fill=bg)
    else: d.polygon([(w - 6, h - 34), (w + 19, h - 2), (w - 40, h - 10)], fill=bg)
    for i, l in enumerate(lines):
        d.text((ox + 36, 23 + i * lh + lh / 2), l, font=f, fill=fg, anchor='lm')
    return with_shadow(im, 12, (0, 8), 90)
BUB = [bubble(m[2], m[1], i) for i, m in enumerate(MSGS)]
def typing_img(phase):
    im = rrect(170, 92, 46, (20, 132, 255, 255)); d = ImageDraw.Draw(im)
    for i in range(3):
        a = 0.5 + 0.5 * math.sin(phase * 9 - i * 1.1)
        d.ellipse([38 + i * 36 - 9, 46 - 9 - a * 6, 38 + i * 36 + 9, 46 + 9 - a * 6], fill=(255, 255, 255, int(150 + 105 * a)))
    return with_shadow(im, 10, (0, 6), 80)
def chat_header():
    im = Image.new('RGBA', (W, 170), (18, 18, 22, 235)); d = ImageDraw.Draw(im)
    d.ellipse([40, 45, 120, 125], fill=(20, 132, 255))
    d.text((80, 85), 'H', font=F(FB, 44), fill='white', anchor='mm')
    d.text((145, 62), 'Hurre New Sports', font=F(FXB, 40), fill='white', anchor='lm')
    d.ellipse([146, 100, 164, 118], fill=(46, 204, 113))
    d.text((174, 109), 'online  •  fariimaha macaamiisha', font=F(FMD, 28), fill=(170, 170, 180), anchor='lm')
    return im
CHAT_HDR = chat_header()

def fx_chat(t, base):
    if not (7.2 <= t < 15.5): return base, None
    out_p = eio(prog(t, 14.65, 0.6))
    n_vis = [i for i, m in enumerate(MSGS) if t >= m[0] - (0.5 if m[1] == 's' else 0)]
    grow = clamp(len(n_vis) / len(MSGS))
    blur = 10 * grow * (1 - out_p)
    fr = base.filter(ImageFilter.GaussianBlur(blur)) if blur > 0.4 else base
    ov = Image.new('RGBA', (W, H), (0, 0, 0, int(255 * 0.42 * grow * (1 - out_p))))
    hp = eout(prog(t, 7.2, 0.35)) * (1 - out_p)
    ov.alpha_composite(CHAT_HDR, (0, int(-170 + 170 * hp))) if hp > 0 else None
    anchor = H - 150
    gap = 16
    for i in n_vis:
        m = MSGS[i]
        # push-up offset from later messages
        off = 0
        for k in n_vis:
            if k > i:
                st = MSGS[k][0] - (0.5 if MSGS[k][1] == 's' else 0)
                off += (BUB[k].height - 40 + gap) * eout(prog(t, st, 0.28))
        img = BUB[i]
        yb = anchor - off - out_p * 2300
        if m[1] == 's' and t < m[0]:
            ti = typing_img(t)
            place(ov, ti, W - 60 - ti.width / 2, yb - ti.height / 2 + 30, eback(prog(t, m[0] - .5, .2)), 0, 1)
            continue
        p = prog(t, m[0], 0.3)
        sc = lerp(0.5, 1, eback(p))
        x = 40 + img.width / 2 - 20 if m[1] == 'c' else W - 40 - img.width / 2 + 20
        place(ov, img, x, yb - img.height / 2 + 20, sc, 0, clamp(p * 3))
    return fr, ov

# ---------------------------------------------------------------- 3. DIGITAL ZOOM
ZK = [  # (t, zoom, cx, cy)
    (18.3, 1.0, .5, .45), (23.0, 1.0, .5, .45), (23.7, 2.0, .57, .40), (25.3, 2.0, .57, .40), (25.9, 1.0, .5, .45),
    (27.3, 1.0, .5, .45), (27.9, 1.6, .48, .50), (29.3, 1.6, .48, .50), (29.8, 1.0, .5, .45),
    (31.7, 1.0, .5, .45), (32.3, 1.45, .56, .33), (34.8, 1.45, .56, .33), (35.4, 1.0, .5, .45)]
ENH = [23.0, 27.3, 31.7]
def zoom_at(t):
    for a, b in zip(ZK, ZK[1:]):
        if a[0] <= t <= b[0]:
            u = eio((t - a[0]) / (b[0] - a[0]))
            return lerp(a[1], b[1], u), lerp(a[2], b[2], u), lerp(a[3], b[3], u)
    return 1, .5, .5
SCAN = Image.new('RGBA', (W, H), (0, 0, 0, 0))
_d = ImageDraw.Draw(SCAN)
for y in range(0, H, 6): _d.line([0, y, W, y], fill=(0, 0, 0, 34), width=2)
def lower_tag(title, sub, col):
    f1, f2 = F(FB, 64), F(FMONO, 30)
    w = max(tsize(f1, title)[0], tsize(f2, sub)[0]) + 90
    im = Image.new('RGBA', (w, 170), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 14, 170], fill=col)
    d.rectangle([14, 0, w, 170], fill=(10, 10, 12, 215))
    d.text((44, 58), title, font=f1, fill='white', anchor='lm')
    d.text((46, 128), sub, font=f2, fill=col, anchor='lm')
    return im
TAG1 = lower_tag('ILAALADA ILKAHA', '> MOUTHGUARD  //  TARGET LOCKED', (255, 214, 0))
TAG3 = lower_tag('ILKAHAAGA ILAALI', '> PROTECTION  //  ACTIVE', (46, 204, 113))
def stamp_img():
    im = Image.new('RGBA', (620, 230), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = (46, 220, 120, 255)
    d.rounded_rectangle([6, 6, 614, 224], 26, outline=c, width=10)
    d.text((310, 88), 'TAYO SARE', font=F(FB, 86), fill=c, anchor='mm')
    d.text((310, 170), 'PROTECTION  100%', font=F(FMONO, 40), fill=c, anchor='mm')
    return im
STAMP = stamp_img()

def fx_zoom(t, base):
    if not (18.2 <= t < 35.7): return base, None
    z, cx, cy = zoom_at(t)
    fr = cam(base, z, cx, cy)
    for e in ENH:
        u = t - e
        if 0 <= u < 1.0:  # stepped enhance
            steps = [34, 20, 11, 5, 1]
            fr = pixelate(fr, steps[min(int(u / 0.2), 4)])
    for e in (25.3, 29.3, 34.8):
        u = t - e
        if 0 <= u < 0.35: fr = pixelate(fr, 2 + 14 * math.sin(u / .35 * math.pi))
    ov = SCAN.copy() if True else None
    a = eout(prog(t, 18.2, .4)) * (1 - prog(t, 35.4, .3))
    d = ImageDraw.Draw(ov)
    wc = (255, 255, 255, int(235 * a))
    m, L = 50, 90
    for (x, y, sx, sy) in [(m, m + 150, 1, 1), (W - m, m + 150, -1, 1), (m, H - m - 60, 1, -1), (W - m, H - m - 60, -1, -1)]:
        d.line([x, y, x + sx * L, y], fill=wc, width=7); d.line([x, y, x, y + sy * L], fill=wc, width=7)
    if int(t * 2) % 2 == 0: d.ellipse([90, 240, 124, 274], fill=(255, 40, 40, int(255 * a)))
    d.text((138, 257), 'REC', font=F(FMONO, 38), fill=wc, anchor='lm')
    fn = int((t % 1) * 30)
    d.text((W - 90, 257), f'00:00:{int(t):02d}:{fn:02d}', font=F(FMONO, 36), fill=wc, anchor='rm')
    d.text((90, H - 185), f'ZOOM {z:.1f}x', font=F(FMONO, 44), fill=(255, 214, 0, int(255 * a)), anchor='lm')
    d.rectangle([90, H - 140, 90 + 360, H - 128], outline=wc, width=2)
    d.rectangle([90, H - 140, 90 + 360 * (z - 1) / 1.2, H - 128], fill=(255, 214, 0, int(255 * a)))
    d.text((W - 90, H - 185), 'ISO 400  F/1.8', font=F(FMONO, 32), fill=wc, anchor='rm')
    # center crosshair
    cxp, cyp = W / 2, H / 2
    d.line([cxp - 30, cyp, cxp + 30, cyp], fill=(255, 255, 255, int(120 * a)), width=3)
    d.line([cxp, cyp - 30, cxp, cyp + 30], fill=(255, 255, 255, int(120 * a)), width=3)
    for e in ENH:
        u = t - e
        if 0 <= u < 1.2:
            dots = '▮' * (1 + min(int(u / .2), 4)) + '▯' * (4 - min(int(u / .2), 4))
            lbl = 'ENHANCING ' + ('.' * (int(u * 8) % 4))
            d.rounded_rectangle([W / 2 - 250, 330, W / 2 + 250, 410], 14, fill=(0, 0, 0, 170))
            d.text((W / 2, 370), lbl, font=F(FMONO, 40), fill=(255, 214, 0), anchor='mm')
    # target box during zoom 1
    if 23.7 <= t < 25.6:
        p = eback(prog(t, 23.7, .3)); s = lerp(420, 240, p); bx, by = W * .58, H * .53
        col = (255, 214, 0, 255)
        for sx in (-1, 1):
            for sy in (-1, 1):
                x0, y0 = bx + sx * s / 2, by + sy * s / 2
                d.line([x0, y0, x0 - sx * 60, y0], fill=col, width=8); d.line([x0, y0, x0, y0 - sy * 60], fill=col, width=8)
    if 23.9 <= t < 26.6:
        p = eout(prog(t, 23.9, .35)) * (1 - prog(t, 26.2, .4))
        place(ov, TAG1, 60 + TAG1.width / 2 - (1 - p) * 700, H * .70, 1, 0, p)
    if 28.1 <= t < 30.0:
        p = prog(t, 28.1, .2)
        place(ov, STAMP, W / 2, H * .72, lerp(2.2, 1, eout(p)), -8, clamp(p * 2) * (1 - prog(t, 29.6, .4)))
    if 32.2 <= t < 35.4:
        p = eout(prog(t, 32.2, .35)) * (1 - prog(t, 34.9, .4))
        place(ov, TAG3, 60 + TAG3.width / 2 - (1 - p) * 700, H * .72, 1, 0, p)
    if a < 1: ov.putalpha(ov.split()[3].point(lambda v: int(v * max(a, 0))))
    return fr, ov

# ---------------------------------------------------------------- 4. UI WORLD
def glass(base, box, r=36):
    x0, y0, x1, y1 = [int(v) for v in box]
    x0c, y0c, x1c, y1c = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    crop = base.crop((x0c, y0c, x1c, y1c)).filter(ImageFilter.GaussianBlur(22)).convert('RGBA')
    panel = Image.new('RGBA', (x1 - x0, y1 - y0), (0, 0, 0, 0))
    panel.paste(crop, (x0c - x0, y0c - y0))
    panel.alpha_composite(Image.new('RGBA', panel.size, (255, 255, 255, 150)))
    mask = Image.new('L', panel.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, panel.width - 1, panel.height - 1], r, fill=255)
    panel.putalpha(mask)
    ImageDraw.Draw(panel).rounded_rectangle([1, 1, panel.width - 2, panel.height - 2], r, outline=(255, 255, 255, 230), width=3)
    return panel

def card_icon(d, x, y, col, ang=0):
    d.rounded_rectangle([x, y, x + 46, y + 64], 7, fill=col)

def ui_content(kind, w, h, t):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    dark = (18, 18, 24)
    if kind == 'search':
        d.ellipse([34, h / 2 - 20, 66, h / 2 + 12], outline=dark, width=6)
        d.line([62, h / 2 + 8, 78, h / 2 + 24], fill=dark, width=7)
        full = 'kaararka garsooraha'
        n = int(clamp((t - 36.9) / 1.0) * len(full))
        txt = full[:n] + ('|' if int(t * 3) % 2 == 0 else '')
        d.text((100, h / 2), txt, font=F(FSB, 40), fill=dark, anchor='lm')
    elif kind == 'product':
        d.rounded_rectangle([30, 34, 160, 186], 20, fill=(255, 255, 255, 200))
        d.rounded_rectangle([52, 66, 104, 140], 8, fill=(255, 210, 0)); d.rounded_rectangle([88, 82, 140, 156], 8, fill=(225, 30, 40))
        d.text((182, 70), 'Kaararka', font=F(FB, 44), fill=dark, anchor='lm')
        d.text((182, 118), 'Garsooraha', font=F(FB, 44), fill=dark, anchor='lm')
        d.text((182, 164), 'Referee cards', font=F(FMD, 28), fill=(80, 80, 92), anchor='lm')
    elif kind in ('yellow', 'red'):
        col = (255, 210, 0) if kind == 'yellow' else (225, 30, 40)
        d.rounded_rectangle([28, h / 2 - 32, 72, h / 2 + 32], 7, fill=col)
        d.text((96, h / 2), 'Kaarka Jaalaha' if kind == 'yellow' else 'Kaarka Cas', font=F(FXB, 40), fill=dark, anchor='lm')
    elif kind == 'rating':
        for i in range(5): star(d, 56 + i * 62, 64, 27, (255, 176, 0))
        d.text((362, 64), '4.9', font=F(FB, 46), fill=dark, anchor='lm')
        d.text((32, 136), 'Tayo sare  •  la isku halleyn karo', font=F(FMD, 30), fill=(60, 60, 70), anchor='lm')
    elif kind == 'stock':
        d.ellipse([26, h / 2 - 28, 82, h / 2 + 28], fill=(34, 197, 94))
        check(d, 30, h / 2 - 26, 50, 'white', 7)
        d.text((102, h / 2), 'Waa diyaar', font=F(FXB, 42), fill=dark, anchor='lm')
    return im

UI = [  # kind, t_in, box(x0,y0,w,h), phase
    ('search', 36.6, (70, 200, 940, 110), 0.0),
    ('product', 37.5, (36, 560, 520, 220), 0.3),
    ('yellow', 38.6, (620, 560, 420, 110), 0.6),
    ('red', 39.4, (660, 700, 380, 110), 0.9),
    ('rating', 41.5, (36, 1060, 520, 190), 0.2),
    ('stock', 42.8, (660, 1120, 380, 110), 0.5),
]
def fx_ui(t, base):
    if not (36.4 <= t < 48.2): return base, None
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    vig = eout(prog(t, 36.4, .5)) * (1 - prog(t, 47.6, .5))
    ov.alpha_composite(Image.new('RGBA', (W, H), (10, 0, 30, int(60 * vig))))
    for i, (k, t0, (x, y, w, h), ph) in enumerate(UI):
        if t < t0: continue
        p = eback(prog(t, t0, .4))
        ex = ein(prog(t, 47.2 + i * .06, .35))
        bob = 10 * math.sin((t * 0.9 + ph) * 2 * math.pi)
        g = glass(base, (x, y + bob, x + w, y + bob + h), 30 if k != 'search' else 55)
        g.alpha_composite(ui_content(k, w, h, t))
        g = with_shadow(g, 18, (0, 14), 90)
        place(ov, g, x + w / 2, y + h / 2 + bob, lerp(.6, 1, p) * (1 - .3 * ex), 0, clamp(prog(t, t0, .15)) * (1 - ex))
    # Buy button + cursor tap
    if t >= 43.8:
        p = eback(prog(t, 43.8, .4)); ex = ein(prog(t, 47.5, .35))
        press = 1 - 0.08 * math.sin(clamp((t - 44.9) / .25) * math.pi)
        btn = rrect(620, 130, 65, (255, 90, 54, 255))
        bd = ImageDraw.Draw(btn); bd.text((310, 65), 'DALBO HADDA', font=F(FB, 52), fill='white', anchor='mm')
        btn = with_shadow(btn, 18, (0, 14), 120)
        place(ov, btn, W / 2, H * .83, lerp(.5, 1, p) * press * (1 - .3 * ex), 0, clamp(prog(t, 43.8, .15)) * (1 - ex))
        # ripple
        u = t - 44.9
        if 0 <= u < .6:
            d = ImageDraw.Draw(ov); rr = 40 + 300 * eout(u / .6)
            d.ellipse([W / 2 + 120 - rr, H * .83 + 20 - rr, W / 2 + 120 + rr, H * .83 + 20 + rr], outline=(255, 255, 255, int(200 * (1 - u / .6))), width=6)
        # cursor
        cp = eio(prog(t, 44.0, .8))
        cx_, cy_ = lerp(W + 80, W / 2 + 120, cp), lerp(H * .95, H * .83 + 20, cp)
        if ex < 1:
            d = ImageDraw.Draw(ov)
            pts = [(0, 0), (0, 62), (16, 48), (28, 74), (40, 68), (28, 44), (48, 44)]
            pts = [(cx_ + a_, cy_ + b_) for a_, b_ in pts]
            d.polygon(pts, fill=(255, 255, 255, int(255 * (1 - ex))), outline=(0, 0, 0, int(255 * (1 - ex))))
    return base, ov

# ---------------------------------------------------------------- 5. CHECKLIST
ITEMS = [('Cabbir yar', 55.9), ('Cabbir weyn', 56.8), ('Noocyo kala duwan', 65.8), ('Wax walba ku qaado', 69.7)]
CK_IN, CK_OUT = 51.7, 70.9
def fx_check(t, base):
    if not (CK_IN <= t < CK_OUT + .5): return base, None
    cw, ch = 940, 700
    card = rrect(cw, ch, 44, (255, 255, 255, 246)); d = ImageDraw.Draw(card)
    d.rounded_rectangle([40, 40, 220, 88], 24, fill=(255, 90, 54))
    d.text((130, 64), 'LIISKA', font=F(FB, 30), fill='white', anchor='mm')
    d.text((40, 150), 'BOORSOOYINKA JIIMKA', font=fit(FB, 'BOORSOOYINKA JIIMKA', 860, 66), fill=(16, 16, 20), anchor='lm')
    done = sum(1 for _, ti in ITEMS if t >= ti)
    d.text((cw - 40, 64), f'{done}/4', font=F(FB, 44), fill=(34, 197, 94) if done == 4 else (120, 120, 130), anchor='rm')
    d.rounded_rectangle([40, 196, cw - 40, 210], 7, fill=(232, 232, 238))
    bp = sum(eout(prog(t, ti, .4)) for _, ti in ITEMS) / 4
    if bp > 0: d.rounded_rectangle([40, 196, 40 + (cw - 80) * bp, 210], 7, fill=(34, 197, 94))
    for i, (txt, ti) in enumerate(ITEMS):
        y = 260 + i * 108
        rp = eout(prog(t, CK_IN + .35 + i * .12, .4))
        xo = (1 - rp) * 120
        p = prog(t, ti, .45)
        if p > 0:
            hl = eout(prog(t, ti, .35))
            d.rounded_rectangle([30 + xo, y - 8, 30 + xo + (cw - 60) * hl, y + 88], 22, fill=(226, 247, 234, 255))
        bs = 72
        if p <= 0:
            d.rounded_rectangle([50 + xo, y + 4, 50 + bs + xo, y + 4 + bs], 18, outline=(200, 200, 210), width=5)
        else:
            s = bs * eback(clamp(p * 1.6), 2.6)
            cxb, cyb = 50 + bs / 2 + xo, y + 4 + bs / 2
            d.rounded_rectangle([cxb - s / 2, cyb - s / 2, cxb + s / 2, cyb + s / 2], 18, fill=(34, 197, 94))
            check(d, cxb - bs / 2 + 4, cyb - bs / 2 + 4, bs - 8, 'white', 9, clamp((p - .2) / .6))
        d.text((150 + xo, y + 40), txt, font=F(FXB, 52), fill=(16, 16, 20, int(255 * rp)) if p <= 0 else (16, 16, 20), anchor='lm')
    card = with_shadow(card, 26, (0, 18), 130)
    pin = eout(prog(t, CK_IN, .5)); pout = ein(prog(t, CK_OUT, .4))
    bounce = 1 + 0.035 * sum(math.sin(clamp((t - ti) / .3) * math.pi) for _, ti in ITEMS if 0 <= t - ti < .3)
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    place(ov, card, W / 2, H - 70 - ch / 2 + (1 - pin) * 900 + pout * 900, bounce, -1.2 * (1 - pin), 1)
    # confetti on completion
    u = t - ITEMS[-1][1]
    if 0 <= u < 1.2:
        d2 = ImageDraw.Draw(ov); rng = np.random.default_rng(7)
        cols = [(255, 90, 54), (34, 197, 94), (20, 132, 255), (255, 214, 0)]
        for k in range(60):
            a_ = rng.uniform(-math.pi, 0); v = rng.uniform(500, 1300)
            x = W / 2 + math.cos(a_) * v * u; y = H * .62 + math.sin(a_) * v * u + 900 * u * u
            c = cols[k % 4]
            d2.rectangle([x, y, x + 16, y + 10], fill=c + (int(255 * (1 - u / 1.2)),))
    return base, ov

# ---------------------------------------------------------------- 6. PHONE MOCKUP + OUTRO
SW, SH = 560, 996
BODY = 24
def persp_coeffs(out_pts, in_pts):
    A, B = [], []
    for (x, y), (u, v) in zip(out_pts, in_pts):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()

def reels_ui(t):
    im = Image.new('RGBA', (SW, SH), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    g = Image.new('RGBA', (SW, 260), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
    for y in range(260): gd.line([0, y, SW, y], fill=(0, 0, 0, int(150 * y / 260)))
    im.alpha_composite(g, (0, SH - 260))
    d.text((28, 70), 'Reels', font=F(FB, 34), fill='white', anchor='lm')
    d.ellipse([28, SH - 170, 76, SH - 122], fill=(255, 90, 54))
    d.text((90, SH - 146), 'hurre.newsports', font=F(FXB, 24), fill='white', anchor='lm')
    d.text((28, SH - 96), 'Boorsooyinka jiimka  •  Hadda ka hel', font=F(FMD, 24), fill='white', anchor='lm')
    likes = 1200 + int(clamp((t - 71.5) / 4) * 3400)
    ix = SW - 50
    hp = 1 + 0.35 * math.sin(clamp((t - 74.4) / .3) * math.pi)
    r = 22 * hp
    hy = SH * .52
    d.ellipse([ix - r, hy - r * .9, ix, hy + r * .1], fill=(255, 48, 80)); d.ellipse([ix, hy - r * .9, ix + r, hy + r * .1], fill=(255, 48, 80))
    d.polygon([(ix - r, hy - r * .3), (ix + r, hy - r * .3), (ix, hy + r)], fill=(255, 48, 80))
    d.text((ix, hy + 48), f'{likes/1000:.1f}K', font=F(FXB, 22), fill='white', anchor='mm')
    d.rounded_rectangle([ix - 22, hy + 90, ix + 22, hy + 124], 10, outline='white', width=4)
    d.text((ix, hy + 148), '318', font=F(FXB, 22), fill='white', anchor='mm')
    d.polygon([(ix - 20, hy + 186), (ix + 22, hy + 202), (ix - 20, hy + 218), (ix - 12, hy + 202)], outline='white', fill=None, width=4)
    d.text((ix, hy + 240), 'Share', font=F(FXB, 20), fill='white', anchor='mm')
    # big heart double-tap
    u = t - 74.4
    if 0 <= u < .9:
        s = 90 * eback(clamp(u / .25)) ; a = int(255 * (1 - clamp((u - .5) / .4)))
        cx, cy = SW / 2, SH * .45 - u * 60
        d.ellipse([cx - s, cy - s * .9, cx, cy + s * .1], fill=(255, 255, 255, a)); d.ellipse([cx, cy - s * .9, cx + s, cy + s * .1], fill=(255, 255, 255, a))
        d.polygon([(cx - s, cy - s * .3), (cx + s, cy - s * .3), (cx, cy + s)], fill=(255, 255, 255, a))
    return im

OUTRO = []
OUTRO_IMG = [headline_img(x[1], x[2]) for x in OUTRO]
BAGTAG = lower_tag('BOORSADA JIIMKA', '> NIKE  //  CABBIR WEYN', (255, 90, 54))

def fx_phone(t, base):
    if t < 71.0: return base, None
    PH_IN, PH_OUT = 71.2, 76.0
    if t < PH_IN or t >= PH_OUT + .75:
        fr = base; ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    else:
        pin = eio(prog(t, PH_IN, .7)); pout = eio(prog(t, PH_OUT, .7))
        k = pin * (1 - pout)  # 0 = full frame, 1 = phone
        bg = base.resize((W // 8, H // 8)).filter(ImageFilter.GaussianBlur(4)).resize((W, H), Image.BICUBIC)
        bg = Image.blend(bg, Image.new('RGB', (W, H), (24, 10, 48)), 0.55)
        fr = Image.blend(base, bg, clamp(k * 3)) if k < .34 else bg
        full_s = W / SW
        s = lerp(full_s * 1.02, 1.0, k)
        yaw = math.radians(14 * math.sin((t - PH_IN) * 1.3)) * k
        pitch_y = lerp(H / 2, H * .47, k)
        # build phone at scale s
        sw, sh, bd = int(SW * s), int(SH * s), int(BODY * s)
        ph = Image.new('RGBA', (sw + 2 * bd, sh + 2 * bd), (0, 0, 0, 0)); d = ImageDraw.Draw(ph)
        d.rounded_rectangle([0, 0, ph.width - 1, ph.height - 1], int(78 * s), fill=(16, 16, 20), outline=(90, 90, 104), width=max(2, int(4 * s)))
        scr = base.resize((sw, sh), Image.BICUBIC).convert('RGBA')
        ui = reels_ui(t)
        if k < .999: ui.putalpha(ui.split()[3].point(lambda v: int(v * clamp(k * 1.5))))
        scr.alpha_composite(ui.resize((sw, sh), Image.BICUBIC))
        m = Image.new('L', (sw, sh), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, sw - 1, sh - 1], int(56 * s), fill=255)
        ph.paste(scr, (bd, bd), m)
        d.rounded_rectangle([ph.width / 2 - 70 * s, bd + 18 * s, ph.width / 2 + 70 * s, bd + 56 * s], int(20 * s), fill=(0, 0, 0))
        hw, hh = ph.width / 2, ph.height / 2
        D = 2600
        pts = []
        for (sx, sy) in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
            x = sx * hw * math.cos(yaw); z = sx * hw * math.sin(yaw)
            f = D / (D + z)
            pts.append((W / 2 + x * f, pitch_y + sy * hh * f))
        src = [(0, 0), (ph.width, 0), (ph.width, ph.height), (0, ph.height)]
        warped = ph.transform((W, H), Image.PERSPECTIVE, persp_coeffs(pts, src), Image.BICUBIC)
        sh_ = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        if k > .05:
            ImageDraw.Draw(sh_).ellipse([W / 2 - hw * .9, pitch_y + hh * .92, W / 2 + hw * .9, pitch_y + hh * 1.05], fill=(0, 0, 0, int(140 * k)))
            sh_ = sh_.filter(ImageFilter.GaussianBlur(30))
        ov = sh_; ov.alpha_composite(warped)
        # floating hearts
        if k > .5:
            dd = ImageDraw.Draw(ov); rng = np.random.default_rng(3)
            for j in range(8):
                st = PH_IN + .8 + j * .45; u = t - st
                if 0 <= u < 2.2:
                    x = W / 2 + 330 + rng.uniform(-40, 60) + 30 * math.sin(u * 4 + j); y = H * .74 - u * 420
                    r = 18 + 8 * (j % 3); a = int(230 * (1 - u / 2.2))
                    dd.ellipse([x - r, y - r * .9, x, y + r * .1], fill=(255, 48, 80, a)); dd.ellipse([x, y - r * .9, x + r, y + r * .1], fill=(255, 48, 80, a))
                    dd.polygon([(x - r, y - r * .3), (x + r, y - r * .3), (x, y + r)], fill=(255, 48, 80, a))
    # pop-out flash
    u = t - (PH_OUT + .7)
    if 0 <= u < .2: ov.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(150 * (1 - u / .2)))))
    if 77.2 <= t < 80.6:
        p = eout(prog(t, 77.2, .35)) * (1 - prog(t, 80.2, .4))
        place(ov, BAGTAG, 60 + BAGTAG.width / 2 - (1 - p) * 700, H * .16, 1, 0, p)
    hits = [o[0] for o in OUTRO]
    dx, dy = shake(t, hits, 22)
    if abs(dx) + abs(dy) > .2: fr = cam(fr, 1.0, .5, .5, dx, dy)
    for i, (t0, txt, st, y, ang) in enumerate(OUTRO):
        if t < t0: continue
        p = prog(t, t0, .22)
        place(ov, OUTRO_IMG[i], W / 2, y * H, lerp(1.6, 1, eback(p, 1.4)), ang, clamp(p * 4))
    return fr, ov


# ---------------------------------------------------------------- TIKTOK PROFILE (top)
def profile_img(following):
    name = 'Hurre New Sports'
    f1 = F(FB, 40)
    nw = tsize(f1, name)[0]
    bw = 210
    w, h = 150 + nw + 30 + bw + 22, 116
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 58, fill=(12, 12, 16, 200))
    # avatar with cyan/pink ring
    d.ellipse([12, 12, 104, 104], fill=(37, 244, 238)); d.ellipse([16, 12, 108, 104], fill=(254, 44, 85))
    d.ellipse([18, 16, 102, 100], fill=(12, 12, 16)); d.ellipse([22, 20, 98, 96], fill=(255, 255, 255))
    d.text((60, 58), 'H', font=F(FB, 46), fill=(12, 12, 16), anchor='mm')
    d.text((126, 44), name, font=f1, fill='white', anchor='lm')
    vx = 126 + nw + 24
    d.ellipse([vx - 15, 29, vx + 15, 59], fill=(32, 213, 236)); check(d, vx - 13, 31, 26, 'white', 4)
    d.text((128, 84), 'TikTok', font=F(FSB, 26), fill=(190, 190, 200), anchor='lm')
    bx = w - bw - 22
    if following:
        d.rounded_rectangle([bx, 28, bx + bw, 88], 14, fill=(60, 60, 70))
        d.text((bx + bw / 2, 58), 'Following', font=F(FXB, 30), fill='white', anchor='mm')
    else:
        d.rounded_rectangle([bx, 28, bx + bw, 88], 14, fill=(254, 44, 85))
        d.text((bx + bw / 2, 58), 'Follow', font=F(FXB, 32), fill='white', anchor='mm')
    return with_shadow(im, 14, (0, 8), 110)
PROF = [profile_img(False), profile_img(True)]
FOLLOW_T = 3.4
def fx_profile(t, base):
    p = eout(prog(t, 0.3, .5))
    hide = eio(prog(t, 7.0, .3)) * (1 - eio(prog(t, 15.3, .4)))  # chat header owns the top 7-15s
    a = p * (1 - hide)
    if a <= 0: return base, None
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    img = PROF[1 if t >= FOLLOW_T else 0]
    press = 1 - 0.05 * math.sin(clamp((t - FOLLOW_T + .1) / .25) * math.pi)
    place(ov, img, 34 + img.width / 2 - 20, 40 + img.height / 2 - 20 - (1 - p) * 200 - hide * 200, press, 0, a)
    return base, ov

EFFECTS = [fx_chat, fx_zoom, fx_ui, fx_check, fx_phone, fx_profile]

def render(t, frame):
    fr = frame
    ovs = []
    for fx in EFFECTS:
        fr, ov = fx(t, fr)
        if ov is not None: ovs.append(ov)
    out = fr.convert('RGBA')
    for ov in ovs: out.alpha_composite(ov)
    return out.convert('RGB')

def reader(ss=None, n=None):
    cmd = ['ffmpeg', '-v', 'error']
    if ss is not None: cmd += ['-ss', str(ss)]
    cmd += ['-i', SRC]
    if n: cmd += ['-frames:v', str(n)]
    cmd += ['-vf', f'scale={W}:{H}:flags=lanczos', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    return subprocess.Popen(cmd, stdout=subprocess.PIPE)

if STILLS:
    for ts in STILLS:
        p = reader(ts, 1); b = p.stdout.read(W * H * 3); p.wait()
        img = Image.frombytes('RGB', (W, H), b)
        render(ts, img).resize((W // 2, H // 2)).save(f'{OUT}_{ts:05.1f}.jpg', quality=85)
    sys.exit()

rd = reader()
wr = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', '30000/1001', '-i', '-',
                       '-i', SRC, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p',
                       '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', OUT], stdin=subprocess.PIPE)
i = 0
while True:
    b = rd.stdout.read(W * H * 3)
    if len(b) < W * H * 3: break
    t = i / FPS
    wr.stdin.write(render(t, Image.frombytes('RGB', (W, H), b)).tobytes())
    i += 1
    if i % 300 == 0: print(f'{t:.1f}s', flush=True)
wr.stdin.close(); wr.wait()
print('done', i)

"""MikroCAM splash screen generator.

Draws the splash procedurally: copper traces are real Shapely geometry, the cyan
isolation path is their buffered outline (what the CAM actually computes) and the
amber lines are a laser hatch of the copper-free area.

Usage: python make_splash.py <font_dir> <out_dir>
Fonts (SIL OFL 1.1): ChakraPetch-{Bold,SemiBold,Medium}.ttf, JetBrainsMono.ttf
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from shapely.affinity import rotate
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union

W, H = 720, 320          # logical size
SS = 4                   # supersampling factor for the master render
FONT_DIR = Path(sys.argv[1])
OUT_DIR = Path(sys.argv[2])

BG_TOP = (9, 13, 20)
BG_BOT = (14, 22, 32)
COPPER = (205, 124, 58)
COPPER_HI = (242, 170, 98)
CYAN = (70, 214, 232)
AMBER = (255, 181, 71)
WHITE = (238, 242, 246)
MUTED = (132, 146, 160)


def s(v):
    return v * SS


def sw(v):
    return max(1, round(v * SS))


def font(name, size):
    return ImageFont.truetype(str(FONT_DIR / name), s(size))


def mono(size, weight=500):
    f = font("JetBrainsMono.ttf", size)
    try:
        f.set_variation_by_axes([weight])
    except OSError:
        pass
    return f


def layer():
    return Image.new("RGBA", (s(W), s(H)), (0, 0, 0, 0))


def iter_polys(geom):
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    return [g for g in getattr(geom, "geoms", []) if isinstance(g, Polygon)]


def fill_geom(draw, geom, color):
    for poly in iter_polys(geom):
        draw.polygon([(s(x), s(y)) for x, y in poly.exterior.coords], fill=color)
        for hole in poly.interiors:
            draw.polygon([(s(x), s(y)) for x, y in hole.coords], fill=(0, 0, 0, 0))


def stroke_geom(draw, geom, color, width):
    lines = []
    for poly in iter_polys(geom):
        lines.append(poly.exterior.coords)
        lines.extend(h.coords for h in poly.interiors)
    for coords in lines:
        pts = [(s(x), s(y)) for x, y in coords]
        draw.line(pts, fill=color, width=max(1, round(s(width))), joint="curve")


def glow(img, radius, strength=1.0):
    g = img.filter(ImageFilter.GaussianBlur(s(radius)))
    if strength != 1.0:
        a = g.getchannel("A").point(lambda v: min(255, int(v * strength)))
        g.putalpha(a)
    return g


def mask_alpha(img, mask):
    a = ImageChops.multiply(img.getchannel("A"), mask)
    out = img.copy()
    out.putalpha(a)
    return out


# --------------------------------------------------------------------------- geometry
TW = 2.5    # trace width
PAD_R = 3.1
VIA_R, VIA_HOLE = 3.0, 1.25


def bus(points, n, pitch, width=TW):
    """n parallel traces following a 45-degree routed centerline."""
    center = LineString(points)
    out = []
    for k in range(n):
        off = (k - (n - 1) / 2) * pitch
        line = center if abs(off) < 1e-9 else center.offset_curve(off, join_style="mitre", mitre_limit=5)
        out.append(line)
    return [ln.buffer(width / 2, cap_style="flat", join_style="mitre", mitre_limit=5) for ln in out], out


def via(x, y):
    return Point(x, y).buffer(VIA_R, 32).difference(Point(x, y).buffer(VIA_HOLE, 24))


def qfp(cx, cy, pins, pitch, body):
    pads, pin_pts = [], {"L": [], "R": [], "T": [], "B": []}
    span = (pins - 1) * pitch
    half = body / 2
    for i in range(pins):
        o = -span / 2 + i * pitch
        pads.append(box(cx - half - 7, cy + o - 1.2, cx - half - 1, cy + o + 1.2))
        pads.append(box(cx + half + 1, cy + o - 1.2, cx + half + 7, cy + o + 1.2))
        pads.append(box(cx + o - 1.2, cy - half - 7, cx + o + 1.2, cy - half - 1))
        pads.append(box(cx + o - 1.2, cy + half + 1, cx + o + 1.2, cy + half + 7))
    return pads


copper = []
traces_center = []

# QFP in the middle of the art
CX, CY, PINS, PP, BODY = 580, 162, 8, 6.0, 44
copper += qfp(CX, CY, PINS, PP, BODY)
edge = BODY / 2 + 7

# chip fan-out buses (pitch == pin pitch)
for pts in (
    [(CX, CY - edge), (CX, CY - edge - 16), (CX + 44, CY - edge - 60), (CX + 44, -20)],                # top
    [(CX + edge, CY), (CX + edge + 18, CY), (CX + edge + 58, CY + 40), (W + 30, CY + 40)],            # right
    [(CX, CY + edge), (CX, CY + edge + 18), (CX - 46, CY + edge + 64), (CX - 46, H + 30)],            # bottom
):
    polys, lines = bus(pts, PINS, PP)
    copper += polys
    traces_center += lines

polys, lines = bus([(CX - edge, CY), (CX - edge - 22, CY), (CX - edge - 62, CY - 40), (CX - edge - 118, CY - 40)], PINS, PP)
copper += polys
for k, ln in enumerate(lines):
    x, y = ln.coords[-1]
    copper.append(LineString([(x, y), (x - 4 - (k % 2) * 8, y)]).buffer(TW / 2, cap_style="flat"))
    copper.append(via(x - 7 - (k % 2) * 8, y))

# secondary buses ending in vias / pads
polys, lines = bus([(250, 36), (430, 36), (462, 4), (462, -20)], 4, 7)
copper += polys
polys, lines = bus([(250, 272), (396, 272), (430, 238), (430, 222)], 4, 7)
copper += polys
for ln in lines:
    x, y = ln.coords[-1]
    copper.append(via(x, y - 3))

polys, lines = bus([(W + 20, 36), (690, 36), (660, 66), (660, 84)], 3, 7)
copper += polys
for ln in lines:
    x, y = ln.coords[-1]
    copper.append(Point(x, y + 2).buffer(PAD_R, 32))

# 0805 passives + short traces on the right
for (x, y, ang) in ((680, 118, 0), (694, 252, 90), (492, 222, 0)):
    p1 = box(x - 5.5, y - 3, x - 1.5, y + 3)
    p2 = box(x + 1.5, y - 3, x + 5.5, y + 3)
    copper += [rotate(p1, ang, origin=(x, y)), rotate(p2, ang, origin=(x, y))]

copper.append(LineString([(686, 118), (702, 118), (720, 100)]).buffer(TW / 2, cap_style="flat"))
copper.append(LineString([(694, 258), (694, 300), (720, 300)]).buffer(TW / 2, cap_style="flat"))
copper.append(LineString([(498, 222), (512, 222), (522, 212)]).buffer(TW / 2, cap_style="round"))
copper.append(via(525, 209))

for (x, y) in ((520, 58), (532, 58), (660, 214), (672, 214), (374, 196), (386, 196), (700, 150)):
    copper.append(via(x, y))

# ground pour in the top-right corner with a thermal relief

COPPER_GEOM = unary_union(copper).intersection(box(0, 0, W, H))

# --------------------------------------------------------------------------- background
img = Image.new("RGBA", (s(W), s(H)), BG_TOP + (255,))
d = ImageDraw.Draw(img)
for y in range(s(H)):
    t = y / (s(H) - 1)
    c = tuple(round(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3))
    d.line([(0, y), (s(W), y)], fill=c + (255,))

# soft radial light behind the PCB art
halo = layer()
hd = ImageDraw.Draw(halo)
hd.ellipse([s(430), s(-40), s(760), s(360)], fill=(40, 72, 92, 90))
img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(s(60))))

# CAM grid (dots every 10 units, crosses every 50)
grid = layer()
gd = ImageDraw.Draw(grid)
for gx in range(0, W + 1, 10):
    for gy in range(0, H + 1, 10):
        if gx % 50 == 0 and gy % 50 == 0:
            gd.line([(s(gx - 2), s(gy)), (s(gx + 2), s(gy))], fill=(120, 150, 175, 70), width=sw(0.5))
            gd.line([(s(gx), s(gy - 2)), (s(gx), s(gy + 2))], fill=(120, 150, 175, 70), width=sw(0.5))
        else:
            r = s(0.35)
            gd.ellipse([s(gx) - r, s(gy) - r, s(gx) + r, s(gy) + r], fill=(120, 150, 175, 45))

# horizontal fade mask for the art: clean on the left where the text lives
fade = Image.new("L", (s(W), s(H)), 0)
fdraw = ImageDraw.Draw(fade)
x0, x1 = s(360), s(500)
for x in range(s(W)):
    t = 0.0 if x < x0 else 1.0 if x > x1 else (x - x0) / (x1 - x0)
    t = t * t * (3 - 2 * t)
    fdraw.line([(x, 0), (x, s(H))], fill=round(255 * t))
grid_fade = fade.point(lambda v: 60 + v * 195 // 255)
img.alpha_composite(mask_alpha(grid, grid_fade))

# --------------------------------------------------------------------------- copper
cu = layer()
cd = ImageDraw.Draw(cu)
fill_geom(cd, COPPER_GEOM, COPPER + (255,))
# vertical sheen: brighter towards the top
sheen = Image.new("RGBA", (s(W), s(H)), COPPER_HI + (0,))
sd = ImageDraw.Draw(sheen)
for y in range(s(H)):
    t = 1 - y / s(H)
    sd.line([(0, y), (s(W), y)], fill=COPPER_HI + (round(110 * t),))
sheen.putalpha(ImageChops.multiply(sheen.getchannel("A"), cu.getchannel("A")))
cu.alpha_composite(sheen)
edge_l = layer()
stroke_geom(ImageDraw.Draw(edge_l), COPPER_GEOM, (255, 205, 150, 120), 0.45)
edge_l.putalpha(ImageChops.multiply(edge_l.getchannel("A"), cu.getchannel("A")))
cu.alpha_composite(edge_l)

cu = mask_alpha(cu, fade)
img.alpha_composite(glow(cu, 3.5, 0.35))
img.alpha_composite(cu)

# chip body
chip = layer()
chd = ImageDraw.Draw(chip)
b = BODY / 2
chd.rounded_rectangle([s(CX - b), s(CY - b), s(CX + b), s(CY + b)], radius=s(2.5),
                      fill=(22, 27, 34, 255), outline=(70, 82, 96, 255), width=sw(0.8))
chd.ellipse([s(CX - b + 5), s(CY - b + 5), s(CX - b + 9), s(CY - b + 9)], fill=(60, 70, 82, 255))
chd.text((s(CX), s(CY - 3)), "MCU", font=font("ChakraPetch-SemiBold.ttf", 11), fill=(120, 134, 150, 255), anchor="mm")
chd.text((s(CX), s(CY + 10)), "LQFP-32", font=mono(5.5), fill=(90, 102, 116, 255), anchor="mm")
img.alpha_composite(chip)

# --------------------------------------------------------------------------- CNC isolation path
# region where the milling pass "has already run"
iso_region = Polygon([(300, 150), (560, 150), (560, H), (300, H)])
iso = COPPER_GEOM.buffer(1.6, quad_segs=12).intersection(iso_region.buffer(0))
iso_l = layer()
stroke_geom(ImageDraw.Draw(iso_l), iso, CYAN + (235,), 0.55)
iso_l.putalpha(ImageChops.multiply(iso_l.getchannel("A"), fade))
img.alpha_composite(glow(iso_l, 2.2, 1.6))
img.alpha_composite(iso_l)

# --------------------------------------------------------------------------- fiber laser hatch
hatch_zone = Polygon([(598, 200), (W, 200), (W, H), (598, H)])
free = hatch_zone.difference(COPPER_GEOM.buffer(1.4))
hatch_lines = []
ang = math.radians(-35)
dx, dy = math.cos(ang), math.sin(ang)
nx, ny = -dy, dx
spacing = 2.2
for i in range(-120, 120):
    ox, oy = 660 + nx * i * spacing, 258 + ny * i * spacing
    ln = LineString([(ox - dx * 200, oy - dy * 200), (ox + dx * 200, oy + dy * 200)])
    seg = ln.intersection(free)
    if not seg.is_empty:
        hatch_lines.append((i, seg))

FRONT = 4            # index of the line currently being scanned
laser = layer()
ld = ImageDraw.Draw(laser)
for i, seg in hatch_lines:
    if i > FRONT:
        continue
    age = FRONT - i
    alpha = 255 if age == 0 else max(110, 235 - age * 2)
    col = (255, 236, 200) if age == 0 else AMBER
    for part in getattr(seg, "geoms", [seg]):
        if part.length < 0.5:
            continue
        ld.line([(s(x), s(y)) for x, y in part.coords], fill=col + (alpha,), width=sw(0.6 if age else 0.9))
img.alpha_composite(glow(laser, 1.6, 1.3))
img.alpha_composite(laser)

# laser spot on the active line
front_seg = next(seg for i, seg in hatch_lines if i == FRONT)
parts = [p for p in getattr(front_seg, "geoms", [front_seg]) if p.length > 5]
part = max(parts, key=lambda p: p.length)
LX, LY = part.interpolate(0.55, normalized=True).coords[0]
spot = layer()
spd = ImageDraw.Draw(spot)
for r, a in ((26, 40), (14, 90), (7, 170)):
    spd.ellipse([s(LX - r), s(LY - r), s(LX + r), s(LY + r)], fill=(255, 150, 60, a))
spot = spot.filter(ImageFilter.GaussianBlur(s(6)))
img.alpha_composite(spot)
core = layer()
crd = ImageDraw.Draw(core)
crd.ellipse([s(LX - 2.6), s(LY - 2.6), s(LX + 2.6), s(LY + 2.6)], fill=(255, 250, 240, 255))
img.alpha_composite(glow(core, 2.5, 2.0))
img.alpha_composite(core)
# thin beam streak (galvo scan direction)
streak = layer()
std = ImageDraw.Draw(streak)
std.line([(s(LX - dx * 30), s(LY - dy * 30)), (s(LX + dx * 30), s(LY + dy * 30))], fill=(255, 220, 170, 120), width=sw(0.8))
img.alpha_composite(glow(streak, 1.5, 1.2))

# tool position + DRO readout
TX, TY = 515.0, 236.0
tool = layer()
td = ImageDraw.Draw(tool)
td.ellipse([s(TX - 5), s(TY - 5), s(TX + 5), s(TY + 5)], outline=CYAN + (255,), width=sw(0.8))
td.ellipse([s(TX - 1.2), s(TY - 1.2), s(TX + 1.2), s(TY + 1.2)], fill=(255, 255, 255, 255))
for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
    td.line([(s(TX + dx * 7), s(TY + dy * 7)), (s(TX + dx * 12), s(TY + dy * 12))], fill=CYAN + (255,), width=sw(0.8))
td.line([(s(TX + 8), s(TY + 8)), (s(TX + 18), s(TY + 18)), (s(TX + 26), s(TY + 18))], fill=CYAN + (170,), width=sw(0.6))
dro = "X 42.195  Y 18.730  Z -0.050"
dro_w = td.textlength(dro, font=mono(6.4, 500)) / SS
td.rounded_rectangle([s(TX + 26), s(TY + 12), s(TX + 32 + dro_w), s(TY + 24)], radius=s(2),
                     fill=(8, 14, 20, 240), outline=CYAN + (120,), width=sw(0.5))
td.text((s(TX + 29), s(TY + 18)), dro, font=mono(6.4, 500), fill=CYAN + (230,), anchor="lm")
img.alpha_composite(glow(tool, 3, 1.4))
img.alpha_composite(tool)

# --------------------------------------------------------------------------- left: logo + text
LOGO_X, LOGO_Y, LOGO = 40, 92, 64


def logo_trace(x0, y0, size):
    """Copper trace used by both the raster and vector logo."""
    u = size / 64
    tw = 6.2 * u
    stem_x, right_x = x0 + 21 * u, x0 + 43 * u
    top, base = y0 + 16 * u, y0 + 38 * u
    r = (right_x - stem_x) / 2
    trace = unary_union([
        LineString([(stem_x, top), (stem_x, y0 + 52 * u)]).buffer(tw / 2, cap_style="flat"),
        LineString([(right_x, top + 6 * u), (right_x, base + 5.5 * u), (right_x + 5 * u, base + 10.5 * u)]).buffer(tw / 2, cap_style="round", join_style="round"),
        Point(stem_x + r, base).buffer(r + tw / 2, 64).difference(Point(stem_x + r, base).buffer(r - tw / 2, 64))
            .intersection(box(stem_x - tw, base, right_x + tw, base + r + tw)),
    ])
    pad = Point(stem_x, y0 + 52 * u).buffer(5.2 * u, 48)
    shoulder = Point(right_x, top + 4 * u).buffer(5.0 * u, 48)
    trace = unary_union([trace, pad, shoulder, box(stem_x - tw / 2, top - 3 * u, stem_x + tw / 2, top)])
    trace = trace.difference(Point(right_x, top + 4 * u).buffer(2.0 * u, 32))
    trace = trace.difference(Point(stem_x, y0 + 52 * u).buffer(1.9 * u, 32))
    return trace


def draw_logo(x0, y0, size):
    """µ built from a PCB trace: pad on the stem, via on the shoulder, laser dot."""
    lg = layer()
    g = ImageDraw.Draw(lg)
    u = size / 64
    g.rounded_rectangle([s(x0), s(y0), s(x0 + size), s(y0 + size)], radius=s(13 * u),
                        fill=(20, 29, 40, 255), outline=(62, 80, 98, 255), width=sw(1.1 * u))
    trace = logo_trace(x0, y0, size)
    cu_l = layer()
    fill_geom(ImageDraw.Draw(cu_l), trace, COPPER + (255,))
    sh = Image.new("RGBA", cu_l.size, COPPER_HI + (0,))
    shd = ImageDraw.Draw(sh)
    for yy in range(s(y0), s(y0 + size)):
        t = 1 - (yy - s(y0)) / s(size)
        shd.line([(0, yy), (s(W), yy)], fill=COPPER_HI + (round(170 * t),))
    sh.putalpha(ImageChops.multiply(sh.getchannel("A"), cu_l.getchannel("A")))
    cu_l.alpha_composite(sh)
    lg.alpha_composite(glow(cu_l, 2.5, 0.5))
    lg.alpha_composite(cu_l)
    # isolation outline around the glyph
    ol = layer()
    stroke_geom(ImageDraw.Draw(ol), trace.buffer(2.4 * u, quad_segs=16), CYAN + (200,), 0.6 * u)
    lg.alpha_composite(glow(ol, 1.5, 1.2))
    lg.alpha_composite(ol)
    # laser dot
    lx, ly = x0 + 50 * u, y0 + 16 * u
    dot = layer()
    dd = ImageDraw.Draw(dot)
    dd.ellipse([s(lx - 2.4 * u), s(ly - 2.4 * u), s(lx + 2.4 * u), s(ly + 2.4 * u)], fill=(255, 245, 225, 255))
    lg.alpha_composite(glow(dot, 3.2 * u, 2.4))
    lg.alpha_composite(dot)
    return lg


img.alpha_composite(draw_logo(LOGO_X, LOGO_Y, LOGO))

txt = layer()
tdraw = ImageDraw.Draw(txt)
title_font = font("ChakraPetch-Bold.ttf", 54)
TX0, TBASE = LOGO_X + LOGO + 16, LOGO_Y + 47
tdraw.text((s(TX0), s(TBASE)), "Mikro", font=title_font, fill=WHITE + (255,), anchor="ls")
mw = tdraw.textlength("Mikro", font=title_font)
cam_x = s(TX0) + mw + s(1)

# "CAM" with copper -> amber gradient
cam_mask = Image.new("L", (s(W), s(H)), 0)
ImageDraw.Draw(cam_mask).text((cam_x, s(TBASE)), "CAM", font=title_font, fill=255, anchor="ls")
grad = Image.new("RGBA", (s(W), s(H)))
gdraw = ImageDraw.Draw(grad)
bbox = cam_mask.getbbox()
for x in range(bbox[0], bbox[2] + 1):
    t = (x - bbox[0]) / max(1, bbox[2] - bbox[0])
    c = tuple(round(COPPER[i] + (AMBER[i] - COPPER[i]) * t) for i in range(3))
    gdraw.line([(x, bbox[1]), (x, bbox[3])], fill=c + (255,))
grad.putalpha(cam_mask)
img.alpha_composite(glow(grad, 6, 0.45))
txt.alpha_composite(grad)

tag_font = font("ChakraPetch-Medium.ttf", 12.5)
tag_y = LOGO_Y + LOGO + 3
tx = s(TX0 + 2)
for i, word in enumerate(("PCB CAM", "CNC CONTROL", "FIBER LASER")):
    if i:
        tdraw.ellipse([tx + s(5), s(tag_y - 1.6), tx + s(8.2), s(tag_y + 1.6)], fill=(AMBER if i == 2 else CYAN) + (255,))
        tx += s(13.2)
    for ch in word:
        tdraw.text((tx, s(tag_y)), ch, font=tag_font, fill=(196, 206, 216, 255), anchor="lm")
        tx += tdraw.textlength(ch, font=tag_font) + s(1.3)

# thin rule between title and tagline
tdraw.line([(s(TX0 + 2), s(LOGO_Y + 55)), (s(TX0 + 60), s(LOGO_Y + 55))], fill=COPPER + (255,), width=sw(1))
tdraw.line([(s(TX0 + 64), s(LOGO_Y + 55)), (s(TX0 + 245), s(LOGO_Y + 55))], fill=(60, 74, 90, 255), width=sw(1))

# footer (bottom-right; bottom-left is reserved for QSplashScreen messages)
foot = font("ChakraPetch-Medium.ttf", 9.5)
tdraw.text((s(TX0 + 2), s(tag_y + 22)), "open source  ·  MIT  ·  based on FlatCAM", font=foot,
           fill=MUTED + (255,), anchor="lm")
img.alpha_composite(txt)

# top accent line + frame
fr = layer()
frd = ImageDraw.Draw(fr)
for x in range(s(W)):
    t = x / s(W)
    if t < 0.5:
        c, a = COPPER, round(255 * (t / 0.5))
    else:
        u = (t - 0.5) / 0.5
        c, a = tuple(round(COPPER[i] + (AMBER[i] - COPPER[i]) * u) for i in range(3)), 255
    frd.line([(x, 0), (x, s(1.5))], fill=c + (a,))
frd.rectangle([0, 0, s(W) - 1, s(H) - 1], outline=(52, 64, 78, 255), width=sw(1))
img.alpha_composite(fr)

# --------------------------------------------------------------------------- export
OUT_DIR.mkdir(parents=True, exist_ok=True)
final = img.convert("RGB")
final.resize((W * 2, H * 2), Image.LANCZOS).save(OUT_DIR / "splash@2x.png", optimize=True)
final.resize((W, H), Image.LANCZOS).save(OUT_DIR / "splash.png", optimize=True)
print("written", OUT_DIR / "splash.png", OUT_DIR / "splash@2x.png")

# Shared logo, small-size application icons, and scalable source.
mark = draw_logo(0, 0, 256).crop((0, 0, s(256), s(256)))
mark.save(OUT_DIR / "logo.png", optimize=True)
for size in (16, 24, 32, 48, 64, 128, 256):
    mark.resize((size, size), Image.Resampling.LANCZOS).save(OUT_DIR / f"app{size}.png", optimize=True)
mark.save(OUT_DIR / "mikrocam.ico", sizes=[(n, n) for n in (16, 24, 32, 48, 64, 128, 256)])

paths = []
outline_paths = []
for poly in iter_polys(logo_trace(0, 0, 64).buffer(2.4, quad_segs=16)):
    for ring in (poly.exterior, *poly.interiors):
        points = list(ring.coords)
        outline_paths.append("M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in points) + " Z")
for poly in iter_polys(logo_trace(0, 0, 64)):
    rings = (poly.exterior, *poly.interiors)
    commands = []
    for ring in rings:
        points = list(ring.coords)
        commands.append(f"M{points[0][0]:.3f},{points[0][1]:.3f}")
        commands.extend(f"L{x:.3f},{y:.3f}" for x, y in points[1:])
        commands.append("Z")
    paths.append(" ".join(commands))
svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
       '<title>MikroCAM</title><defs><linearGradient id="copper" x2="0" y2="1">'
       '<stop stop-color="#f2aa62"/><stop offset="1" stop-color="#cd7c3a"/>'
       '</linearGradient></defs>'
       '<rect x=".5" y=".5" width="63" height="63" rx="13" fill="#141d28" stroke="#3e5062"/>')
for path in outline_paths:
    svg += f'<path d="{path}" fill="none" stroke="#46d6e8" stroke-width=".6"/>'
for path in paths:
    svg += f'<path d="{path}" fill="url(#copper)" fill-rule="evenodd"/>'
svg += '<circle cx="50" cy="16" r="2.4" fill="#fff5e1"/></svg>'
(OUT_DIR / "logo.svg").write_text(svg, encoding="utf-8")
print("written logo, SVG, PNG icon sizes and multi-resolution ICO")

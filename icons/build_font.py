#!/usr/bin/env python3
import re
from pathlib import Path
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path
import pathops

SVG_DIR = Path(__file__).parent / "svg"
OUTPUT_DIR = Path(__file__).parent / "fonts"
FONT_NAME = "DeviceIcons"

ICON_MAP = {
    "optical-modem": 0xE001, "adsl-modem": 0xE002, "router": 0xE003,
    "wifi-router": 0xE004, "wifi-ap": 0xE005, "unmanaged-switch": 0xE006,
    "managed-switch": 0xE007, "camera": 0xE008, "nvr": 0xE009,
    "server": 0xE00A, "desktop-pc": 0xE00B, "micro-pc": 0xE00C,
    "notebook": 0xE00D, "tablet": 0xE00E, "phone": 0xE00F,
    "smart-watch": 0xE010, "tv-box": 0xE011, "tv": 0xE012,
    "smart-plug": 0xE013, "smart-lamp": 0xE014, "smart-relay": 0xE015,
    "door-bell": 0xE016, "printer": 0xE017, "scanner": 0xE018,
    "speaker": 0xE019, "other": 0xE01A,
}

def get_glyph_bounds(recording_pen):
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')
    for op, args in recording_pen.value:
        if op in ('moveTo', 'lineTo'):
            x, y = args[0]
            min_x, max_x = min(min_x, x), max(max_x, x)
            min_y, max_y = min(min_y, y), max(max_y, y)
        elif op in ('curveTo', 'qCurveTo'):
            for x, y in args:
                min_x, max_x = min(min_x, x), max(max_x, x)
                min_y, max_y = min(min_y, y), max(max_y, y)
    if min_x == float('inf'):
        return 0, 0, 0, 0
    return min_x, min_y, max_x, max_y

def build_font():
    OUTPUT_DIR.mkdir(exist_ok=True)
    glyphs = {}
    
    for svg_file in sorted(SVG_DIR.glob("*.svg")):
        name = svg_file.stem
        if name not in ICON_MAP:
            continue
        svg_content = svg_file.read_text()
        paths = re.findall(r'<path[^>]*d="([^"]*)"', svg_content)
        circles = re.findall(r'<circle[^>]*cx="([^"]*)"[^>]*cy="([^"]*)"[^>]*r="([^"]*)"', svg_content)
        rects = re.findall(r'<rect[^>]*x="([^"]*)"[^>]*y="([^"]*)"[^>]*width="([^"]*)"[^>]*height="([^"]*)"', svg_content)
        
        if paths or circles or rects:
            glyphs[name] = {"codepoint": ICON_MAP[name], "paths": paths, "circles": circles, "rects": rects}
    
    print(f"Building font with {len(glyphs)} glyphs...")
    
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder([".notdef"] + list(glyphs.keys()))
    fb.setupCharacterMap({data["codepoint"]: name for name, data in glyphs.items()})
    
    glyph_table = {}
    advance_width = 1000
    target_size = 800  # Fit within 800x800, leaving 100 padding on each side
    
    for name, data in glyphs.items():
        rec_pen = RecordingPen()
        
        for path_data in data["paths"]:
            try:
                # Parse SVG path into skia-pathops, mark as even-odd (SVG default for fill-rule="evenodd"),
                # then simplify — this resolves overlaps and produces nonzero-compatible contours
                # with correct winding directions for TrueType glyph rendering.
                sk_path = pathops.Path()
                sk_pen = sk_path.getPen()
                parse_path(path_data, sk_pen)
                sk_path.fillType = pathops.FillType.EVEN_ODD
                sk_path_simplified = pathops.simplify(sk_path)
                sk_path_simplified.draw(rec_pen)
            except Exception as e:
                print(f"Error in {name} path: {e}")
        
        for cx, cy, r in data["circles"]:
            cx, cy, r = float(cx), float(cy), float(r)
            rec_pen.moveTo((cx + r, cy))
            rec_pen.curveTo((cx + r, cy + r * 0.55), (cx + r * 0.55, cy + r), (cx, cy + r))
            rec_pen.curveTo((cx - r * 0.55, cy + r), (cx - r, cy + r * 0.55), (cx - r, cy))
            rec_pen.curveTo((cx - r, cy - r * 0.55), (cx - r * 0.55, cy - r), (cx, cy - r))
            rec_pen.curveTo((cx + r * 0.55, cy - r), (cx + r, cy - r * 0.55), (cx + r, cy))
            rec_pen.closePath()
        
        for rect_data in data["rects"]:
            x, y, w, h = float(rect_data[0]), float(rect_data[1]), float(rect_data[2]), float(rect_data[3])
            rec_pen.moveTo((x, y))
            rec_pen.lineTo((x + w, y))
            rec_pen.lineTo((x + w, y + h))
            rec_pen.lineTo((x, y + h))
            rec_pen.closePath()
        
        min_x, min_y, max_x, max_y = get_glyph_bounds(rec_pen)
        raw_width = max_x - min_x
        raw_height = max_y - min_y
        
        if raw_width == 0 or raw_height == 0:
            continue
            
        scale = target_size / max(raw_width, raw_height)
        raw_center_x = (min_x + max_x) / 2
        raw_center_y = (min_y + max_y) / 2
        
        # Center horizontally at x=500, vertically at y=300 (center of ascent=800, descent=-200)
        offset_x = 500 - (raw_center_x * scale)
        offset_y = 300 + (raw_center_y * scale)  # Y is inverted in fonts
        
        tt_pen = TTGlyphPen(None)
        cu2qu_pen = Cu2QuPen(tt_pen, max_err=1.0, reverse_direction=False)
        transform = (scale, 0, 0, -scale, offset_x, offset_y)
        t_pen = TransformPen(cu2qu_pen, transform)
        
        for op, args in rec_pen.value:
            getattr(t_pen, op)(*args)
        
        glyph_table[name] = tt_pen.glyph()
    
    pen = TTGlyphPen(None)
    glyph_table[".notdef"] = pen.glyph()
    
    fb.setupGlyf(glyph_table)
    
    # Calculate proper LSB for each glyph to center it horizontally
    metrics = {}
    for name in glyphs.keys():
        glyf = glyph_table[name]
        if hasattr(glyf, 'xMin') and hasattr(glyf, 'xMax'):
            glyph_width = glyf.xMax - glyf.xMin
            lsb = int((advance_width - glyph_width) / 2)
        else:
            lsb = 0
        metrics[name] = (advance_width, lsb)
    metrics[".notdef"] = (advance_width, 0)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": FONT_NAME, "styleName": "Regular"})
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, sTypoLineGap=0)
    fb.setupPost()
    fb.setupHead(unitsPerEm=1000)
    
    ttf_path = OUTPUT_DIR / f"{FONT_NAME}.ttf"
    fb.font.save(ttf_path)
    print(f"Saved: {ttf_path}")
    
    css = f"""@font-face {{
  font-family: '{FONT_NAME}';
  src: url('/static/fonts/{FONT_NAME}.ttf') format('truetype');
  font-weight: normal;
  font-style: normal;
}}

.icon {{
  font-family: '{FONT_NAME}';
  font-style: normal;
  font-weight: normal;
  font-variant: normal;
  text-transform: none;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1em;
  height: 1em;
  vertical-align: middle;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}}

"""
    for name, data in glyphs.items():
        css += f".icon-{name}:before {{\n  content: '\\{data['codepoint']:04X}';\n}}\n\n"
    
    css_path = OUTPUT_DIR / f"{FONT_NAME}.css"
    css_path.write_text(css)
    print(f"Saved: {css_path}")
    print("Done!")

if __name__ == "__main__":
    build_font()

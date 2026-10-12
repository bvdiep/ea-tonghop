#!/usr/bin/env python3
"""Style the Quarto pptx deck: navy cover, footer, title colors."""
from pptx import Presentation
from pptx.util import Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

NAVY = RGBColor(0x1F, 0x38, 0x64)
STEEL = RGBColor(0x2E, 0x4A, 0x7A)
GOLD = RGBColor(0xBF, 0x8F, 0x00)
GRAY = RGBColor(0x59, 0x59, 0x59)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHTBLUE = RGBColor(0xD9, 0xE2, 0xF3)

P = "/home/diep/work/diep/hermes-web-workspace/14c042c2-ba50-495f-8509-401649007210/coding/tong-hop/showcase-slides.pptx"
prs = Presentation(P)
W, H = prs.slide_width, prs.slide_height

def solid_bg(slide, color):
    bg = slide.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = color

def add_rect(slide, x, y, w, h, color):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    shp.line.fill.background()
    shp.shadow.inherit = False
    return shp

def add_text(slide, x, y, w, h, text, size, color, bold=False, align=PP_ALIGN.LEFT, font="Calibri"):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    first = True
    for line in text.split("\n"):
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.color.rgb = color
        r.font.bold = bold
        r.font.name = font
    return tb

slides = list(prs.slides)
n = len(slides)

# --- Title slide (slide 0): navy background, centered ---
s0 = slides[0]
solid_bg(s0, NAVY)
for shape in s0.shapes:
    if shape.has_text_frame:
        for p in shape.text_frame.paragraphs:
            for r in p.runs:
                t = r.text
                if t and "Từ bài toán" in t or "Nền tảng" in t:
                    r.font.color.rgb = LIGHTBLUE
                    r.font.size = Pt(20)
                elif t:
                    r.font.color.rgb = WHITE
                    r.font.size = Pt(36) if len(t) > 12 else Pt(20)
                    r.font.bold = True
        shape.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        shape.top = Emu(int(H*0.30))
for shape in s0.shapes:
    if shape.has_text_frame and shape != s0.shapes[0]:
        for p in shape.text_frame.paragraphs:
            p.alignment = PP_ALIGN.CENTER
            for r in p.runs:
                r.font.color.rgb = LIGHTBLUE
                r.font.size = Pt(14)
                r.font.bold = False
        shape.top = Emu(int(H*0.62))
add_rect(s0, Emu(int(W*0.35)), Emu(int(H*0.55)), Emu(int(W*0.30)), Emu(45720), GOLD)
add_text(s0, Emu(int(W*0.05)), Emu(int(H*0.05)), Emu(int(W*0.9)), Emu(int(H*0.05)),
         "BSM SUPER AI", 11, LIGHTBLUE, bold=True)

# --- Content slides: footer + title color ---
for idx, s in enumerate(slides[1:], start=1):
    for shape in s.shapes:
        if shape.has_text_frame and shape == s.shapes.title:
            for p in shape.text_frame.paragraphs:
                for r in p.runs:
                    r.font.color.rgb = NAVY
                    r.font.bold = True
    add_rect(s, Emu(int(W*0.05)), Emu(int(H*0.945)), Emu(228600), Emu(30480), GOLD)
    add_text(s, Emu(int(W*0.93)), Emu(int(H*0.93)), Emu(int(W*0.05)), Emu(int(H*0.04)),
             str(idx+1), 10, GRAY, align=PP_ALIGN.RIGHT)
    add_text(s, Emu(int(W*0.07)), Emu(int(H*0.93)), Emu(int(W*0.5)), Emu(int(H*0.04)),
             "Chatbot AI Nội bộ cho Ngân hàng — BSM Super AI", 9, GRAY)

prs.save(P)
print(f"styled {n} slides ->", P)

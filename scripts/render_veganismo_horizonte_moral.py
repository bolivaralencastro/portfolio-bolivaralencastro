from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets/images/social/instagram/veganismo-horizonte-moral"
SRC_DIR = OUT_DIR / "sources"
FONT_DIR = OUT_DIR / "fonts"

W = 1080
H = 1350
BG = "#f7f5f2"
DOT = "#d6d1cb"
TEXT = "#111111"
MUTED = "#5f5f5f"
BLUE = "#2f6ee5"
BORDER = "#282828"
RULE = "#cfc8bf"

TITLE_FONT = FONT_DIR / "SpaceGrotesk-wght.ttf"
BODY_FONT = FONT_DIR / "InstrumentSans-wdth-wght.ttf"

IMAGE_BOX = (54, 118, 1026, 618)
TEXT_X = 68
TITLE_TOP = 742
TEXT_MAX_WIDTH = 944
SUPPORT_MAX_WIDTH = 900
NOTE_WIDTH = 760
NOTE_Y = 1004
CREDIT_Y = H - 132

SLIDES = [
    {
        "kicker": "1 / CONVITE",
        "kind": "cover_diptych",
        "left_image": SRC_DIR / "ebensee-prisoners-1945.jpg",
        "right_image": SRC_DIR / "pig-in-cage.jpg",
        "title": "Os animais seguem fora do horizonte moral da esquerda?",
        "support": "Uma pergunta inicial para quem diz defender igualdade, dignidade e libertacao.",
        "credit": "Montagem com imagens documentais historicas via Wikimedia Commons.",
    },
    {
        "kicker": "2 / HIPOTESE",
        "kind": "image",
        "image": SRC_DIR / "farrowing-full-stall.jpg",
        "title": "O veganismo talvez nao seja uma pauta lateral.",
        "support": "Talvez seja coerencia politica.",
        "credit": "Mercy For Animals MFA, CC BY 2.0, via Wikimedia Commons.",
    },
    {
        "kicker": "3 / ESTRUTURA",
        "kind": "image_pair",
        "left_image": SRC_DIR / "calf-caged.jpg",
        "right_image": SRC_DIR / "person-drinking-milk-modern.jpg",
        "title": "Toda escravizacao comeca quando um corpo vira propriedade.",
        "support": "Depois vira produto, rotina e consumo.",
        "right_center": (0.54, 0.36),
        "credit": "Montagem com imagens de Maqi e USDA via Wikimedia Commons.",
    },
    {
        "kicker": "4 / INDUSTRIA",
        "kind": "image_pair",
        "left_image": SRC_DIR / "gestation-crates-2.jpg",
        "right_image": SRC_DIR / "man-eats-meat-and-bread.jpg",
        "title": "Entre o confinamento e o prato, a violencia desaparece.",
        "support": "Confinar, separar, reproduzir, transportar, matar.",
        "right_center": (0.62, 0.48),
        "credit": "Montagem com imagens da Humane Society e de Tomwsulcer via Wikimedia Commons.",
    },
    {
        "kicker": "5 / CONSUMO",
        "kind": "image_pair",
        "left_image": SRC_DIR / "battery-farm.jpg",
        "right_image": SRC_DIR / "happy-egg-company-carton.png",
        "title": "A embalagem promete cuidado. A industria segue fora do quadro.",
        "support": "O consumo costuma apagar a origem.",
        "right_center": (0.5, 0.5),
        "credit": "Montagem com imagens de Maqi e The Happy Egg Company via Wikimedia Commons.",
    },
    {
        "kicker": "6 / MERCADORIA",
        "kind": "image_pair",
        "left_image": SRC_DIR / "luwak-civet-in-cage.jpg",
        "right_image": SRC_DIR / "woman-trying-on-fur-coat.jpg",
        "title": "Quando o luxo entra em cena, o sofrimento sai do enquadramento.",
        "support": "A promessa de refinamento aparece. O animal desaparece.",
        "left_center": (0.58, 0.5),
        "right_center": (0.5, 0.32),
        "credit": "Montagem com imagens de surtr e Spaarnestad Photo via Wikimedia Commons.",
    },
    {
        "kicker": "7 / ASSIMETRIA",
        "kind": "image_note",
        "image": SRC_DIR / "ebensee-prisoners-1945.jpg",
        "title": "Quando a vitima e humana, espera-se de nos a palavra horror.*",
        "title_max_size": 72,
        "title_max_width": 900,
        "note": "* E, para muita gente, nem quando a vitima e humana isso basta para produzir horror.",
        "note_max_width": 780,
        "credit": "Lt. Arnold E. Samuelson, U.S. Army, dominio publico, via Wikimedia Commons.",
    },
    {
        "kicker": "8 / CONVITE",
        "kind": "image",
        "image": SRC_DIR / "buckeye-trapped-dying-hen.jpg",
        "title": "Talvez esteja na hora de incluir os animais no nosso horizonte moral.",
        "title_max_size": 72,
        "support": "Nao como apendice das lutas. Como parte delas.",
        "credit": "Mercy For Animals MFA, CC BY 2.0, via Wikimedia Commons.",
    },
]


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def text_width(draw: ImageDraw.ImageDraw, text: str, text_font: ImageFont.FreeTypeFont) -> float:
    return draw.textlength(text, font=text_font)


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    text_font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if text_width(draw, trial, text_font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def line_height(text_font: ImageFont.FreeTypeFont, factor: float = 1.1) -> int:
    bbox = text_font.getbbox("Ag")
    return int((bbox[3] - bbox[1]) * factor)


def fit_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    path: Path,
    max_size: int,
    min_size: int,
    max_width: int,
    max_height: int | None = None,
    factor: float = 1.07,
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    for size in range(max_size, min_size - 1, -2):
        current_font = font(path, size)
        lines = wrap_text(draw, text, current_font, max_width)
        total_height = len(lines) * line_height(current_font, factor)
        if max_height is not None and total_height > max_height:
            continue
        if all(text_width(draw, line, current_font) <= max_width for line in lines):
            return current_font, lines
    current_font = font(path, min_size)
    return current_font, wrap_text(draw, text, current_font, max_width)


def draw_multiline(
    draw: ImageDraw.ImageDraw,
    lines: Iterable[str],
    x: int,
    y: int,
    fill: str,
    text_font: ImageFont.FreeTypeFont,
    factor: float = 1.07,
) -> int:
    current_y = y
    step = line_height(text_font, factor)
    for line in lines:
        draw.text((x, current_y), line, font=text_font, fill=fill)
        current_y += step
    return current_y


def background() -> Image.Image:
    image = Image.new("RGB", (W, H), ImageColor.getrgb(BG))
    draw = ImageDraw.Draw(image)
    for x in range(12, W, 35):
        for y in range(12, H, 35):
            draw.ellipse((x, y, x + 3, y + 3), fill=DOT)
    return image


def add_kicker(draw: ImageDraw.ImageDraw, text: str) -> None:
    kicker_font = font(BODY_FONT, 26)
    x = 66
    y = 58
    text_bbox = draw.textbbox((0, 0), text, font=kicker_font)
    box_w = (text_bbox[2] - text_bbox[0]) + 30
    box_h = (text_bbox[3] - text_bbox[1]) + 18
    draw.rounded_rectangle((x, y, x + box_w, y + box_h), radius=10, fill=BLUE)
    draw.text((x + 15, y + 7), text, font=kicker_font, fill="white")


def add_footer(draw: ImageDraw.ImageDraw, idx: int, total: int) -> None:
    footer_font = font(BODY_FONT, 14)
    draw.ellipse((52, H - 53, 63, H - 42), fill=BLUE)
    draw.text((74, H - 56), "bolivaralencastro.com.br", font=footer_font, fill="#3a3a3a")
    draw.text((W - 95, H - 56), f"{idx:02d}/{total:02d}", font=footer_font, fill="#6d6d6d")


def add_credit(draw: ImageDraw.ImageDraw, text: str) -> None:
    credit_font = font(BODY_FONT, 12)
    draw.text((TEXT_X, CREDIT_Y), text, font=credit_font, fill="#6d6d6d")


def load_fill(
    path: Path,
    box: tuple[int, int, int, int],
    centering: tuple[float, float] = (0.5, 0.5),
) -> Image.Image:
    image = Image.open(path).convert("RGB")
    width = box[2] - box[0]
    height = box[3] - box[1]
    return ImageOps.fit(image, (width, height), method=Image.Resampling.LANCZOS, centering=centering)


def add_image_block(base: Image.Image, slide: dict) -> None:
    draw = ImageDraw.Draw(base)
    box = IMAGE_BOX
    image = load_fill(slide["image"], box, slide.get("center", (0.5, 0.5)))
    base.paste(image, box[:2])
    draw.rectangle(box, outline=BORDER, width=2)


def add_cover_diptych(base: Image.Image, slide: dict) -> None:
    draw = ImageDraw.Draw(base)
    box = IMAGE_BOX
    draw.rectangle(box, outline=BORDER, width=2)

    gap = 8
    total_w = box[2] - box[0]
    left_w = (total_w - gap) // 2
    right_w = total_w - gap - left_w
    left_box = (box[0], box[1], box[0] + left_w, box[3])
    right_box = (box[0] + left_w + gap, box[1], box[2], box[3])

    left = load_fill(slide["left_image"], left_box, slide.get("left_center", (0.5, 0.5))).convert("L").convert("RGB")
    right = load_fill(slide["right_image"], right_box, slide.get("right_center", (0.5, 0.5))).convert("L").convert("RGB")

    base.paste(left, left_box[:2])
    base.paste(right, right_box[:2])
    draw.rectangle((left_box[2], box[1], left_box[2] + gap, box[3]), fill=BG)
    draw.rectangle(box, outline=BORDER, width=2)


def add_image_pair(base: Image.Image, slide: dict) -> None:
    draw = ImageDraw.Draw(base)
    box = IMAGE_BOX
    draw.rectangle(box, outline=BORDER, width=2)

    gap = 8
    total_w = box[2] - box[0]
    left_w = (total_w - gap) // 2
    right_w = total_w - gap - left_w
    left_box = (box[0], box[1], box[0] + left_w, box[3])
    right_box = (box[0] + left_w + gap, box[1], box[2], box[3])

    left = load_fill(slide["left_image"], left_box, slide.get("left_center", (0.5, 0.5)))
    right = load_fill(slide["right_image"], right_box, slide.get("right_center", (0.5, 0.5)))

    base.paste(left, left_box[:2])
    base.paste(right, right_box[:2])
    draw.rectangle((left_box[2], box[1], left_box[2] + gap, box[3]), fill=BG)
    draw.rectangle(box, outline=BORDER, width=2)


def add_text_block(base: Image.Image, slide: dict) -> None:
    draw = ImageDraw.Draw(base)
    title_font, title_lines = fit_wrapped_text(
        draw,
        slide["title"],
        TITLE_FONT,
        max_size=slide.get("title_max_size", 76),
        min_size=slide.get("title_min_size", 46),
        max_width=slide.get("title_max_width", TEXT_MAX_WIDTH),
        max_height=430,
    )

    top_y = 730 if slide["kind"] in {"image", "image_note", "image_pair", "cover_diptych"} else 255
    end_y = draw_multiline(draw, title_lines, TEXT_X, slide.get("title_y", TITLE_TOP if top_y == 730 else top_y), TEXT, title_font)

    if slide.get("support"):
        support_font, support_lines = fit_wrapped_text(
            draw,
            slide["support"],
            BODY_FONT,
            max_size=32,
            min_size=24,
            max_width=slide.get("support_max_width", SUPPORT_MAX_WIDTH),
            max_height=130,
            factor=1.04,
        )
        draw_multiline(draw, support_lines, TEXT_X, end_y + 16, MUTED, support_font, factor=1.08)


def add_note_block(base: Image.Image, slide: dict) -> None:
    draw = ImageDraw.Draw(base)
    title_font, title_lines = fit_wrapped_text(
        draw,
        slide["title"],
        TITLE_FONT,
        max_size=78,
        min_size=48,
        max_width=950,
        max_height=350,
    )
    end_y = draw_multiline(draw, title_lines, 68, 255, TEXT, title_font)

    note_font, note_lines = fit_wrapped_text(
        draw,
        slide["note"],
        BODY_FONT,
        max_size=24,
        min_size=18,
        max_width=945,
        max_height=180,
        factor=1.02,
    )
    draw_multiline(draw, note_lines, 68, max(end_y + 90, 975), MUTED, note_font, factor=1.02)


def add_note_only(base: Image.Image, slide: dict) -> None:
    if not slide.get("note"):
        return
    draw = ImageDraw.Draw(base)
    note_x = TEXT_X
    note_y = slide.get("note_y", NOTE_Y)
    note_width = slide.get("note_max_width", NOTE_WIDTH)

    draw.line((note_x, note_y - 18, note_x + 180, note_y - 18), fill=RULE, width=2)
    note_font, note_lines = fit_wrapped_text(
        draw,
        slide["note"],
        BODY_FONT,
        max_size=24,
        min_size=18,
        max_width=note_width,
        max_height=140,
        factor=1.08,
    )
    draw_multiline(draw, note_lines, note_x, note_y, MUTED, note_font, factor=1.08)


def render_slide(idx: int, slide: dict, total: int) -> Image.Image:
    base = background()
    add_kicker(ImageDraw.Draw(base), slide["kicker"])

    if slide["kind"] in {"image", "image_note"}:
        add_image_block(base, slide)
        add_text_block(base, slide)
        add_note_only(base, slide)
    elif slide["kind"] == "image_pair":
        add_image_pair(base, slide)
        add_text_block(base, slide)
        add_note_only(base, slide)
    elif slide["kind"] == "cover_diptych":
        add_cover_diptych(base, slide)
        add_text_block(base, slide)
    elif slide["kind"] == "text_note":
        add_note_block(base, slide)
    else:
        add_text_block(base, slide)

    if slide.get("credit"):
        add_credit(ImageDraw.Draw(base), slide["credit"])
    add_footer(ImageDraw.Draw(base), idx, total)
    return base


def write_caption() -> None:
    caption = """Se a esquerda fala tanto em justica, libertacao e dignidade, por que os animais quase sempre seguem fora do horizonte moral?

Esse carrossel nao tenta fechar a conversa. Tenta abri-la.

Tenho pensado que o veganismo talvez nao seja uma pauta lateral para quem se alinha a agendas antirracistas, feministas, anticoloniais, ecologicas e anticapitalistas. Talvez seja uma exigencia de coerencia.

Quanto mais olho para a forma como tratamos os animais, mais dificil fica ignorar o parentesco entre sistemas que transformam vidas em propriedade, recurso, mercadoria e silencio.

Imagens usadas nesta versao:
- Ebensee concentration camp prisoners 1945, dominio publico, via Wikimedia Commons
- Pig in cage, CC0, via Wikimedia Commons
- FarrowingFullStall, CC BY 2.0, via Wikimedia Commons
- Calf-caged, CC BY-SA 3.0, via Wikimedia Commons
- Person drinking milk, CC BY 2.0, via Wikimedia Commons
- Gestation crates 2, CC BY 3.0, via Wikimedia Commons
- Man Eats Meat and Bread, CC BY-SA 3.0, via Wikimedia Commons
- Battery-farm, CC BY-SA 3.0, via Wikimedia Commons
- The Happy Egg Company Free Range eggs and carton, CC BY-SA 4.0, via Wikimedia Commons
- Luwak (civet cat) in cage, CC BY-SA 2.0, via Wikimedia Commons
- Woman trying on a fur coat, CC BY-SA 3.0 NL, via Wikimedia Commons
- Buckeye Trapped Dying Hen, CC BY 2.0, via Wikimedia Commons

#veganismo #antiespecismo #justicasocial #caroljadams"""
    (OUT_DIR / "caption.txt").write_text(caption + "\n", encoding="utf-8")


def write_credits() -> None:
    credits = """Fontes
- Space Grotesk, Google Fonts, OFL 1.1
- Instrument Sans, Google Fonts, OFL 1.1

Imagens
- Ebensee concentration camp prisoners 1945.jpg — U.S. Army — dominio publico — Wikimedia Commons
- Pig in cage.jpg — CC0 — Wikimedia Commons
- 2.1 FarrowingFullStall (4098887317).jpg — Mercy For Animals MFA — CC BY 2.0 — Wikimedia Commons
- Calf-caged.jpg — Maqi — CC BY-SA 3.0 — Wikimedia Commons
- Person drinking milk.jpg — U.S. Department of Agriculture / Peggy Greb — CC BY 2.0 — Wikimedia Commons
- Gestation crates 2.jpg — Humane Society of the United States — CC BY 3.0 — Wikimedia Commons
- Man Eats Meat and Bread.jpg — Tomwsulcer — CC BY-SA 3.0 — Wikimedia Commons
- Battery-farm.jpg — Maqi — CC BY-SA 3.0 — Wikimedia Commons
- The Happy Egg Company Free Range eggs and carton.png — The Happy Egg Company — CC BY-SA 4.0 — Wikimedia Commons
- Vrouw past bontjas - Woman trying on a fur coat (4106589852).jpg — Spaarnestad Photo — CC BY-SA 3.0 NL — Wikimedia Commons
- Buckeye Trapped Dying Hen (4018460472).jpg — Mercy For Animals MFA — CC BY 2.0 — Wikimedia Commons
- Luwak (civet cat) in cage.jpg — surtr — CC BY-SA 2.0 — Wikimedia Commons
"""
    (OUT_DIR / "credits.txt").write_text(credits, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = len(SLIDES)
    for idx, slide in enumerate(SLIDES, start=1):
        image = render_slide(idx, slide, total)
        image.save(OUT_DIR / f"slide-{idx:02d}.jpg", quality=93, subsampling=0)
    write_caption()
    write_credits()
    print(f"rendered {total} slides")


if __name__ == "__main__":
    main()

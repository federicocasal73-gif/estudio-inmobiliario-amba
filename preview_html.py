"""
Preview HTML de carruseles y posts: templates self-contained.

Genera un archivo HTML standalone que muestra como quedaria visualmente
un carrusel o un post antes de generar las imagenes con IA.

Uso:
    from preview_html import PreviewHTML

    preview = PreviewHTML()
    # Preview de carrusel
    html_path = preview.carrusel(
        carrusel=carrusel,        # objeto Carrusel de carruseles.py
        ruta_salida=Path("preview.html"),
    )
    # Preview de post simple
    html_path = preview.post(
        tema="5 ha en Cañuelas",
        caption="...",
        hashtags=["#lotes", "#chacras"],
        ruta_imagen="imagen.jpg",  # opcional, usa placeholder si falta
        ruta_salida=Path("preview_post.html"),
    )

Los HTML son self-contained (CSS inline, sin dependencias externas)
y se pueden abrir directamente con doble-click en el navegador.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


@dataclass
class PreviewConfig:
    """Configuracion visual del preview."""

    ancho_slide_px: int = 540  # 540 es tipico para preview 4:5
    alto_slide_px: int = 675  # mantiene 4:5
    color_fondo: str = "#fafafa"
    color_slide: str = "#ffffff"
    color_overlay: str = "rgba(0,0,0,0.55)"
    color_texto_overlay: str = "#ffffff"
    color_caption: str = "#262626"
    fuente: str = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
    logo_emoji: str = "🌾"


PALETA_PLACEHOLDERS = [
    ("#ffe0b2", "#5d4037"),  # warm
    ("#c8e6c9", "#2e7d32"),  # verde
    ("#bbdefb", "#1565c0"),  # azul
    ("#f8bbd0", "#880e4f"),  # rosa
    ("#d1c4e9", "#4527a0"),  # lila
    ("#ffccbc", "#bf360c"),  # naranja
    ("#b2dfdb", "#004d40"),  # turquesa
    ("#fff9c4", "#827717"),  # amarillo
    ("#cfd8dc", "#263238"),  # gris azulado
    ("#f0f4c3", "#827717"),  # lima
]


def _color_para_slide(idx: int) -> tuple[str, str]:
    return PALETA_PLACEHOLDERS[idx % len(PALETA_PLACEHOLDERS)]


def _html_escape(s: str) -> str:
    return html.escape(s or "")


class PreviewHTML:
    """Generador de previews HTML self-contained."""

    def __init__(self, config: PreviewConfig | None = None):
        self.config = config or PreviewConfig()

    # ---------------- Carrusel ----------------

    def carrusel(self, carrusel: Any, ruta_salida: str | Path) -> Path:
        """Genera preview HTML de un carrusel."""
        ruta_salida = Path(ruta_salida)
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)

        slides = carrusel.slides
        tema = carrusel.tema
        caption = carrusel.caption_narrativo or ""
        hashtags = carrusel.hashtags or []

        # Slide activa
        slides_html = []
        for idx, slide in enumerate(slides):
            bg, fg = _color_para_slide(idx)
            if slide.tipo == "placeholder_foto":
                bg, fg = "#e0e0e0", "#424242"
            overlay_text = slide.texto_overlay or slide.descripcion or f"Slide {slide.numero}"
            prompt = slide.prompt or ""
            metadata = slide.metadata or {}
            placeholder_path = metadata.get("placeholder_foto_path", "")

            tipo_badge = f'<div class="tipo-badge">{_html_escape(slide.tipo)}</div>'

            placeholder_block = ""
            if placeholder_path:
                placeholder_block = (
                    f'<div class="placeholder-path">📷 {_html_escape(placeholder_path)}</div>'
                )

            prompt_block = ""
            if prompt:
                prompt_short = prompt[:120] + ("..." if len(prompt) > 120 else "")
                prompt_block = (
                    f'<details class="prompt-details">'
                    f"<summary>Ver prompt SDXL</summary>"
                    f'<pre class="prompt-text">{_html_escape(prompt_short)}</pre>'
                    f"</details>"
                )

            slides_html.append(f'''
            <div class="slide" data-slide-idx="{idx}" style="display: {"block" if idx == 0 else "none"};">
                <div class="slide-canvas" style="background: linear-gradient(135deg, {bg} 0%, {fg}22 100%); color: {fg};">
                    {tipo_badge}
                    <div class="slide-numero">{slide.numero}/{len(slides)}</div>
                    <div class="slide-contenido">
                        <div class="slide-placeholder-icon">📸</div>
                        <div class="slide-texto-overlay">
                            {_html_escape(overlay_text).replace(chr(10), "<br>")}
                        </div>
                    </div>
                </div>
                <div class="slide-meta">
                    {placeholder_block}
                    {prompt_block}
                </div>
            </div>
            ''')

        dots_html = ""
        for i in range(len(slides)):
            dots_html += f'<span class="dot" data-idx="{i}" onclick="irASlide({i})"></span>'

        # Caption y hashtags
        caption_html = _html_escape(caption).replace("\n", "<br>")
        hashtags_html = " ".join(
            f'<span class="hashtag">{_html_escape(h)}</span>' for h in hashtags
        )

        # Indicar si es placeholder
        metadata_carrusel = getattr(carrusel, "metadata", {}) or {}
        es_placeholder = any(s.tipo == "placeholder_foto" for s in slides)

        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Preview Carrusel: {_html_escape(tema)}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    background: {self.config.color_fondo};
    font-family: {self.config.fuente};
    padding: 24px 16px;
    color: #262626;
}}
.container {{ max-width: 720px; margin: 0 auto; }}
.header {{
    background: white;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    border: 1px solid #dbdbdb;
}}
.header h1 {{ font-size: 18px; margin-bottom: 8px; }}
.header .meta {{ font-size: 13px; color: #8e8e8e; }}
.header .logo {{ font-size: 24px; }}
.header .placeholder-warning {{
    background: #fff3cd;
    color: #856404;
    padding: 8px 12px;
    border-radius: 6px;
    margin-top: 12px;
    font-size: 13px;
}}
.slide {{
    margin-bottom: 16px;
}}
.slide-canvas {{
    width: 100%;
    max-width: {self.config.ancho_slide_px}px;
    aspect-ratio: 4 / 5;
    margin: 0 auto;
    border-radius: 12px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    display: flex;
    align-items: center;
    justify-content: center;
}}
.slide-contenido {{
    text-align: center;
    padding: 32px;
}}
.slide-placeholder-icon {{
    font-size: 64px;
    opacity: 0.4;
    margin-bottom: 16px;
}}
.slide-texto-overlay {{
    font-size: 24px;
    font-weight: 600;
    line-height: 1.3;
    text-shadow: 0 2px 4px rgba(0,0,0,0.3);
}}
.slide-numero {{
    position: absolute;
    top: 12px;
    right: 12px;
    background: {self.config.color_overlay};
    color: {self.config.color_texto_overlay};
    padding: 4px 10px;
    border-radius: 16px;
    font-size: 12px;
    font-weight: 600;
}}
.tipo-badge {{
    position: absolute;
    top: 12px;
    left: 12px;
    background: {self.config.color_overlay};
    color: {self.config.color_texto_overlay};
    padding: 4px 10px;
    border-radius: 16px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.slide-meta {{
    max-width: {self.config.ancho_slide_px}px;
    margin: 12px auto 0;
    padding: 12px;
    background: white;
    border-radius: 8px;
    font-size: 13px;
    border: 1px solid #dbdbdb;
}}
.placeholder-path {{
    background: #fff3cd;
    color: #856404;
    padding: 6px 10px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 11px;
    margin-bottom: 8px;
    word-break: break-all;
}}
.prompt-details summary {{
    cursor: pointer;
    color: #8e8e8e;
    font-size: 12px;
    user-select: none;
}}
.prompt-text {{
    background: #f5f5f5;
    padding: 8px;
    border-radius: 4px;
    font-size: 11px;
    margin-top: 6px;
    white-space: pre-wrap;
    word-break: break-word;
}}
.dots {{
    text-align: center;
    margin: 16px 0;
}}
.dot {{
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #dbdbdb;
    margin: 0 4px;
    cursor: pointer;
}}
.dot.active {{ background: #262626; }}
.nav-controls {{
    display: flex;
    justify-content: space-between;
    margin: 16px 0;
    max-width: {self.config.ancho_slide_px}px;
    margin: 16px auto;
}}
.nav-btn {{
    background: white;
    border: 1px solid #dbdbdb;
    padding: 8px 16px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
}}
.nav-btn:hover {{ background: #fafafa; }}
.caption-box {{
    background: white;
    border: 1px solid #dbdbdb;
    border-radius: 12px;
    padding: 20px;
    margin-top: 16px;
}}
.caption {{
    color: {self.config.color_caption};
    line-height: 1.5;
    margin-bottom: 12px;
    white-space: pre-wrap;
    word-break: break-word;
}}
.hashtags {{
    margin-top: 12px;
    line-height: 1.8;
}}
.hashtag {{
    color: #00376b;
    margin-right: 6px;
}}
.footer {{
    text-align: center;
    font-size: 12px;
    color: #8e8e8e;
    margin-top: 32px;
}}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <div style="display: flex; align-items: center; gap: 12px;">
            <span class="logo">{self.config.logo_emoji}</span>
            <h1>{_html_escape(tema)}</h1>
        </div>
        <div class="meta">
            Tipo: <strong>{_html_escape(carrusel.tipo)}</strong> ·
            Municipio: <strong>{_html_escape(carrusel.municipio)}</strong> ·
            Tono: <strong>{_html_escape(carrusel.tono)}</strong> ·
            Slides: <strong>{len(slides)}</strong>
        </div>
        {"<div class='placeholder-warning'>⚠️ Este carrusel contiene slides con placeholder_foto. Subi las fotos reales antes de publicar.</div>" if es_placeholder else ""}
    </div>

    <div class="nav-controls">
        <button class="nav-btn" onclick="anterior()">← Anterior</button>
        <span id="slide-counter" style="align-self: center; font-size: 14px; color: #8e8e8e;">1 / {len(slides)}</span>
        <button class="nav-btn" onclick="siguiente()">Siguiente →</button>
    </div>

    <div class="dots">
        {dots_html}
    </div>

    {"".join(slides_html)}

    <div class="caption-box">
        <h3 style="margin-bottom: 12px; font-size: 16px;">Caption</h3>
        <div class="caption">{caption_html}</div>
        <h3 style="margin-top: 16px; margin-bottom: 8px; font-size: 16px;">Hashtags ({len(hashtags)})</h3>
        <div class="hashtags">{hashtags_html}</div>
    </div>

    <div class="footer">
        Generado por Realestate Studio AMBA · {datetime.now().strftime("%Y-%m-%d %H:%M")}
    </div>
</div>

<script>
let slideActual = 0;
const totalSlides = {len(slides)};

function irASlide(idx) {{
    document.querySelectorAll('.slide').forEach(s => s.style.display = 'none');
    document.querySelectorAll('.dot').forEach(d => d.classList.remove('active'));
    const target = document.querySelector(`[data-slide-idx="${{idx}}"]`);
    if (target) target.style.display = 'block';
    const dot = document.querySelector(`[data-idx="${{idx}}"].dot`);
    if (dot) dot.classList.add('active');
    document.getElementById('slide-counter').textContent = `${{idx + 1}} / ${{totalSlides}}`;
    slideActual = idx;
}}

function siguiente() {{
    slideActual = (slideActual + 1) % totalSlides;
    irASlide(slideActual);
}}

function anterior() {{
    slideActual = (slideActual - 1 + totalSlides) % totalSlides;
    irASlide(slideActual);
}}

document.addEventListener('keydown', e => {{
    if (e.key === 'ArrowRight') siguiente();
    if (e.key === 'ArrowLeft') anterior();
}});

irASlide(0);
</script>
</body>
</html>"""

        ruta_salida.write_text(html_content, encoding="utf-8")
        return ruta_salida

    # ---------------- Post simple ----------------

    def post(
        self,
        tema: str,
        caption: str,
        hashtags: list[str],
        ruta_imagen: str | Path | None = None,
        ruta_salida: str | Path = "preview_post.html",
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Genera preview HTML de un post individual."""
        ruta_salida = Path(ruta_salida)
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)

        bg, fg = _color_para_pla(0)
        imagen_html = ""
        if ruta_imagen and Path(ruta_imagen).exists():
            rel_path = Path(ruta_imagen).resolve().as_uri()
            imagen_html = (
                f'<img src="{rel_path}" alt="{_html_escape(tema)}" '
                f'style="width: 100%; height: 100%; object-fit: cover;">'
            )
        else:
            imagen_html = (
                f'<div style="background: linear-gradient(135deg, {bg} 0%, {fg}22 100%); '
                f"color: {fg}; width: 100%; height: 100%; display: flex; align-items: center; "
                f'justify-content: center; flex-direction: column;">'
                f'<div style="font-size: 64px; opacity: 0.4;">📸</div>'
                f'<div style="margin-top: 12px; font-size: 14px; opacity: 0.6;">Imagen no generada</div>'
                f"</div>"
            )

        caption_html = _html_escape(caption).replace("\n", "<br>")
        hashtags_html = " ".join(
            f'<span class="hashtag">{_html_escape(h)}</span>' for h in hashtags
        )

        meta = metadata or {}
        meta_items = "".join(
            f"<div><strong>{_html_escape(str(k))}:</strong> {_html_escape(str(v))}</div>"
            for k, v in meta.items()
        )

        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Preview Post: {_html_escape(tema)}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    background: {self.config.color_fondo};
    font-family: {self.config.fuente};
    padding: 24px 16px;
    color: #262626;
}}
.container {{ max-width: 540px; margin: 0 auto; }}
.post {{
    background: white;
    border-radius: 12px;
    border: 1px solid #dbdbdb;
    overflow: hidden;
}}
.post-header {{
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    border-bottom: 1px solid #efefef;
}}
.avatar {{
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: linear-gradient(135deg, #ffd54f, #ff9800);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
}}
.username {{ font-weight: 600; font-size: 14px; }}
.location {{ font-size: 12px; color: #8e8e8e; }}
.post-imagen {{
    width: 100%;
    aspect-ratio: 4 / 5;
    overflow: hidden;
}}
.post-caption {{
    padding: 16px;
    line-height: 1.5;
    font-size: 14px;
    color: {self.config.color_caption};
    white-space: pre-wrap;
    word-break: break-word;
}}
.post-hashtags {{
    padding: 0 16px 16px;
    line-height: 1.8;
    font-size: 14px;
}}
.hashtag {{ color: #00376b; margin-right: 6px; }}
.meta-box {{
    margin-top: 16px;
    padding: 16px;
    background: white;
    border-radius: 12px;
    border: 1px solid #dbdbdb;
    font-size: 13px;
    line-height: 1.6;
}}
.footer {{
    text-align: center;
    font-size: 12px;
    color: #8e8e8e;
    margin-top: 32px;
}}
</style>
</head>
<body>
<div class="container">
    <div class="post">
        <div class="post-header">
            <div class="avatar">{self.config.logo_emoji}</div>
            <div>
                <div class="username">tu_cuenta_inmobiliaria</div>
                <div class="location">{_html_escape(metadata.get("municipio", "AMBA")) if metadata else "AMBA"}</div>
            </div>
        </div>
        <div class="post-imagen">{imagen_html}</div>
        <div class="post-caption">
            <strong style="display: block; margin-bottom: 8px;">{_html_escape(tema)}</strong>
            {caption_html}
        </div>
        <div class="post-hashtags">{hashtags_html}</div>
    </div>

    {f'<div class="meta-box">{meta_items}</div>' if meta_items else ""}

    <div class="footer">
        Generado por Realestate Studio AMBA · {datetime.now().strftime("%Y-%m-%d %H:%M")}
    </div>
</div>
</body>
</html>"""

        ruta_salida.write_text(html_content, encoding="utf-8")
        return ruta_salida


def _color_para_pla(idx: int) -> tuple[str, str]:
    return _color_para_slide(idx)


def demo() -> None:
    """Demo: genera preview de un carrusel."""
    from carruseles import CarruselFactory
    from realestate_studio import RealestateStudio

    studio = RealestateStudio()
    factory = CarruselFactory(studio)

    carrusel = factory.lote_premium(
        tema="5 ha en Cañuelas, a 65 km de CABA",
        municipio="Cañuelas",
        hectareas=5,
        precio_usd="USD 60.000",
        tono="emotivo",
        n_slides=5,
    )

    preview = PreviewHTML()
    html_path = preview.carrusel(
        carrusel=carrusel,
        ruta_salida=ROOT / "inmuebles" / "_test_preview.html",
    )
    print(f"Preview HTML generado en: {html_path.relative_to(ROOT)}")
    print(f"Tamaño: {html_path.stat().st_size:,} bytes")

    # Tambien demo de post
    post = studio.post.post_lote_venta(
        tema="5 ha en Cañuelas",
        municipio="Cañuelas",
        hectareas="5 ha",
        distancia_caba="65 km",
        tono="emotivo",
    )
    html_path2 = preview.post(
        tema="5 ha en Cañuelas",
        caption=post["caption"],
        hashtags=post["hashtags"],
        ruta_imagen=None,
        ruta_salida=ROOT / "inmuebles" / "_test_preview_post.html",
        metadata={"municipio": "Cañuelas", "tono": "emotivo"},
    )
    print(f"Preview post generado en: {html_path2.relative_to(ROOT)}")
    print(f"Tamaño: {html_path2.stat().st_size:,} bytes")


if __name__ == "__main__":
    demo()

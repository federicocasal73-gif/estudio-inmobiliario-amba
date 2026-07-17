"""Generador de PDF profesional para NOVA ARGENTUM - Estudio Inmobiliario AMBA."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import os
from datetime import datetime

# Colors
PRIMARY = HexColor("#1a1a2e")
SECONDARY = HexColor("#16213e")
ACCENT = HexColor("#0f3460")
HIGHLIGHT = HexColor("#e94560")
LIGHT_BG = HexColor("#f5f5f5")
DARK_TEXT = HexColor("#2d2d2d")
GRAY_TEXT = HexColor("#666666")

OUTPUT_DIR = "inmuebles/outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def create_styles():
    """Create custom paragraph styles."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='CoverTitle',
        parent=styles['Title'],
        fontSize=32,
        textColor=PRIMARY,
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        name='CoverSubtitle',
        parent=styles['Normal'],
        fontSize=16,
        textColor=ACCENT,
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica'
    ))

    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=PRIMARY,
        spaceBefore=20,
        spaceAfter=12,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        name='SubsectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=ACCENT,
        spaceBefore=12,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        name='BodyText2',
        parent=styles['Normal'],
        fontSize=10,
        textColor=DARK_TEXT,
        spaceAfter=8,
        alignment=TA_JUSTIFY,
        fontName='Helvetica',
        leading=14
    ))

    styles.add(ParagraphStyle(
        name='BulletItem',
        parent=styles['Normal'],
        fontSize=10,
        textColor=DARK_TEXT,
        leftIndent=20,
        spaceAfter=4,
        fontName='Helvetica',
        leading=13
    ))

    styles.add(ParagraphStyle(
        name='CodeStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=HexColor("#333333"),
        fontName='Courier',
        backColor=LIGHT_BG,
        leftIndent=10,
        rightIndent=10,
        spaceBefore=6,
        spaceAfter=6,
        leading=12
    ))

    styles.add(ParagraphStyle(
        name='CaptionStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=GRAY_TEXT,
        alignment=TA_CENTER,
        spaceAfter=12,
        fontName='Helvetica-Oblique'
    ))

    return styles


class NumberedCanvas(canvas.Canvas):
    """Canvas with page numbers and footer."""

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        page_num = len(self._saved_page_states)
        if page_num > 1:
            self.setFont("Helvetica", 8)
            self.setFillColor(GRAY_TEXT)
            self.drawCentredString(
                A4[0] / 2, 15 * mm,
                f"NOVA ARGENTUM - Documentación Técnica | Página {page_num} de {page_count}"
            )


def create_cover_page(story, styles):
    """Create the cover page."""
    story.append(Spacer(1, 60 * mm))

    # Logo placeholder - decorative line
    story.append(HRFlowable(
        width="60%", thickness=2, color=ACCENT,
        spaceAfter=10, spaceBefore=0
    ))

    story.append(Paragraph("NOVA ARGENTUM", styles['CoverTitle']))
    story.append(Spacer(1, 5 * mm))

    story.append(HRFlowable(
        width="40%", thickness=1, color=ACCENT,
        spaceAfter=15, spaceBefore=0
    ))

    story.append(Paragraph(
        "Estudio Inmobiliario AMBA",
        styles['CoverSubtitle']
    ))

    story.append(Spacer(1, 10 * mm))

    story.append(Paragraph(
        "Sistema de Generación y Publicación de Contenido<br/>"
        "para Instagram - Documentación Técnica",
        ParagraphStyle(
            'CoverDesc',
            parent=styles['Normal'],
            fontSize=12,
            textColor=GRAY_TEXT,
            alignment=TA_CENTER,
            leading=16
        )
    ))

    story.append(Spacer(1, 30 * mm))

    # Metadata table
    meta_data = [
        ['Versión', '1.0.0'],
        ['Fecha', datetime.now().strftime('%d/%m/%Y')],
        ['Stack', 'Python 3.14 + Next.js 16 + Tailwind CSS v4'],
        ['Coverage', '90.12% (1071 tests)'],
    ]

    meta_table = Table(meta_data, colWidths=[40 * mm, 80 * mm])
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), ACCENT),
        ('TEXTCOLOR', (1, 0), (1, -1), DARK_TEXT),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(meta_table)
    story.append(PageBreak())


def create_toc(story, styles):
    """Create table of contents."""
    story.append(Paragraph("Índice", styles['SectionTitle']))
    story.append(Spacer(1, 5 * mm))

    toc_items = [
        ("1.", "Resumen Ejecutivo"),
        ("2.", "Arquitectura del Sistema"),
        ("3.", "Backend - Módulos Principales"),
        ("4.", "Frontend - Interfaz de Usuario"),
        ("5.", "Pipeline de Generación de Contenido"),
        ("6.", "Publicación en Instagram"),
        ("7.", "Fooocus - Generación de Imágenes IA"),
        ("8.", "Sistema de Testeo y Coverage"),
        ("9.", "Guía de Despliegue"),
        ("10.", "API Reference"),
    ]

    for num, title in toc_items:
        story.append(Paragraph(
            f"<b>{num}</b>  {title}",
            ParagraphStyle(
                'TOCItem',
                parent=styles['Normal'],
                fontSize=12,
                textColor=DARK_TEXT,
                spaceAfter=8,
                leftIndent=10,
                fontName='Helvetica'
            )
        ))

    story.append(PageBreak())


def create_section_1(story, styles):
    """Resumen Ejecutivo."""
    story.append(Paragraph("1. Resumen Ejecutivo", styles['SectionTitle']))

    story.append(Paragraph(
        "NOVA ARGENTUM es un sistema integral de automatización de contenido inmobiliario "
        "para Instagram, diseñado específicamente para el mercado inmobiliario del AMBA "
        "(Área Metropolitana de Buenos Aires). El sistema combina generación de carruseles "
        "con prompts optimizados para Stable Diffusion (Fooocus), programación de publicaciones, "
        "y análisis de métricas de Instagram.",
        styles['BodyText2']
    ))

    story.append(Paragraph("Objetivos principales:", styles['SubsectionTitle']))

    objectives = [
        "• Generar contenido visual profesional para propiedades inmobiliarias",
        "• Automatizar la creación de carruseles con prompts optimizados para IA",
        "• Programar y publicar automáticamente en Instagram",
        "• Analizar métricas de engagement y generar reportes",
        "• Gestionar respuestas automáticas a DMs de clientes",
    ]

    for obj in objectives:
        story.append(Paragraph(obj, styles['BulletItem']))

    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("Stack tecnológico:", styles['SubsectionTitle']))

    stack_data = [
        ['Componente', 'Tecnología', 'Versión'],
        ['Backend', 'Python + FastAPI', '3.14'],
        ['Frontend', 'Next.js + TypeScript', '16.x'],
        ['UI Components', 'shadcn/ui + Tailwind CSS', 'v4'],
        ['Image Generation', 'Fooocus (Stable Diffusion)', '2.5+'],
        ['Testing', 'pytest + coverage', '90.12%'],
        ['Deploy', 'Vercel (frontend) + Railway (backend)', '-'],
    ]

    stack_table = Table(stack_data, colWidths=[45 * mm, 55 * mm, 35 * mm])
    stack_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_BG]),
    ]))

    story.append(stack_table)
    story.append(PageBreak())


def create_section_2(story, styles):
    """Arquitectura del Sistema."""
    story.append(Paragraph("2. Arquitectura del Sistema", styles['SectionTitle']))

    story.append(Paragraph(
        "El sistema sigue una arquitectura modular con separación clara de responsabilidades. "
        "El orquestador principal (studio.py) coordina todos los módulos del pipeline:",
        styles['BodyText2']
    ))

    # Architecture diagram as text
    arch_text = """
┌─────────────────────────────────────────────────────────────┐
│                    STUDIO (Orquestador)                     │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Realestate   │  │ Carrusel     │  │ Calendario   │     │
│  │ Studio       │  │ Factory      │  │ Editorial    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Image        │  │ Instagram    │  │ Preview      │     │
│  │ Generator    │  │ Publisher    │  │ HTML         │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Mejora       │  │ Antes/       │  │ Historial    │     │
│  │ Fotos        │  │ Despues      │  │ Publicaciones│     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
"""

    story.append(Paragraph(arch_text.strip(), styles['CodeStyle']))

    story.append(Paragraph("Módulos del backend:", styles['SubsectionTitle']))

    modules = [
        ("studio.py", "Orquestador principal del pipeline semanal"),
        ("realestate_studio.py", "Generador de prompts para Stable Diffusion"),
        ("carruseles.py", "Factory de carruseles con 10+ tipos de contenido"),
        ("calendario_editorial.py", "Programación semanal de posts"),
        ("image_generator.py", "Cliente para Fooocus con cache y retry"),
        ("publishing.py", "Scheduler, Monitor y templates de DM"),
        ("instagram_publisher.py", "Publicación via Instagram Graph API"),
        ("validators.py", "Validación de captions y hashtags"),
        ("caption_variants.py", "Generación de variantes de captions"),
        ("mejora_fotos.py", "Mejora de fotos placeholder"),
    ]

    for mod, desc in modules:
        story.append(Paragraph(
            f"<b>{mod}</b> - {desc}",
            styles['BulletItem']
        ))

    story.append(PageBreak())


def create_section_3(story, styles):
    """Backend - Módulos Principales."""
    story.append(Paragraph("3. Backend - Módulos Principales", styles['SectionTitle']))

    # Studio
    story.append(Paragraph("3.1 studio.py - Orquestador", styles['SubsectionTitle']))
    story.append(Paragraph(
        "El módulo principal coordina el pipeline completo de generación de contenido. "
        "Incluye generación de calendarios, carruseles, mejora de fotos, publicación "
        "y exportación de reportes. Maneja el flujo completo desde la planificación "
        "hasta la publicación en Instagram.",
        styles['BodyText2']
    ))

    story.append(Paragraph("Funciones principales:", styles['SubsectionTitle']))
    funcs = [
        "• pipeline_semana() - Genera calendario semanal completo",
        "• _generar_o_reusar_carrusel() - Crea carruseles con cache",
        "• _publicar_slot() - Publica cada slot del calendario",
        "• generar_imagenes_carrusel() - Genera imágenes via Fooocus",
        "• guardar_pipeline() - Persiste resultados en JSON",
    ]
    for f in funcs:
        story.append(Paragraph(f, styles['BulletItem']))

    # Realestate Studio
    story.append(Paragraph("3.2 realestate_studio.py - Prompts", styles['SubsectionTitle']))
    story.append(Paragraph(
        "Generador de prompts optimizados para Stable Diffusion/Fooocus. "
        "Contiene módulos especializados para lotes, construcciones, servicios, "
        "y contenido de Instagram. Cada prompt incluye aspect_ratio y styles específicos.",
        styles['BodyText2']
    ))

    # Carruseles
    story.append(Paragraph("3.3 carruseles.py - Factory de Carruseles", styles['SubsectionTitle']))
    story.append(Paragraph(
        "Factory con 10+ tipos de carruseles predefinidos: lote_premium, country_etapa, "
        "obra_avance, servicios, story, reel, etapas_construccion, steel_frame, "
        "llave_en_mano, terminaciones, obra_completa. Cada tipo genera slides "
        "con prompts, overlays y captions optimizados.",
        styles['BodyText2']
    ))

    story.append(PageBreak())


def create_section_4(story, styles):
    """Frontend."""
    story.append(Paragraph("4. Frontend - Interfaz de Usuario", styles['SectionTitle']))

    story.append(Paragraph(
        "La interfaz web está construida con Next.js 16, TypeScript y shadcn/ui v4. "
        "Proporciona un dashboard completo para gestionar todo el pipeline de contenido:",
        styles['BodyText2']
    ))

    pages = [
        ("Dashboard", "Resumen de actividad y métricas rápidas"),
        ("Carrusel Editor", "Editor visual de slides con drag & drop"),
        ("Caption Editor", "Editor de captions con variantes y validación"),
        ("Calendario", "Vista semanal/monthly de publicaciones programadas"),
        ("Photo Upload", "Subida y mejora de fotos placeholder"),
        ("Publish Preview", "Preview antes de publicar con dry-run"),
        ("Instagram Metrics", "Dashboard de métricas de engagement"),
    ]

    pages_data = [['Página', 'Función']] + [[p, d] for p, d in pages]
    pages_table = Table(pages_data, colWidths=[40 * mm, 100 * mm])
    pages_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_BG]),
    ]))

    story.append(pages_table)
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("Stack del frontend:", styles['SubsectionTitle']))
    story.append(Paragraph(
        "• Next.js 16 con App Router y Server Components<br/>"
        "• TypeScript estricto (0 errores)<br/>"
        "• Tailwind CSS v4 con theming dinámico<br/>"
        "• shadcn/ui v4 con componentes base-ui<br/>"
        "• Lucide React para iconografía<br/>"
        "• React Hook Form para formularios<br/>"
        "• date-fns para manejo de fechas",
        styles['BulletItem']
    ))

    story.append(PageBreak())


def create_section_5(story, styles):
    """Pipeline de Generación."""
    story.append(Paragraph("5. Pipeline de Generación de Contenido", styles['SectionTitle']))

    story.append(Paragraph(
        "El pipeline completo de generación sigue estos pasos:",
        styles['BodyText2']
    ))

    steps = [
        ("1. Planificación", "CalendarioEditorial genera slots para la semana"),
        ("2. Carruseles", "CarruselFactory crea carruseles según el tipo de slot"),
        ("3. Prompts", "RealestateStudio genera prompts optimizados"),
        ("4. Imágenes", "ImageGenerator envía prompts a Fooocus"),
        ("5. Mejora", "MejoraFotos aplica mejoras a fotos placeholder"),
        ("6. Captions", "CaptionVariants genera variantes de captions"),
        ("7. Validación", "Validators verifica hashtags y captions"),
        ("8. Publicación", "InstagramPublisher publica el carrusel"),
        ("9. Monitoreo", "Monitor lee insights y genera reportes"),
    ]

    steps_data = [['Paso', 'Descripción']] + steps
    steps_table = Table(steps_data, colWidths=[35 * mm, 110 * mm])
    steps_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_BG]),
    ]))

    story.append(steps_table)
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("Modos de publicación:", styles['SubsectionTitle']))
    modes = [
        "• <b>dry-run</b> - Simula la publicación sin enviar a Instagram",
        "• <b>interactivo</b> - Pide confirmación antes de publicar",
        "• <b>real</b> - Publica directamente en Instagram",
    ]
    for m in modes:
        story.append(Paragraph(m, styles['BulletItem']))

    story.append(PageBreak())


def create_section_6(story, styles):
    """Publicación en Instagram."""
    story.append(Paragraph("6. Publicación en Instagram", styles['SectionTitle']))

    story.append(Paragraph(
        "El sistema utiliza Instagram Graph API para publicar carruseles. "
        "Soporta publicación directa y programada con las siguientes capacidades:",
        styles['BodyText2']
    ))

    story.append(Paragraph("Scheduler:", styles['SubsectionTitle']))
    story.append(Paragraph(
        "Cola persistente de publicaciones programadas con soporte para "
        "cancelación, reprogramación y manejo de errores con retry automático.",
        styles['BodyText2']
    ))

    story.append(Paragraph("Monitor:", styles['SubsectionTitle']))
    story.append(Paragraph(
        "Lee insights de Instagram Graph API (impressions, reach, likes, comments, "
        "saves, shares) y genera reportes semanales de engagement.",
        styles['BodyText2']
    ))

    story.append(Paragraph("DM Templates:", styles['SubsectionTitle']))
    story.append(Paragraph(
        "Sistema de respuesta automática a DMs frecuentes con matching por keywords. "
        "Templates predefinidos para: precio, ubicación, financiación, visitas, "
        "información general y agradecimiento.",
        styles['BodyText2']
    ))

    story.append(PageBreak())


def create_section_7(story, styles):
    """Fooocus."""
    story.append(Paragraph("7. Fooocus - Generación de Imágenes IA", styles['SectionTitle']))

    story.append(Paragraph(
        "El sistema integra con Fooocus (basado en Stable Diffusion XL) para "
        "generar imágenes de propiedades inmobiliarias. La integración funciona "
        "a través de gradio-client con auto-detección de endpoints.",
        styles['BodyText2']
    ))

    story.append(Paragraph("Arquitectura:", styles['SubsectionTitle']))
    story.append(Paragraph(
        "• <b>ImageGenerator</b> - Interfaz abstracta<br/>"
        "• <b>StubImageGenerator</b> - Fallback cuando Fooocus no está disponible<br/>"
        "• <b>FooocusImageGenerator</b> - Cliente real para Fooocus<br/>"
        "• <b>ImageCache</b> - Cache de imágenes generadas<br/>"
        "• <b>BatchGenerator</b> - Generación en paralelo con retry",
        styles['BulletItem']
    ))

    story.append(Paragraph("Aspect ratios soportados:", styles['SubsectionTitle']))
    aspects = [
        ['Ratio', 'Uso', 'Dimensiones'],
        ['Instagram Post', 'Carruseles', '896 × 1152 px'],
        ['Instagram Story', 'Stories/Reels', '1152 × 896 px'],
        ['16:9', 'Portadas', '1344 × 768 px'],
        ['1:1', 'Cuadrado', '1024 × 1024 px'],
    ]

    aspects_table = Table(aspects, colWidths=[40 * mm, 40 * mm, 40 * mm])
    aspects_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_BG]),
    ]))

    story.append(aspects_table)

    story.append(PageBreak())


def create_section_8(story, styles):
    """Test Coverage."""
    story.append(Paragraph("8. Sistema de Testeo y Coverage", styles['SectionTitle']))

    story.append(Paragraph(
        "El proyecto cuenta con 1071 tests automatizados alcanzando un coverage "
        "del 90.12%. Los tests cubren todos los módulos principales del backend:",
        styles['BodyText2']
    ))

    coverage_data = [
        ['Módulo', 'Stmts', 'Miss', 'Cover'],
        ['studio.py', '661', '72', '89%'],
        ['publishing.py', '341', '7', '98%'],
        ['carruseles.py', '397', '47', '88%'],
        ['validators.py', '230', '3', '99%'],
        ['image_generator.py', '181', '13', '93%'],
        ['mejora_fotos.py', '186', '12', '94%'],
        ['caption_variants.py', '103', '13', '87%'],
        ['email_notifier.py', '110', '5', '95%'],
        ['instagram_publisher.py', '217', '26', '88%'],
        ['calendario_editorial.py', '325', '26', '92%'],
        ['TOTAL', '4729', '467', '90.12%'],
    ]

    cov_table = Table(coverage_data, colWidths=[50 * mm, 25 * mm, 25 * mm, 25 * mm])
    cov_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT_BG),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [white, LIGHT_BG]),
    ]))

    story.append(cov_table)
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("Estrategia de testing:", styles['SubsectionTitle']))
    story.append(Paragraph(
        "• Mock de todas las dependencias externas (SMTP, OAuth2, HTTP, Fooocus)<br/>"
        "• Uso de tmp_path para pruebas de sistema de archivos<br/>"
        "• Patching de ROOT para pruebas de studio.py<br/>"
        "• Tests de integración para flujos completos<br/>"
        "• Validación de edge cases y manejo de errores",
        styles['BulletItem']
    ))

    story.append(PageBreak())


def create_section_9(story, styles):
    """Guía de Despliegue."""
    story.append(Paragraph("9. Guía de Despliegue", styles['SectionTitle']))

    story.append(Paragraph("Requisitos previos:", styles['SubsectionTitle']))
    story.append(Paragraph(
        "• Python 3.14+<br/>"
        "• Node.js 20+ (para frontend)<br/>"
        "• Fooocus (opcional, para generación de imágenes)<br/>"
        "• Cuenta de Instagram con permisos de Graph API<br/>"
        "• Cuenta de Vercel (para frontend)<br/>"
        "• Cuenta de Railway (para backend)",
        styles['BulletItem']
    ))

    story.append(Paragraph("Instalación del backend:", styles['SubsectionTitle']))
    story.append(Paragraph(
        "git clone https://github.com/user/estudio-inmobiliario-amba.git<br/>"
        "cd estudio-inmobiliario-amba<br/>"
        "pip install -r requirements.txt<br/>"
        "python studio.py demo",
        styles['CodeStyle']
    ))

    story.append(Paragraph("Instalación del frontend:", styles['SubsectionTitle']))
    story.append(Paragraph(
        "cd frontend<br/>"
        "npm install<br/>"
        "npm run dev",
        styles['CodeStyle']
    ))

    story.append(Paragraph("Variables de entorno:", styles['SubsectionTitle']))
    env_vars = [
        ['Variable', 'Descripción', 'Requerida'],
        ['INSTAGRAM_ACCESS_TOKEN', 'Token de Instagram Graph API', 'Sí'],
        ['INSTAGRAM_USER_ID', 'ID de usuario de Instagram', 'Sí'],
        ['FOOOCUS_URL', 'URL del servidor Fooocus', 'No'],
        ['SMTP_HOST', 'Servidor de correo para notificaciones', 'No'],
        ['SMTP_USER', 'Usuario de correo', 'No'],
        ['SMTP_PASS', 'Contraseña de correo', 'No'],
    ]

    env_table = Table(env_vars, colWidths=[50 * mm, 55 * mm, 25 * mm])
    env_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_BG]),
    ]))

    story.append(env_table)

    story.append(PageBreak())


def create_section_10(story, styles):
    """API Reference."""
    story.append(Paragraph("10. API Reference", styles['SectionTitle']))

    story.append(Paragraph("Comandos CLI principales:", styles['SubsectionTitle']))

    cli_cmds = [
        ['Comando', 'Descripción'],
        ['python studio.py demo', 'Ejecuta pipeline de demostración'],
        ['python studio.py semana --n 1', 'Genera calendario semanal'],
        ['python studio.py generar --carrusel path', 'Genera imágenes para carrusel'],
        ['python studio.py publicar --carrusel path', 'Publica carrusel en Instagram'],
        ['python studio.py preview --carrusel path', 'Genera preview HTML'],
        ['python studio.py programar --id post1 --carrusel path', 'Programa publicación'],
        ['python studio.py listar', 'Lista carruseles disponibles'],
        ['python studio.py cache-stats', 'Estadísticas de caché'],
        ['python studio.py reporte-semanal', 'Genera reporte de métricas'],
    ]

    cli_table = Table(cli_cmds, colWidths=[70 * mm, 75 * mm])
    cli_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Courier'),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_BG]),
    ]))

    story.append(cli_table)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Estructura de archivos:", styles['SubsectionTitle']))
    story.append(Paragraph(
        "estudio-inmobiliario-amba/<br/>"
        "├── studio.py                    # Orquestador principal<br/>"
        "├── realestate_studio.py         # Generador de prompts<br/>"
        "├── carruseles.py                # Factory de carruseles<br/>"
        "├── calendario_editorial.py      # Programación semanal<br/>"
        "├── image_generator.py           # Cliente Fooocus<br/>"
        "├── publishing.py                # Scheduler/Monitor/DM<br/>"
        "├── instagram_publisher.py       # Publicación IG<br/>"
        "├── validators.py                # Validación<br/>"
        "├── caption_variants.py          # Variantes de captions<br/>"
        "├── mejora_fotos.py              # Mejora de fotos<br/>"
        "├── generation_pipeline.py       # Pipeline de generación<br/>"
        "├── frontend/                    # Next.js frontend<br/>"
        "│   ├── src/app/                 # Páginas<br/>"
        "│   ├── src/components/          # Componentes<br/>"
        "│   └── src/lib/                 # Utilidades<br/>"
        "├── tests/                       # Tests automatizados<br/>"
        "└── inmuebles/                   # Datos generados<br/>"
        "    ├── lotes/                   # Carruseles por proyecto<br/>"
        "    ├── calendarios/             # Calendarios semanales<br/>"
        "    └── outputs/                 # Outputs generados",
        styles['CodeStyle']
    ))

    story.append(Spacer(1, 10 * mm))

    story.append(HRFlowable(
        width="100%", thickness=1, color=ACCENT,
        spaceAfter=10, spaceBefore=10
    ))

    story.append(Paragraph(
        f"Generado automáticamente el {datetime.now().strftime('%d/%m/%Y %H:%M')}<br/>"
        "NOVA ARGENTUM - Estudio Inmobiliario AMBA<br/>"
        "© 2026 - Todos los derechos reservados",
        ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=GRAY_TEXT,
            alignment=TA_CENTER
        )
    ))


def generate_pdf():
    """Generate the complete PDF document."""
    pdf_path = os.path.join(OUTPUT_DIR, "NOVA_ARGENTUM_Documentacion_Tecnica.pdf")

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm
    )

    styles = create_styles()
    story = []

    # Build document
    create_cover_page(story, styles)
    create_toc(story, styles)
    create_section_1(story, styles)
    create_section_2(story, styles)
    create_section_3(story, styles)
    create_section_4(story, styles)
    create_section_5(story, styles)
    create_section_6(story, styles)
    create_section_7(story, styles)
    create_section_8(story, styles)
    create_section_9(story, styles)
    create_section_10(story, styles)

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF generado: {pdf_path}")
    return pdf_path


if __name__ == "__main__":
    generate_pdf()

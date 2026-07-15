"""Tests del modulo calendario_editorial.py.

Cubre:
  - _tercer_domingo, _fechas_dinamicas_para_anio, _fechas_clave_completas
  - SlotEditorial, SemanaEditorial dataclasses
  - CalendarioEditorial.generar_semana: various posts_por_semana, proyectos, dias_personalizados
  - _slot_normal, _slot_fecha_clave (Madre, Padre, Navidad, Black Friday, etc.)
  - _generar_post_para_slot: all types (lote_venta, country, campo, etc.)
  - _caption_placeholder_*: carrusel, render, obra, generico
  - _caption_fecha_especial: Madre, Padre, Navidad, etc.
  - guardar, exportar_markdown, exportar_csv, exportar_ics
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from calendario_editorial import (
    CALENDARIOS_DIR,
    DIAS_SEMANA,
    DISTRIBUCION_DEFAULT,
    FECHAS_CLAVE_AR_FIJAS,
    FECHAS_INMO,
    CalendarioEditorial,
    SemanaEditorial,
    SlotEditorial,
    _fechas_clave_completas,
    _fechas_dinamicas_para_anio,
    _tercer_domingo,
)

# ===== Fixtures =====


def _mock_studio():
    studio = MagicMock()
    studio.post.post_lote_venta = MagicMock(
        return_value={
            "caption": "Lote test",
            "hashtags": ["#lotes"],
            "caption_completo": "Lote test\n#lotes",
        }
    )
    studio.post.post_country = MagicMock(
        return_value={
            "caption": "Country test",
            "hashtags": ["#country"],
            "caption_completo": "Country test\n#country",
        }
    )
    studio.post.post_campo = MagicMock(
        return_value={
            "caption": "Campo test",
            "hashtags": ["#campo"],
            "caption_completo": "Campo test\n#campo",
        }
    )
    studio.post.post_lote_periurbano = MagicMock(
        return_value={
            "caption": "Periurbano test",
            "hashtags": ["#lotes"],
            "caption_completo": "Periurbano\n#lotes",
        }
    )
    studio.post.post_preventa = MagicMock(
        return_value={
            "caption": "Preventa test",
            "hashtags": ["#country"],
            "caption_completo": "Preventa\n#country",
        }
    )
    studio.post.hashtags = MagicMock(return_value=["#lotes", "#campo"])
    req_mock = MagicMock()
    req_mock.prompt = "prompt render"
    req_mock.aspect_ratio = "896*1152"
    req_mock.styles = ["Fooocus V2"]
    studio.construccion.render_proyecto = MagicMock(return_value=req_mock)
    return studio


# ===== Module-level functions =====


class TestTercerDomingo:
    def test_junio_2025(self):
        mes, dia = _tercer_domingo(2025, 6)
        assert mes == 6
        assert 15 <= dia <= 21

    def test_octubre_2025(self):
        mes, dia = _tercer_domingo(2025, 10)
        assert mes == 10
        assert 15 <= dia <= 21


class TestFechasDinamicas:
    def test_dos_fechas(self):
        fechas = _fechas_dinamicas_para_anio(2025)
        assert len(fechas) == 2
        assert any("Padre" in f[2] for f in fechas)
        assert any("Madre" in f[2] for f in fechas)


class TestFechasClaveCompletas:
    def test_contiene_fijas(self):
        fechas = _fechas_clave_completas(2025)
        assert len(fechas) > len(FECHAS_CLAVE_AR_FIJAS)
        assert any("Black Friday" in f[2] for f in fechas)
        assert any("Padre" in f[2] for f in fechas)


# ===== Dataclasses =====


class TestSlotEditorial:
    def test_creacion(self):
        slot = SlotEditorial(
            fecha="2025-07-14",
            dia_semana="lunes",
            hora_sugerida="19:00",
            tipo_post="lote_venta",
            tono="emotivo",
            nicho=["general"],
            municipio="Cañuelas",
        )
        assert slot.fecha == "2025-07-14"
        assert slot.es_fecha_clave is False

    def test_to_dict(self):
        slot = SlotEditorial(
            fecha="2025-07-14",
            dia_semana="lunes",
            hora_sugerida="19:00",
            tipo_post="lote_venta",
            tono="emotivo",
            nicho=["general"],
            municipio="Cañuelas",
        )
        d = slot.to_dict()
        assert d["fecha"] == "2025-07-14"
        assert d["es_fecha_clave"] is False


class TestSemanaEditorial:
    def test_creacion(self):
        s = SemanaEditorial(
            numero=1,
            fecha_inicio="2025-07-14",
            fecha_fin="2025-07-20",
            proyectos_disponibles=["p1"],
            municipio_principal="Cañuelas",
        )
        assert s.numero == 1
        assert len(s.slots) == 0

    def test_to_dict(self):
        s = SemanaEditorial(
            numero=1,
            fecha_inicio="2025-07-14",
            fecha_fin="2025-07-20",
            proyectos_disponibles=[],
            municipio_principal="M",
        )
        d = s.to_dict()
        assert d["numero"] == 1


# ===== CalendarioEditorial =====


class TestCalendarioEditorial:
    def setup_method(self):
        self.studio = _mock_studio()
        self.cal = CalendarioEditorial(self.studio)

    # --- generar_semana ---

    def test_generar_semana_5_posts(self):
        s = self.cal.generar_semana(
            semana_n=1,
            proyectos=["chacra-5ha"],
            posts_por_semana=5,
            municipio_principal="Cañuelas",
        )
        assert isinstance(s, SemanaEditorial)
        assert len(s.slots) == 5
        assert s.municipio_principal == "Cañuelas"

    def test_generar_semana_7_posts(self):
        s = self.cal.generar_semana(posts_por_semana=7)
        assert len(s.slots) == 7

    def test_generar_semana_1_post(self):
        s = self.cal.generar_semana(posts_por_semana=1)
        assert len(s.slots) == 1

    def test_generar_semana_clamps_posts(self):
        s = self.cal.generar_semana(posts_por_semana=100)
        assert len(s.slots) == 7
        s2 = self.cal.generar_semana(posts_por_semana=0)
        assert len(s2.slots) == 1

    def test_generar_semana_con_fecha_inicio(self):
        s = self.cal.generar_semana(
            posts_por_semana=3,
            fecha_inicio="2025-07-14",
        )
        assert s.fecha_inicio == "2025-07-14"
        assert s.fecha_fin == "2025-07-20"

    def test_generar_semana_sin_proyectos(self):
        s = self.cal.generar_semana(posts_por_semana=3)
        for slot in s.slots:
            assert slot.proyecto is None

    def test_generar_semana_proyectos_rotate(self):
        s = self.cal.generar_semana(
            posts_por_semana=4,
            proyectos=["p1", "p2"],
        )
        proyectos = [slot.proyecto for slot in s.slots]
        assert "p1" in proyectos
        assert "p2" in proyectos

    def test_generar_semana_dias_personalizados(self):
        custom = {
            "lunes": {"tipo": "custom", "tono": "emotivo", "nicho": ["general"]},
        }
        s = self.cal.generar_semana(
            posts_por_semana=1,
            dias_personalizados=custom,
        )
        assert s.slots[0].tipo_post == "custom"

    def test_generar_semana_metadata(self):
        s = self.cal.generar_semana(posts_por_semana=3)
        assert "posts_por_semana" in s.metadata
        assert "dias_elegidos" in s.metadata
        assert len(s.metadata["dias_elegidos"]) == 3

    # --- slot_fecha_clave ---

    def test_slot_fecha_clave_madre(self):
        # 3er domingo octubre 2025 = 19 oct. Usar 7 posts para cubrir el domingo
        s = self.cal.generar_semana(
            posts_por_semana=7,
            fecha_inicio="2025-10-13",
        )
        fc_slot = next((sl for sl in s.slots if sl.es_fecha_clave), None)
        assert fc_slot is not None
        assert "Madre" in (fc_slot.fecha_clave_nombre or "")

    def test_slot_fecha_clave_navidad(self):
        s = self.cal.generar_semana(
            posts_por_semana=1,
            fecha_inicio="2025-12-22",  # semana que incluye 25 dic
        )
        fc_slot = next((sl for sl in s.slots if sl.es_fecha_clave), None)
        assert fc_slot is not None
        assert "Navidad" in (fc_slot.fecha_clave_nombre or "")

    def test_slot_fecha_clave_black_friday(self):
        s = self.cal.generar_semana(
            posts_por_semana=1,
            fecha_inicio="2025-11-24",  # semana que incluye BF
        )
        fc_slot = next((sl for sl in s.slots if sl.es_fecha_clave), None)
        assert fc_slot is not None
        assert "Black Friday" in (fc_slot.fecha_clave_nombre or "")

    def test_slot_fecha_clave_independencia(self):
        s = self.cal.generar_semana(
            posts_por_semana=1,
            fecha_inicio="2025-07-07",  # semana que incluye 9 jul
        )
        fc_slot = next((sl for sl in s.slots if sl.es_fecha_clave), None)
        assert fc_slot is not None
        assert "Independencia" in (fc_slot.fecha_clave_nombre or "")

    def test_slot_fecha_clave_nino(self):
        # Dia del Nino = 17 agosto (domingo). Usar 7 posts para cubrir domingo
        s = self.cal.generar_semana(
            posts_por_semana=7,
            fecha_inicio="2025-08-11",
        )
        fc_slot = next((sl for sl in s.slots if sl.es_fecha_clave), None)
        assert fc_slot is not None
        assert "Nino" in (fc_slot.fecha_clave_nombre or "")

    def test_slot_fecha_clave_ano_nuevo(self):
        s = self.cal.generar_semana(
            posts_por_semana=1,
            fecha_inicio="2025-12-29",  # semana que incluye 31 dic / 1 ene
        )
        fc_slot = next((sl for sl in s.slots if sl.es_fecha_clave), None)
        assert fc_slot is not None

    # --- _generar_post_para_slot ---

    def test_post_lote_venta(self):
        slot = SlotEditorial(
            fecha="2025-07-14",
            dia_semana="lunes",
            hora_sugerida="19:00",
            tipo_post="lote_venta",
            tono="emotivo",
            nicho=["general"],
            municipio="Cañuelas",
        )
        post = self.cal._generar_post_para_slot(slot)
        assert post["caption"] == "Lote test"
        self.studio.post.post_lote_venta.assert_called()

    def test_post_country(self):
        slot = SlotEditorial(
            fecha="2025-07-14",
            dia_semana="lunes",
            hora_sugerida="19:00",
            tipo_post="country",
            tono="premium",
            nicho=["country"],
            municipio="Pilar",
        )
        post = self.cal._generar_post_para_slot(slot)
        assert post["caption"] == "Country test"

    def test_post_campo(self):
        slot = SlotEditorial(
            fecha="2025-07-14",
            dia_semana="lunes",
            hora_sugerida="19:00",
            tipo_post="campo",
            tono="inversion",
            nicho=["campo"],
            municipio="Cañuelas",
        )
        post = self.cal._generar_post_para_slot(slot)
        assert post["caption"] == "Campo test"

    def test_post_lote_periurbano(self):
        slot = SlotEditorial(
            fecha="2025-07-14",
            dia_semana="lunes",
            hora_sugerida="19:00",
            tipo_post="lote_periurbano",
            tono="emotivo",
            nicho=["general"],
            municipio="Cañuelas",
        )
        post = self.cal._generar_post_para_slot(slot)
        assert post["caption"] == "Periurbano test"

    def test_post_preventa(self):
        slot = SlotEditorial(
            fecha="2025-07-14",
            dia_semana="lunes",
            hora_sugerida="19:00",
            tipo_post="preventa",
            tono="premium",
            nicho=["country"],
            municipio="Pilar",
        )
        post = self.cal._generar_post_para_slot(slot)
        assert post["caption"] == "Preventa test"

    def test_post_carrusel(self):
        slot = SlotEditorial(
            fecha="2025-07-14",
            dia_semana="lunes",
            hora_sugerida="19:00",
            tipo_post="carrusel",
            tono="premium",
            nicho=["general"],
            municipio="Cañuelas",
        )
        post = self.cal._generar_post_para_slot(slot)
        assert post["tipo"] == "carrusel"
        assert post["placeholder"] is True

    def test_post_servicios(self):
        slot = SlotEditorial(
            fecha="2025-07-14",
            dia_semana="lunes",
            hora_sugerida="19:00",
            tipo_post="servicios",
            tono="premium",
            nicho=["servicios"],
            municipio="Cañuelas",
        )
        post = self.cal._generar_post_para_slot(slot)
        assert post["tipo"] == "carrusel"
        assert post["placeholder"] is True

    def test_post_render_proyecto(self):
        slot = SlotEditorial(
            fecha="2025-07-14",
            dia_semana="lunes",
            hora_sugerida="19:00",
            tipo_post="render_proyecto",
            tono="aspiracional",
            nicho=["casas"],
            municipio="Cañuelas",
        )
        post = self.cal._generar_post_para_slot(slot)
        assert post["tipo"] == "render_proyecto"
        assert "prompt" in post

    def test_post_obra_avance(self):
        slot = SlotEditorial(
            fecha="2025-07-14",
            dia_semana="lunes",
            hora_sugerida="19:00",
            tipo_post="obra_avance",
            tono="practico",
            nicho=["construccion"],
            municipio="Cañuelas",
        )
        post = self.cal._generar_post_para_slot(slot)
        assert post["tipo"] == "obra_avance"
        assert post["placeholder"] is True

    def test_post_fecha_especial(self):
        slot = SlotEditorial(
            fecha="2025-07-14",
            dia_semana="lunes",
            hora_sugerida="10:00",
            tipo_post="fecha_especial",
            tono="emotivo",
            nicho=["general"],
            municipio="Cañuelas",
            es_fecha_clave=True,
            fecha_clave_nombre="Dia de la Madre",
        )
        post = self.cal._generar_post_para_slot(slot)
        assert post["tipo"] == "fecha_especial"

    def test_post_tipo_generico(self):
        slot = SlotEditorial(
            fecha="2025-07-14",
            dia_semana="lunes",
            hora_sugerida="19:00",
            tipo_post="tipo_raro",
            tono="emotivo",
            nicho=["general"],
            municipio="Cañuelas",
        )
        post = self.cal._generar_post_para_slot(slot)
        assert post["tipo"] == "tipo_raro"
        assert post["placeholder"] is True

    def test_post_error_handling(self):
        self.studio.post.post_lote_venta.side_effect = Exception("API down")
        slot = SlotEditorial(
            fecha="2025-07-14",
            dia_semana="lunes",
            hora_sugerida="19:00",
            tipo_post="lote_venta",
            tono="emotivo",
            nicho=["general"],
            municipio="Cañuelas",
        )
        post = self.cal._generar_post_para_slot(slot)
        assert "error" in post
        assert "API down" in post["error"]

    # --- _caption_placeholder_* ---

    def test_caption_carrusel_premium(self):
        c = CalendarioEditorial._caption_placeholder_carrusel("Cañuelas", "premium", ["general"])
        assert "✨" in c
        assert "Cañuelas" in c

    def test_caption_carrusel_emotivo(self):
        c = CalendarioEditorial._caption_placeholder_carrusel("Pilar", "emotivo", ["campo"])
        assert "🌾" in c

    def test_caption_carrusel_default(self):
        c = CalendarioEditorial._caption_placeholder_carrusel("M", "practico", [])
        assert "M" in c

    def test_caption_render_aspiracional(self):
        c = CalendarioEditorial._caption_placeholder_render("Cañuelas", "aspiracional")
        assert "🏡" in c

    def test_caption_render_default(self):
        c = CalendarioEditorial._caption_placeholder_render("Pilar", "premium")
        assert "📐" in c

    def test_caption_obra_practico(self):
        c = CalendarioEditorial._caption_placeholder_obra("Cañuelas", "practico")
        assert "🏗" in c

    def test_caption_obra_default(self):
        c = CalendarioEditorial._caption_placeholder_obra("M", "emotivo")
        assert "🚧" in c

    def test_caption_generico(self):
        c = CalendarioEditorial._caption_placeholder_generico(
            "render_proyecto", "Cañuelas", "emotivo"
        )
        assert "Render proyecto" in c

    # --- _caption_fecha_especial ---

    def test_caption_madre(self):
        c = CalendarioEditorial._caption_fecha_especial("Dia de la Madre", "Cañuelas", "emotivo")
        assert "madres" in c.lower()

    def test_caption_padre(self):
        c = CalendarioEditorial._caption_fecha_especial("Dia del Padre", "Pilar", "emotivo")
        assert "padre" in c.lower()

    def test_caption_navidad(self):
        c = CalendarioEditorial._caption_fecha_especial("Navidad", "M", "emotivo")
        assert "fiestas" in c.lower()

    def test_caption_ano_nuevo(self):
        c = CalendarioEditorial._caption_fecha_especial("Ano Nuevo", "M", "emotivo")
        assert "2026" in c

    def test_caption_black_friday(self):
        c = CalendarioEditorial._caption_fecha_especial("Black Friday", "M", "urgencia")
        assert "Black Friday" in c

    def test_caption_independencia(self):
        c = CalendarioEditorial._caption_fecha_especial("Dia de la Independencia", "M", "emotivo")
        assert "Julio" in c or "julio" in c

    def test_caption_nino(self):
        c = CalendarioEditorial._caption_fecha_especial("Dia del Nino", "M", "emotivo")
        assert "ninio" in c.lower()

    def test_caption_generica(self):
        c = CalendarioEditorial._caption_fecha_especial("Dia del Maestro", "M", "practico")
        assert "Maestro" in c

    # --- Helpers de fecha ---

    def test_lunes_de_semana_1(self):
        lunes = CalendarioEditorial._lunes_de_semana(1)
        assert lunes.weekday() == 0  # Monday

    def test_parsear_fecha(self):
        dt = CalendarioEditorial._parsear_fecha("2025-07-14")
        assert dt.year == 2025
        assert dt.month == 7
        assert dt.day == 14

    def test_fechas_clave_en_rango(self):
        inicio = datetime(2025, 7, 7)
        fin = datetime(2025, 7, 13)
        fechas = self.cal._fechas_clave_en_rango(inicio, fin)
        assert any(f["nombre"] == "Dia de la Independencia" for f in fechas)

    def test_fechas_clave_en_rango_multi_anio(self):
        inicio = datetime(2025, 12, 29)
        fin = datetime(2026, 1, 4)
        fechas = self.cal._fechas_clave_en_rango(inicio, fin)
        assert len(fechas) > 0


# ===== Persistencia =====


class TestPersistencia:
    def setup_method(self):
        self.studio = _mock_studio()
        self.cal = CalendarioEditorial(self.studio)

    def test_guardar(self, tmp_path):
        with patch("calendario_editorial.CALENDARIOS_DIR", tmp_path):
            s = self.cal.generar_semana(posts_por_semana=3)
            ruta = self.cal.guardar(s)
            assert (ruta / "plan.json").exists()

    def test_exportar_markdown(self, tmp_path):
        with patch("calendario_editorial.CALENDARIOS_DIR", tmp_path):
            s = self.cal.generar_semana(posts_por_semana=3)
            ruta = self.cal.exportar_markdown(s)
            assert ruta.exists()
            contenido = ruta.read_text()
            assert "Semana" in contenido

    def test_exportar_markdown_custom_ruta(self, tmp_path):
        s = self.cal.generar_semana(posts_por_semana=2)
        ruta = tmp_path / "custom" / "plan.md"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        result = self.cal.exportar_markdown(s, ruta=ruta)
        assert result.exists()

    def test_exportar_csv(self, tmp_path):
        with patch("calendario_editorial.CALENDARIOS_DIR", tmp_path):
            s = self.cal.generar_semana(posts_por_semana=3)
            ruta = self.cal.exportar_csv(s)
            assert ruta.exists()
            contenido = ruta.read_text()
            assert "fecha" in contenido

    def test_exportar_csv_custom_ruta(self, tmp_path):
        s = self.cal.generar_semana(posts_por_semana=2)
        ruta = tmp_path / "custom" / "plan.csv"
        result = self.cal.exportar_csv(s, ruta=ruta)
        assert result.exists()

    def test_exportar_ics(self, tmp_path):
        with patch("calendario_editorial.CALENDARIOS_DIR", tmp_path):
            s = self.cal.generar_semana(posts_por_semana=3)
            ruta = self.cal.exportar_ics(s)
            assert ruta.exists()
            contenido = ruta.read_text()
            assert "BEGIN:VCALENDAR" in contenido

    def test_exportar_ics_custom_ruta(self, tmp_path):
        s = self.cal.generar_semana(posts_por_semana=2)
        ruta = tmp_path / "custom" / "plan.ics"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        result = self.cal.exportar_ics(s, ruta=ruta)
        assert result.exists()
        contenido = result.read_text()
        assert "BEGIN:VEVENT" in contenido

    def test_markdown_con_fecha_clave(self, tmp_path):
        s = self.cal.generar_semana(
            posts_por_semana=1,
            fecha_inicio="2025-12-22",
        )
        ruta = tmp_path / "fc.md"
        self.cal.exportar_markdown(s, ruta=ruta)
        contenido = ruta.read_text()
        assert "🎉" in contenido

    def test_markdown_con_proyecto(self, tmp_path):
        s = self.cal.generar_semana(
            posts_por_semana=1,
            proyectos=["chacra-5ha"],
        )
        ruta = tmp_path / "proj.md"
        self.cal.exportar_markdown(s, ruta=ruta)
        contenido = ruta.read_text()
        assert "chacra-5ha" in contenido


# ===== Import patching =====


from unittest.mock import patch

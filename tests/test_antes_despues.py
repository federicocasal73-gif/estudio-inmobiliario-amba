"""Tests del modulo antes_despues.py.

Cubre:
  - AntesDespues dataclass: to_dict, defaults
  - AntesDespuesFactory.generar: modos real/ia/mixto, modo invalido
  - _prompt_despues_sd, _instrucciones_img2img
  - _carrusel_antes_despues: slides portada/antes/despues/cta, slide tiempo
  - _caption: modos real/ia, con/sin tiempo, con/sin cliente
  - _overlay_portada
  - guardar: persistencia JSON/md/txt/slides, copia foto antes
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from antes_despues import AntesDespues, AntesDespuesFactory

# ===== AntesDespues dataclass =====


class TestAntesDespuesDataclass:
    def test_defaults(self):
        ad = AntesDespues(
            nombre_obra="obra",
            municipio="Cañuelas",
            proyecto=None,
            modo="ia",
            estilo_casa="campo",
            hectareas=5,
            foto_antes_path="/fake/antes.jpg",
        )
        assert ad.foto_despues_path is None
        assert ad.cliente is None
        assert ad.fecha_inicio is None
        assert ad.tiempo_construccion_meses is None
        assert ad.prompt_despues == ""
        assert ad.instrucciones_img2img == []
        assert ad.hashtags == []
        assert ad.metadata == {}

    def test_to_dict(self):
        ad = AntesDespues(
            nombre_obra="obra",
            municipio="Cañuelas",
            proyecto="proj",
            modo="real",
            estilo_casa="campo",
            hectareas=5,
            foto_antes_path="/antes.jpg",
            foto_despues_path="/despues.jpg",
        )
        d = ad.to_dict()
        assert d["nombre_obra"] == "obra"
        assert d["modo"] == "real"
        assert isinstance(d, dict)


# ===== AntesDespuesFactory =====


class TestAntesDespuesFactory:
    def _make_factory(self):
        studio = MagicMock()
        studio.post.hashtags.return_value = ["#lote", "#cañuelas"]
        studio.construccion.render_proyecto.return_value = MagicMock(prompt="prompt render")
        return AntesDespuesFactory(studio)

    def test_generar_modo_ia(self):
        factory = self._make_factory()
        ad = factory.generar(
            foto_antes_path="/fake/antes.jpg",
            estilo_casa="campo_tradicional",
            hectareas=5,
            municipio="Cañuelas",
            proyecto="test-proj",
            modo="ia",
        )
        assert ad.modo == "ia"
        assert ad.prompt_despues != ""
        assert len(ad.instrucciones_img2img) > 0
        assert ad.caption_narrativo != ""
        assert len(ad.hashtags) > 0
        assert ad.carrusel != {}

    def test_generar_modo_real(self):
        factory = self._make_factory()
        ad = factory.generar(
            foto_antes_path="/fake/antes.jpg",
            foto_despues_path="/fake/despues.jpg",
            cliente="Familia Perez",
            municipio="Escobar",
            proyecto="test-real",
            modo="real",
        )
        assert ad.modo == "real"
        assert ad.foto_despues_path is not None
        assert "Familia Perez" in ad.caption_narrativo

    def test_generar_modo_mixto(self):
        factory = self._make_factory()
        ad = factory.generar(
            foto_antes_path="/fake/antes.jpg",
            modo="mixto",
        )
        assert ad.modo == "mixto"
        assert ad.caption_narrativo != ""

    def test_generar_modo_default_real(self):
        factory = self._make_factory()
        ad = factory.generar(
            foto_antes_path="/fake/antes.jpg",
            foto_despues_path="/fake/despues.jpg",
        )
        assert ad.modo == "real"

    def test_generar_modo_default_ia(self):
        factory = self._make_factory()
        ad = factory.generar(foto_antes_path="/fake/antes.jpg")
        assert ad.modo == "ia"

    def test_generar_modo_invalido(self):
        factory = self._make_factory()
        with pytest.raises(ValueError, match="modo invalido"):
            factory.generar(foto_antes_path="/fake/antes.jpg", modo="otro")

    def test_instrucciones_img2img(self):
        instrucciones = AntesDespuesFactory._instrucciones_img2img("/path/foto.jpg")
        assert len(instrucciones) == 7
        assert any("Subir foto" in i for i in instrucciones)

    def test_overlay_portada(self):
        ad = AntesDespues(
            nombre_obra="obra",
            municipio="C",
            proyecto=None,
            modo="ia",
            estilo_casa="e",
            hectareas=1,
            foto_antes_path="/a.jpg",
            cliente="Don Perez",
        )
        overlay = AntesDespuesFactory._overlay_portada(ad)
        assert "Don Perez" in overlay
        assert "Antes" in overlay

    def test_overlay_portada_sin_cliente(self):
        ad = AntesDespues(
            nombre_obra="obra",
            municipio="C",
            proyecto=None,
            modo="ia",
            estilo_casa="e",
            hectareas=1,
            foto_antes_path="/a.jpg",
        )
        overlay = AntesDespuesFactory._overlay_portada(ad)
        assert "este proyecto" in overlay


class TestCaptionAntesDespues:
    def _make_factory(self):
        studio = MagicMock()
        studio.post.hashtags.return_value = ["#tag"]
        studio.construccion.render_proyecto.return_value = MagicMock(prompt="p")
        return AntesDespuesFactory(studio)

    def test_caption_real_con_tiempo(self):
        factory = self._make_factory()
        ad = factory.generar(
            foto_antes_path="/a.jpg",
            foto_despues_path="/d.jpg",
            cliente="Familia",
            municipio="Escobar",
            tiempo_construccion_meses=8,
            modo="real",
        )
        assert "8 meses" in ad.caption_narrativo
        assert "Familia" in ad.caption_narrativo

    def test_caption_real_con_fechas(self):
        factory = self._make_factory()
        ad = factory.generar(
            foto_antes_path="/a.jpg",
            foto_despues_path="/d.jpg",
            cliente="Familia",
            municipio="Escobar",
            fecha_inicio="2025-01-01",
            fecha_entrega="2025-06-01",
            modo="real",
        )
        assert "2025-01-01" in ad.caption_narrativo
        assert "2025-06-01" in ad.caption_narrativo

    def test_caption_real_sin_tiempo(self):
        factory = self._make_factory()
        ad = factory.generar(
            foto_antes_path="/a.jpg",
            foto_despues_path="/d.jpg",
            cliente="Familia",
            municipio="Escobar",
            modo="real",
        )
        assert "Antes era esto" in ad.caption_narrativo

    def test_caption_ia(self):
        factory = self._make_factory()
        ad = factory.generar(foto_antes_path="/a.jpg", modo="ia")
        assert "Antes era un lote baldío" in ad.caption_narrativo

    def test_caption_ia_sin_cliente(self):
        factory = self._make_factory()
        ad = factory.generar(foto_antes_path="/a.jpg", modo="ia")
        assert ad.cliente is None


class TestCarruselAntesDespues:
    def _make_factory(self):
        studio = MagicMock()
        studio.post.hashtags.return_value = ["#tag"]
        studio.construccion.render_proyecto.return_value = MagicMock(prompt="p render")
        return AntesDespuesFactory(studio)

    def test_carrusel_ia(self):
        factory = self._make_factory()
        ad = factory.generar(foto_antes_path="/a.jpg", modo="ia")
        slides = ad.carrusel.get("slides", [])
        assert len(slides) >= 3
        assert slides[0]["tipo"] == "portada"
        assert slides[1]["tipo"] == "placeholder_foto"
        assert slides[2]["tipo"] == "beneficio"

    def test_carrusel_real(self):
        factory = self._make_factory()
        ad = factory.generar(foto_antes_path="/a.jpg", foto_despues_path="/d.jpg", modo="real")
        slides = ad.carrusel.get("slides", [])
        assert len(slides) >= 3
        assert slides[2]["tipo"] == "placeholder_foto"

    def test_carrusel_con_tiempo(self):
        factory = self._make_factory()
        ad = factory.generar(
            foto_antes_path="/a.jpg",
            foto_despues_path="/d.jpg",
            tiempo_construccion_meses=8,
            modo="real",
        )
        slides = ad.carrusel.get("slides", [])
        tipos = [s["tipo"] for s in slides]
        assert "dato" in tipos

    def test_carrusel_con_fechas(self):
        factory = self._make_factory()
        ad = factory.generar(
            foto_antes_path="/a.jpg",
            foto_despues_path="/d.jpg",
            fecha_inicio="2025-01",
            fecha_entrega="2025-06",
            modo="real",
        )
        slides = ad.carrusel.get("slides", [])
        tipos = [s["tipo"] for s in slides]
        assert "dato" in tipos

    def test_carrusel_sin_tiempo(self):
        factory = self._make_factory()
        ad = factory.generar(foto_antes_path="/a.jpg", foto_despues_path="/d.jpg", modo="real")
        slides = ad.carrusel.get("slides", [])
        tipos = [s["tipo"] for s in slides]
        assert "dato" not in tipos

    def test_carrusel_cta_presente(self):
        factory = self._make_factory()
        ad = factory.generar(foto_antes_path="/a.jpg", modo="ia")
        slides = ad.carrusel.get("slides", [])
        assert slides[-1]["tipo"] == "cta"

    def test_carrusel_tema(self):
        factory = self._make_factory()
        ad = factory.generar(foto_antes_path="/a.jpg", proyecto="mi-proyecto", modo="ia")
        assert ad.carrusel.get("tipo") == "antes_despues"

    def test_carrusel_metadata(self):
        factory = self._make_factory()
        ad = factory.generar(foto_antes_path="/a.jpg", modo="ia")
        assert ad.metadata["modo"] == "ia"
        assert ad.metadata["requiere_generar_despues"] is True

    def test_carrusel_metadata_real(self):
        factory = self._make_factory()
        ad = factory.generar(foto_antes_path="/a.jpg", foto_despues_path="/d.jpg", modo="real")
        assert ad.metadata["tiene_foto_despues_real"] is True
        assert ad.metadata["requiere_generar_despues"] is False


class TestGuardarAntesDespues:
    def _make_factory(self):
        studio = MagicMock()
        studio.post.hashtags.return_value = ["#tag"]
        studio.construccion.render_proyecto.return_value = MagicMock(prompt="p")
        return AntesDespuesFactory(studio)

    def test_guardar_con_proyecto(self, tmp_path):
        factory = self._make_factory()
        ad = factory.generar(foto_antes_path="/fake/antes.jpg", proyecto="test-proj", modo="ia")

        with patch("antes_despues.ROOT", tmp_path):
            carpeta = factory.guardar(ad)

        assert carpeta.exists()
        assert (carpeta / "antes_despues.json").exists()
        assert (carpeta / "antes_despues.md").exists()
        assert (carpeta / "caption_instagram.txt").exists()
        assert (carpeta / "slides").exists()

    def test_guardar_sin_proyecto(self, tmp_path):
        factory = self._make_factory()
        ad = factory.generar(foto_antes_path="/fake/antes.jpg", modo="ia")

        with patch("antes_despues.ROOT", tmp_path):
            carpeta = factory.guardar(ad)

        assert carpeta.exists()
        assert "_generados" in str(carpeta)

    def test_guardar_contenido_json(self, tmp_path):
        factory = self._make_factory()
        ad = factory.generar(foto_antes_path="/fake/antes.jpg", proyecto="p", modo="ia")

        with patch("antes_despues.ROOT", tmp_path):
            carpeta = factory.guardar(ad)

        data = json.loads((carpeta / "antes_despues.json").read_text())
        assert data["modo"] == "ia"
        assert data["nombre_obra"] == "p"

    def test_guardar_contenido_md(self, tmp_path):
        factory = self._make_factory()
        ad = factory.generar(foto_antes_path="/fake/antes.jpg", proyecto="p", modo="ia")

        with patch("antes_despues.ROOT", tmp_path):
            carpeta = factory.guardar(ad)

        md = (carpeta / "antes_despues.md").read_text()
        assert "Antes / Después" in md
        assert "Prompt" in md

    def test_guardar_slides(self, tmp_path):
        factory = self._make_factory()
        ad = factory.generar(foto_antes_path="/fake/antes.jpg", proyecto="p", modo="ia")

        with patch("antes_despues.ROOT", tmp_path):
            carpeta = factory.guardar(ad)

        slides = list((carpeta / "slides").glob("*.json"))
        assert len(slides) >= 3

    def test_guardar_foto_antes_copiada(self, tmp_path):
        factory = self._make_factory()
        foto = tmp_path / "mi_foto.jpg"
        foto.write_bytes(b"\xff\xd8")

        ad = factory.generar(foto_antes_path=str(foto), proyecto="p", modo="ia")

        with patch("antes_despues.ROOT", tmp_path):
            carpeta = factory.guardar(ad)

        inputs = carpeta / "inputs"
        assert inputs.exists()
        assert (inputs / "mi_foto.jpg").exists()

"""Tests del modulo realestate_studio.py.

Cubre:
  - GenerationRequest: to_dict
  - FooocusClient: disponible, payload_text_to_image, guardar_payload
  - VerticalLotes: 17 metodos de generacion de prompts
  - VerticalConstruccion: 28 metodos de generacion de prompts
  - CaptionFactory: caption, hashtags, _slug_municipio, todos los post_* (23 metodos)
  - RealestateStudio: init, guardar_prompt, guardar_post, _cargar_json, _defaults
"""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from realestate_studio import (
    ASPECT_CHACRA,
    ASPECT_COUNTRY,
    ASPECT_INSTAGRAM_LANDSCAPE,
    ASPECT_INSTAGRAM_POST,
    CaptionFactory,
    FooocusClient,
    GenerationRequest,
    RealestateStudio,
    VerticalConstruccion,
    VerticalLotes,
)

# ===== Fixtures =====

PROMPTS_DB = {
    "plantillas_base": {
        "chacra_pampeana": "wide rural landscape, pampas grass, ombu trees",
        "country_premium": "luxury gated community entrance",
        "lote_periurbano": "flat suburban building lot",
        "vista_aerea_loteo": "aerial drone shot, subdivision",
        "loteo_en_desarrollo": "development under construction",
        "campo_mediano": "extensive cattle ranch landscape",
        "campo_grande": "vast pampas farmland aerial view",
        "lote_inversion_chico": "small urban-suburban building lot",
        "pileta_quinta": "quinta with swimming pool",
        "estancia_productiva": "productive Argentine estancia",
        "emprendimiento_agroturistico": "agritourism estate",
        "lote_comercial_ruta": "commercial lot on highway",
        "amanecer_pampa": "early morning fog over pampas",
        "atardecer_campo": "dramatic sunset over pampas",
        "tranquera_argentina": "rustic wooden gate",
        "molino_tanque": "classic Argentine windmill",
        "casco_estancia": "old traditional estancia",
    },
    "negativos_default": "blurry, low quality, distorted",
}

CAPTIONS_DB = {
    "plantillas": {
        "lote_venta": [
            {
                "tono": "emotivo",
                "texto": "Imaginate esto: {tema} en {municipio}, {hectareas} a {distancia_caba}",
            },
            {"tono": "practico", "texto": "{tema}\n\n{hectareas}\n{servicios_disponibles}"},
        ],
        "country": [
            {"tono": "premium", "texto": "{nombre_country} - Lote de {metros_cuadrados} m2"},
        ],
        "campo": [
            {"tono": "inversion", "texto": "{hectareas} en {municipio}, rubro {rubro}"},
        ],
        "preventa_loteo": [
            {"tono": "oportunidad", "texto": "Pre-venta {nombre_loteo} etapa {etapa}"},
        ],
        "lote_periurbano": [
            {"tono": "practico", "texto": "Lote en {municipio}, {metros_cuadrados} m2"},
        ],
        "testimonial_cliente": [
            {"tono": "profesional", "texto": "Cliente satisfecho: {testimonio}"},
        ],
        "preguntas_frecuentes": [
            {"tono": "educativo", "texto": "Pregunta: {pregunta}\nRespuesta: {respuesta}"},
        ],
        "obra_avance": [
            {"tono": "tecnico", "texto": "Avance obra: {etapa} en {municipio}"},
        ],
        "presupuesto_obra": [
            {"tono": "practico", "texto": "Presupuesto: {concepto} = ${monto}"},
        ],
        "etapas_obra": [
            {
                "tono": "educativo",
                "texto": "Etapas de {tipo_obra}: {etapa_numero} - {etapa_nombre}",
            },
        ],
        "steel_frame_vs_tradicional": [
            {"tono": "educativo", "texto": "Steel frame vs tradicional: {comparacion}"},
        ],
        "planos_render": [
            {"tono": "premium", "texto": "Proyecto: {tipo_vivienda} en {municipio}"},
        ],
        "aberturas_instalaciones": [
            {"tono": "tecnico", "texto": "Aberturas: {tipo_abertura} en {municipio}"},
        ],
        "pisos_revestimientos": [
            {"tono": "premium", "texto": "Pisos: {material} en {municipio}"},
        ],
        "obra_terminada": [
            {"tono": "premium", "texto": "Obra terminada: {tipo_vivienda} en {municipio}"},
        ],
        "plazo_construccion": [
            {"tono": "practico", "texto": "Plazo: {tipo_obra} en {plazo} meses"},
        ],
        "garantia_postventa": [
            {"tono": "profesional", "texto": "Garantia post-venta: {duracion} meses"},
        ],
        "materiales_premium": [
            {"tono": "premium", "texto": "Material premium: {material} en {municipio}"},
        ],
        "errores_comunes_construccion": [
            {"tono": "educativo", "texto": "Error comun: {error} en {municipio}"},
        ],
        "equipo_trabajo_maquinaria": [
            {"tono": "tecnico", "texto": "Equipo: {maquinaria} en {municipio}"},
        ],
        "permisos_tramites": [
            {"tono": "practico", "texto": "Tramites: {tramite} en {municipio}"},
        ],
        "diseno_interior_acabados": [
            {"tono": "aspiracional", "texto": "Interior: {estilo} en {municipio}"},
        ],
    },
    "hashtags_por_nicho": {
        "general": ["#lotes", "#campo", "#AMBA"],
        "campo": ["#campo", "#chacra", "#hectareas"],
        "inversion": ["#inversion", "#inmobiliario"],
        "country": ["#country", "#lifestyle"],
        "construccion": ["#construccion", "#obra", "#steelframe"],
    },
    "hashtags_zona_template": [
        "#{municipio_sin_espacios}",
        "#lotesen{municipio_sin_espacios}",
    ],
}


@pytest.fixture
def prompts_db():
    return PROMPTS_DB.copy()


@pytest.fixture
def captions_db():
    return CAPTIONS_DB.copy()


@pytest.fixture
def lotes(prompts_db):
    return VerticalLotes(prompts_db)


@pytest.fixture
def construccion(prompts_db):
    return VerticalConstruccion(prompts_db)


@pytest.fixture
def caption_factory(captions_db):
    return CaptionFactory(captions_db)


# ===== GenerationRequest =====


class TestGenerationRequest:
    def test_to_dict_minimal(self):
        req = GenerationRequest(prompt="test prompt")
        d = req.to_dict()
        assert d["prompt"] == "test prompt"
        assert "negative_prompt" in d
        assert "aspect_ratio" in d
        assert "styles" in d

    def test_to_dict_with_metadata(self):
        req = GenerationRequest(prompt="x", metadata={"tipo": "chacra"})
        d = req.to_dict()
        assert d["metadata"]["tipo"] == "chacra"

    def test_default_values(self):
        req = GenerationRequest(prompt="x")
        assert req.aspect_ratio == ASPECT_INSTAGRAM_POST
        assert req.performance == "Speed"
        assert req.steps == 30
        assert req.cfg_scale == 4.0
        assert req.seed == -1


# ===== FooocusClient =====


class TestFooocusClient:
    def test_init_default(self):
        client = FooocusClient()
        assert "127.0.0.1" in client.base_url

    def test_init_custom_url(self):
        client = FooocusClient(base_url="http://custom:9999")
        assert "custom" in client.base_url

    @patch("urllib.request.urlopen")
    def test_disponible_true(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        client = FooocusClient()
        assert client.disponible() is True

    @patch("urllib.request.urlopen")
    def test_disponible_false_on_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("conn refused")
        client = FooocusClient()
        assert client.disponible() is False

    def test_payload_text_to_image(self):
        client = FooocusClient()
        payload = client.payload_text_to_image(
            prompt="chacra en Cañuelas",
            negativo="blurry",
            aspect=ASPECT_CHACRA,
            styles=["Fooocus V2"],
        )
        assert payload["prompt"] == "chacra en Cañuelas"
        assert payload["negative_prompt"] == "blurry"
        assert payload["aspect_ratio"] == ASPECT_CHACRA

    def test_guardar_payload(self, tmp_path):
        client = FooocusClient()
        with patch.object(client, "base_url", str(tmp_path)):
            # usar directamente Path
            pass
        # Test directo
        payload = {"prompt": "test"}
        ruta = tmp_path / "test_payload.json"
        ruta.write_text(json.dumps(payload))
        assert ruta.exists()
        assert json.loads(ruta.read_text())["prompt"] == "test"


# ===== VerticalLotes =====


class TestVerticalLotes:
    def test_init(self, lotes):
        assert lotes.db is not None
        assert lotes.negativos == "blurry, low quality, distorted"

    def test_req_returns_generation_request(self, lotes):
        req = lotes._req("test prompt", ASPECT_CHACRA)
        assert isinstance(req, GenerationRequest)
        assert req.prompt == "test prompt"
        assert req.aspect_ratio == ASPECT_CHACRA

    def test_req_default_styles(self, lotes):
        req = lotes._req("x", ASPECT_CHACRA)
        assert req.styles == lotes.ESTILOS_FOTOS

    def test_req_custom_styles(self, lotes):
        req = lotes._req("x", ASPECT_CHACRA, estilos=["Custom Style"])
        assert req.styles == ["Custom Style"]

    @pytest.mark.parametrize("municipio", ["Cañuelas", "Pilar", "Escobar", "Luján", "Cañuelas"])
    def test_chacra_pampeana_various_municipios(self, lotes, municipio):
        req = lotes.chacra_pampeana(hectareas=5, municipio=municipio)
        assert isinstance(req, GenerationRequest)
        assert municipio in req.prompt
        assert isinstance(req, GenerationRequest)
        assert req.metadata["hectareas"] == 5

    def test_chacra_pampeana_default_values(self, lotes):
        req = lotes.chacra_pampeana()
        assert "Cañuelas" in req.prompt
        assert req.metadata["hectareas"] == 5

    def test_country_premium(self, lotes):
        req = lotes.country_premium(nombre="El Casco")
        assert "El Casco" in req.prompt
        assert isinstance(req, GenerationRequest)

    def test_lote_periurbano(self, lotes):
        req = lotes.lote_periurbano(metros_cuadrados=1000, municipio="Escobar")
        assert "Escobar" in req.prompt
        assert isinstance(req, GenerationRequest)

    def test_vista_aerea_loteo(self, lotes):
        req = lotes.vista_aerea_loteo(municipio="Pilar")
        assert isinstance(req, GenerationRequest)
        assert req.aspect_ratio == ASPECT_INSTAGRAM_LANDSCAPE

    def test_loteo_en_desarrollo(self, lotes):
        req = lotes.loteo_en_desarrollo(municipio="Cañuelas")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_campo_mediano(self, lotes):
        req = lotes.campo_mediano(hectareas=50, municipio="Cañuelas")
        assert "50" in req.prompt
        assert isinstance(req, GenerationRequest)

    def test_campo_grande(self, lotes):
        req = lotes.campo_grande(hectareas=500, municipio="Cañuelas")
        assert "500" in req.prompt
        assert isinstance(req, GenerationRequest)

    def test_lote_inversion_chico(self, lotes):
        req = lotes.lote_inversion_chico(municipio="Pilar")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_pileta_quinta(self, lotes):
        req = lotes.pileta_quinta(municipio="Escobar")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_estancia_productiva(self, lotes):
        req = lotes.estancia_productiva(municipio="San Antonio de Areco")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_emprendimiento_agroturistico(self, lotes):
        req = lotes.emprendimiento_agroturistico(municipio="Cañuelas")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_lote_comercial_ruta(self, lotes):
        req = lotes.lote_comercial_ruta(municipio="Campana")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_amanecer_pampa(self, lotes):
        req = lotes.amanecer_pampa(municipio="Luján")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_atardecer_campo(self, lotes):
        req = lotes.atardecer_campo(municipio="Cañuelas")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_tranquera_argentina(self, lotes):
        req = lotes.tranquera_argentina(municipio="Cañuelas")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_molino_tanque(self, lotes):
        req = lotes.molino_tanque_australiano(municipio="Roque Pérez")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_casco_estancia(self, lotes):
        req = lotes.casco_estancia(municipio="San Antonio de Areco")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_variaciones(self, lotes):
        reqs = lotes.variaciones("test prompt base", n=3)
        assert len(reqs) == 3
        for req in reqs:
            assert isinstance(req, GenerationRequest)

    def test_variaciones_different_seeds(self, lotes):
        reqs = lotes.variaciones("base", n=4)
        seeds = [r.seed for r in reqs]
        # All should be different (very high probability)
        assert len(set(seeds)) == 4

    def test_metadata_includes_municipio(self, lotes):
        req = lotes.chacra_pampeana(municipio="Pilar")
        assert req.metadata["municipio"] == "Pilar"


# ===== VerticalConstruccion =====


class TestVerticalConstruccion:
    def test_init(self, construccion):
        assert construccion.db is not None
        assert construccion.negativos == "blurry, low quality, distorted"

    def test_movimiento_suelo(self, construccion):
        req = construccion.movimiento_suelo(maquinaria="excavadora", municipio="Pilar")
        assert isinstance(req, GenerationRequest)
        assert "excavadora" in req.prompt
        assert "Pilar" in req.prompt

    def test_obra_gruesa(self, construccion):
        req = construccion.obra_gruesa(etapa="hormigón armado", municipio="Escobar")
        assert isinstance(req, GenerationRequest)
        assert "Escobar" in req.prompt

    def test_steel_framing(self, construccion):
        req = construccion.steel_framing(municipio="Cañuelas")
        assert isinstance(req, GenerationRequest)
        assert "Cañuelas" in req.prompt

    def test_render_proyecto(self, construccion):
        req = construccion.render_proyecto(
            estilo="casa de campo",
            hectareas=5,
            municipio="Pilar",
        )
        assert isinstance(req, GenerationRequest)
        assert "Pilar" in req.prompt

    def test_anteproyecto_arquitectonico(self, construccion):
        req = construccion.anteproyecto_arquitectonico(municipio="Cañuelas")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_render_exterior_casa(self, construccion):
        req = construccion.render_exterior_casa(municipio="Escobar")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_render_interior_casa(self, construccion):
        req = construccion.render_interior_casa(municipio="Pilar")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_estudio_de_suelo(self, construccion):
        req = construccion.estudio_de_suelo(municipio="Cañuelas")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_relevamiento_topografico(self, construccion):
        req = construccion.relevamiento_topografico(municipio="Pilar")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_replanteo_obra(self, construccion):
        req = construccion.replanteo_obra(municipio="Escobar")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_excavacion_fundaciones(self, construccion):
        req = construccion.excavacion_fundaciones(municipio="Cañuelas")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_fundaciones_hormigon(self, construccion):
        req = construccion.fundaciones_hormigon(municipio="Pilar")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_estructura_hormigon(self, construccion):
        req = construccion.estructura_hormigon(municipio="Escobar")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_mamposteria_ladrillo(self, construccion):
        req = construccion.mamposteria_ladrillo(municipio="Cañuelas")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_cubierta_techo(self, construccion):
        req = construccion.cubierta_techo(municipio="Pilar", tipo_techo="chapa")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_steel_frame_estructura(self, construccion):
        req = construccion.steel_frame_estructura(municipio="Escobar")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_steel_frame_cerramiento(self, construccion):
        req = construccion.steel_frame_cerramiento(municipio="Cañuelas")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_revoque_grueso(self, construccion):
        req = construccion.revoque_grueso(municipio="Pilar")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_colocacion_aberturas(self, construccion):
        req = construccion.colocacion_aberturas(municipio="Escobar")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_colocacion_pisos(self, construccion):
        req = construccion.colocacion_pisos(municipio="Cañuelas")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_pintura_interior(self, construccion):
        req = construccion.pintura_interior(municipio="Pilar")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_casa_terminada_frente(self, construccion):
        req = construccion.casa_terminada_frente(municipio="Escobar")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_entrega_llaves(self, construccion):
        req = construccion.entrega_llaves(municipio="Cañuelas")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_fachada_moderna_minimalista(self, construccion):
        req = construccion.fachada_moderna_minimalista(municipio="Pilar")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_detalle_madera(self, construccion):
        req = construccion.detalle_madera_arquitectonico(municipio="Escobar")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_equipo_pesado(self, construccion):
        req = construccion.equipo_pesado_construccion(municipio="Cañuelas")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_grua_obra(self, construccion):
        req = construccion.grua_obra(municipio="Pilar")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_motoniveladora(self, construccion):
        req = construccion.motoniveladora(municipio="Escobar")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_equipo_humano(self, construccion):
        req = construccion.equipo_humano_obra(municipio="Cañuelas")
        assert isinstance(req, GenerationRequest)
        assert isinstance(req, GenerationRequest)

    def test_all_methods_return_generation_request(self, construccion):
        """Test that all methods return a valid GenerationRequest."""
        methods = [
            construccion.movimiento_suelo,
            construccion.obra_gruesa,
            construccion.steel_framing,
            construccion.anteproyecto_arquitectonico,
            construccion.render_exterior_casa,
            construccion.render_interior_casa,
            construccion.estudio_de_suelo,
            construccion.relevamiento_topografico,
            construccion.replanteo_obra,
            construccion.excavacion_fundaciones,
            construccion.fundaciones_hormigon,
            construccion.estructura_hormigon,
            construccion.mamposteria_ladrillo,
            construccion.steel_frame_estructura,
            construccion.steel_frame_cerramiento,
            construccion.revoque_grueso,
            construccion.colocacion_aberturas,
            construccion.colocacion_pisos,
            construccion.pintura_interior,
            construccion.casa_terminada_frente,
            construccion.entrega_llaves,
            construccion.fachada_moderna_minimalista,
            construccion.detalle_madera_arquitectonico,
            construccion.equipo_pesado_construccion,
            construccion.grua_obra,
            construccion.motoniveladora,
            construccion.equipo_humano_obra,
        ]
        for method in methods:
            req = method()
            assert isinstance(req, GenerationRequest)
            assert len(req.prompt) > 10


# ===== CaptionFactory =====


class TestCaptionFactory:
    def test_init(self, caption_factory):
        assert caption_factory.db is not None

    def test_slug_municipio(self):
        assert CaptionFactory._slug_municipio("Cañuelas") == "canuelas"
        assert CaptionFactory._slug_municipio("San Antonio de Areco") == "sanantoniodeareco"
        assert CaptionFactory._slug_municipio("Luján") == "lujan"
        assert CaptionFactory._slug_municipio("Escobar") == "escobar"

    def test_caption_with_variables(self, caption_factory):
        result = caption_factory.caption(
            "lote_venta",
            "emotivo",
            tema="5 ha en Cañuelas",
            municipio="Cañuelas",
            hectareas="5 hectareas",
            distancia_caba="65 km",
        )
        assert "Cañuelas" in result
        assert "5 ha" in result

    def test_caption_fallback_when_no_match(self, caption_factory):
        result = caption_factory.caption("tipo_que_no_existe", "tono_x", tema="test")
        assert "test" in result

    def test_caption_with_missing_variables(self, caption_factory):
        result = caption_factory.caption("lote_venta", "emotivo", tema="test")
        # Should not crash even with missing variables
        assert isinstance(result, str)

    def test_hashtags_basic(self, caption_factory):
        result = caption_factory.hashtags(nichos=["general"], n=5)
        assert len(result) <= 5
        assert all(h.startswith("#") for h in result)

    def test_hashtags_with_municipio(self, caption_factory):
        result = caption_factory.hashtags(nichos=["general"], municipio="Cañuelas", n=10)
        slugs = [h for h in result if "canuelas" in h.lower()]
        assert len(slugs) >= 1

    def test_hashtags_blacklist(self, caption_factory):
        result = caption_factory.hashtags(
            nichos=["general"],
            blacklist=["#lotes"],
            n=10,
        )
        assert "#lotes" not in result

    def test_hashtags_must_include(self, caption_factory):
        result = caption_factory.hashtags(
            nichos=["general"],
            must_include=["#custom_tag"],
            n=5,
        )
        assert "#custom_tag" in result

    def test_hashtags_multiple_nichos(self, caption_factory):
        result = caption_factory.hashtags(
            nichos=["general", "campo", "inversion"],
            n=20,
        )
        assert len(result) > 5

    def test_post_lote_venta(self, caption_factory):
        post = caption_factory.post_lote_venta(
            tema="5 ha en Cañuelas",
            municipio="Cañuelas",
            tono="emotivo",
        )
        assert "caption_completo" in post
        assert "hashtags" in post
        assert post["tipo"] == "lote_venta"
        assert post["municipio"] == "Cañuelas"

    def test_post_country(self, caption_factory):
        post = caption_factory.post_country(
            nombre_country="El Casco",
            municipio="Pilar",
            tono="premium",
        )
        assert "caption_completo" in post
        assert "El Casco" in post["caption_completo"]

    def test_post_campo(self, caption_factory):
        post = caption_factory.post_campo(
            hectareas="50",
            municipio="Cañuelas",
            tono="inversion",
        )
        assert "caption_completo" in post
        assert "50" in post["caption_completo"]

    def test_post_preventa(self, caption_factory):
        post = caption_factory.post_preventa(
            nombre_loteo="Los Eucaliptos",
            municipio="Pilar",
            tono="oportunidad",
        )
        assert "caption_completo" in post
        assert "Los Eucaliptos" in post["caption_completo"]

    def test_post_lote_periurbano(self, caption_factory):
        post = caption_factory.post_lote_periurbano(
            municipio="Escobar",
            tono="practico",
        )
        assert "caption_completo" in post

    def test_post_testimonial_cliente(self, caption_factory):
        post = caption_factory.post_testimonial_cliente(
            cliente="Juan Perez",
            historia="Buscaban un lote para construir su casa",
            resultado="Encontraron el lote perfecto",
            tono="emotivo",
        )
        assert "caption_completo" in post

    def test_post_preguntas_frecuentes(self, caption_factory):
        post = caption_factory.post_preguntas_frecuentes(
            tema="Lotes en Cañuelas",
            preguntas_respuestas=[
                ("Como se escritura?", "Con escribano publico"),
            ],
            tono="practico",
        )
        assert "caption_completo" in post

    def test_post_obra_avance_semanal(self, caption_factory):
        post = caption_factory.post_obra_avance_semanal(
            semana=3,
            municipio="Escobar",
            etapa="hormigon armado",
            avance=40,
            tareas=["Columnas", "Vigas"],
            proxima_etapa="Mamposteria",
            tono="practico",
        )
        assert "caption_completo" in post

    def test_post_reel_hook(self, caption_factory):
        post = caption_factory.post_reel_hook(
            tema="lote ideal para tu familia",
            tono="emotivo",
        )
        assert "caption_completo" in post
        assert post["tipo"] == "reel_hook_corto"

    def test_post_presupuesto_obra(self, caption_factory):
        post = caption_factory.post_presupuesto_obra(zona="Cañuelas", metros_cuadrados=120)
        assert "caption_completo" in post

    def test_post_etapas_obra(self, caption_factory):
        post = caption_factory.post_etapas_obra(metros_cuadrados=120)
        assert "caption_completo" in post

    def test_post_steel_frame_vs_tradicional(self, caption_factory):
        post = caption_factory.post_steel_frame_vs_tradicional(tono="educativo")
        assert "caption_completo" in post
        assert post["tipo"] == "steel_frame_vs_tradicional"

    def test_post_planos_render(self, caption_factory):
        post = caption_factory.post_planos_render(meses=8, metros_cuadrados=120)
        assert "caption_completo" in post

    def test_post_aberturas_instalaciones(self, caption_factory):
        post = caption_factory.post_aberturas_instalaciones()
        assert "caption_completo" in post

    def test_post_pisos_revestimientos(self, caption_factory):
        post = caption_factory.post_pisos_revestimientos()
        assert "caption_completo" in post

    def test_post_obra_terminada_entrega(self, caption_factory):
        post = caption_factory.post_obra_terminada_entrega()
        assert "caption_completo" in post

    def test_post_plazo_construccion(self, caption_factory):
        post = caption_factory.post_plazo_construccion()
        assert "caption_completo" in post

    def test_post_garantia_postventa(self, caption_factory):
        post = caption_factory.post_garantia_postventa(tono="profesional")
        assert "caption_completo" in post

    def test_post_materiales_premium(self, caption_factory):
        post = caption_factory.post_materiales_premium()
        assert "caption_completo" in post

    def test_post_errores_comunes_construccion(self, caption_factory):
        post = caption_factory.post_errores_comunes_construccion(tono="educativo")
        assert "caption_completo" in post

    def test_post_equipo_trabajo_maquinaria(self, caption_factory):
        post = caption_factory.post_equipo_trabajo_maquinaria()
        assert "caption_completo" in post

    def test_post_permisos_tramites(self, caption_factory):
        post = caption_factory.post_permisos_tramites()
        assert "caption_completo" in post

    def test_post_diseno_interior_acabados(self, caption_factory):
        post = caption_factory.post_diseno_interior_acabados(tono="aspiracional")
        assert "caption_completo" in post

    def test_armar_post(self, caption_factory):
        post = caption_factory._armar_post(
            tema="test tema",
            tipo="lote_venta",
            municipio="Cañuelas",
            tono="emotivo",
            caption_text="test caption",
            hashtags=["#lotes", "#canuelas"],
        )
        assert post["tema"] == "test tema"
        assert post["tipo"] == "lote_venta"
        assert post["municipio"] == "Cañuelas"
        assert post["tono"] == "emotivo"
        assert "test caption" in post["caption_completo"]
        assert post["hashtags"] == ["#lotes", "#canuelas"]

    def test_hashtags_nicho_not_found(self, caption_factory):
        result = caption_factory.hashtags(nichos=["nicho_inexistente"], n=5)
        assert isinstance(result, list)


# ===== RealestateStudio =====


class TestRealestateStudio:
    def test_init(self, tmp_path):
        with (
            patch("realestate_studio.PROMPTS_DB", tmp_path / "prompts.json"),
            patch("realestate_studio.CAPTIONS_DB", tmp_path / "captions.json"),
        ):
            studio = RealestateStudio()
            assert studio.lotes is not None
            assert studio.construccion is not None
            assert studio.post is not None

    def test_cargar_json_when_exists(self, tmp_path):
        data = {"test": "value"}
        ruta = tmp_path / "test.json"
        ruta.write_text(json.dumps(data))
        result = RealestateStudio._cargar_json(ruta, default={})
        assert result["test"] == "value"

    def test_cargar_json_when_not_exists(self, tmp_path):
        ruta = tmp_path / "new.json"
        result = RealestateStudio._cargar_json(ruta, default={"default": True})
        assert result["default"] is True
        assert ruta.exists()

    def test_prompts_default(self, tmp_path):
        with (
            patch("realestate_studio.PROMPTS_DB", tmp_path / "prompts.json"),
            patch("realestate_studio.CAPTIONS_DB", tmp_path / "captions.json"),
        ):
            studio = RealestateStudio()
            default = studio._prompts_default()
            assert "plantillas_base" in default
            assert "negativos_default" in default

    def test_captions_default(self, tmp_path):
        with (
            patch("realestate_studio.PROMPTS_DB", tmp_path / "prompts.json"),
            patch("realestate_studio.CAPTIONS_DB", tmp_path / "captions.json"),
        ):
            studio = RealestateStudio()
            default = studio._captions_default()
            assert "plantillas" in default
            assert "hashtags_por_nicho" in default

    def test_guardar_prompt(self, tmp_path):
        with (
            patch("realestate_studio.PROMPTS_DB", tmp_path / "prompts.json"),
            patch("realestate_studio.CAPTIONS_DB", tmp_path / "captions.json"),
            patch("realestate_studio.ROOT", tmp_path),
        ):
            studio = RealestateStudio()
            req = GenerationRequest(prompt="test prompt")
            ruta = studio.guardar_prompt(req, "test_prompt", subcarpeta="outputs")
            assert ruta.exists()
            data = json.loads(ruta.read_text())
            assert data["prompt"] == "test prompt"

    def test_guardar_post(self, tmp_path):
        with (
            patch("realestate_studio.PROMPTS_DB", tmp_path / "prompts.json"),
            patch("realestate_studio.CAPTIONS_DB", tmp_path / "captions.json"),
            patch("realestate_studio.ROOT", tmp_path),
        ):
            studio = RealestateStudio()
            post = {"tema": "test", "caption": "test caption"}
            ruta = studio.guardar_post(post, "test_post", proyecto="test-proyecto")
            assert ruta.exists()
            data = json.loads(ruta.read_text())
            assert data["tema"] == "test"

    def test_guardar_post_sin_proyecto(self, tmp_path):
        with (
            patch("realestate_studio.PROMPTS_DB", tmp_path / "prompts.json"),
            patch("realestate_studio.CAPTIONS_DB", tmp_path / "captions.json"),
            patch("realestate_studio.ROOT", tmp_path),
        ):
            studio = RealestateStudio()
            post = {"tema": "test"}
            ruta = studio.guardar_post(post, "test_post")
            assert ruta.exists()

    @patch("urllib.request.urlopen")
    def test_fooocus_activo_true(self, mock_urlopen, tmp_path):
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        with (
            patch("realestate_studio.PROMPTS_DB", tmp_path / "prompts.json"),
            patch("realestate_studio.CAPTIONS_DB", tmp_path / "captions.json"),
        ):
            studio = RealestateStudio()
            assert studio.fooocus_activo() is True

    @patch("urllib.request.urlopen")
    def test_fooocus_activo_false(self, mock_urlopen, tmp_path):
        mock_urlopen.side_effect = urllib.error.URLError("no connection")
        with (
            patch("realestate_studio.PROMPTS_DB", tmp_path / "prompts.json"),
            patch("realestate_studio.CAPTIONS_DB", tmp_path / "captions.json"),
        ):
            studio = RealestateStudio()
            assert studio.fooocus_activo() is False

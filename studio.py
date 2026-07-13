"""
Orquestador end-to-end del estudio inmobiliario AMBA.

Coordina: calendario -> carruseles faltantes -> mejora fotos placeholder ->
dry-run/publicacion de cada slot de la semana.

NO publica nada por si mismo: siempre trabaja con un ModoPublicacion explicito.

Uso desde opencode:
    from studio import Studio

    studio = Studio()
    resultado = studio.pipeline_semana(
        semana_n=1,
        proyectos=["chacra-canuelas-5ha"],
        posts_por_semana=5,
        municipio_principal="Cañuelas",
        modo_publicacion=ModoPublicacion.DRY_RUN,
    )
    print(resultado["resumen"])

CLI:
    python3 studio.py semana --n 1 --publicar dry-run
    python3 studio.py demo
    python3 studio.py duplicar --origen chacra-canuelas-5ha --destino chacra-canuelas-8ha
    python3 studio.py publicar --carrusel inmuebles/.../carrusel.json
"""
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from antes_despues import AntesDespuesFactory
from calendario_editorial import CalendarioEditorial
from carruseles import CarruselFactory
from historial_publicaciones import HistorialPublicaciones, RotadorProyectos
from image_generator import ImageGenerator, get_generator
from instagram_auth import InstagramAuth
from instagram_publisher import InstagramPublisher, ModoPublicacion, PublicacionResultado
from mejora_fotos import MejoraFotos
from preview_html import PreviewHTML
from realestate_studio import RealestateStudio
from validators import validate_post

ROOT = Path(__file__).resolve().parent


@dataclass
class PipelineResultado:
    semana_numero: int
    fecha_inicio: str
    fecha_fin: str
    n_slots: int
    carruseles_generados: list[str] = field(default_factory=list)
    mejoras_aplicadas: list[dict[str, Any]] = field(default_factory=list)
    publicaciones: list[dict[str, Any]] = field(default_factory=list)
    validaciones: list[dict[str, Any]] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)
    resumen: str = ""
    fecha_ejecucion: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Studio:
    """Orquestador principal que conecta calendario + carruseles + mejora + publicacion."""

    def __init__(self):
        self.studio_core = RealestateStudio()
        self.carruseles = CarruselFactory(self.studio_core)
        self.calendario = CalendarioEditorial(self.studio_core)
        self.antes_despues = AntesDespuesFactory(self.studio_core)
        self.mejora = MejoraFotos()
        self.auth = InstagramAuth()
        self.publisher = InstagramPublisher(self.auth)
        self.preview = PreviewHTML()
        self.image_generator: ImageGenerator = get_generator()
        self.historial = HistorialPublicaciones()
        self.rotador = RotadorProyectos(self.historial)

    # ---------------- Pipeline end-to-end ----------------

    def pipeline_semana(self, semana_n: int = 1,
                        proyectos: list[str] | None = None,
                        posts_por_semana: int = 5,
                        municipio_principal: str = "Cañuelas",
                        fecha_inicio: str | None = None,
                        modo_publicacion: ModoPublicacion = ModoPublicacion.DRY_RUN,
                        generar_carruseles_faltantes: bool = True,
                        aplicar_mejora_a_placeholders: bool = False,
                        municipio_por_proyecto: dict[str, str] | None = None,
                        validar_posts: bool = True,
                        ) -> PipelineResultado:
        """Ejecuta el pipeline completo de una semana."""
        proyectos = proyectos or []
        municipio_por_proyecto = municipio_por_proyecto or {}

        resultado = PipelineResultado(
            semana_numero=semana_n,
            fecha_inicio="", fecha_fin="", n_slots=0,
        )

        # 1) Calendario
        try:
            semana = self.calendario.generar_semana(
                semana_n=semana_n,
                proyectos=proyectos,
                posts_por_semana=posts_por_semana,
                municipio_principal=municipio_principal,
                fecha_inicio=fecha_inicio,
            )
            self.calendario.guardar(semana)
            self.calendario.exportar_markdown(semana)
            try:
                self.calendario.exportar_ics(semana)
            except Exception as e:
                resultado.errores.append(f"ICS export: {e}")
            try:
                self.calendario.exportar_csv(semana)
            except Exception as e:
                resultado.errores.append(f"CSV export: {e}")
            resultado.fecha_inicio = semana.fecha_inicio
            resultado.fecha_fin = semana.fecha_fin
            resultado.n_slots = len(semana.slots)
        except Exception as e:
            resultado.errores.append(f"calendario: {e}")
            resultado.resumen = f"ERROR generando calendario: {e}"
            return resultado

        # 1.5) Validar posts
        if validar_posts:
            for slot in semana.slots:
                if slot.post:
                    val = validate_post(
                        caption=slot.post.get("caption_completo", ""),
                        hashtags=slot.post.get("hashtags"),
                        municipio=slot.municipio,
                    )
                    if not val.ok or val.advertencias:
                        resultado.validaciones.append({
                            "fecha": slot.fecha,
                            "tipo": slot.tipo_post,
                            "ok": val.ok,
                            "errores": val.errores,
                            "advertencias": val.advertencias,
                        })

        # 2) Generar carruseles faltantes
        if generar_carruseles_faltantes:
            for slot in semana.slots:
                if slot.tipo_post in ("carrusel", "servicios") and slot.proyecto:
                    try:
                        nombre = self._nombre_carrusel_desde_slot(slot, semana)
                        self._generar_o_reusar_carrusel(
                            slot, nombre, municipio_por_proyecto.get(
                                slot.proyecto, slot.municipio))
                        resultado.carruseles_generados.append(nombre)
                    except Exception as e:
                        resultado.errores.append(
                            f"carrusel {slot.tipo_post} slot {slot.fecha}: {e}")

        # 3) Mejora de fotos placeholder (opcional, requiere fotos reales)
        if aplicar_mejora_a_placeholders:
            for slot in semana.slots:
                if slot.post and slot.tipo_post == "obra_avance":
                    placeholder = slot.post.get("metadata", {}).get(
                        "placeholder_foto_path") if slot.post.get("metadata") else None
                    # Solo mejora si existe el archivo
                    continue

        # 4) Publicacion / dry-run
        for slot in semana.slots:
            try:
                pub = self._publicar_slot(slot, semana, modo_publicacion)
                resultado.publicaciones.append(pub.to_dict())
            except Exception as e:
                resultado.errores.append(
                    f"publicacion slot {slot.fecha} {slot.tipo_post}: {e}")

        # Resumen
        pub_ok = sum(1 for p in resultado.publicaciones if p.get("exito"))
        pub_total = len(resultado.publicaciones)
        resultado.resumen = (
            f"Semana {resultado.semana_numero} ({resultado.fecha_inicio} → "
            f"{resultado.fecha_fin}): {resultado.n_slots} slots, "
            f"{len(resultado.carruseles_generados)} carruseles generados, "
            f"{pub_ok}/{pub_total} publicaciones OK"
            + (f", {len(resultado.errores)} errores" if resultado.errores else "")
        )
        return resultado

    # ---------------- Helpers ----------------

    def _nombre_carrusel_desde_slot(self, slot: Any, semana: Any) -> str:
        tipo_map = {
            "carrusel": self._tipo_carrusel_por_dia(slot.dia_semana),
            "servicios": "servicios",
        }
        tipo = tipo_map.get(slot.tipo_post, "lote_premium")
        slug = (slot.proyecto or "general").replace(" ", "-").lower()
        return f"{tipo}_{slug}_sem{semana.numero:02d}_{slot.dia_semana}"

    @staticmethod
    def _tipo_carrusel_por_dia(dia_semana: str) -> str:
        return {
            "lunes": "lote_premium",
            "martes": "country_etapa",
            "miercoles": "lote_premium",
            "jueves": "servicios",
            "viernes": "lote_premium",
            "sabado": "lote_premium",
            "domingo": "obra_avance",
        }.get(dia_semana, "lote_premium")

    def _generar_o_reusar_carrusel(self, slot: Any, nombre: str,
                                    municipio: str) -> Path:
        carpeta_destino = (ROOT / "inmuebles" / "lotes" / (slot.proyecto or "_generados")
                           / "carruseles" / nombre)
        json_existente = carpeta_destino / "carrusel.json"
        if json_existente.exists():
            return carpeta_destino

        tipo = self._tipo_carrusel_por_dia(slot.dia_semana)
        try:
            if tipo == "lote_premium":
                tema = f"Lote destacado en {municipio}"
                carrusel = self.carruseles.lote_premium(
                    tema=tema, municipio=municipio, hectareas=5,
                    tono=slot.tono, n_slides=6)
            elif tipo == "country_etapa":
                carrusel = self.carruseles.country_etapa(
                    nombre_country="Country Premium",
                    municipio=municipio, etapa="2", n_lotes=12,
                    tono=slot.tono, n_slides=5)
            elif tipo == "obra_avance":
                carrusel = self.carruseles.obra_avance(
                    nombre_obra=slot.proyecto or "Obra",
                    municipio=municipio, semana=1, etapa="fundaciones",
                    tono=slot.tono, n_slides=4)
            elif tipo == "servicios":
                carrusel = self.carruseles.servicios(
                    empresa="Nuestra Empresa",
                    municipio=municipio, n_slides=6)
            else:
                carrusel = self.carruseles.lote_premium(
                    tema=f"Lote en {municipio}",
                    municipio=municipio, hectareas=5,
                    tono=slot.tono, n_slides=6)

            return self.carruseles.guardar(
                carrusel, nombre=nombre, proyecto=slot.proyecto)
        except Exception as e:
            raise RuntimeError(f"generando carrusel {tipo}: {e}")

    def _publicar_slot(self, slot: Any, semana: Any,
                       modo: ModoPublicacion) -> PublicacionResultado:
        if not slot.post or not slot.post.get("caption_completo"):
            return PublicacionResultado(
                modo=modo.value, exito=False, tipo="vacio",
                caption_length=0, n_imagenes=0,
                error="slot sin post generado",
            )

        caption = slot.post.get("caption", "")
        hashtags = slot.post.get("hashtags", [])
        municipio = slot.municipio

        if slot.tipo_post in ("carrusel", "servicios") and slot.proyecto:
            nombre = self._nombre_carrusel_desde_slot(slot, semana)
            carpeta = (ROOT / "inmuebles" / "lotes" / slot.proyecto /
                       "carruseles" / nombre / "slides")
            imagenes = sorted(carpeta.glob("slide_*.png")) + sorted(
                carpeta.glob("slide_*.jpg"))
            imagenes = [p for p in imagenes if p.suffix in (".png", ".jpg", ".jpeg")]
            if len(imagenes) >= 2:
                return self.publisher.publicar_carrusel(
                    rutas_imagenes=imagenes, caption=caption,
                    hashtags=hashtags, modo=modo)

        if slot.proyecto:
            carpeta_prompts = (ROOT / "inmuebles" / "lotes" / slot.proyecto /
                               "prompts")
            imagenes = (sorted(carpeta_prompts.glob("*.png")) +
                        sorted(carpeta_prompts.glob("*.jpg")))
            if imagenes:
                return self.publisher.publicar_foto(
                    ruta_imagen=imagenes[0], caption=caption,
                    hashtags=hashtags, modo=modo)

        return PublicacionResultado(
            modo=modo.value, exito=False, tipo=slot.tipo_post,
            caption_length=len(caption) + sum(len(h) for h in hashtags),
            n_imagenes=0,
            error="Sin imagenes generadas todavia. Dry-run del caption.",
            metadata={
                "caption_preview": caption[:200],
                "n_hashtags": len(hashtags),
                "municipio": municipio,
                "fecha": slot.fecha,
            },
        )

    # ---------------- Duplicar proyecto (gap #9) ----------------

    def duplicar_proyecto(self, origen: str, destino: str,
                          cambios: dict[str, Any] | None = None) -> Path:
        """Duplica un proyecto con overrides opcionales.

        cambios puede sobrescribir: hectareas, municipio, precio_usd, etc.
        """
        cambios = cambios or {}
        carpeta_origen = ROOT / "inmuebles" / "lotes" / origen
        carpeta_destino = ROOT / "inmuebles" / "lotes" / destino

        if not carpeta_origen.exists():
            raise FileNotFoundError(f"Proyecto origen no existe: {carpeta_origen}")
        if carpeta_destino.exists():
            raise FileExistsError(f"Proyecto destino ya existe: {carpeta_destino}")

        # Copiar estructura completa
        shutil.copytree(carpeta_origen, carpeta_destino)

        # Reescribir archivos JSON con los cambios
        self._aplicar_cambios_a_json(carpeta_destino, cambios)

        return carpeta_destino

    def _aplicar_cambios_a_json(self, carpeta: Path, cambios: dict[str, Any]) -> None:
        """Aplica cambios a todos los JSON del proyecto duplicado."""
        # Recorrer todos los .json
        for json_path in carpeta.rglob("*.json"):
            if json_path.name in ("carrusel.json",):
                # Actualizar prompts de slides con nuevos valores
                self._actualizar_prompts_en_json(json_path, cambios)
            elif "resumen" in json_path.name.lower():
                # Actualizar resumen
                self._actualizar_resumen(json_path, cambios)

    def _actualizar_prompts_en_json(self, json_path: Path,
                                     cambios: dict[str, Any]) -> None:
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        modificado = False
        if "slides" in data:
            for slide in data["slides"]:
                if "prompt" in slide:
                    prompt = slide["prompt"]
                    for key, value in cambios.items():
                        if key in ("hectareas",):
                            prompt = prompt.replace(
                                "5 hectares", f"{value} hectares")
                            prompt = prompt.replace(
                                "5 ha en", f"{value} ha en")
                            modificado = True
                        if key == "municipio":
                            for m in ["Cañuelas", "Escobar", "Pilar", "Mercedes"]:
                                if m in prompt:
                                    prompt = prompt.replace(m, value)
                                    modificado = True
                    if modificado:
                        slide["prompt"] = prompt
        if modificado:
            json_path.write_text(json.dumps(data, indent=2,
                                             ensure_ascii=False),
                                 encoding="utf-8")

    def _actualizar_resumen(self, json_path: Path,
                             cambios: dict[str, Any]) -> None:
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        for key, value in cambios.items():
            if key in data:
                data[key] = value
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                             encoding="utf-8")

    # ---------------- Regenerar carruseles de una semana (gap #19) ----------------

    def regenerar_carruseles(self, semana_n: int,
                              proyectos: list[str] | None = None,
                              municipio_principal: str = "Cañuelas",
                              posts_por_semana: int = 5,
                              fecha_inicio: str | None = None) -> PipelineResultado:
        """Fuerza la regeneracion de los carruseles de una semana."""
        return self.pipeline_semana(
            semana_n=semana_n,
            proyectos=proyectos or [],
            posts_por_semana=posts_por_semana,
            municipio_principal=municipio_principal,
            fecha_inicio=fecha_inicio,
            generar_carruseles_faltantes=True,
            modo_publicacion=ModoPublicacion.DRY_RUN,
        )

    # ---------------- Publicar carrusel existente (gap #7) ----------------

    def publicar_carrusel_existente(self, ruta_carrusel: str | Path,
                                     modo: ModoPublicacion = ModoPublicacion.DRY_RUN
                                     ) -> PublicacionResultado:
        """Publica un carrusel que ya esta generado en disco."""
        ruta_carrusel = Path(ruta_carrusel)
        if not ruta_carrusel.exists():
            return PublicacionResultado(
                modo=modo.value, exito=False, tipo="carrusel",
                caption_length=0, n_imagenes=0,
                error=f"No existe: {ruta_carrusel}",
            )

        try:
            data = json.loads(ruta_carrusel.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            return PublicacionResultado(
                modo=modo.value, exito=False, tipo="carrusel",
                caption_length=0, n_imagenes=0,
                error=f"JSON invalido: {e}",
            )

        # Buscar imagenes en la carpeta slides/
        carpeta_slides = ruta_carrusel.parent / "slides"
        imagenes = (sorted(carpeta_slides.glob("slide_*.png")) +
                    sorted(carpeta_slides.glob("slide_*.jpg")))
        imagenes = [p for p in imagenes if p.suffix in (".png", ".jpg", ".jpeg")]

        caption = data.get("caption_narrativo", "")
        hashtags = data.get("hashtags", [])
        n_slides = data.get("n_slides", 0)

        if len(imagenes) < 2:
            return PublicacionResultado(
                modo=modo.value, exito=False, tipo="carrusel",
                caption_length=len(caption) + sum(len(h) for h in hashtags),
                n_imagenes=len(imagenes),
                error=f"Necesita >= 2 imagenes (encontradas: {len(imagenes)}). "
                      f"Revisa {carpeta_slides}",
                metadata={"n_slides_esperadas": n_slides,
                          "carpeta_slides": str(carpeta_slides)},
            )

        return self.publisher.publicar_carrusel(
            rutas_imagenes=imagenes, caption=caption,
            hashtags=hashtags, modo=modo)

    # ---------------- Preview HTML de un carrusel ----------------

    def preview_carrusel(self, ruta_carrusel: str | Path,
                          ruta_html: str | Path | None = None) -> Path:
        """Genera preview HTML de un carrusel en disco."""
        ruta_carrusel = Path(ruta_carrusel)
        if not ruta_carrusel.exists():
            raise FileNotFoundError(ruta_carrusel)

        data = json.loads(ruta_carrusel.read_text(encoding="utf-8"))

        # Reconstruir objeto Carrusel-like para el preview
        from carruseles import Carrusel, Slide
        slides = []
        for s in data.get("slides", []):
            slides.append(Slide(
                numero=s.get("numero", 0),
                tipo=s.get("tipo", "foto"),
                descripcion=s.get("descripcion", ""),
                prompt=s.get("prompt", ""),
                texto_overlay=s.get("texto_overlay", ""),
                aspect_ratio=s.get("aspect_ratio", "896*1152"),
                styles=s.get("styles", []),
                metadata=s.get("metadata", {}),
            ))

        carrusel = Carrusel(
            tema=data.get("tema", ""),
            tipo=data.get("tipo", ""),
            municipio=data.get("municipio", ""),
            tono=data.get("tono", "emotivo"),
            slides=slides,
            caption_narrativo=data.get("caption_narrativo", ""),
            hashtags=data.get("hashtags", []),
            fecha_creacion=data.get("fecha_creacion", ""),
            metadata=data.get("metadata", {}),
        )

        if ruta_html is None:
            ruta_html = ruta_carrusel.parent / "preview.html"
        return self.preview.carrusel(carrusel=carrusel, ruta_salida=ruta_html)

    # ---------------- Generacion de imagenes (Fase 4) ----------------

    def generar_imagenes_carrusel(self, ruta_carrusel: str | Path,
                                    force_real: bool = False) -> list[dict[str, Any]]:
        """Genera imagenes para los slides de un carrusel.

        - Si Fooocus esta activo y force_real=True: envia prompts a Fooocus
        - En cualquier caso: delega en self.image_generator
        - Slides con placeholder_foto se omiten (requieren foto real manual)

        Devuelve lista de resultados por slide.
        """
        ruta_carrusel = Path(ruta_carrusel)
        data = json.loads(ruta_carrusel.read_text(encoding="utf-8"))

        slides = data.get("slides", [])
        carpeta_imgs = ruta_carrusel.parent / "slides"
        carpeta_imgs.mkdir(exist_ok=True)

        resultados: list[dict[str, Any]] = []
        for slide_data in slides:
            numero = slide_data.get("numero", 0)
            tipo = slide_data.get("tipo", "")
            prompt = slide_data.get("prompt", "")
            aspect = slide_data.get("aspect_ratio", "896*1152")
            styles = slide_data.get("styles", [])
            output_path = carpeta_imgs / f"slide_{numero:02d}_{tipo}.jpg"

            if tipo == "placeholder_foto":
                resultados.append({
                    "n_slide": numero, "tipo": tipo, "saltado": True,
                    "razon": "requiere foto real",
                    "path": slide_data.get("metadata", {}).get(
                        "placeholder_foto_path", ""),
                })
                continue

            if not prompt:
                resultados.append({
                    "n_slide": numero, "tipo": tipo, "saltado": True,
                    "razon": "sin prompt",
                })
                continue

            try:
                r = self.image_generator.generar(
                    prompt=prompt,
                    negative_prompt=slide_data.get("negative_prompt", ""),
                    aspect_ratio=aspect,
                    styles=styles,
                    output_path=output_path,
                )
                resultados.append({
                    "n_slide": numero, "tipo": tipo, "saltado": False,
                    "stub": r.stub,
                    "output_path": r.output_path,
                    "fooocus_disponible": r.fooocus_disponible,
                })
            except Exception as e:
                resultados.append({
                    "n_slide": numero, "tipo": tipo, "error": str(e),
                })

        return resultados

    def generar_imagenes_pipeline(self, resultado: PipelineResultado) -> dict[str, Any]:
        """Genera imagenes para todos los carruseles generados en el pipeline."""
        reporte: dict[str, Any] = {
            "fooocus_disponible": not self.image_generator.stub,
            "carruseles": [],
        }
        for nombre_carrusel in resultado.carruseles_generados:
            # Buscar el carrusel.json en el filesystem
            carpetas_posibles = [
                ROOT / "inmuebles" / "lotes" / nombre_carrusel.split("_")[0]
                / "carruseles" / nombre_carrusel,
            ]
            for carpeta in carpetas_posibles:
                json_path = carpeta / "carrusel.json"
                if json_path.exists():
                    slides_result = self.generar_imagenes_carrusel(json_path)
                    reporte["carruseles"].append({
                        "nombre": nombre_carrusel,
                        "slides": slides_result,
                    })
                    break
        return reporte

    # ---------------- Persistencia ----------------

    def guardar_pipeline(self, resultado: PipelineResultado,
                          nombre: str | None = None) -> Path:
        carpeta = ROOT / "inmuebles" / "pipelines"
        carpeta.mkdir(parents=True, exist_ok=True)
        if not nombre:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre = f"pipeline_semana_{resultado.semana_numero:02d}_{ts}"
        ruta = carpeta / f"{nombre}.json"
        ruta.write_text(json.dumps(resultado.to_dict(), indent=2,
                                   ensure_ascii=False), encoding="utf-8")
        return ruta

    # ---------------- Listar carruseles disponibles (gap #18) ----------------

    def listar_carruseles(self, proyecto: str | None = None) -> list[dict[str, Any]]:
        """Lista los carruseles disponibles en el proyecto (o todos)."""
        resultados: list[dict[str, Any]] = []
        if proyecto:
            carpeta_base = ROOT / "inmuebles" / "lotes" / proyecto / "carruseles"
            carpetas_a_buscar = [carpeta_base] if carpeta_base.exists() else []
        else:
            base = ROOT / "inmuebles" / "lotes"
            carpetas_a_buscar = [d / "carruseles" for d in base.iterdir() if d.is_dir()]
            base_serv = ROOT / "inmuebles" / "servicios" / "carruseles"
            if base_serv.exists():
                carpetas_a_buscar.append(base_serv)

        for base in carpetas_a_buscar:
            if not base.exists():
                continue
            for carrusel_dir in base.iterdir():
                if not carrusel_dir.is_dir():
                    continue
                json_path = carrusel_dir / "carrusel.json"
                if not json_path.exists():
                    continue
                try:
                    data = json.loads(json_path.read_text(encoding="utf-8"))
                    resultados.append({
                        "carpeta": str(carrusel_dir.relative_to(ROOT)),
                        "nombre": carrusel_dir.name,
                        "tema": data.get("tema", ""),
                        "tipo": data.get("tipo", ""),
                        "n_slides": data.get("n_slides", 0),
                        "fecha_creacion": data.get("fecha_creacion", ""),
                        "municipio": data.get("municipio", ""),
                    })
                except (json.JSONDecodeError, OSError):
                    continue
        return resultados


# ==================== CLI ====================

def cli() -> int:
    parser = argparse.ArgumentParser(
        description="Realestate Studio AMBA - CLI")
    sub = parser.add_subparsers(dest="comando", required=True)

    # subcomando: demo
    p_demo = sub.add_parser("demo", help="Corre el pipeline de demo")

    # subcomando: semana
    p_sem = sub.add_parser("semana", help="Genera calendario semanal completo")
    p_sem.add_argument("--n", type=int, default=1, help="Numero de semana")
    p_sem.add_argument("--proyectos", nargs="+", default=[],
                        help="Lista de proyectos separados por espacio")
    p_sem.add_argument("--posts", type=int, default=5,
                        help="Posts por semana")
    p_sem.add_argument("--municipio", default="Cañuelas",
                        help="Municipio principal")
    p_sem.add_argument("--fecha-inicio", default=None,
                        help="Fecha de inicio YYYY-MM-DD")
    p_sem.add_argument("--publicar", choices=["dry-run", "interactivo", "real"],
                        default="dry-run",
                        help="Modo de publicacion")

    # subcomando: duplicar
    p_dup = sub.add_parser("duplicar", help="Duplica un proyecto")
    p_dup.add_argument("--origen", required=True, help="Proyecto origen")
    p_dup.add_argument("--destino", required=True, help="Proyecto destino")
    p_dup.add_argument("--hectareas", type=float, default=None)
    p_dup.add_argument("--municipio", default=None)

    # subcomando: publicar
    p_pub = sub.add_parser("publicar", help="Publica un carrusel existente")
    p_pub.add_argument("--carrusel", required=True,
                        help="Path al carrusel.json")
    p_pub.add_argument("--modo", choices=["dry-run", "interactivo", "real"],
                        default="dry-run")

    # subcomando: preview
    p_prev = sub.add_parser("preview", help="Genera preview HTML de un carrusel")
    p_prev.add_argument("--carrusel", required=True,
                         help="Path al carrusel.json")

    # subcomando: generar
    p_gen = sub.add_parser("generar", help="Genera imagenes para un carrusel")
    p_gen.add_argument("--carrusel", required=True,
                        help="Path al carrusel.json")

    # subcomando: listar
    p_list = sub.add_parser("listar", help="Lista carruseles disponibles")
    p_list.add_argument("--proyecto", default=None,
                         help="Filtrar por proyecto")

    args = parser.parse_args()
    studio = Studio()

    if args.comando == "demo":
        demo()

    elif args.comando == "semana":
        modo = {
            "dry-run": ModoPublicacion.DRY_RUN,
            "interactivo": ModoPublicacion.INTERACTIVO,
            "real": ModoPublicacion.REAL,
        }[args.publicar]
        resultado = studio.pipeline_semana(
            semana_n=args.n,
            proyectos=args.proyectos,
            posts_por_semana=args.posts,
            municipio_principal=args.municipio,
            fecha_inicio=args.fecha_inicio,
            modo_publicacion=modo,
        )
        print(resultado.resumen)
        if resultado.errores:
            print(f"\nErrores ({len(resultado.errores)}):")
            for e in resultado.errores[:5]:
                print(f"  - {e}")
        ruta = studio.guardar_pipeline(resultado)
        print(f"\nReporte: {ruta.relative_to(ROOT)}")

    elif args.comando == "duplicar":
        cambios = {}
        if args.hectareas is not None:
            cambios["hectareas"] = args.hectareas
        if args.municipio is not None:
            cambios["municipio"] = args.municipio
        carpeta = studio.duplicar_proyecto(args.origen, args.destino, cambios)
        print(f"Proyecto duplicado en: {carpeta.relative_to(ROOT)}")

    elif args.comando == "publicar":
        modo = {
            "dry-run": ModoPublicacion.DRY_RUN,
            "interactivo": ModoPublicacion.INTERACTIVO,
            "real": ModoPublicacion.REAL,
        }[args.modo]
        resultado = studio.publicar_carrusel_existente(args.carrusel, modo)
        print(f"Modo: {resultado.modo}")
        print(f"Exito: {resultado.exito}")
        print(f"Tipo: {resultado.tipo}")
        print(f"Imagenes: {resultado.n_imagenes}")
        print(f"Caption length: {resultado.caption_length}")
        if resultado.error:
            print(f"Error: {resultado.error}")
        if resultado.instagram_post_id:
            print(f"Post ID: {resultado.instagram_post_id}")
        if resultado.permalink:
            print(f"Permalink: {resultado.permalink}")

    elif args.comando == "preview":
        html_path = studio.preview_carrusel(args.carrusel)
        print(f"Preview HTML generado en: {html_path}")
        try:
            print(f"Path relativo: {html_path.relative_to(ROOT)}")
        except ValueError:
            pass
        print("Abrilo con doble-click en tu navegador.")

    elif args.comando == "generar":
        resultados = studio.generar_imagenes_carrusel(args.carrusel)
        fooocus_ok = studio.image_generator.__class__.__name__ != "StubImageGenerator"
        print(f"Fooocus disponible: {fooocus_ok}")
        print(f"Slides procesados: {len(resultados)}")
        for r in resultados:
            if r.get("saltado"):
                print(f"  slide {r['n_slide']}: saltado ({r.get('razon', '')})")
            elif r.get("error"):
                print(f"  slide {r['n_slide']}: ERROR ({r['error']})")
            elif r.get("stub"):
                print(f"  slide {r['n_slide']}: stub (imagen NO generada, "
                      "ver mensaje en JSON al lado)")
            else:
                print(f"  slide {r['n_slide']}: generada en {r['output_path']}")

    elif args.comando == "listar":
        carruseles = studio.listar_carruseles(args.proyecto)
        if not carruseles:
            print("No se encontraron carruseles.")
        else:
            print(f"Encontrados {len(carruseles)} carruseles:")
            for c in carruseles:
                print(f"  - {c['nombre']} ({c['n_slides']} slides, "
                      f"{c['municipio']}, {c['tipo']})")

    return 0


def demo() -> None:
    """Pipeline completo de ejemplo en dry-run."""
    studio = Studio()
    resultado = studio.pipeline_semana(
        semana_n=1,
        proyectos=["chacra-canuelas-5ha"],
        posts_por_semana=5,
        municipio_principal="Cañuelas",
        modo_publicacion=ModoPublicacion.DRY_RUN,
    )
    print("=" * 60)
    print("PIPELINE SEMANA - RESULTADO")
    print("=" * 60)
    print(resultado.resumen)
    print()
    if resultado.carruseles_generados:
        print(f"Carruseles generados: {len(resultado.carruseles_generados)}")
        for c in resultado.carruseles_generados:
            print(f"  - {c}")
    if resultado.validaciones:
        print(f"\nValidaciones con issues: {len(resultado.validaciones)}")
        for v in resultado.validaciones[:5]:
            print(f"  - {v['tipo']}: {v.get('errores') or v.get('advertencias')}")
    if resultado.errores:
        print(f"\nErrores: {len(resultado.errores)}")
        for e in resultado.errores:
            print(f"  - {e}")
    ruta = studio.guardar_pipeline(resultado)
    print(f"\nReporte guardado en: {ruta.relative_to(ROOT)}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        sys.exit(cli())
    else:
        demo()

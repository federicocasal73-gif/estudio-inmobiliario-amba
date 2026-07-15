"""
Calendario editorial semanal para Instagram.
Genera slots de publicacion (lun a dom) con tipo, tono, municipio y hora,
mas el post completo (caption + hashtags) por slot.

Tambien soporta fechas clave argentinas (Dia de la Madre, Padre, Black Friday,
Navidad, Año Nuevo, etc.) que el calendario intenta cubrir automaticamente.

Uso desde opencode:
    from realestate_studio import RealestateStudio
    from calendario_editorial import CalendarioEditorial

    studio = RealestateStudio()
    cal = CalendarioEditorial(studio)
    semana = cal.generar_semana(
        semana_n=1,
        proyectos=["chacra-canuelas-5ha", "country-pilar-ejemplo"],
        posts_por_semana=5,
        municipio_principal="Cañuelas",
    )
    cal.exportar_markdown(semana, ruta=Path("inmuebles/calendarios/semana_01/plan.md"))
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from realestate_studio import RealestateStudio

ROOT = Path(__file__).resolve().parent
CALENDARIOS_DIR = ROOT / "inmuebles" / "calendarios"

DIAS_SEMANA = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]

# Distribucion recomendada por dia (en orden de prioridad por dia de la semana)
DISTRIBUCION_DEFAULT = {
    "lunes": {"tipo": "lote_venta", "tono": "emotivo", "nicho": ["general", "inversion"]},
    "martes": {"tipo": "carrusel", "tono": "premium", "nicho": ["country", "general"]},
    "miercoles": {"tipo": "country", "tono": "premium", "nicho": ["country"]},
    "jueves": {"tipo": "campo", "tono": "inversion", "nicho": ["campo", "inversion"]},
    "viernes": {"tipo": "carrusel", "tono": "emotivo", "nicho": ["servicios", "casas"]},
    "sabado": {"tipo": "render_proyecto", "tono": "aspiracional", "nicho": ["casas"]},
    "domingo": {"tipo": "obra_avance", "tono": "practico", "nicho": ["construccion"]},
}

HORAS_SUGERIDAS = {
    "lunes": "19:00",
    "martes": "12:30",
    "miercoles": "19:00",
    "jueves": "12:30",
    "viernes": "18:30",
    "sabado": "11:00",
    "domingo": "10:00",
}

# Fechas clave argentinas (mes, dia, nombre) — Madre y Padre se calculan dinamicamente
FECHAS_CLAVE_AR_FIJAS = [
    (1, 1, "Ano Nuevo"),
    (2, 14, "San Valentin"),
    (3, 24, "Dia de la Memoria"),
    (4, 2, "Dia del Veterano"),
    (5, 1, "Dia del Trabajador"),
    (5, 25, "Dia de la Revolucion de Mayo"),
    (6, 20, "Dia de la Bandera"),
    (7, 9, "Dia de la Independencia"),
    (8, 17, "Dia del Nino"),
    (9, 11, "Dia del Maestro"),
    (10, 12, "Dia de la Diversidad Cultural"),
    (11, 23, "Dia de la Soberania Nacional"),
    (12, 8, "Inmaculada Concepcion"),
    (12, 24, "Nochebuena"),
    (12, 25, "Navidad"),
    (12, 31, "Fin de Ano"),
]


def _tercer_domingo(anio: int, mes: int) -> tuple[int, int]:
    """Devuelve (mes, dia) del 3er domingo del mes."""
    import calendar

    domingos = [
        d
        for d in calendar.Calendar().itermonthdates(anio, mes)
        if d.month == mes and d.weekday() == 6
    ]
    return mes, domingos[2].day


def _fechas_dinamicas_para_anio(anio: int) -> list[tuple[int, int, str]]:
    """Devuelve fechas variables (Padre, Madre) para el anio dado."""
    m_padre, d_padre = _tercer_domingo(anio, 6)
    m_madre, d_madre = _tercer_domingo(anio, 10)
    return [
        (m_padre, d_padre, "Dia del Padre"),
        (m_madre, d_madre, "Dia de la Madre"),
    ]


def _fechas_clave_completas(anio: int) -> list[tuple[int, int, str]]:
    """Lista completa de fechas clave AR + inmo para un anio."""
    return FECHAS_CLAVE_AR_FIJAS + _fechas_dinamicas_para_anio(anio) + FECHAS_INMO


# Fechas del rubro inmobiliario / comercial
FECHAS_INMO = [
    (11, 27, "Black Friday"),
    (12, 2, "Cyber Monday"),
]


@dataclass
class SlotEditorial:
    fecha: str  # YYYY-MM-DD
    dia_semana: str  # lunes..domingo
    hora_sugerida: str  # HH:MM
    tipo_post: str  # lote_venta / country / campo / carrusel / render_proyecto / obra_avance / servicios / fecha_especial
    tono: str  # emotivo / inversion / practico / premium / aspiracional
    nicho: list[str]
    municipio: str
    proyecto: str | None = None
    notas: str = ""
    es_fecha_clave: bool = False
    fecha_clave_nombre: str | None = None
    post: dict[str, Any] | None = None  # post completo generado (caption + hashtags)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SemanaEditorial:
    numero: int
    fecha_inicio: str  # lunes
    fecha_fin: str  # domingo
    proyectos_disponibles: list[str]
    municipio_principal: str
    slots: list[SlotEditorial] = field(default_factory=list)
    fechas_clave_cubiertas: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CalendarioEditorial:
    """Generador de planificacion semanal + posts completos para IG."""

    def __init__(self, studio: RealestateStudio):
        self.studio = studio

    def generar_semana(
        self,
        semana_n: int = 1,
        proyectos: list[str] | None = None,
        posts_por_semana: int = 5,
        municipio_principal: str = "Cañuelas",
        fecha_inicio: str | None = None,
        dias_personalizados: dict[str, dict] | None = None,
    ) -> SemanaEditorial:
        if posts_por_semana < 1:
            posts_por_semana = 1
        if posts_por_semana > 7:
            posts_por_semana = 7

        proyectos = proyectos or []
        inicio = (
            self._parsear_fecha(fecha_inicio) if fecha_inicio else self._lunes_de_semana(semana_n)
        )
        fin = inicio + timedelta(days=6)

        distribucion = dias_personalizados or DISTRIBUCION_DEFAULT

        # Seleccionar dias segun posts_por_semana (priorizando dias de mayor engagement)
        dias_prioritarios = [
            "lunes",
            "miercoles",
            "viernes",
            "sabado",
            "martes",
            "jueves",
            "domingo",
        ]

        # Detectar fechas clave en la semana
        fechas_clave_en_semana = self._fechas_clave_en_rango(inicio, fin)

        # Si hay fechas clave en domingo, incluirlo aunque no este priorizado
        dias_elegidos = list(dias_prioritarios[:posts_por_semana])
        for fc in fechas_clave_en_semana:
            fecha_dt = datetime.strptime(fc["fecha"], "%Y-%m-%d")
            dia_nombre = DIAS_SEMANA[fecha_dt.weekday()]
            if dia_nombre not in dias_elegidos:
                # Reemplazar el de menor prioridad (ultimo en dias_elegidos)
                if len(dias_elegidos) >= posts_por_semana:
                    dias_elegidos.pop()
                dias_elegidos.append(dia_nombre)

        # Detectar fechas clave en la semana
        fechas_clave_en_semana = self._fechas_clave_en_rango(inicio, fin)

        slots: list[SlotEditorial] = []
        proyectos_usados = list(proyectos)
        idx_proyecto = 0

        for i, dia in enumerate(dias_elegidos):
            fecha_dia = inicio + timedelta(days=DIAS_SEMANA.index(dia))
            fecha_str = fecha_dia.strftime("%Y-%m-%d")

            # Si este dia es una fecha clave, usar ese slot
            fecha_clave_match = next(
                (fc for fc in fechas_clave_en_semana if fc["fecha"] == fecha_str), None
            )

            if fecha_clave_match:
                slot = self._slot_fecha_clave(fecha_dia, fecha_clave_match, municipio_principal)
            else:
                config_dia = distribucion.get(dia, distribucion["lunes"])
                proyecto = None
                if proyectos_usados:
                    proyecto = proyectos_usados[idx_proyecto % len(proyectos_usados)]
                    idx_proyecto += 1
                slot = self._slot_normal(fecha_dia, dia, config_dia, municipio_principal, proyecto)

            slots.append(slot)

        semana = SemanaEditorial(
            numero=semana_n,
            fecha_inicio=inicio.strftime("%Y-%m-%d"),
            fecha_fin=fin.strftime("%Y-%m-%d"),
            proyectos_disponibles=proyectos,
            municipio_principal=municipio_principal,
            slots=slots,
            fechas_clave_cubiertas=[
                fc["nombre"]
                for fc in fechas_clave_en_semana
                if any(s.es_fecha_clave for s in slots)
            ],
            metadata={"posts_por_semana": posts_por_semana, "dias_elegidos": dias_elegidos},
        )

        # Generar posts completos por slot
        for slot in semana.slots:
            slot.post = self._generar_post_para_slot(slot)

        return semana

    # ---------------- Generadores de slot ----------------

    def _slot_normal(
        self, fecha_dia: datetime, dia: str, config: dict, municipio: str, proyecto: str | None
    ) -> SlotEditorial:
        return SlotEditorial(
            fecha=fecha_dia.strftime("%Y-%m-%d"),
            dia_semana=dia,
            hora_sugerida=HORAS_SUGERIDAS.get(dia, "19:00"),
            tipo_post=config["tipo"],
            tono=config["tono"],
            nicho=config["nicho"],
            municipio=municipio,
            proyecto=proyecto,
            notas=f"Distribucion default para {dia}",
        )

    def _slot_fecha_clave(
        self, fecha_dia: datetime, fecha_clave: dict, municipio: str
    ) -> SlotEditorial:
        nombre = fecha_clave["nombre"]
        # Plantillas especiales por fecha
        if "Madre" in nombre or "Padre" in nombre:
            tipo, tono, nichos = "fecha_especial", "emotivo", ["general", "casas"]
            notas = f"Post para {nombre}: enfoque emotivo/familiar, evita parecer comercial"
        elif "Navidad" in nombre or "Ano Nuevo" in nombre or "Nochebuena" in nombre:
            tipo, tono, nichos = "fecha_especial", "emotivo", ["general", "casas"]
            notas = f"Post para {nombre}: enfoque cierre de ano, balance del 2026, deseos"
        elif "Black Friday" in nombre or "Cyber Monday" in nombre:
            tipo, tono, nichos = "fecha_especial", "urgencia", ["inversion", "country"]
            notas = f"Post para {nombre}: oportunidad, preventa, descuento por pago contado"
        elif "Independencia" in nombre or "Bandera" in nombre or "Revolucion" in nombre:
            tipo, tono, nichos = "fecha_especial", "emotivo", ["general"]
            notas = f"Post para {nombre}: orgullo nacional, campo argentino, identidad"
        elif "Nino" in nombre:
            tipo, tono, nichos = "fecha_especial", "emotivo", ["general", "casas"]
            notas = "Post para el Ninio: vida en el campo, espacios para jugar"
        else:
            tipo, tono, nichos = "fecha_especial", "practico", ["general"]
            notas = f"Post para {nombre}"

        return SlotEditorial(
            fecha=fecha_dia.strftime("%Y-%m-%d"),
            dia_semana=DIAS_SEMANA[fecha_dia.weekday()],
            hora_sugerida="10:00",
            tipo_post=tipo,
            tono=tono,
            nicho=nichos,
            municipio=municipio,
            proyecto=None,
            notas=notas,
            es_fecha_clave=True,
            fecha_clave_nombre=nombre,
        )

    def _generar_post_para_slot(self, slot: SlotEditorial) -> dict[str, Any]:
        """Genera el post completo segun el tipo de slot."""
        tipo = slot.tipo_post
        municipio = slot.municipio
        tono = slot.tono

        try:
            if tipo == "lote_venta":
                return self.studio.post.post_lote_venta(
                    tema=f"Lote en {municipio}",
                    municipio=municipio,
                    hectareas="5 hectareas",
                    distancia_caba="65 km",
                    tono=tono,
                    nichos=slot.nicho,
                )
            elif tipo == "country":
                return self.studio.post.post_country(
                    nombre_country="Country Premium",
                    municipio=municipio,
                    metros_cuadrados=1000,
                    tono=tono,
                )
            elif tipo == "campo":
                return self.studio.post.post_campo(
                    hectareas="50 ha",
                    municipio=municipio,
                    tono=tono,
                )
            elif tipo == "lote_periurbano":
                return self.studio.post.post_lote_periurbano(
                    municipio=municipio,
                    metros_cuadrados=1000,
                    tono=tono,
                )
            elif tipo == "preventa":
                return self.studio.post.post_preventa(
                    nombre_loteo="Country Premium",
                    municipio=municipio,
                    tono=tono,
                )
            elif tipo == "carrusel" or tipo == "servicios":
                caption = self._caption_placeholder_carrusel(municipio, tono, slot.nicho)
                hashtags = self.studio.post.hashtags(slot.nicho, municipio)
                return {
                    "fecha_creacion": datetime.now().isoformat(timespec="seconds"),
                    "tema": "Carrusel (pendiente de generar)",
                    "tipo": "carrusel",
                    "municipio": municipio,
                    "tono": tono,
                    "caption": caption,
                    "hashtags": hashtags,
                    "caption_completo": caption + "\n\n" + " ".join(hashtags),
                    "placeholder": True,
                    "accion_requerida": "Generar carrusel con CarruselFactory.lote_premium / country_etapa / obra_avance / servicios",
                }
            elif tipo == "render_proyecto":
                req = self.studio.construccion.render_proyecto(
                    estilo="casa de campo tradicional", hectareas=5, municipio=municipio
                )
                caption = self._caption_placeholder_render(municipio, tono)
                hashtags = self.studio.post.hashtags(["casas", "general"], municipio)
                return {
                    "fecha_creacion": datetime.now().isoformat(timespec="seconds"),
                    "tema": "Render de proyecto",
                    "tipo": "render_proyecto",
                    "municipio": municipio,
                    "tono": tono,
                    "caption": caption,
                    "hashtags": hashtags,
                    "caption_completo": caption + "\n\n" + " ".join(hashtags),
                    "prompt": req.prompt,
                    "aspect_ratio": req.aspect_ratio,
                    "styles": req.styles,
                    "placeholder": True,
                    "accion_requerida": "Generar imagen del prompt en Fooocus/Midjourney y reemplazar placeholder",
                }
            elif tipo == "obra_avance":
                caption = self._caption_placeholder_obra(municipio, tono)
                hashtags = self.studio.post.hashtags(["construccion", "casas"], municipio)
                return {
                    "fecha_creacion": datetime.now().isoformat(timespec="seconds"),
                    "tema": "Avance de obra",
                    "tipo": "obra_avance",
                    "municipio": municipio,
                    "tono": tono,
                    "caption": caption,
                    "hashtags": hashtags,
                    "caption_completo": caption + "\n\n" + " ".join(hashtags),
                    "placeholder": True,
                    "accion_requerida": "Subir foto real del avance y completar el carrusel con CarruselFactory.obra_avance",
                }
            elif tipo == "fecha_especial":
                nombre = slot.fecha_clave_nombre or "Fecha especial"
                caption = self._caption_fecha_especial(nombre, municipio, tono)
                hashtags = self.studio.post.hashtags(slot.nicho, municipio)
                return {
                    "fecha_creacion": datetime.now().isoformat(timespec="seconds"),
                    "tema": nombre,
                    "tipo": "fecha_especial",
                    "municipio": municipio,
                    "tono": tono,
                    "caption": caption,
                    "hashtags": hashtags,
                    "caption_completo": caption + "\n\n" + " ".join(hashtags),
                }
            else:
                caption = self._caption_placeholder_generico(tipo, municipio, tono)
                hashtags = self.studio.post.hashtags(["general"], municipio)
                return {
                    "fecha_creacion": datetime.now().isoformat(timespec="seconds"),
                    "tema": tipo.replace("_", " ").capitalize(),
                    "tipo": tipo,
                    "municipio": municipio,
                    "tono": tono,
                    "caption": caption,
                    "hashtags": hashtags,
                    "caption_completo": caption + "\n\n" + " ".join(hashtags),
                    "placeholder": True,
                    "accion_requerida": f"Tipo {tipo} pendiente de implementacion",
                }
        except Exception as e:
            return {
                "tipo_post": tipo,
                "error": str(e),
                "municipio": municipio,
                "placeholder": True,
            }

    @staticmethod
    def _caption_placeholder_carrusel(municipio: str, tono: str, nichos: list[str]) -> str:
        nichos_txt = ", ".join(nichos[:3]) if nichos else "lotes"
        if tono == "premium":
            return (
                f"✨ Algo especial para vos\n\n"
                f"Te armamos un carrusel con todo lo que tenes que saber sobre esta oportunidad en {municipio}.\n\n"
                f"Desliza → y mira las {len(nichos_txt)} cosas que hacen diferente a este proyecto.\n\n"
                f"📍 {municipio}, Buenos Aires\n\n"
                f"_Este caption es provisorio: se regenera cuando produzcas el carrusel._"
            )
        if tono == "emotivo":
            return (
                f"🌾 Una historia que vale la pena contar\n\n"
                f"En {municipio} hay un lugar que estamos armando con mucho amor. Te mostramos todo en este carrusel.\n\n"
                f"Empeza por el primer slide →\n\n"
                f"📍 {municipio}, Buenos Aires\n\n"
                f"_Este caption es provisorio: se regenera cuando produzcas el carrusel._"
            )
        return (
            f"📌 Hoy te mostramos algo que estabas buscando\n\n"
            f"En este carrusel reunimos todo lo importante sobre {municipio}. Desliza → y descubrilo.\n\n"
            f"📍 {municipio}, Buenos Aires\n\n"
            f"_Este caption es provisorio: se regenera cuando produzcas el carrusel._"
        )

    @staticmethod
    def _caption_placeholder_render(municipio: str, tono: str) -> str:
        if tono == "aspiracional":
            return (
                f"🏡 Asi podria quedar tu casa en {municipio}\n\n"
                f"Render conceptual basado en uno de nuestros proyectos en la zona.\n\n"
                f"Cada terreno tiene su casa ideal. Te ayudamos a diseñarla y construirla.\n\n"
                f"📍 {municipio}, Buenos Aires\n\n"
                f"_Caption provisorio: se regenera cuando generes la imagen del render._"
            )
        return (
            f"📐 Render de proyecto en {municipio}\n\n"
            f"Te mostramos una posibilidad concreta. Te la diseñamos llave en mano.\n\n"
            f"📍 {municipio}, Buenos Aires\n\n"
            f"_Caption provisorio: se regenera cuando generes la imagen del render._"
        )

    @staticmethod
    def _caption_placeholder_obra(municipio: str, tono: str) -> str:
        if tono == "practico":
            return (
                f"🏗 Avance de obra en {municipio}\n\n"
                f"Te mostramos como viene este proyecto. Diseño, movimiento de suelo, estructura, terminaciones: cada paso cuenta.\n\n"
                f"📍 {municipio}, Buenos Aires\n\n"
                f"_Caption provisorio: se regenera cuando subas la foto real del avance._"
            )
        return (
            f"🚧 Semana de obra\n\n"
            f"Algo se mueve en {municipio}. Te contamos en este post.\n\n"
            f"📍 {municipio}, Buenos Aires\n\n"
            f"_Caption provisorio: se regenera cuando subas la foto real._"
        )

    @staticmethod
    def _caption_placeholder_generico(tipo: str, municipio: str, tono: str) -> str:
        tipo_legible = tipo.replace("_", " ").capitalize()
        return (
            f"📍 {municipio}, Buenos Aires\n\n"
            f"_Caption provisorio para {tipo_legible}: implementar tipo de post._"
        )

    @staticmethod
    def _caption_fecha_especial(nombre: str, municipio: str, tono: str) -> str:
        if "Madre" in nombre:
            return (
                f"🌻 Feliz dia de las madres\n\n"
                f"Para la que nos enseno que lo mas valioso no se compra, se construye.\n\n"
                f"Para la que eligio vivir en el campo para que nosotros crezcamos con los pies en la tierra.\n\n"
                f"Gracias mama. Este proyecto (y todos) llevan tu firma.\n\n"
                f"📍 {municipio}, Buenos Aires"
            )
        if "Padre" in nombre:
            return (
                f"👨‍🌾 Feliz dia del padre\n\n"
                f"Para el que nos enseno que las cosas importantes se hacen con tiempo y con las manos.\n\n"
                f"Para el que eligio este lote y se quedo a construir su casa con su propia familia.\n\n"
                f"Gracias papa. La tranquera queda abierta para vos.\n\n"
                f"📍 {municipio}, Buenos Aires"
            )
        if "Navidad" in nombre or "Nochebuena" in nombre:
            return (
                f"🎄 Felices fiestas\n\n"
                f"Cerramos un ano mas abriendo tranqueras.\n\n"
                f"Gracias a las familias que confiaron en nosotros para construir su casa, "
                f"a los que compraron su lote y empezaron a proyectar, "
                f"y a los que todavia estan decidiendo: los esperamos en el 2026.\n\n"
                f"Que el ano que viene les encuentre con su casa propia, en el campo, en paz.\n\n"
                f"Brindemos desde {municipio} ✨"
            )
        if "Ano Nuevo" in nombre or "Fin de Ano" in nombre:
            return (
                f"🥂 Feliz 2026\n\n"
                f"Ano nuevo, casa nueva, vida nueva.\n\n"
                f"Este ano lo arrancamos con [X] proyectos en marcha y [Y] lotes disponibles. "
                f"¿Te sumas?\n\n"
                f"📍 {municipio}, Buenos Aires"
            )
        if "Black Friday" in nombre:
            return (
                f"🔥 Black Friday inmobiliario\n\n"
                f"Esta semana, [X]% de descuento en lotes seleccionados por pago al contado.\n\n"
                f"Stock limitado. Aplica para reservas en {municipio}.\n\n"
                f"Link en bio para ver disponibilidad."
            )
        if "Independencia" in nombre:
            return (
                f"🇦🇷 Feliz 9 de Julio\n\n"
                f"Argentina es campo, es familia, es trabajo.\n\n"
                f"Desde {municipio} seguimos construyendo el pais lote por lote, casa por casa.\n\n"
                f"Salud a todos los que eligen vivir en esta tierra."
            )
        if "Nino" in nombre:
            return (
                f"🧒 Feliz dia del ninio\n\n"
                f"Para los que van a crecer en este campo, corriendo entre los eucaliptos, "
                f"aprendiendo a montar a caballo y a mirar las estrellas sin luz artificial.\n\n"
                f"Esa es la casa que construimos. No paredes: un lugar para crecer.\n\n"
                f"📍 {municipio}, Buenos Aires"
            )
        return f"🌾 {nombre}\n\nDesde {municipio} les deseamos lo mejor."

    # ---------------- Helpers de fecha ----------------

    @staticmethod
    def _lunes_de_semana(semana_n: int) -> datetime:
        """Devuelve el lunes de la semana N (semana 1 = lunes actual)."""
        hoy = datetime.now().date()
        lunes_actual = hoy - timedelta(days=hoy.weekday())
        return datetime.combine(
            lunes_actual + timedelta(weeks=semana_n - 1),
            datetime.min.time(),
        )

    @staticmethod
    def _parsear_fecha(fecha_str: str) -> datetime:
        return datetime.strptime(fecha_str, "%Y-%m-%d")

    def _fechas_clave_en_rango(self, inicio: datetime, fin: datetime) -> list[dict]:
        """Detecta fechas clave AR + inmobiliarias en el rango (multi-anio)."""
        encontradas: list[dict] = []
        anios = {inicio.year, fin.year}
        todas: list[tuple[int, int, str]] = []
        for anio in anios:
            todas.extend(_fechas_clave_completas(anio))
        actual = inicio.date()
        fin_date = fin.date()
        while actual <= fin_date:
            for mes, dia, nombre in todas:
                if actual.month == mes and actual.day == dia:
                    encontradas.append(
                        {
                            "fecha": actual.strftime("%Y-%m-%d"),
                            "nombre": nombre,
                            "mes": mes,
                            "dia": dia,
                        }
                    )
            actual += timedelta(days=1)
        return encontradas

    # ---------------- Persistencia y exportacion ----------------

    def guardar(self, semana: SemanaEditorial) -> Path:
        carpeta = CALENDARIOS_DIR / f"semana_{semana.numero:02d}"
        carpeta.mkdir(parents=True, exist_ok=True)
        json_path = carpeta / "plan.json"
        json_path.write_text(
            json.dumps(semana.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return carpeta

    def exportar_markdown(self, semana: SemanaEditorial, ruta: Path | None = None) -> Path:
        if ruta is None:
            carpeta = CALENDARIOS_DIR / f"semana_{semana.numero:02d}"
            carpeta.mkdir(parents=True, exist_ok=True)
            ruta = carpeta / "plan.md"

        lineas: list[str] = [
            f"# Semana {semana.numero} · {semana.fecha_inicio} → {semana.fecha_fin}",
            "",
            f"**Municipio principal:** {semana.municipio_principal}  ",
            f"**Proyectos disponibles:** {', '.join(semana.proyectos_disponibles) or '(ninguno)'}  ",
            f"**Posts esta semana:** {len(semana.slots)}  ",
            f"**Fechas clave cubiertas:** {', '.join(semana.fechas_clave_cubiertas) or '(ninguna)'}  ",
            "",
            "## Planificacion",
            "",
            "| Fecha | Dia | Hora | Tipo | Tono | Municipio | Proyecto | Notas |",
            "|-------|-----|------|------|------|-----------|----------|-------|",
        ]
        for slot in semana.slots:
            marca = "🎉 " if slot.es_fecha_clave else ""
            tipo = marca + slot.tipo_post
            proyecto = slot.proyecto or "-"
            lineas.append(
                f"| {slot.fecha} | {slot.dia_semana} | {slot.hora_sugerida} "
                f"| {tipo} | {slot.tono} | {slot.municipio} | {proyecto} | {slot.notas} |"
            )

        lineas.extend(["", "## Posts completos", ""])
        for slot in semana.slots:
            lineas.append(f"### {slot.fecha} · {slot.dia_semana} · {slot.tipo_post} ({slot.tono})")
            lineas.append(f"_Hora sugerida: {slot.hora_sugerida}_")
            if slot.es_fecha_clave and slot.fecha_clave_nombre:
                lineas.append(f"_🎉 Fecha clave: {slot.fecha_clave_nombre}_")
            lineas.append("")
            if slot.post:
                if slot.post.get("placeholder"):
                    lineas.append(f"⚠️ *Placeholder:* {slot.post.get('notas', 'requiere acción')}")
                    if slot.post.get("prompt"):
                        lineas.append("")
                        lineas.append("```")
                        lineas.append(slot.post["prompt"])
                        lineas.append("```")
                else:
                    lineas.append("**Caption:**")
                    lineas.append("")
                    lineas.append("```")
                    lineas.append(slot.post.get("caption", ""))
                    lineas.append("```")
                    lineas.append("")
                    if slot.post.get("hashtags"):
                        lineas.append("**Hashtags:**")
                        lineas.append("")
                        lineas.append(" ".join(slot.post["hashtags"]))
                        lineas.append("")
                    lineas.append("**Caption completo para copiar:**")
                    lineas.append("")
                    lineas.append("```")
                    lineas.append(slot.post.get("caption_completo", ""))
                    lineas.append("```")
            else:
                lineas.append("_(no se genero post)_")
            lineas.append("")

        ruta.write_text("\n".join(lineas), encoding="utf-8")
        return ruta

    def exportar_csv(self, semana: SemanaEditorial, ruta: Path | None = None) -> Path:
        """Exporta el calendario a CSV (importable a Excel / Google Sheets)."""
        if ruta is None:
            carpeta = CALENDARIOS_DIR / f"semana_{semana.numero:02d}"
            carpeta.mkdir(parents=True, exist_ok=True)
            ruta = carpeta / "plan.csv"

        import csv

        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "fecha",
                    "dia_semana",
                    "hora",
                    "tipo_post",
                    "tono",
                    "nicho",
                    "municipio",
                    "proyecto",
                    "es_fecha_clave",
                    "fecha_clave_nombre",
                    "caption_preview",
                    "n_hashtags",
                    "placeholder",
                    "notas",
                ]
            )
            for slot in semana.slots:
                caption = (slot.post or {}).get("caption_completo", "")
                hashtags = (slot.post or {}).get("hashtags", [])
                placeholder = (slot.post or {}).get("placeholder", False) if slot.post else False
                caption_preview = caption[:200].replace("\n", " ")
                nichos = ",".join(slot.nicho)
                writer.writerow(
                    [
                        slot.fecha,
                        slot.dia_semana,
                        slot.hora_sugerida,
                        slot.tipo_post,
                        slot.tono,
                        nichos,
                        slot.municipio,
                        slot.proyecto or "",
                        "SI" if slot.es_fecha_clave else "no",
                        slot.fecha_clave_nombre or "",
                        caption_preview,
                        len(hashtags),
                        "SI" if placeholder else "no",
                        slot.notas,
                    ]
                )
        return ruta

    def exportar_ics(self, semana: SemanaEditorial, ruta: Path | None = None) -> Path:
        """Exporta a formato .ics para Google Calendar / Apple Calendar."""
        if ruta is None:
            carpeta = CALENDARIOS_DIR / f"semana_{semana.numero:02d}"
            carpeta.mkdir(parents=True, exist_ok=True)
            ruta = carpeta / "plan.ics"

        lineas: list[str] = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//RealestateStudio//AMBA//ES",
            "CALSCALE:GREGORIAN",
        ]

        for slot in semana.slots:
            dt = datetime.strptime(f"{slot.fecha} {slot.hora_sugerida}", "%Y-%m-%d %H:%M")
            dt_fin = dt + timedelta(hours=1)
            titulo = f"[IG] {slot.tipo_post} ({slot.tono}) - {slot.municipio}"
            if slot.es_fecha_clave and slot.fecha_clave_nombre:
                titulo = f"🎉 {titulo} - {slot.fecha_clave_nombre}"
            descripcion = slot.notas or ""
            if slot.proyecto:
                descripcion += f"\\nProyecto: {slot.proyecto}"
            uid = f"{slot.fecha}-{slot.hora_sugerida}-{slot.tipo_post}@realestate-studio"

            lineas.extend(
                [
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
                    f"DTSTART:{dt.strftime('%Y%m%dT%H%M%S')}",
                    f"DTEND:{dt_fin.strftime('%Y%m%dT%H%M%S')}",
                    f"SUMMARY:{titulo}",
                    f"DESCRIPTION:{descripcion}",
                    "END:VEVENT",
                ]
            )

        lineas.append("END:VCALENDAR")
        ruta.write_text("\n".join(lineas), encoding="utf-8")
        return ruta


def demo() -> None:
    from realestate_studio import RealestateStudio

    studio = RealestateStudio()
    cal = CalendarioEditorial(studio)

    semana = cal.generar_semana(
        semana_n=1,
        proyectos=["chacra-canuelas-5ha", "country-pilar-ejemplo"],
        posts_por_semana=5,
        municipio_principal="Cañuelas",
    )

    carpeta = cal.guardar(semana)
    md_path = cal.exportar_markdown(semana)
    ics_path = cal.exportar_ics(semana)

    print(f"Semana {semana.numero}: {semana.fecha_inicio} → {semana.fecha_fin}")
    print(f"Slots: {len(semana.slots)}")
    print(f"Fechas clave cubiertas: {semana.fechas_clave_cubiertas or '(ninguna)'}")
    print()
    for slot in semana.slots:
        marca = "🎉 " if slot.es_fecha_clave else ""
        print(
            f"  {slot.fecha} {slot.hora_sugerida} {marca}{slot.dia_semana}: "
            f"{slot.tipo_post} ({slot.tono}) en {slot.municipio}"
        )
    print()
    print(f"Markdown: {md_path}")
    print(f"ICS:      {ics_path}")


if __name__ == "__main__":
    demo()

"""Genera el informe final en PDF a partir de los resultados del análisis.

El informe está escrito para personas que trabajan en temas ambientales pero no
programan: explica qué se midió, cómo se midió y qué significa, sin pedirle al
lector que entienda el código.

Uso (después de `python -m src.analisis`):
    python -m src.informe
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.carga import UMBRAL_FLORACION
from src.comparacion import CONTEXTO
from src.config import DIR_FIGURAS, LAGOS, RAIZ
from src.temporal import UMBRAL_INTENSO

AUTORES = "Pablo Cabrera · Luis Mendoza"
CURSO = "CC3084 — Data Science · Universidad del Valle de Guatemala · Semestre II 2026"

ANCHO_UTIL = A4[0] - 4 * cm

AZUL = colors.HexColor("#2a78d6")
NARANJA = colors.HexColor("#eb6834")
TINTA = colors.HexColor("#0b0b0b")
TINTA_SEC = colors.HexColor("#52514e")
TINTA_TENUE = colors.HexColor("#898781")
FONDO_NOTA = colors.HexColor("#f2f6fd")
FONDO_ALERTA = colors.HexColor("#fdf3ec")
LINEA = colors.HexColor("#e1e0d9")


# --------------------------------------------------------------------------- #
# Estilos
# --------------------------------------------------------------------------- #
def construir_estilos():
    base = getSampleStyleSheet()
    e = {}
    e["titulo"] = ParagraphStyle(
        "titulo", parent=base["Title"], fontName="Helvetica-Bold",
        fontSize=25, leading=30, textColor=TINTA, spaceAfter=6,
    )
    e["subtitulo"] = ParagraphStyle(
        "subtitulo", parent=base["Normal"], fontName="Helvetica",
        fontSize=13, leading=18, textColor=TINTA_SEC, alignment=TA_CENTER,
    )
    e["portada_meta"] = ParagraphStyle(
        "portada_meta", parent=base["Normal"], fontName="Helvetica",
        fontSize=10.5, leading=16, textColor=TINTA_TENUE, alignment=TA_CENTER,
    )
    e["h1"] = ParagraphStyle(
        "h1", parent=base["Heading1"], fontName="Helvetica-Bold",
        fontSize=16, leading=20, textColor=TINTA, spaceBefore=18, spaceAfter=8,
    )
    e["h2"] = ParagraphStyle(
        "h2", parent=base["Heading2"], fontName="Helvetica-Bold",
        fontSize=12.5, leading=16, textColor=AZUL, spaceBefore=14, spaceAfter=5,
    )
    e["cuerpo"] = ParagraphStyle(
        "cuerpo", parent=base["BodyText"], fontName="Helvetica",
        fontSize=10.3, leading=15.5, textColor=TINTA, alignment=TA_JUSTIFY,
        spaceAfter=7,
    )
    e["vineta"] = ParagraphStyle(
        "vineta", parent=e["cuerpo"], leftIndent=14, bulletIndent=3, spaceAfter=5,
    )
    e["pie"] = ParagraphStyle(
        "pie", parent=base["Normal"], fontName="Helvetica-Oblique",
        fontSize=8.8, leading=12, textColor=TINTA_TENUE, alignment=TA_CENTER,
        spaceBefore=3, spaceAfter=12,
    )
    e["nota"] = ParagraphStyle(
        "nota", parent=e["cuerpo"], fontSize=9.8, leading=14.5,
        leftIndent=9, rightIndent=9, spaceBefore=5, spaceAfter=5,
    )
    e["celda"] = ParagraphStyle(
        "celda", parent=base["Normal"], fontName="Helvetica",
        fontSize=9, leading=12, textColor=TINTA,
    )
    e["celda_enc"] = ParagraphStyle(
        "celda_enc", parent=e["celda"], fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    return e


def marcar(texto: str) -> str:
    """Convierte el marcado ligero de los textos generados a etiquetas de PDF."""
    texto = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", texto)
    return texto.replace("µ", "µ")


# --------------------------------------------------------------------------- #
# Piezas reutilizables
# --------------------------------------------------------------------------- #
def parrafos(texto: str, estilos) -> list:
    return [Paragraph(marcar(p), estilos["cuerpo"]) for p in texto.split("\n\n") if p.strip()]


def figura(nombre: str, pie: str, estilos, ancho: float = ANCHO_UTIL) -> list:
    ruta = DIR_FIGURAS / nombre
    if not ruta.exists():
        return [Paragraph(f"[falta la figura {nombre}]", estilos["pie"])]

    from PIL import Image as PILImage

    with PILImage.open(ruta) as img:
        w, h = img.size
    alto = ancho * h / w
    # Nada debe exceder el alto útil de la página, o reportlab la parte mal.
    maximo = A4[1] - 7 * cm
    if alto > maximo:
        ancho, alto = ancho * maximo / alto, maximo

    return [
        Spacer(1, 6),
        Image(str(ruta), width=ancho, height=alto),
        Paragraph(pie, estilos["pie"]),
    ]


def recuadro(titulo: str, cuerpo: str, estilos, fondo=FONDO_NOTA, borde=AZUL) -> Table:
    contenido = [
        Paragraph(f"<b>{titulo}</b>", estilos["nota"]),
        Paragraph(marcar(cuerpo), estilos["nota"]),
    ]
    tabla = Table([[contenido]], colWidths=[ANCHO_UTIL])
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fondo),
                ("LINEBEFORE", (0, 0), (0, -1), 3, borde),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return tabla


def tabla_datos(encabezados, filas, estilos, anchos=None) -> Table:
    datos = [[Paragraph(str(h), estilos["celda_enc"]) for h in encabezados]]
    datos += [[Paragraph(str(c), estilos["celda"]) for c in fila] for fila in filas]

    tabla = Table(datos, colWidths=anchos or [ANCHO_UTIL / len(encabezados)] * len(encabezados),
                  repeatRows=1)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, LINEA),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, TINTA_TENUE),
    ]
    for i in range(1, len(datos)):
        if i % 2 == 0:
            estilo.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f7f7f5")))
    tabla.setStyle(TableStyle(estilo))
    return tabla


def encabezado_pie(canvas, doc):
    """Numeración y línea de pie en todas las páginas menos la portada."""
    canvas.saveState()
    if doc.page > 1:
        canvas.setStrokeColor(LINEA)
        canvas.setLineWidth(0.5)
        canvas.line(2 * cm, 1.7 * cm, A4[0] - 2 * cm, 1.7 * cm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(TINTA_TENUE)
        canvas.drawString(2 * cm, 1.25 * cm,
                          "Monitoreo satelital de cianobacteria — Atitlán y Amatitlán")
        canvas.drawRightString(A4[0] - 2 * cm, 1.25 * cm, f"Página {doc.page}")
    canvas.restoreState()


# --------------------------------------------------------------------------- #
# Secciones
# --------------------------------------------------------------------------- #
def portada(estilos, datos) -> list:
    n = sum(datos["n_escenas"].values())
    return [
        Spacer(1, 3.4 * cm),
        Paragraph("Monitoreo satelital de floraciones de cianobacteria", estilos["titulo"]),
        Spacer(1, 0.2 * cm),
        Paragraph("Lago de Atitlán y lago de Amatitlán, Guatemala<br/>2025 – 2026",
                  estilos["subtitulo"]),
        Spacer(1, 1.1 * cm),
        recuadro(
            "En una línea",
            f"Se analizaron {n} imágenes del satélite Sentinel-2 para medir, sin salir a "
            f"campo, cuánta cianobacteria hay en cada lago, dónde se concentra y cómo "
            f"cambió a lo largo de {'año y medio' if n else ''}.",
            estilos,
        ),
        Spacer(1, 1.4 * cm),
        Paragraph(AUTORES, estilos["subtitulo"]),
        Spacer(1, 0.35 * cm),
        Paragraph(CURSO, estilos["portada_meta"]),
        Paragraph(f"Laboratorio 4 — Análisis de datos geoespaciales<br/>{date.today():%d de %B de %Y}",
                  estilos["portada_meta"]),
        PageBreak(),
    ]


def resumen_ejecutivo(estilos, datos) -> list:
    resumen = {r["lago"]: r for r in datos["resumen_lagos"]}
    at, am = resumen["Atitlan"], resumen["Amatitlan"]
    serie = datos["serie"]

    peor_am = max((s for s in serie if s["lago"] == "Amatitlan"), key=lambda s: s["chl_medio"])
    peor_at = max((s for s in serie if s["lago"] == "Atitlan"), key=lambda s: s["chl_medio"])

    puntos = [
        f"<b>Amatitlán está permanentemente afectado.</b> Su nivel promedio de "
        f"clorofila-a fue de {am['chl_medio']:.1f} µg/L y superó el umbral de floración "
        f"en {int(am['fechas_con_floracion'])} de las {int(am['n_fechas'])} fechas "
        f"analizadas. No es un problema de episodios aislados: es su estado habitual.",

        f"<b>Atitlán está mejor, pero no está limpio.</b> Su promedio fue de "
        f"{at['chl_medio']:.1f} µg/L y superó el umbral en "
        f"{int(at['fechas_con_floracion'])} de {int(at['n_fechas'])} fechas. "
        f"Su comportamiento es más episódico: largos períodos aceptables interrumpidos "
        f"por eventos puntuales.",

        f"<b>Las peores fechas registradas</b> fueron el {peor_am['fecha']} en Amatitlán "
        f"({peor_am['chl_medio']:.1f} µg/L de promedio, con el "
        f"{peor_am['pct_area_alta']:.0f} % de la superficie afectada) y el "
        f"{peor_at['fecha']} en Atitlán ({peor_at['chl_medio']:.1f} µg/L, "
        f"{peor_at['pct_area_alta']:.0f} % de la superficie).",

        f"<b>El problema no se reparte de forma pareja dentro de cada lago.</b> Hay zonas "
        f"que aparecen afectadas fecha tras fecha, lo que apunta a fuentes continuas de "
        f"nutrientes y no a eventos climáticos pasajeros.",

        f"<b>La diferencia entre ambos lagos tiene explicación física.</b> Amatitlán es "
        f"casi nueve veces más pequeño y diez veces menos profundo que Atitlán, pero "
        f"recibe la descarga de una cuenca con más de un millón y medio de habitantes.",
    ]

    return [
        Paragraph("Resumen ejecutivo", estilos["h1"]),
        Paragraph(
            "Este informe resume lo que las imágenes de satélite muestran sobre la "
            "proliferación de cianobacterias en los dos lagos más monitoreados de "
            "Guatemala. Los cinco hallazgos principales son:",
            estilos["cuerpo"],
        ),
        Spacer(1, 4),
        *[Paragraph(p, estilos["vineta"], bulletText="•") for p in puntos],
        Spacer(1, 10),
        recuadro(
            "Qué hacer con esta información",
            "Los resultados sirven para <b>priorizar</b>: indican qué lago necesita "
            "atención sostenida y cuál necesita alerta temprana, en qué zonas conviene "
            "ubicar los puntos de muestreo físico, y en qué momentos del año hay que "
            "reforzar la vigilancia. No sustituyen al análisis de laboratorio: lo "
            "orientan para que cueste menos y llegue antes.",
            estilos, fondo=FONDO_ALERTA, borde=NARANJA,
        ),
        PageBreak(),
    ]


def metodologia(estilos, datos) -> list:
    n_at = datos["n_escenas"].get("Atitlan", 0)
    n_am = datos["n_escenas"].get("Amatitlan", 0)

    return [
        Paragraph("1. Cómo se obtuvieron estos resultados", estilos["h1"]),

        Paragraph("Qué es lo que mide el satélite", estilos["h2"]),
        Paragraph(
            "Los satélites Sentinel-2, del programa europeo Copernicus, fotografían toda "
            "la superficie terrestre cada pocos días. A diferencia de una cámara común, "
            "no registran solo los colores que ve el ojo humano: miden por separado la "
            "cantidad de luz que la superficie refleja en trece rangos distintos del "
            "espectro, incluidos varios que el ojo no percibe.",
            estilos["cuerpo"],
        ),
        Paragraph(
            "Esto es útil porque cada material refleja la luz de forma característica. "
            "El agua limpia absorbe casi toda la luz y se ve muy oscura. Las "
            "cianobacterias, en cambio, contienen clorofila, y la clorofila tiene una "
            "firma inconfundible: absorbe fuertemente el rojo y refleja mucho justo en el "
            "límite entre el rojo y el infrarrojo. Cuando ese salto aparece sobre un "
            "cuerpo de agua, significa que en el agua hay organismos fotosintéticos.",
            estilos["cuerpo"],
        ),

        Paragraph("El índice que se usó", estilos["h2"]),
        Paragraph(
            "Para convertir esa firma en un número se utilizó un procedimiento publicado y "
            "revisado por especialistas, el script <i>CyanoLakes Chlorophyll-a</i> "
            "(Kravitz y Matthews, 2020), disponible en la biblioteca oficial de scripts de "
            "Sentinel Hub. El procedimiento tiene tres pasos:",
            estilos["cuerpo"],
        ),
        Paragraph(
            "Primero <b>identifica qué píxeles son agua</b> y descarta todo lo demás, para "
            "no confundir la vegetación de la orilla con una floración. Segundo, calcula "
            "el <b>índice NDCI</b>, que compara la luz reflejada en el rojo con la del "
            "borde rojo y detecta la firma de la clorofila. Tercero, traduce ese índice a "
            "una <b>concentración estimada de clorofila-a en microgramos por litro "
            "(µg/L)</b>, que es la unidad con la que trabajan habitualmente los "
            "laboratorios de calidad de agua.",
            estilos["cuerpo"],
        ),
        recuadro(
            f"Cómo leer las cifras de clorofila-a",
            f"Por debajo de <b>{UMBRAL_FLORACION:.0f} µg/L</b> el agua se considera en "
            f"condiciones aceptables. A partir de {UMBRAL_FLORACION:.0f} µg/L se habla de "
            f"<b>floración</b>: hay suficiente biomasa como para que la Organización "
            f"Mundial de la Salud señale un riesgo bajo pero real para el contacto "
            f"recreativo. Por encima de <b>{UMBRAL_INTENSO:.0f} µg/L</b> hablamos de "
            f"<b>floración intensa</b>, con agua visiblemente teñida. En este informe esos "
            f"dos valores son los cortes usados en todos los mapas y gráficos.",
            estilos,
        ),

        *figura("03_vista_cyanolakes_Amatitlan.png",
                "A la izquierda, el lago de Amatitlán como lo vería el ojo humano desde el "
                "satélite. A la derecha, el mismo día procesado con el índice: el azul es "
                "agua limpia y los verdes, amarillos y rojos indican cantidades crecientes "
                "de clorofila-a.", estilos),

        Paragraph("Qué imágenes se analizaron", estilos["h2"]),
        Paragraph(
            f"Se trabajó con el calendario de fechas fijado para el ejercicio: "
            f"{n_at} imágenes utilizables del lago de Atitlán y {n_am} del lago de "
            f"Amatitlán, repartidas entre enero de 2025 y julio de 2026. Son fechas "
            f"elegidas por tener poca nubosidad, que es la limitación principal del "
            f"monitoreo satelital en el trópico. Cada imagen se analizó a una resolución "
            f"de 20 metros: cada dato del mapa corresponde a un cuadrado de 20 × 20 "
            f"metros de superficie de agua.",
            estilos["cuerpo"],
        ),
        Paragraph(
            "Antes de calcular cualquier promedio se descartaron los píxeles cubiertos por "
            "nubes y los que quedaban fuera del espejo de agua. Además, para que las "
            "comparaciones entre fechas fueran válidas, todas las fechas de un mismo lago "
            "se analizaron sobre exactamente la misma superficie de agua: de otro modo, un "
            "cambio en el nivel del lago se habría confundido con un cambio en la "
            "floración.",
            estilos["cuerpo"],
        ),
        PageBreak(),
    ]


def seccion_temporal(estilos, datos) -> list:
    serie = datos["serie"]
    filas = [
        (
            s["fecha"],
            LAGOS[s["lago"]]["nombre"].replace("Lago de ", ""),
            f"{s['chl_medio']:.1f}",
            f"{s['chl_p90']:.1f}",
            f"{s['pct_area_alta']:.0f} %",
            f"{s['pct_area_intensa']:.0f} %",
        )
        for s in sorted(serie, key=lambda s: (s["lago"], s["fecha"]))
    ]

    return [
        Paragraph("2. Cómo cambió la situación en el tiempo", estilos["h1"]),
        Paragraph(
            "El primer gráfico muestra, para cada lago, el nivel promedio de clorofila-a "
            "en cada una de las fechas analizadas. La línea roja punteada marca el umbral "
            "de floración: todo lo que queda por encima significa que el lago, en promedio, "
            "estaba en floración ese día. Los círculos rojos señalan las fechas críticas, "
            "es decir, aquellas en que el lago se apartó claramente de su propio "
            "comportamiento habitual.",
            estilos["cuerpo"],
        ),
        *figura("04_serie_temporal_por_lago.png",
                "Evolución del nivel promedio de clorofila-a en cada lago. La banda sombreada "
                "indica cuánto se separan las zonas más afectadas del valor típico.", estilos),
        PageBreak(),

        Paragraph("Qué muestran estas series", estilos["h2"]),
        *parrafos(datos["textos"]["temporal"], estilos),

        Paragraph("Cuánta superficie del lago está afectada", estilos["h2"]),
        Paragraph(
            "El promedio de un lago puede ocultar información importante. Un lago puede "
            "tener un promedio aceptable y aun así tener una bahía entera en floración. "
            "Por eso conviene mirar también qué porcentaje de la superficie supera el "
            "umbral en cada fecha.",
            estilos["cuerpo"],
        ),
        *figura("04_extension_floracion.png",
                "Porcentaje de la superficie de cada lago con niveles de floración.", estilos),
        *figura("08_composicion_superficie.png",
                "Composición de la superficie de cada lago en cada fecha: agua en condiciones "
                "aceptables (azul claro), en floración (amarillo) y en floración intensa (rojo).",
                estilos),
        PageBreak(),

        Paragraph("Tabla de resultados por fecha", estilos["h2"]),
        Paragraph(
            "La columna «10 % más afectado» indica el nivel que supera la décima parte más "
            "afectada del lago: es una medida de qué tan malas están las peores zonas, "
            "aunque el promedio general parezca aceptable.",
            estilos["cuerpo"],
        ),
        Spacer(1, 6),
        tabla_datos(
            ["Fecha", "Lago", "Promedio<br/>(µg/L)", "10 % más<br/>afectado (µg/L)",
             "Superficie en<br/>floración", "Superficie en<br/>floración intensa"],
            filas, estilos,
            anchos=[2.4 * cm, 2.6 * cm, 2.4 * cm, 3.2 * cm, 2.9 * cm, 3.5 * cm],
        ),
        PageBreak(),
    ]


def seccion_espacial(estilos, datos) -> list:
    elementos = [
        Paragraph("3. Dónde se concentra la cianobacteria", estilos["h1"]),
        Paragraph(
            "Los mapas de esta sección muestran la distribución de clorofila-a dentro de "
            "cada lago. El color claro indica agua en buenas condiciones y el color oscuro "
            "indica floración; el gris es tierra firme, que queda fuera del análisis. "
            "Todos los mapas de un mismo lago usan la misma escala de color, de modo que "
            "dos fechas se pueden comparar directamente a simple vista.",
            estilos["cuerpo"],
        ),
    ]

    for clave in LAGOS:
        nombre = LAGOS[clave]["nombre"]
        elementos += [
            Paragraph(nombre, estilos["h2"]),
            # La vista equivalente de Amatitlán ya se mostró como ejemplo en la
            # sección de metodología; no hace falta repetirla aquí.
            *(figura(f"03_vista_cyanolakes_{clave}.png",
                     f"{nombre}: la imagen real y su procesamiento con el índice de "
                     f"cianobacteria, en la fecha más afectada del período.", estilos)
              if clave != "Amatitlan" else []),
            *figura(f"05_mapas_por_fecha_{clave}.png",
                    f"{nombre}: distribución de clorofila-a en cada fecha analizada.", estilos),
            PageBreak(),
            *figura(f"05_comparacion_fechas_{clave}.png",
                    f"{nombre}: comparación directa entre la fecha más limpia y la más "
                    f"afectada. El tercer mapa muestra dónde ocurrió el cambio.", estilos),
            *figura(f"08_persistencia_{clave}.png",
                    f"{nombre}: a la izquierda, el promedio de todo el período; a la derecha, "
                    f"en qué porcentaje de las fechas cada punto superó el umbral de floración.",
                    estilos),
            PageBreak(),
        ]

    elementos += [
        Paragraph("Qué muestran los mapas", estilos["h2"]),
        *parrafos(datos["textos"]["espacial"], estilos),
        recuadro(
            "Por qué importan las zonas persistentes",
            "Una zona que aparece afectada en una sola fecha puede deberse a una lluvia "
            "reciente o a una condición de viento puntual. Una zona que aparece afectada "
            "en la mayoría de las fechas indica algo estructural: una desembocadura que "
            "descarga nutrientes de forma continua, una bahía donde el agua circula poco, "
            "o una zona somera donde el sedimento del fondo devuelve nutrientes al agua. "
            "<b>Son estas zonas, y no las peores fechas, las que conviene priorizar para "
            "el muestreo físico y para las medidas de saneamiento.</b>",
            estilos, fondo=FONDO_ALERTA, borde=NARANJA,
        ),
        Spacer(1, 8),
        Paragraph(
            "Junto con este informe se entregan dos mapas interactivos "
            "(<font face='Courier'>outputs/mapas/</font>), que permiten encender y apagar "
            "cada fecha sobre un mapa base y hacer zoom sobre cualquier zona del lago.",
            estilos["cuerpo"],
        ),
        PageBreak(),
    ]
    return elementos


def seccion_correlacion(estilos, datos) -> list:
    return [
        Paragraph("4. Verificación con otros indicadores", estilos["h1"]),
        Paragraph(
            "Antes de dar por buenos los resultados conviene comprobarlos con indicadores "
            "independientes. Se usaron dos índices muy establecidos en teledetección:",
            estilos["cuerpo"],
        ),
        Paragraph(
            "<b>NDVI</b> (índice de vegetación). Mide cuánta materia vegetal verde y activa "
            "hay en una superficie. Se usa normalmente para cultivos y bosques, pero como "
            "las cianobacterias también hacen fotosíntesis, un agua con floración empieza a "
            "«parecerse» ópticamente a vegetación.",
            estilos["vineta"], bulletText="•",
        ),
        Paragraph(
            "<b>NDWI</b> (índice de agua). Mide qué tan «limpia» de vegetación se ve una "
            "superficie de agua. Baja cuando la superficie se cubre de biomasa.",
            estilos["vineta"], bulletText="•",
        ),
        Paragraph(
            "Si el índice de cianobacteria está midiendo algo real, debería subir cuando "
            "sube el NDVI y bajar cuando sube el NDWI. Eso es exactamente lo que se "
            "observa.",
            estilos["cuerpo"],
        ),
        *figura("06_dispersion_indices.png",
                "Cada punto de estos gráficos es un cuadrado de 20 × 20 m de agua. Las zonas "
                "más oscuras concentran más puntos. La línea punteada resume la tendencia.",
                estilos),
        PageBreak(),
        *figura("06_correlacion_temporal.png",
                "La misma relación vista fecha por fecha: cada punto es una imagen completa.",
                estilos),
        Paragraph("Hallazgos", estilos["h2"]),
        *parrafos(datos["textos"]["correlacion"], estilos),
        PageBreak(),
    ]


def seccion_comparacion(estilos, datos) -> list:
    resumen = {r["lago"]: r for r in datos["resumen_lagos"]}
    filas = []
    for clave, ctx in CONTEXTO.items():
        r = resumen[clave]
        filas.append(
            (
                LAGOS[clave]["nombre"].replace("Lago de ", ""),
                f"{ctx['area_km2']:.0f} km²",
                f"{ctx['prof_max_m']} m",
                f"{r['chl_medio']:.1f} µg/L",
                f"{int(r['fechas_con_floracion'])} de {int(r['n_fechas'])}",
                f"{r['pct_area_alta_media']:.0f} %",
            )
        )

    return [
        Paragraph("5. Los dos lagos, uno al lado del otro", estilos["h1"]),
        *figura("07_comparacion_lagos.png",
                "Cuatro vistas de la misma comparación: nivel típico, evolución conjunta, "
                "frecuencia de floración y extensión de la superficie afectada.", estilos),
        Spacer(1, 8),
        tabla_datos(
            ["Lago", "Superficie", "Profundidad<br/>máxima", "Clorofila-a<br/>promedio",
             "Fechas con<br/>floración", "Superficie<br/>afectada (media)"],
            filas, estilos,
            anchos=[2.6 * cm, 2.4 * cm, 2.7 * cm, 2.9 * cm, 2.7 * cm, 3.7 * cm],
        ),
        PageBreak(),
        Paragraph("Interpretación", estilos["h2"]),
        *parrafos(datos["textos"]["comparacion"], estilos),
        PageBreak(),
    ]


def seccion_exploratoria(estilos, datos) -> list:
    elementos = [
        Paragraph("6. Análisis complementario", estilos["h1"]),
        Paragraph(
            "Mirar solo el promedio de un lago puede llevar a conclusiones equivocadas. "
            "Los gráficos siguientes muestran la distribución completa de valores en cada "
            "fecha: cada curva representa una fecha, y cuanto más se desplaza hacia la "
            "derecha, más superficie del lago tiene valores altos. Una curva ancha o con "
            "una cola larga hacia la derecha indica que el lago está desigual, con zonas "
            "buenas y zonas malas al mismo tiempo.",
            estilos["cuerpo"],
        ),
    ]
    for clave in LAGOS:
        elementos += figura(
            f"08_distribuciones_{clave}.png",
            f"{LAGOS[clave]['nombre']}: distribución de valores de clorofila-a en cada fecha.",
            estilos,
        )
    elementos += [
        PageBreak(),
        Paragraph("¿Hay un patrón estacional?", estilos["h2"]),
        *figura("08_patron_estacional.png",
                "Comparación entre la época seca y la época lluviosa. Cada punto es una fecha.",
                estilos),
        Paragraph("Hallazgos", estilos["h2"]),
        *parrafos(datos["textos"]["exploratorio"], estilos),
        PageBreak(),
    ]
    return elementos


def conclusiones(estilos, datos) -> list:
    resumen = {r["lago"]: r for r in datos["resumen_lagos"]}
    at, am = resumen["Atitlan"], resumen["Amatitlan"]

    return [
        Paragraph("7. Conclusiones", estilos["h1"]),
        Paragraph(
            f"<b>Los dos lagos tienen problemas distintos y necesitan respuestas "
            f"distintas.</b> Amatitlán presenta un nivel de fondo alto y sostenido "
            f"({am['chl_medio']:.1f} µg/L de promedio, floración en "
            f"{am['frec_floracion_pct']:.0f} % de las fechas): su problema no es de alerta "
            f"temprana sino de saneamiento de la cuenca, y particularmente del río "
            f"Villalobos. Atitlán presenta un nivel de fondo más bajo "
            f"({at['chl_medio']:.1f} µg/L) con episodios puntuales: su problema sí es de "
            f"vigilancia y respuesta rápida, para detectar los eventos mientras están "
            f"empezando.",
            estilos["cuerpo"],
        ),
        Paragraph(
            "<b>El satélite sirve para vigilar, no para diagnosticar.</b> Estas mediciones "
            "cubren el lago entero cada pocos días y sin costo de campo, lo que ninguna "
            "campaña de muestreo puede igualar. Pero estiman clorofila-a a partir del "
            "color del agua: no distinguen qué especie de cianobacteria hay ni miden "
            "toxinas. La decisión sanitaria sigue necesitando laboratorio.",
            estilos["cuerpo"],
        ),
        Paragraph(
            "<b>La combinación de ambos enfoques es lo que sale a cuenta.</b> Los mapas de "
            "persistencia identifican dónde vale la pena poner los puntos fijos de "
            "muestreo; las series temporales indican en qué momentos del año conviene "
            "aumentar la frecuencia; y cuando una imagen muestra un salto brusco, esa es "
            "la señal para salir a tomar muestras sin esperar al calendario.",
            estilos["cuerpo"],
        ),

        Paragraph("Recomendaciones operativas", estilos["h2"]),
        *[
            Paragraph(t, estilos["vineta"], bulletText="•")
            for t in (
                "Instalar puntos fijos de muestreo en las zonas que los mapas de "
                "persistencia señalan como crónicamente afectadas, en lugar de repartir "
                "los puntos de forma homogénea por el lago.",
                "Procesar cada nueva imagen Sentinel-2 sin nubes en cuanto está disponible "
                "(cada 2 a 5 días) y disparar una alerta cuando el promedio del lago o la "
                "superficie afectada superen su comportamiento habitual.",
                "En Amatitlán, concentrar el esfuerzo de reducción de nutrientes en la "
                "cuenca del río Villalobos, que es donde los mapas muestran la entrada "
                "sostenida de carga.",
                "En Atitlán, priorizar la vigilancia en las bahías cercanas a los núcleos "
                "poblados y en las desembocaduras, y sostener el monitoreo aunque el lago "
                "aparezca limpio: su patrón es episódico, no ausente.",
                "Complementar con datos que el satélite no ve: temperatura del agua, "
                "nutrientes, caudal de los afluentes y descargas de aguas residuales.",
            )
        ],

        Paragraph("Limitaciones de este estudio", estilos["h2"]),
        *[
            Paragraph(t, estilos["vineta"], bulletText="•")
            for t in (
                f"<b>Once fechas por lago.</b> Es suficiente para describir el "
                f"comportamiento general, pero corto para afirmar tendencias de largo "
                f"plazo o estacionalidad con seguridad estadística.",
                "<b>Las nubes sesgan el calendario.</b> Las fechas disponibles son las de "
                "cielo despejado, más frecuentes en la época seca. Si las floraciones "
                "fueran más intensas en días nublados de la época lluviosa, este análisis "
                "las vería poco.",
                "<b>El índice estima, no mide.</b> La conversión de color a µg/L procede de "
                "un ajuste calibrado en otros lagos del mundo. Los valores absolutos deben "
                "tomarse como órdenes de magnitud; las comparaciones entre fechas y entre "
                "zonas, que es lo que sostiene las conclusiones, son mucho más sólidas.",
                "<b>El satélite ve la superficie.</b> Las cianobacterias que se concentran "
                "a un metro de profundidad no se detectan, de modo que las cifras pueden "
                "quedar por debajo de la biomasa real.",
                "<b>Sin validación de campo.</b> No se dispuso de mediciones de laboratorio "
                "simultáneas para contrastar los valores estimados.",
            )
        ],
        PageBreak(),
    ]


def anexo(estilos, datos) -> list:
    return [
        Paragraph("Anexo — Ficha técnica", estilos["h1"]),
        Spacer(1, 4),
        tabla_datos(
            ["Elemento", "Detalle"],
            [
                ("Fuente de datos", "Sentinel-2 (L1C), programa Copernicus de la Agencia "
                                    "Espacial Europea, vía el API de Sentinel Hub en el "
                                    "Copernicus Data Space Ecosystem"),
                ("Índice de cianobacteria", "Script <i>CyanoLakes Chlorophyll-a</i>, "
                                            "Kravitz &amp; Matthews (2020), publicado en "
                                            "custom-scripts.sentinel-hub.com. Detección de "
                                            "agua acreditada a Mohor Gartner"),
                ("Fórmula del NDCI", "(B05 − B04) / (B05 + B04)"),
                ("Conversión a clorofila-a", "826.57·NDCI³ − 176.43·NDCI² + 19·NDCI + 4.071"),
                ("NDVI", "(B08 − B04) / (B08 + B04)"),
                ("NDWI", "(B03 − B08) / (B03 + B08)"),
                ("Resolución espacial", "20 metros por píxel"),
                ("Sistema de coordenadas", "UTM zona 15 N (EPSG:32615)"),
                ("Filtro de nubes", "Probabilidad de nube (s2cloudless) menor al 40 %"),
                ("Umbrales", f"Floración: {UMBRAL_FLORACION:.0f} µg/L · "
                             f"Floración intensa: {UMBRAL_INTENSO:.0f} µg/L"),
                ("Herramientas", "Python con sentinelhub-py, rasterio, geopandas, "
                                 "numpy, pandas, scipy, matplotlib y folium"),
                ("Fecha de proceso", datos["generado"][:10]),
            ],
            estilos,
            anchos=[5 * cm, ANCHO_UTIL - 5 * cm],
        ),
        Spacer(1, 14),
        Paragraph("Productos entregados junto a este informe", estilos["h2"]),
        *[
            Paragraph(t, estilos["vineta"], bulletText="•")
            for t in (
                "<font face='Courier'>outputs/figuras/</font> — todas las figuras del informe "
                "en alta resolución.",
                "<font face='Courier'>outputs/mapas/</font> — mapas interactivos, uno por "
                "lago, que se abren en cualquier navegador.",
                "<font face='Courier'>outputs/tablas/</font> — los datos numéricos en "
                "formato de hoja de cálculo (CSV).",
                "<font face='Courier'>src/</font> — el código completo que produjo estos "
                "resultados, de modo que el análisis pueda repetirse con fechas nuevas.",
            )
        ],
    ]


# --------------------------------------------------------------------------- #
def main() -> int:
    ruta_datos = RAIZ / "informe" / "resultados.json"
    if not ruta_datos.exists():
        print("Faltan los resultados. Corré primero: python -m src.analisis")
        return 1

    datos = json.loads(ruta_datos.read_text(encoding="utf-8"))
    estilos = construir_estilos()

    destino = RAIZ / "informe" / "Informe_Lab4_Cianobacteria_Atitlan_Amatitlan.pdf"
    doc = SimpleDocTemplate(
        str(destino), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2.2 * cm,
        title="Monitoreo satelital de cianobacteria — Atitlán y Amatitlán",
        author=AUTORES,
    )

    historia = (
        portada(estilos, datos)
        + resumen_ejecutivo(estilos, datos)
        + metodologia(estilos, datos)
        + seccion_temporal(estilos, datos)
        + seccion_espacial(estilos, datos)
        + seccion_correlacion(estilos, datos)
        + seccion_comparacion(estilos, datos)
        + seccion_exploratoria(estilos, datos)
        + conclusiones(estilos, datos)
        + anexo(estilos, datos)
    )

    doc.build(historia, onFirstPage=encabezado_pie, onLaterPages=encabezado_pie)
    print(f"Informe -> {destino.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

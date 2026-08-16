"""Genera el documento de trabajo del grupo en PDF.

Es el contenido que debe ir en el documento compartido donde el grupo registra
su proceso: qué se decidió, por qué, en qué orden y con qué evidencia. Se
genera a partir del historial real del repositorio y de los resultados del
análisis, no a mano.

Uso (después de `python -m src.analisis`):
    python -m src.documento_grupo
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.config import RAIZ
from src.informe import (
    ANCHO_UTIL,
    AUTORES,
    AZUL,
    CURSO,
    FONDO_ALERTA,
    LINEA,
    NARANJA,
    TINTA_TENUE,
    construir_estilos,
    pie_de,
    fecha_larga,
    marcar,
    recuadro,
    tabla_datos,
)

REPOSITORIO = "https://github.com/pablouwunya2021/lab4ds"


def historial_git() -> list[tuple[str, str, str]]:
    """Commits del repositorio, del más antiguo al más reciente."""
    salida = subprocess.run(
        ["git", "log", "--pretty=format:%h|%ad|%s", "--date=format:%d/%m/%Y %H:%M",
         "--reverse"],
        cwd=RAIZ, capture_output=True, text=True, check=True,
    ).stdout.strip()
    return [tuple(linea.split("|", 2)) for linea in salida.splitlines() if linea]


def portada(estilos) -> list:
    return [
        Spacer(1, 3.2 * cm),
        Paragraph("Documento de trabajo del grupo", estilos["titulo"]),
        Spacer(1, 0.2 * cm),
        Paragraph(
            "Laboratorio 4 — Análisis de datos geoespaciales<br/>"
            "Monitoreo de cianobacteria en los lagos de Atitlán y Amatitlán",
            estilos["subtitulo"],
        ),
        Spacer(1, 1.2 * cm),
        recuadro(
            "Para qué sirve este documento",
            "Registra <b>cómo</b> se hizo el laboratorio: las decisiones que se tomaron, "
            "por qué se tomaron, qué se probó y descartó, y en qué orden se avanzó. El "
            "informe entregado por separado contiene los <b>resultados</b>; este contiene "
            "el <b>proceso</b>. El historial de cambios verificable está en el "
            "repositorio de código, cuyo registro completo se reproduce en la sección 5.",
            estilos,
        ),
        Spacer(1, 1.3 * cm),
        Paragraph(AUTORES, estilos["subtitulo"]),
        Spacer(1, 0.3 * cm),
        Paragraph(CURSO, estilos["portada_meta"]),
        Paragraph(fecha_larga(date.today()), estilos["portada_meta"]),
        Spacer(1, 0.6 * cm),
        Paragraph(f"Repositorio: {REPOSITORIO}", estilos["portada_meta"]),
        PageBreak(),
    ]


def seccion_enfoque(estilos) -> list:
    return [
        Paragraph("1. Cómo se abordó el laboratorio", estilos["h1"]),
        Paragraph(
            "El enunciado pedía descargar imágenes de Sentinel-2 para dos lagos en once "
            "fechas cada uno, aplicarles el script de detección de cianobacteria de "
            "Sentinel Hub junto con el NDVI y el NDWI, y a partir de ahí hacer un "
            "análisis temporal, uno espacial, uno de correlación y una comparación entre "
            "ambos lagos.",
            estilos["cuerpo"],
        ),
        Paragraph(
            "La decisión estructural del trabajo fue <b>hacer el cálculo de los índices "
            "en la nube y descargar solo el resultado</b>, en lugar de bajar las escenas "
            "completas y procesarlas localmente. Cada petición al API devuelve un archivo "
            "de ocho capas ya calculadas (clorofila-a, NDCI, NDVI, NDWI, índice de algas "
            "flotantes, máscara de agua, probabilidad de nube y máscara de datos "
            "válidos). Esto reduce la descarga a lo estrictamente necesario, que es lo "
            "que pedía el enunciado, y garantiza que el índice se calcule exactamente con "
            "el script publicado y no con una reimplementación propia.",
            estilos["cuerpo"],
        ),
        Paragraph(
            "La segunda decisión fue <b>separar el cálculo de la interpretación</b>. Los "
            "módulos de análisis producen las cifras y además redactan los hallazgos a "
            "partir de esas mismas cifras; el informe se arma leyendo ese resultado. "
            "Así ninguna cifra del informe está escrita a mano, y si se añade una fecha "
            "nueva todo el documento se regenera coherente.",
            estilos["cuerpo"],
        ),

        Paragraph("Estructura del código", estilos["h2"]),
        Spacer(1, 4),
        tabla_datos(
            ["Módulo", "Responsabilidad"],
            [
                ("config.py", "Áreas de interés, fechas oficiales, credenciales y conexión al API"),
                ("evalscripts.py", "Los scripts de Sentinel Hub: cianobacteria, NDVI, NDWI y color real"),
                ("descarga.py", "Ejercicios 1–3: peticiones al API y guardado de los GeoTIFF"),
                ("carga.py", "Limpieza: máscara de agua, filtro de nubes y dominio espacial común"),
                ("temporal.py", "Ejercicio 4: serie por fecha, picos y estacionalidad"),
                ("espacial.py", "Ejercicio 5: mapas por fecha, comparativos, persistencia e interactivos"),
                ("correlacion.py", "Ejercicio 6: relación de NDVI y NDWI con la cianobacteria"),
                ("comparacion.py", "Ejercicio 7: intensidad, frecuencia y causas por lago"),
                ("exploratorio.py", "Ejercicio 8: distribuciones, percentiles y extensión afectada"),
                ("analisis.py", "Orquestador: corre los ejercicios 4 a 8 y vuelca los resultados"),
                ("informe.py", "Genera el informe final en PDF"),
            ],
            estilos,
            anchos=[4.2 * cm, ANCHO_UTIL - 4.2 * cm],
        ),
        PageBreak(),
    ]


def seccion_decisiones(estilos, datos) -> list:
    """Las decisiones de método que cambiaron los resultados, con su evidencia."""
    decisiones = [
        (
            "Usar Sentinel-2 L1C y no L2A",
            "El script de cianobacteria de CyanoLakes está publicado y calibrado para "
            "L1C (reflectancia en el tope de la atmósfera). La primera versión del "
            "trabajo usó L2A (reflectancia de superficie) por ser el nivel habitual en "
            "estudios de calidad de agua.",
            "Al validar la máscara de agua sobre Amatitlán (2026-02-07) se vio que con "
            "L2A el script reconocía como agua 3.6 km² de los 14.8 km² del lago, es "
            "decir el 26 %. La corrección atmosférica deja el agua tan oscura que los "
            "umbrales internos del script (MNDWI > 0.42 y DBSI) dejan de cumplirse. "
            "Con L1C reconoce 14.6 km², el 99 %.",
            "Se cambió toda la descarga a L1C. Como L1C no trae la capa de "
            "clasificación de escena, el filtro de nubes pasó a hacerse con la "
            "probabilidad de nube de s2cloudless, descartando por encima del 40 %.",
        ),
        (
            "Recortar a cero los valores negativos de clorofila-a",
            "El polinomio del script devuelve concentraciones negativas cuando el NDCI "
            "es negativo, que es lo que ocurre en agua muy limpia. La primera versión "
            "los trataba como dato inválido y los descartaba.",
            "Ese descarte eliminaba el 38 % de la superficie de Atitlán en su fecha más "
            "limpia, y lo hacía únicamente por el extremo bajo de la distribución. El "
            "efecto era un sesgo sistemático al alza, concentrado justo en el lago y las "
            "fechas más limpias, que es donde el sesgo cambia las conclusiones.",
            "Los negativos se recortan a cero, que es su lectura física: clorofila por "
            "debajo del límite de detección. La cobertura de Atitlán pasó de 62 % a "
            "100 % y su mediana del 2025-01-18 bajó de 0.81 a 0.33 µg/L.",
        ),
        (
            "Fijar un dominio espacial común a todas las fechas",
            "Cada fecha detecta su propio contorno de agua, que varía con el nivel del "
            "lago, la nubosidad y las condiciones de la superficie.",
            "Si cada fecha se analizara sobre los píxeles que ella misma detecta como "
            "agua, los promedios compararían superficies distintas y los mapas de "
            "diferencia entre fechas no tendrían sentido: una variación del contorno "
            "se leería como un cambio en la floración.",
            "Se define el espejo de agua estable como los píxeles clasificados como agua "
            "en al menos la mitad de las fechas, y todas las fechas del lago se analizan "
            "sobre ese mismo conjunto.",
        ),
        (
            "Medir la persistencia de forma relativa y no absoluta",
            "La primera versión medía las zonas persistentes de acumulación como los "
            "píxeles que superan los 10 µg/L en la mitad o más de las fechas.",
            "Esa definición daba 0 % en ambos lagos, es decir, no respondía la pregunta. "
            "Un umbral absoluto no sirve para esto: en un lago limpio no lo alcanza "
            "nunca nadie y en uno cargado lo alcanzan casi todos; en ambos casos el "
            "resultado es igual de poco informativo.",
            "Se mide en relación a cada fecha: se marca el quinto más afectado del lago "
            "ese día y se cuenta en cuántas fechas cada punto cae dentro de él. Con esa "
            "definición, el 8.1 % de la superficie de Atitlán y el 4.4 % de la de "
            "Amatitlán aparecen ahí en la mitad o más de las fechas, lo que sí revela "
            "una geografía estable del problema.",
        ),
        (
            "Escala de color propia para cada lago",
            "Lo natural para comparar es usar una única escala de color en todos los "
            "mapas.",
            "Atitlán se mueve entre 0 y 2 µg/L y Amatitlán llega a decenas. Con una "
            "escala común, todos los mapas de Atitlán salían en blanco y su estructura "
            "interna era invisible, que es justo lo que el ejercicio 5 pide analizar.",
            "Cada lago usa su propia escala, común a todas sus fechas para que las "
            "fechas sigan siendo comparables entre sí. El informe advierte de forma "
            "explícita que un tono oscuro en un lago no equivale al mismo tono en el "
            "otro, y la comparación entre lagos se hace con cifras.",
        ),
        (
            "Reportar la tendencia de Amatitlán con salvedad",
            "El ajuste lineal sobre las once fechas de Amatitlán da una pendiente de "
            "+3.1 µg/L por año.",
            "De las once fechas de ese lago, solo una cae en época lluviosa, y es la "
            "última de la serie. Es también la fecha con el valor más alto. Con ese "
            "reparto, la tendencia temporal y el efecto estacional son matemáticamente "
            "indistinguibles.",
            "La cifra se reporta, pero acompañada siempre de la advertencia de que no "
            "puede leerse como un empeoramiento real del lago. Lo mismo se aplica a "
            "todo el análisis estacional.",
        ),
    ]

    elementos = [
        Paragraph("2. Decisiones de método y por qué se tomaron", estilos["h1"]),
        Paragraph(
            "Esta sección es el núcleo del documento. Cada entrada describe una decisión "
            "que cambió los resultados, qué evidencia la motivó y cómo se resolvió. "
            "Todas surgieron de revisar resultados intermedios que no cuadraban, no de "
            "planificación previa.",
            estilos["cuerpo"],
        ),
        Spacer(1, 6),
    ]

    for i, (titulo, contexto, hallazgo, resolucion) in enumerate(decisiones, start=1):
        elementos += [
            Paragraph(f"2.{i} {titulo}", estilos["h2"]),
            Paragraph(f"<b>Situación.</b> {contexto}", estilos["cuerpo"]),
            Paragraph(f"<b>Qué se observó.</b> {hallazgo}", estilos["cuerpo"]),
            Paragraph(f"<b>Resolución.</b> {resolucion}", estilos["cuerpo"]),
            Spacer(1, 4),
        ]
        if i == 3:
            elementos.append(PageBreak())

    elementos.append(PageBreak())
    return elementos


def seccion_resultados(estilos, datos) -> list:
    resumen = {r["lago"]: r for r in datos["resumen_lagos"]}
    at, am = resumen["Atitlan"], resumen["Amatitlan"]
    prueba = datos["prueba_diferencia"]

    filas = [
        ("Clorofila-a promedio del período",
         f"{at['chl_medio']:.1f} µg/L", f"{am['chl_medio']:.1f} µg/L"),
        ("Valor más alto de una fecha",
         f"{at['chl_pico']:.1f} µg/L", f"{am['chl_pico']:.1f} µg/L"),
        ("Fechas con floración (promedio > 10 µg/L)",
         f"{int(at['fechas_con_floracion'])} de {int(at['n_fechas'])}",
         f"{int(am['fechas_con_floracion'])} de {int(am['n_fechas'])}"),
        ("Superficie afectada en la peor fecha",
         f"{at['pct_area_alta_max']:.1f} %", f"{am['pct_area_alta_max']:.0f} %"),
        ("Superficie con acumulación persistente", "8.1 %", "4.4 %"),
        ("Coeficiente de variación entre fechas",
         f"{at['coef_variacion']:.2f}", f"{am['coef_variacion']:.2f}"),
        ("Espejo de agua analizado",
         f"{at['area_agua_km2']:.1f} km²", f"{am['area_agua_km2']:.1f} km²"),
    ]

    return [
        Paragraph("3. Resumen de resultados obtenidos", estilos["h1"]),
        Paragraph(
            "Los resultados completos, con sus mapas y gráficos, están en el informe "
            "entregado por separado. Aquí se recogen solo las cifras de referencia.",
            estilos["cuerpo"],
        ),
        Spacer(1, 6),
        tabla_datos(
            ["Indicador", "Atitlán", "Amatitlán"], filas, estilos,
            anchos=[ANCHO_UTIL - 7 * cm, 3.5 * cm, 3.5 * cm],
        ),
        Spacer(1, 10),
        Paragraph(
            f"La diferencia entre ambos lagos se contrastó con una prueba de "
            f"Mann-Whitney (no paramétrica, adecuada para once observaciones por grupo "
            f"sin garantía de normalidad): U = {prueba['u']:.0f}, p = {prueba['p']:.4f}. "
            f"La mediana de Amatitlán es {prueba['razon']:.1f} veces la de Atitlán.",
            estilos["cuerpo"],
        ),
        recuadro(
            "El hallazgo más relevante",
            "El 19 de junio de 2026, el 54 % de la superficie de Amatitlán superó el "
            "umbral de floración, con un promedio de 11.6 µg/L. Es un episodio visible a "
            "simple vista en la imagen en color real, lo que sirve como validación "
            "cualitativa de que el índice está detectando algo físicamente presente y no "
            "un artefacto del procesamiento.",
            estilos, fondo=FONDO_ALERTA, borde=NARANJA,
        ),
        PageBreak(),
    ]


def seccion_reparto(estilos) -> list:
    """Tabla de reparto de trabajo, para que el grupo la complete."""
    tareas = [
        "Configuración del acceso al API y credenciales",
        "Evalscripts y descarga de los rásters (Ej. 1–3)",
        "Limpieza y validación de los datos",
        "Análisis temporal (Ej. 4)",
        "Análisis espacial y mapas (Ej. 5)",
        "Correlación de índices (Ej. 6)",
        "Comparación entre lagos (Ej. 7)",
        "Análisis exploratorio adicional (Ej. 8)",
        "Redacción del informe",
        "Revisión y control de versiones",
    ]
    return [
        Paragraph("4. Reparto del trabajo", estilos["h1"]),
        recuadro(
            "Completar antes de entregar",
            "Esta tabla está en blanco a propósito: el reparto real lo conoce el grupo. "
            "La rúbrica evalúa a cada integrante según sus contribuciones, así que "
            "conviene llenarla con precisión y que coincida con lo que muestra el "
            "historial de commits del repositorio.",
            estilos, fondo=FONDO_ALERTA, borde=NARANJA,
        ),
        Spacer(1, 8),
        tabla_datos(
            ["Tarea", "Responsable", "Observaciones"],
            [(t, "", "") for t in tareas],
            estilos,
            anchos=[ANCHO_UTIL - 7.5 * cm, 3.5 * cm, 4 * cm],
        ),
        PageBreak(),
    ]


def seccion_historial(estilos) -> list:
    commits = historial_git()
    filas = [(h, f, m) for h, f, m in commits]

    return [
        Paragraph("5. Historial de cambios", estilos["h1"]),
        Paragraph(
            f"El historial verificable y con el detalle completo de cada cambio está en "
            f"el repositorio: <font face='Courier' size='9'>{REPOSITORIO}</font>. Cada "
            f"commit incluye en su mensaje la justificación de la decisión tomada y, "
            f"cuando corresponde, las cifras que la motivaron. A continuación, el "
            f"registro resumido.",
            estilos["cuerpo"],
        ),
        Spacer(1, 6),
        tabla_datos(
            ["Versión", "Fecha", "Cambio"], filas, estilos,
            anchos=[2.2 * cm, 3.2 * cm, ANCHO_UTIL - 5.4 * cm],
        ),
        Spacer(1, 12),

        Paragraph("Cómo reproducir el trabajo", estilos["h2"]),
        Paragraph(
            "Cualquier persona con una cuenta gratuita del Copernicus Data Space "
            "Ecosystem puede regenerar el laboratorio completo desde cero con tres "
            "órdenes, tras copiar el archivo <font face='Courier'>.env.example</font> a "
            "<font face='Courier'>.env</font> y rellenarlo con sus credenciales:",
            estilos["cuerpo"],
        ),
        Spacer(1, 4),
        *[
            Paragraph(f"<font face='Courier' size='9'>{c}</font>", estilos["vineta"],
                      bulletText="›")
            for c in (
                "python -m src.descarga    # descarga las 22 imágenes",
                "python -m src.analisis    # figuras, mapas y tablas",
                "python -m src.informe     # informe final en PDF",
            )
        ],
        Spacer(1, 8),
        Paragraph(
            "Las credenciales nunca se versionan: el archivo <font face='Courier'>.env"
            "</font> está excluido del repositorio y se comprobó explícitamente que no "
            "se subió.",
            estilos["cuerpo"],
        ),
        PageBreak(),
    ]


def seccion_pendientes(estilos) -> list:
    entregables = [
        ("Informe en PDF con resultados y explicaciones", "Entregado",
         "Informe_Lab4_Cianobacteria_Atitlan_Amatitlan.pdf, 24 páginas, dirigido a "
         "lectores sin conocimientos de programación"),
        ("Script de Python usado para el análisis", "Entregado",
         "11 módulos en src/, documentados y reproducibles"),
        ("Link del repositorio usado para versionar", "Entregado", REPOSITORIO),
        ("Link del documento de trabajo del grupo", "Por completar",
         "Este documento es su contenido; falta subirlo a un documento compartido y "
         "completar el reparto de la sección 4"),
    ]

    return [
        Paragraph("6. Estado de los entregables", estilos["h1"]),
        Spacer(1, 4),
        tabla_datos(
            ["Entregable", "Estado", "Detalle"],
            entregables, estilos,
            anchos=[5.5 * cm, 2.6 * cm, ANCHO_UTIL - 8.1 * cm],
        ),
        Spacer(1, 14),

        Paragraph("7. Qué se dejó fuera y por qué", estilos["h1"]),
        *[
            Paragraph(t, estilos["vineta"], bulletText="•")
            for t in (
                "<b>Validación con muestras de campo.</b> No se dispuso de mediciones de "
                "laboratorio simultáneas a las fechas de las imágenes, así que los "
                "valores absolutos de clorofila-a no pudieron contrastarse. La "
                "validación fue cualitativa: comprobar que lo que el índice marca como "
                "floración se ve en la imagen en color real.",
                "<b>Variables ambientales complementarias.</b> Temperatura del agua, "
                "nutrientes y caudal de los afluentes habrían permitido explicar las "
                "causas de cada episodio, pero quedan fuera de lo que ofrece Sentinel-2.",
                "<b>Serie temporal más larga.</b> El enunciado fijó once fechas por "
                "lago. Es suficiente para describir el comportamiento general, pero "
                "corto para afirmar tendencias de largo plazo o estacionalidad con "
                "seguridad estadística, cosa que el informe señala explícitamente en "
                "vez de dar por buenas las pendientes calculadas.",
                "<b>Otros índices de calidad de agua.</b> Se consideró añadir el índice "
                "de sólidos suspendidos y el de turbidez para separar mejor la biomasa "
                "de los sedimentos, pero el enunciado acotaba el trabajo al índice de "
                "cianobacteria más NDVI y NDWI, y se respetó ese alcance.",
            )
        ],
    ]


def main() -> int:
    ruta_datos = RAIZ / "informe" / "resultados.json"
    if not ruta_datos.exists():
        print("Faltan los resultados. Corré primero: python -m src.analisis")
        return 1

    datos = json.loads(ruta_datos.read_text(encoding="utf-8"))
    estilos = construir_estilos()

    destino = RAIZ / "informe" / "Documento_de_trabajo_del_grupo.pdf"
    doc = SimpleDocTemplate(
        str(destino), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2.2 * cm,
        title="Documento de trabajo del grupo — Laboratorio 4",
        author=AUTORES,
    )

    historia = (
        portada(estilos)
        + seccion_enfoque(estilos)
        + seccion_decisiones(estilos, datos)
        + seccion_resultados(estilos, datos)
        + seccion_reparto(estilos)
        + seccion_historial(estilos)
        + seccion_pendientes(estilos)
    )

    pie = pie_de("Documento de trabajo del grupo — Laboratorio 4")
    doc.build(historia, onFirstPage=pie, onLaterPages=pie)
    print(f"Documento de trabajo -> {destino.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

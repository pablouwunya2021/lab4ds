"""Genera el informe Parte 2 exclusivamente desde artefactos reproducibles."""
from __future__ import annotations

from datetime import date

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                               Table, TableStyle)

from src.config import DIR_PARTE2_METRICS, DIR_PARTE2_TABLES, RAIZ

OUTPUT = RAIZ / "informe" / "Informe_Lab4_Parte2_Cianobacteria.pdf"
AUTHORS = "Pablo Cabrera · Luis Mendoza"


def _table(df, max_rows=30):
    shown = df.head(max_rows).copy()
    data = [list(shown.columns)] + [[str(v) for v in row] for row in shown.itertuples(index=False)]
    table = Table(data, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#124559")),
                               ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                               ("FONTSIZE", (0, 0), (-1, -1), 7),
                               ("GRID", (0, 0), (-1, -1), .25, colors.grey),
                               ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return table


def main() -> int:
    required = [DIR_PARTE2_METRICS / "random_metrics.csv",
                DIR_PARTE2_METRICS / "validation_metrics_by_fold.csv",
                DIR_PARTE2_TABLES / "predictor_audit.csv",
                DIR_PARTE2_TABLES / "filter_log.csv"]
    missing = [p for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError("No se genera un PDF incompleto. Ejecute primero: python -m src.parte2")
    random = pd.read_csv(required[0]); validations = pd.read_csv(required[1])
    audit = pd.read_csv(required[2]); filters = pd.read_csv(required[3])
    styles = getSampleStyleSheet(); styles.add(ParagraphStyle("Center", parent=styles["Title"], alignment=TA_CENTER))
    story = [Spacer(1, 1.4*inch), Paragraph("Laboratorio 4 · Parte 2", styles["Center"]),
             Paragraph("Clasificación geoespacial de alta presencia de cianobacteria", styles["Center"]),
             Spacer(1, .5*inch), Paragraph(AUTHORS, styles["Center"]),
             Paragraph("CC3084 Data Science · UVG · Semestre II 2026", styles["Center"]),
             Paragraph(str(date.today()), styles["Center"]), PageBreak()]
    sections = [
        ("Objetivos y alcance", "Se desarrollan tres clasificadores y se contrastan evaluaciones aleatoria, espacial, temporal y entre lagos. La respuesta es una categoría operativa derivada de un proxy satelital; no mide toxicidad ni sustituye muestreo de campo."),
        ("Preparación y limpieza", "Cada fila conserva lago, fecha, celda raster, coordenadas WGS84/UTM 15N y metadatos. Todos los descartes se registran; no se eliminan observaciones silenciosamente."),
        ("Linaje de la respuesta", "NDCI=(B05−B04)/(B05+B04); clorofila-a proxy=826.57·NDCI³−176.43·NDCI²+19·NDCI+4.071; categoría alta=1 si proxy≥10 µg/L. El corte no equivale a concentración de cianobacterias ni riesgo toxicológico confirmado."),
        ("Modelos e hiperparámetros", "Regresión logística, Random Forest e HistGradientBoosting se implementan en pipelines. La búsqueda usa solo entrenamiento, PR-AUC como criterio y un test 30% común que no participa en decisiones."),
        ("Criterio ambiental", "La selección prioriza capacidad de recuperar la clase positiva mediante PR-AUC y recall, examinando precisión para limitar falsas alarmas. Los falsos negativos pueden retrasar verificación de campo; los falsos positivos consumen recursos operativos."),
        ("Limitaciones", "Once fechas por lago, autocorrelación, dominio espectral distinto, nubes y una respuesta construida del mismo sensor limitan inferencia y generalización. Importancia no implica causalidad. Se requiere validación in situ de clorofila, composición taxonómica y toxinas."),
        ("Referencias", "Mishra & Mishra (2012), DOI 10.1016/j.rse.2011.10.016. WHO (2021), Guidelines on recreational water quality, ISBN 9789240031302. US EPA (2019), Recommendations for Cyanobacteria and Cyanotoxin Monitoring in Recreational Waters. Kravitz & Matthews (2020), CyanoLakes custom script."),
        ("Reproducibilidad", "Comandos: python -m src.descarga --ml; python -m src.parte2; pytest -q; jupyter nbconvert --execute --to notebook --inplace notebooks/laboratorio4_parte2.ipynb; python -m src.informe_parte2."),
    ]
    for title, body in sections[:3]:
        story += [Paragraph(title, styles["Heading1"]), Paragraph(body, styles["BodyText"]), Spacer(1, 12)]
    story += [Paragraph("Auditoría de predictores", styles["Heading2"]), _table(audit),
              PageBreak(), Paragraph("Bitácora de filtros", styles["Heading1"]), _table(filters),
              PageBreak(), Paragraph("Evaluación 70/30", styles["Heading1"]), _table(random.round(4)),
              Paragraph("Validaciones espacial, temporal y entre lagos", styles["Heading1"]),
              _table(validations.round(4))]
    for title, body in sections[3:]:
        story += [Paragraph(title, styles["Heading1"]), Paragraph(body, styles["BodyText"]), Spacer(1, 12)]
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=letter, rightMargin=45, leftMargin=45,
                            topMargin=45, bottomMargin=45, title="Laboratorio 4 Parte 2", author=AUTHORS)
    doc.build(story); print(OUTPUT); return 0


if __name__ == "__main__":
    raise SystemExit(main())

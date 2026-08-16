"""Orquestador de los ejercicios 4 a 8.

Carga los rásters descargados, corre cada análisis en orden y deja en
`outputs/` las figuras, los mapas y las tablas, más un archivo de hallazgos en
`informe/hallazgos.md` con los textos interpretativos ya redactados sobre los
números reales (que es la base del informe final).

Uso:
    python -m src.analisis
"""

from __future__ import annotations

import sys
from datetime import datetime

from src import comparacion, correlacion, espacial, exploratorio, temporal
from src.carga import cargar_lago
from src.config import DIR_MAPAS, LAGOS, RAIZ
from src.estilo import aplicar_estilo


def main() -> int:
    aplicar_estilo()

    print("Cargando rásters")
    escenas_por_lago = {}
    for clave in LAGOS:
        escenas = cargar_lago(clave)
        if not escenas:
            print(f"ERROR: no hay rásters utilizables de {clave}. "
                  "Corré primero: python -m src.descarga")
            return 1
        escenas_por_lago[clave] = escenas
        print(f"  {LAGOS[clave]['nombre']}: {len(escenas)} fechas utilizables")

    print("\nEjercicio 4 — análisis temporal")
    serie = temporal.ejecutar(escenas_por_lago)
    texto_temporal = temporal.interpretar(serie)

    print("\nEjercicio 5 — análisis espacial")
    persistencias = espacial.ejecutar(escenas_por_lago)
    texto_espacial = "\n\n".join(
        espacial.interpretar(clave, escenas_por_lago[clave], persistencias[clave])
        for clave in LAGOS
    )

    print("\nEjercicio 6 — correlación de índices")
    _, corr_pixel, corr_fecha = correlacion.ejecutar(escenas_por_lago, serie)
    texto_correlacion = correlacion.interpretar(corr_pixel, corr_fecha)

    print("\nEjercicio 7 — comparación entre lagos")
    resumen, prueba = comparacion.ejecutar(serie)
    texto_comparacion = comparacion.interpretar(resumen, prueba, serie)

    print("\nEjercicio 8 — análisis exploratorio adicional")
    percentiles = exploratorio.ejecutar(escenas_por_lago, serie)
    texto_exploratorio = exploratorio.interpretar(serie, percentiles)

    destino = RAIZ / "informe" / "hallazgos.md"
    destino.write_text(
        "\n".join(
            [
                "# Hallazgos generados automáticamente",
                "",
                f"_Generado el {datetime.now():%Y-%m-%d %H:%M} a partir de "
                f"{sum(len(v) for v in escenas_por_lago.values())} imágenes Sentinel-2._",
                "",
                "## Ejercicio 4 — Análisis temporal", "", texto_temporal, "",
                "## Ejercicio 5 — Análisis espacial", "", texto_espacial, "",
                "## Ejercicio 6 — Correlación con NDVI y NDWI", "", texto_correlacion, "",
                "## Ejercicio 7 — Comparación entre lagos", "", texto_comparacion, "",
                "## Ejercicio 8 — Análisis exploratorio adicional", "", texto_exploratorio, "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"\nHallazgos -> {destino.relative_to(RAIZ)}")
    print(f"Mapas interactivos -> {DIR_MAPAS.relative_to(RAIZ)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

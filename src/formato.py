"""Formato de cifras para los textos y el informe.

Escribir "0.0 %" cuando el valor no es exactamente cero engaña al lector, y
escribirlo cuando sí lo es se lee como un redondeo dudoso. Estas funciones
resuelven ambos casos de una sola forma en todo el proyecto.
"""

from __future__ import annotations


def pct(valor: float, decimales: int = 1) -> str:
    """Porcentaje legible."""
    if valor == 0:
        return "0 %"
    if 0 < valor < 0.05:
        return "menos del 0.1 %"
    return f"{valor:.{decimales}f} %"

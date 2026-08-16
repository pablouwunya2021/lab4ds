# Laboratorio 4 — Análisis de datos geoespaciales

**CC3084 Data Science · Universidad del Valle de Guatemala · Semestre II 2026**

Monitoreo de floraciones de **cianobacteria** en el **lago de Atitlán** y el
**lago de Amatitlán** a partir de imágenes **Sentinel-2** del programa Copernicus,
accedidas mediante el API de **Sentinel Hub**.

## Cómo reproducir el análisis

### 1. Instalar dependencias

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Configurar credenciales

Se necesita una cuenta gratuita del [Copernicus Data Space Ecosystem](https://dataspace.copernicus.eu)
y un cliente OAuth creado desde el
[dashboard de Sentinel Hub](https://shapps.dataspace.copernicus.eu/dashboard/#/account/settings).

```bash
cp .env.example .env    # y llenar SH_CLIENT_ID y SH_CLIENT_SECRET
```

El archivo `.env` está en `.gitignore`: las credenciales nunca se versionan.

### 3. Descargar los rásters y correr el análisis

```bash
.venv/bin/python -m src.descarga --probar   # verifica la conexión con el API
.venv/bin/python -m src.descarga            # descarga los rásters
.venv/bin/python -m src.analisis            # genera figuras, mapas y tablas
```

## Estructura

| Ruta | Contenido |
|---|---|
| `src/config.py` | Rutas, áreas de interés, fechas oficiales y conexión al API |
| `src/evalscripts.py` | Scripts personalizados de Sentinel Hub (cianobacteria, NDVI, NDWI) |
| `src/descarga.py` | Ejercicios 1–3: conexión y descarga de rásters |
| `src/analisis.py` | Ejercicios 4–8: análisis temporal, espacial, correlación y comparación |
| `data/geojson/` | Polígonos de los dos lagos |
| `data/raw/` | GeoTIFF descargados (no versionados: se regeneran con `src/descarga.py`) |
| `outputs/` | Figuras, mapas interactivos y tablas de resultados |
| `informe/` | Informe final en PDF |

## Datos

- **Misión:** Sentinel-2 **L1C** (reflectancia en el tope de la atmósfera), que es el
  nivel para el que fue calibrado el script de cianobacteria. Se verificó que sobre
  L2A el detector de agua del script solo reconoce el 26 % del lago de Amatitlán,
  frente al 99 % sobre L1C (ver la nota en `src/config.py`).
- **Resolución de trabajo:** 20 m
- **Fechas:** las 11 fechas oficiales por lago indicadas en el enunciado
- **Índice de cianobacteria:** script
  [CyanoLakes Chlorophyll-a](https://custom-scripts.sentinel-hub.com/custom-scripts/sentinel-2/cyanobacteria_chla_ndci_l1c/)
  (Kravitz & Matthews, 2020), basado en el NDCI del borde rojo
- **NDVI:** `(B08 − B04) / (B08 + B04)`
- **NDWI:** `(B03 − B08) / (B03 + B08)`

"""Evalscripts (scripts personalizados de Sentinel Hub) usados en el laboratorio.

Se usan dos variantes del mismo script de detección de cianobacteria:

* `EVALSCRIPT_INDICES` devuelve los índices como **valores numéricos** en un
  GeoTIFF multibanda, que es lo que permite hacer estadística y mapas propios.
* `EVALSCRIPT_CYANO_RGB` es el script original de CyanoLakes, que devuelve la
  imagen ya coloreada tal y como se ve en el Copernicus Browser. Se descarga
  para poder mostrar en el informe la misma vista que produce Sentinel Hub.

Fuente del script de cianobacteria:
https://custom-scripts.sentinel-hub.com/custom-scripts/sentinel-2/cyanobacteria_chla_ndci_l1c/
"CyanoLakes Chlorophyll-a" — Jeremy Kravitz & Mark Matthews (2020).
Detección de cuerpos de agua acreditada a Mohor Gartner.

Nota metodológica: el script se aplica sobre Sentinel-2 **L1C**, que es el
nivel de procesamiento para el que fue publicado y calibrado. Ver la nota en
`config.py` sobre por qué L2A no funciona con este detector de agua.
"""

# Entrada común a ambos scripts. Las bandas ópticas se piden en reflectancia
# (que es lo que esperan las fórmulas del script); la probabilidad de nube
# (CLP, de s2cloudless) es una capa auxiliar que el API sirve en su escala
# original de 0 a 255.
_ENTRADA = """{
    bands: ["B02","B03","B04","B05","B07","B08","B8A","B11","B12","CLP","dataMask"],
    units: ["REFLECTANCE","REFLECTANCE","REFLECTANCE","REFLECTANCE","REFLECTANCE",
            "REFLECTANCE","REFLECTANCE","REFLECTANCE","REFLECTANCE","DN","DN"]
  }"""

# Bloque compartido: detección de agua, FAI, NDCI y clorofila-a.
_NUCLEO_CYANO = """
// ---- Detección de cuerpos de agua — crédito Mohor Gartner ----
var MNDWI_threshold = 0.42;
var NDWI_threshold  = 0.4;
var filter_UABS = true;

function wbi(r, g, b, nir, swir1, swir2) {
  let ws = 0;
  try {
    var ndvi   = (nir - r) / (nir + r),
        mndwi  = (g - swir1) / (g + swir1),
        ndwi   = (g - nir) / (g + nir),
        ndwi_leaves = (nir - swir1) / (nir + swir1),
        aweish = b + 2.5 * g - 1.5 * (nir + swir1) - 0.25 * swir2,
        aweinsh = 4 * (g - swir1) - (0.25 * nir + 2.75 * swir1);
    var dbsi = ((swir1 - g) / (swir1 + g)) - ndvi;
    if (mndwi > MNDWI_threshold || ndwi > NDWI_threshold ||
        aweinsh > 0.1879 || aweish > 0.1112 || ndvi < -0.2 ||
        ndwi_leaves > 1) { ws = 1; }
    if (filter_UABS && ws == 1) {
      if ((aweinsh <= -0.03) || (dbsi > 0)) { ws = 0; }
    }
  } catch (err) { ws = 0; }
  return ws;
}

// ---- Vegetación flotante (Floating Algae Index) ----
function FAI(a, b, c) { return (b - a - (c - a) * (783 - 665) / (865 - 665)); }

// ---- Clorofila-a a partir del NDCI (borde rojo) ----
function NDCI(a, b) { return (b - a) / (b + a); }
"""

# --------------------------------------------------------------------------- #
# 1) Índices numéricos (el que alimenta todo el análisis)
# --------------------------------------------------------------------------- #
EVALSCRIPT_INDICES = f"""//VERSION=3
// Devuelve los índices como valores numéricos para análisis posterior.
function setup() {{
  return {{
    input: [{_ENTRADA}],
    output: {{ id: "default", bands: 8, sampleType: "FLOAT32" }}
  }};
}}
{_NUCLEO_CYANO}
function evaluatePixel(s) {{
  let agua  = wbi(s.B04, s.B03, s.B02, s.B08, s.B11, s.B12);
  let faiv  = FAI(s.B04, s.B07, s.B8A);
  let ndciv = NDCI(s.B04, s.B05);
  let chl   = 826.57 * Math.pow(ndciv, 3) - 176.43 * Math.pow(ndciv, 2)
              + 19 * ndciv + 4.071;
  let ndvi  = (s.B08 - s.B04) / (s.B08 + s.B04);
  let ndwi  = (s.B03 - s.B08) / (s.B03 + s.B08);

  // Banda 1: clorofila-a (ug/L) — proxy de biomasa de cianobacteria
  // Banda 2: NDCI          Banda 3: NDVI        Banda 4: NDWI
  // Banda 5: FAI (algas flotantes)              Banda 6: máscara de agua 0/1
  // Banda 7: CLP (probabilidad de nube 0-255, para filtrar nubes)
  // Banda 8: dataMask (1 = píxel con dato válido)
  return [chl, ndciv, ndvi, ndwi, faiv, agua, s.CLP, s.dataMask];
}}
"""

# --------------------------------------------------------------------------- #
# 2) Visualización original de CyanoLakes (RGB tal cual el Copernicus Browser)
# --------------------------------------------------------------------------- #
EVALSCRIPT_CYANO_RGB = f"""//VERSION=3
// Script original "CyanoLakes Chlorophyll-a" con su rampa de color.
function setup() {{
  return {{
    input: [{_ENTRADA}],
    output: {{ id: "default", bands: 3, sampleType: "AUTO" }}
  }};
}}
{_NUCLEO_CYANO}
function evaluatePixel(s) {{
  let water = wbi(s.B04, s.B03, s.B02, s.B08, s.B11, s.B12);
  let FAIv  = FAI(s.B04, s.B07, s.B8A);
  let NDCIv = NDCI(s.B04, s.B05);
  let chl   = 826.57 * Math.pow(NDCIv, 3) - 176.43 * Math.pow(NDCIv, 2)
              + 19 * NDCIv + 4.071;
  let trueColor = [3 * s.B04, 3 * s.B03, 3 * s.B02];

  if (water == 0)      return trueColor;
  if (FAIv > 0.08)     return [233/255,  72/255,  21/255];
  if (chl <  1)        return [0, 0, 1.0];
  if (chl <  2.5)      return [0,  59/255, 1];
  if (chl <  3.5)      return [0,  98/255, 1];
  if (chl <  5)        return [ 15/255, 113/255, 141/255];
  if (chl <  7)        return [ 14/255, 141/255, 120/255];
  if (chl <  8)        return [ 13/255, 141/255, 103/255];
  if (chl < 14)        return [ 30/255, 226/255,  28/255];
  if (chl < 18)        return [ 68/255, 226/255,  28/255];
  if (chl < 24)        return [134/255, 247/255,   0];
  if (chl < 30)        return [140/255, 247/255,   0];
  if (chl < 45)        return [205/255, 237/255,   0];
  if (chl < 50)        return [251/255, 210/255,   3/255];
  if (chl < 90)        return [248/255, 207/255,   2/255];
  if (chl < 150)       return [245/255, 164/255,   9/255];
  if (chl < 300)       return [237/255, 157/255,   7/255];
  if (chl < 450)       return [239/255, 101/255,  15/255];
  return [233/255, 72/255, 21/255];
}}
"""

# --------------------------------------------------------------------------- #
# 3) Color verdadero, para contexto visual en el informe
# --------------------------------------------------------------------------- #
EVALSCRIPT_RGB = """//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B02","B03","B04","dataMask"], units: "REFLECTANCE" }],
    output: { bands: 3, sampleType: "AUTO" }
  };
}
function evaluatePixel(s) {
  return [3.0 * s.B04, 3.0 * s.B03, 3.0 * s.B02];
}
"""

# Índice de cada banda dentro del GeoTIFF que produce EVALSCRIPT_INDICES.
BANDAS_INDICES = {
    "chl": 1,       # clorofila-a (ug/L) — proxy de cianobacteria
    "ndci": 2,
    "ndvi": 3,
    "ndwi": 4,
    "fai": 5,
    "agua": 6,
    "clp": 7,
    "datamask": 8,
}

# Umbral de nubosidad sobre la banda CLP (probabilidad de nube de s2cloudless,
# escalada de 0 a 255). 102 equivale a un 40 % de probabilidad: por encima de
# eso el píxel se descarta. Es un corte conservador — sobre agua limpia la CLP
# medida ronda 1, así que descarta nubes reales sin comerse el lago.
CLP_MAXIMO = 102

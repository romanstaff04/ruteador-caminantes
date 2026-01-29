"""import subprocess
import sys
import os

BASE_DIR = os.path.dirname(__file__)
APP_REAL = os.path.join(BASE_DIR, "ruteoprueba.py")

subprocess.run([
    sys.executable,
    "-m", "streamlit", "run", APP_REAL,
])"""
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Ruteador Caminantes", layout="wide")

st.title("📍 Ruteador Centralizado de Caminantes")

# =========================
# SUBIDA DE ARCHIVO
# =========================
archivo = st.file_uploader(
    "📤 Subí el archivo Excel de caminantes",
    type=["xlsx"]
)

if archivo is None:
    st.info("Esperando que subas un archivo Excel...")
    st.stop()

# =========================
# LECTURA DEL EXCEL
# =========================
df = pd.read_excel(archivo, dtype={"Equipo": str})
df["Equipo"] = df["Equipo"].astype(str).str.replace(r"\.0$", "", regex=True)

df = df.dropna(subset=["Latitud", "Longitud"]).copy()

# =========================
# CONSOLIDAR EQUIPOS
# =========================
df_grouped = (
    df.groupby(["Latitud", "Longitud"])["Equipo"]
    .apply(lambda x: ", ".join(sorted(set(x))))
    .reset_index()
)

coord_map = {
    (row["Latitud"], row["Longitud"]): row["Equipo"]
    for _, row in df_grouped.iterrows()
}

# =========================
# SESIÓN
# =========================
if "seleccionados" not in st.session_state:
    st.session_state.seleccionados = []
    st.session_state.ruta_coords = []

# =========================
# MAPA
# =========================
m = folium.Map(
    location=[df["Latitud"].mean(), df["Longitud"].mean()],
    zoom_start=12
)

for lat, lng, equipos in zip(
    df_grouped["Latitud"],
    df_grouped["Longitud"],
    df_grouped["Equipo"]
):
    folium.CircleMarker(
        location=[lat, lng],
        radius=6,
        color="blue",
        fill=True,
        fill_opacity=0.8,
        tooltip=equipos
    ).add_to(m)

if len(st.session_state.ruta_coords) >= 2:
    folium.PolyLine(
        locations=st.session_state.ruta_coords,
        color="red",
        weight=4
    ).add_to(m)

mapa = st_folium(m, width=900, height=600)

# =========================
# CLICK EN MAPA
# =========================
if mapa and mapa.get("last_object_clicked"):
    lat = mapa["last_object_clicked"]["lat"]
    lng = mapa["last_object_clicked"]["lng"]

    eq = coord_map.get((lat, lng))
    if eq and eq not in st.session_state.seleccionados:
        st.session_state.seleccionados.append(eq)
        st.session_state.ruta_coords.append((lat, lng))

# =========================
# SIDEBAR
# =========================
st.sidebar.header("🧭 Ruta seleccionada")

for i, eq in enumerate(st.session_state.seleccionados, start=1):
    st.sidebar.write(f"{i}. {eq}")

# =========================
# EXPORTAR
# =========================
if st.sidebar.button("📥 Descargar ruta"):
    if st.session_state.seleccionados:
        salida = []

        for orden, (eq, (lat, lng)) in enumerate(
            zip(st.session_state.seleccionados, st.session_state.ruta_coords),
            start=1
        ):
            for e in eq.split(","):
                salida.append({
                    "Orden": orden,
                    "Equipo": e.strip(),
                    "Latitud": lat,
                    "Longitud": lng
                })

        out_df = pd.DataFrame(salida)
        st.download_button(
            "⬇️ Descargar Excel",
            out_df.to_excel(index=False),
            file_name="ruta.xlsx"
        )

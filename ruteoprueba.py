import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import glob

# Definir carpeta Ruteador/viajes en el escritorio
carpeta_ruteador = os.path.join(os.path.expanduser("~"), "Desktop", "Ruteador")
carpeta_viajes = os.path.join(carpeta_ruteador, "viajes")
os.makedirs(carpeta_viajes, exist_ok=True)

# Cargar datos una sola vez
if "con_geo" not in st.session_state:
    entrada = os.path.join(carpeta_ruteador, "caminantes.xlsx")
    df = pd.read_excel(entrada, dtype={"Equipo": str}, engine="openpyxl")
    df["Equipo"] = df["Equipo"].astype(str).str.replace(r"\.0$", "", regex=True)
    df = df.dropna(subset=["Latitud", "Longitud"]).copy()
    st.session_state.con_geo = df

    # Consolidar equipos con misma geo
    df_grouped = (
        df.groupby(["Latitud", "Longitud"])["Equipo"]
        .apply(lambda x: ", ".join(sorted(set(x))))
        .reset_index()
    )
    st.session_state.consolidado = df_grouped

    # Diccionario para búsquedas rápidas
    st.session_state.coord_map = {
        (row["Latitud"], row["Longitud"]): row["Equipo"]
        for _, row in df_grouped.iterrows()
    }

# Inicializar variables de sesión
for key, default in {
    "seleccionados": [],
    "ruta_coords": [],
    "ruta_coords_fija": [],
    "map_center": [
        st.session_state.con_geo["Latitud"].mean(),
        st.session_state.con_geo["Longitud"].mean()
    ],
    "map_zoom": 12,
    "ruta_dibujada": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.title("Programa de Ruteo Centralizado Caminantes")

# Botón para actualizar la ruta
if st.sidebar.button("Actualizar ruta") and len(st.session_state.ruta_coords) >= 2:
    st.session_state.ruta_coords_fija = st.session_state.ruta_coords.copy()
    st.session_state.ruta_dibujada = True

# Crear mapa
m = folium.Map(
    location=st.session_state.map_center,
    zoom_start=st.session_state.map_zoom,
    tiles="OpenStreetMap"
)

# Dibujar marcadores consolidados
for lat, lng, equipos in zip(
    st.session_state.consolidado["Latitud"],
    st.session_state.consolidado["Longitud"],
    st.session_state.consolidado["Equipo"]
):
    folium.CircleMarker(
        location=[lat, lng],
        radius=5,
        color="blue",
        fill=True,
        fill_color="blue",
        tooltip=equipos
    ).add_to(m)

# Dibujar la ruta
if st.session_state.ruta_dibujada and len(st.session_state.ruta_coords_fija) >= 2:
    folium.PolyLine(
        locations=st.session_state.ruta_coords_fija,
        color="red",
        weight=3,
        opacity=0.8
    ).add_to(m)

# Capturar clics
mapa = st_folium(
    m,
    width=800,
    height=600,
    returned_objects=["last_object_clicked"]
)

if mapa and mapa.get("last_object_clicked"):
    click_lat = mapa["last_object_clicked"]["lat"]
    click_lng = mapa["last_object_clicked"]["lng"]

    eq_nombre = st.session_state.coord_map.get((click_lat, click_lng))
    if eq_nombre:
        if eq_nombre in st.session_state.seleccionados:
            idx = st.session_state.seleccionados.index(eq_nombre)
            st.session_state.seleccionados.pop(idx)
            st.session_state.ruta_coords.pop(idx)
        else:
            st.session_state.seleccionados.append(eq_nombre)
            st.session_state.ruta_coords.append((click_lat, click_lng))

# Sidebar selección
st.sidebar.header("Selección actual")
if st.session_state.seleccionados:
    for i, eq in reversed(list(enumerate(st.session_state.seleccionados, start=1))):
        st.sidebar.write(f"{i}. {eq}")
else:
    st.sidebar.write("No hay elementos seleccionados aún.")

# Cambiar orden
if st.session_state.seleccionados:
    equipo_a_mover = st.sidebar.selectbox("Cambiar orden de:", st.session_state.seleccionados)
    nueva_pos = st.sidebar.number_input(
        "Nueva posición:",
        min_value=1,
        max_value=len(st.session_state.seleccionados),
        value=st.session_state.seleccionados.index(equipo_a_mover) + 1
    )
    if st.sidebar.button("Reordenar"):
        idx = st.session_state.seleccionados.index(equipo_a_mover)
        coord = st.session_state.ruta_coords.pop(idx)
        st.session_state.seleccionados.pop(idx)
        st.session_state.seleccionados.insert(nueva_pos - 1, equipo_a_mover)
        st.session_state.ruta_coords.insert(nueva_pos - 1, coord)
        st.sidebar.success(f"Equipo '{equipo_a_mover}' movido a la posición {nueva_pos}.")

# Guardado de rutas con expansión de equipos
st.sidebar.write("---")
ruta_num = st.sidebar.text_input("Número de ruta para guardar:", "")
if st.sidebar.button("Guardar ruta en Excel"):
    if st.session_state.seleccionados and ruta_num.strip():
        equipos_expandidos = []
        latitudes = []
        longitudes = []

        for eq, (lat, lng) in zip(st.session_state.seleccionados, st.session_state.ruta_coords):
            eqs = [e.strip() for e in eq.split(",")]
            for e in eqs:
                equipos_expandidos.append(e)
                latitudes.append(lat)
                longitudes.append(lng)

        ruta_df = pd.DataFrame({
            "Ruta": [ruta_num] * len(equipos_expandidos),
            "Orden": list(range(1, len(equipos_expandidos) + 1)),
            "Equipo": equipos_expandidos,
            "Latitud": latitudes,
            "Longitud": longitudes,
        })
        archivo = os.path.join(carpeta_viajes, f"ruta_{ruta_num}.xlsx")
        ruta_df.to_excel(archivo, index=False)
        st.sidebar.success(f"Ruta guardada en: {archivo}")

        # Filtrar equipos ya ruteados
        equipos_guardados = set(equipos_expandidos)
        st.session_state.con_geo = st.session_state.con_geo[
            ~st.session_state.con_geo["Equipo"].isin(equipos_guardados)
        ].copy()

        # Recalcular consolidado
        df_grouped = (
            st.session_state.con_geo
            .groupby(["Latitud", "Longitud"])["Equipo"]
            .apply(lambda x: ", ".join(sorted(set(x))))
            .reset_index()
        )
        st.session_state.consolidado = df_grouped
        st.session_state.coord_map = {
            (row["Latitud"], row["Longitud"]): row["Equipo"]
            for _, row in df_grouped.iterrows()
        }

        # Vaciar selección y ruta
        st.session_state.seleccionados.clear()
        st.session_state.ruta_coords.clear()
        st.session_state.ruta_coords_fija.clear()
        st.session_state.ruta_dibujada = False

        # Forzar actualización inmediata del mapa
        st.rerun()
    else:
        st.sidebar.error("Debe seleccionar equipos y asignar un número de ruta.")

# Menú de viajes guardados
st.sidebar.write("---")
st.sidebar.subheader("Viajes guardados")

rutas_guardadas = glob.glob(os.path.join(carpeta_viajes, "ruta_*.xlsx"))

if rutas_guardadas:
    ruta_seleccionada = st.sidebar.selectbox(
        "Seleccionar un viaje:", rutas_guardadas, format_func=os.path.basename
    )

    if st.sidebar.button("Cargar viaje"):
        ruta_df = pd.read_excel(ruta_seleccionada, engine="openpyxl")
        st.write("Viaje cargado:", ruta_df)

        st.session_state.seleccionados = ruta_df["Equipo"].astype(str).tolist()
        st.session_state.ruta_coords = list(zip(ruta_df["Latitud"], ruta_df["Longitud"]))
        st.session_state.ruta_coords_fija = st.session_state.ruta_coords.copy()
        st.session_state.ruta_dibujada = True

        st.sidebar.success(f"Viaje {os.path.basename(ruta_seleccionada)} cargado en el mapa.")
else:
    st.sidebar.write("No hay viajes guardados aún.")

# Debug opcional
if st.sidebar.checkbox("Mostrar debug"):
    st.write("DEBUG seleccionados:", st.session_state.seleccionados)
    st.write("DEBUG ruta_coords:", st.session_state.ruta_coords)
    st.write("DEBUG ruta_coords_fija:", st.session_state.ruta_coords_fija)
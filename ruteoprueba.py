import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# ===============================
# TÍTULO
# ===============================
st.title("Programa de Ruteo Centralizado Caminantes")

# ===============================
# SUBIDA DE ARCHIVO
# ===============================
archivo = st.file_uploader(
    "📂 Subí el archivo de caminantes (.xlsx)",
    type=["xlsx"]
)

# ===============================
# SOLO EJECUTAR LA APP SI HAY ARCHIVO
# ===============================
if archivo is not None:

    # ===============================
    # CARGA DEL EXCEL
    # ===============================
    df = pd.read_excel(
        archivo,
        dtype={"Equipo": str},
        engine="openpyxl"
    )

    df["Equipo"] = (
        df["Equipo"]
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
    )

    df = df.dropna(subset=["Latitud", "Longitud"]).copy()

    # ===============================
    # SESSION STATE (una sola vez)
    # ===============================
    if "con_geo" not in st.session_state:
        st.session_state.con_geo = df

        df_grouped = (
            df.groupby(["Latitud", "Longitud"])["Equipo"]
            .apply(lambda x: ", ".join(sorted(set(x))))
            .reset_index()
        )

        st.session_state.consolidado = df_grouped

        st.session_state.coord_map = {
            (row["Latitud"], row["Longitud"]): row["Equipo"]
            for _, row in df_grouped.iterrows()
        }

    # ===============================
    # VARIABLES DE SESIÓN
    # ===============================
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

    # ===============================
    # SIDEBAR – ACTUALIZAR RUTA
    # ===============================
    if st.sidebar.button("Actualizar ruta") and len(st.session_state.ruta_coords) >= 2:
        st.session_state.ruta_coords_fija = st.session_state.ruta_coords.copy()
        st.session_state.ruta_dibujada = True

    # ===============================
    # MAPA
    # ===============================
    m = folium.Map(
        location=st.session_state.map_center,
        zoom_start=st.session_state.map_zoom,
        tiles="OpenStreetMap"
    )

    # Marcadores
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

    # Ruta
    if st.session_state.ruta_dibujada and len(st.session_state.ruta_coords_fija) >= 2:
        folium.PolyLine(
            locations=st.session_state.ruta_coords_fija,
            color="red",
            weight=3,
            opacity=0.8
        ).add_to(m)

    # ===============================
    # INTERACCIÓN MAPA
    # ===============================
    mapa = st_folium(
        m,
        width=800,
        height=600,
        returned_objects=["last_object_clicked"]
    )

    if mapa and mapa.get("last_object_clicked"):
        lat = mapa["last_object_clicked"]["lat"]
        lng = mapa["last_object_clicked"]["lng"]

        eq = st.session_state.coord_map.get((lat, lng))
        if eq:
            if eq in st.session_state.seleccionados:
                idx = st.session_state.seleccionados.index(eq)
                st.session_state.seleccionados.pop(idx)
                st.session_state.ruta_coords.pop(idx)
            else:
                st.session_state.seleccionados.append(eq)
                st.session_state.ruta_coords.append((lat, lng))

    # ===============================
    # SIDEBAR – SELECCIÓN
    # ===============================
    st.sidebar.header("Selección actual")

    if st.session_state.seleccionados:
        for i, eq in reversed(list(enumerate(st.session_state.seleccionados, start=1))):
            st.sidebar.write(f"{i}. {eq}")
    else:
        st.sidebar.write("No hay elementos seleccionados.")

    # ===============================
    # REORDENAR
    # ===============================
    if st.session_state.seleccionados:
        mover = st.sidebar.selectbox(
            "Cambiar orden de:",
            st.session_state.seleccionados
        )

        nueva_pos = st.sidebar.number_input(
            "Nueva posición:",
            min_value=1,
            max_value=len(st.session_state.seleccionados),
            value=st.session_state.seleccionados.index(mover) + 1
        )

        if st.sidebar.button("Reordenar"):
            idx = st.session_state.seleccionados.index(mover)
            coord = st.session_state.ruta_coords.pop(idx)
            st.session_state.seleccionados.pop(idx)

            st.session_state.seleccionados.insert(nueva_pos - 1, mover)
            st.session_state.ruta_coords.insert(nueva_pos - 1, coord)

            st.sidebar.success("Orden actualizado")

    # ===============================
    # GUARDAR Y DESCARGAR
    # ===============================
    st.sidebar.write("---")
    ruta_num = st.sidebar.text_input("Número de ruta:")

    if st.sidebar.button("Guardar ruta"):
        if st.session_state.seleccionados and ruta_num.strip():

            equipos, latitudes, longitudes = [], [], []

            for eq, (lat, lng) in zip(
                st.session_state.seleccionados,
                st.session_state.ruta_coords
            ):
                for e in eq.split(","):
                    equipos.append(e.strip())
                    latitudes.append(lat)
                    longitudes.append(lng)

            ruta_df = pd.DataFrame({
                "Ruta": ruta_num,
                "Orden": range(1, len(equipos) + 1),
                "Equipo": equipos,
                "Latitud": latitudes,
                "Longitud": longitudes
            })

            nombre = f"ruta_{ruta_num}.xlsx"
            ruta_df.to_excel(nombre, index=False)

            st.download_button(
                "⬇️ Descargar ruta",
                data=open(nombre, "rb"),
                file_name=nombre,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.sidebar.error("Seleccioná equipos y asigná un número de ruta.")

# ===============================
# MENSAJE SIN ARCHIVO
# ===============================
else:
    st.info("👆 Subí un archivo Excel para comenzar")

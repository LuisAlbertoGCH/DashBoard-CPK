import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Dashboard CPK TDR", layout="wide", page_icon="🚛")

# --- Estilo TDR ---
st.markdown("""
    <style>
    .stSidebar { background-color: #002F6C !important; }
    .stSidebar h1, .stSidebar h2, .stSidebar h3, .stSidebar p, .stSidebar span {
        color: white !important;
    }
    h1, h2 { color: #002F6C; font-weight: bold; }
    .stButton>button {
        background-color: #FFD100;
        color: #002F6C;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- Cargar archivo ---
st.sidebar.title("📁 Cargar archivo")
uploaded_file = st.sidebar.file_uploader("Sube tu archivo CSV con datos TDR", type=["csv"])

if uploaded_file is None:
    st.warning("⚠️ Sube un archivo CSV para comenzar.")
    st.stop()

df = pd.read_csv(uploaded_file)
df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
df["CPK total"] = pd.to_numeric(df["CPK total"], errors="coerce")

# --- Preprocesamiento ---
df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
df["Unidad"] = df["Unidad"].astype(str)
df["Flota"] = df["Flota"].astype(str)
df["Tipo de Carga"] = df["Tipo de Carga"].astype(str)
df["Mes"] = df["Fecha"].dt.month
df["Año"] = df["Fecha"].dt.year

# --- Sidebar Filtros básicos ---
st.sidebar.title("🔎 Filtros")

mostrar_top = st.sidebar.checkbox("🎯 Solo mostrar top 10 mayor y menor CPK", value=False)

if not mostrar_top:
    flotas = st.sidebar.multiselect("Selecciona Flotas", sorted(df["Flota"].dropna().unique()))
    unidades = st.sidebar.multiselect("Selecciona Unidades", sorted(df["Unidad"].dropna().unique()))
    tipos_carga = st.sidebar.multiselect("Tipo de Carga", sorted(df["Tipo de Carga"].unique()))

    fecha_min = df["Fecha"].min().date()
    fecha_max = df["Fecha"].max().date()

    rango_fechas = st.sidebar.date_input("Rango de Fechas", [fecha_min, fecha_max])

    cpk_min = float(df["CPK total"].min())
    cpk_max = float(df["CPK total"].max())
    rango_cpk = st.sidebar.slider("Rango de CPK total", cpk_min, cpk_max, (cpk_min, cpk_max))

    # --- Aplicar filtros generales ---
    df_filtrado = df.copy()
    df_filtrado = df_filtrado[df_filtrado["Fecha"].between(pd.to_datetime(rango_fechas[0]), pd.to_datetime(rango_fechas[1]))]
    if flotas:
        df_filtrado = df_filtrado[df_filtrado["Flota"].isin(flotas)]
    if unidades:
        df_filtrado = df_filtrado[df_filtrado["Unidad"].isin(unidades)]
    if tipos_carga:
        df_filtrado = df_filtrado[df_filtrado["Tipo de Carga"].isin(tipos_carga)]
    df_filtrado = df_filtrado[df_filtrado["CPK total"].between(*rango_cpk)]

else:
    st.sidebar.markdown("### 📆 Periodo a analizar")
    periodo = st.sidebar.selectbox("Selecciona mes o semestre", [
        "Octubre", "Noviembre", "Diciembre", "Enero", "Febrero", "Marzo", "Semestre Oct-Mar"
    ])

    mes_dict = {
        "Octubre": (10, 2024),
        "Noviembre": (11, 2024),
        "Diciembre": (12, 2024),
        "Enero": (1, 2025),
        "Febrero": (2, 2025),
        "Marzo": (3, 2025)
    }

    if periodo == "Semestre Oct-Mar":
        filtro = (
            ((df["Mes"].isin([10,11,12])) & (df["Año"] == 2024)) |
            ((df["Mes"].isin([1,2,3])) & (df["Año"] == 2025))
        )
    else:
        mes, anio = mes_dict[periodo]
        filtro = (df["Mes"] == mes) & (df["Año"] == anio)

    df_periodo = df[filtro]
    top_10 = df_periodo.groupby("Unidad")["CPK total"].mean().nsmallest(10).index
    bottom_10 = df_periodo.groupby("Unidad")["CPK total"].mean().nlargest(10).index
    unidades_top = top_10.union(bottom_10)
    df_filtrado = df_periodo[df_periodo["Unidad"].isin(unidades_top)]

# --- Visualización principal ---
st.title("📊 Dashboard de Análisis CPK - TDR")

vista = st.radio("Selecciona una vista:", [
    "Resumen por Flota",
    "Boxplot por Unidad",
    "CPK en el Tiempo",
    "Heatmap Semanal",
    "CPK vs Km Totales",
    "Ver Datos en Tabla"
])

if vista == "Resumen por Flota":
    st.subheader("Promedio de CPK total por Flota")
    resumen = df_filtrado.groupby("Flota")["CPK total"].mean().reset_index().sort_values("CPK total", ascending=False)
    fig = px.bar(resumen, x="Flota", y="CPK total", color="CPK total", title="CPK promedio por Flota")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🏆 Top 10 Unidades con mejor CPK (más bajo)")
    top_unidades = (
        df_filtrado.groupby("Unidad")["CPK total"]
        .mean()
        .reset_index()
        .sort_values("CPK total", ascending=True)
        .head(10)
    )
    fig2 = px.bar(top_unidades, x="Unidad", y="CPK total", color="CPK total", title="Top 10 Unidades con CPK más bajo")
    st.plotly_chart(fig2, use_container_width=True)

elif vista == "Boxplot por Unidad":
    st.subheader("Boxplot de CPK total por Unidad")
    fig = px.box(df_filtrado, x="Unidad", y="CPK total", color="Flota", points="outliers")
    st.plotly_chart(fig, use_container_width=True)

elif vista == "CPK en el Tiempo":
    st.subheader("Tendencia de CPK total en el tiempo")
    df_line = df_filtrado.groupby("Fecha")["CPK total"].mean().reset_index()
    fig = px.line(df_line, x="Fecha", y="CPK total", markers=True)
    st.plotly_chart(fig, use_container_width=True)

elif vista == "Heatmap Semanal":
    st.subheader("Heatmap semanal de CPK por Unidad")
    df_filtrado["Semana"] = df_filtrado["Fecha"].dt.strftime("%Y-%U")
    pivot = df_filtrado.pivot_table(index="Unidad", columns="Semana", values="CPK total", aggfunc="mean")
    fig = px.imshow(pivot, aspect="auto", color_continuous_scale="Viridis")
    st.plotly_chart(fig, use_container_width=True)

elif vista == "CPK vs Km Totales":
    st.subheader("Relación entre CPK total y Km recorridos")
    agrupado = df_filtrado.groupby(["Unidad", "Flota"]).agg({
        "CPK total": "mean", "kmstotales": "sum"
    }).reset_index()
    fig = px.scatter(agrupado, x="CPK total", y="kmstotales", color="Flota", size="kmstotales", hover_data=["Unidad"])
    st.plotly_chart(fig, use_container_width=True)

elif vista == "Ver Datos en Tabla":
    st.subheader("📄 Datos filtrados")
    st.dataframe(df_filtrado)

    buffer = BytesIO()
    df_filtrado.to_csv(buffer, index=False)
    st.download_button(
        label="📥 Descargar CSV filtrado",
        data=buffer.getvalue(),
        file_name="TDR_datos_filtrados.csv",
        mime="text/csv"
    )

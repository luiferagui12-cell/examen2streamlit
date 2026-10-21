from datetime import date, datetime
import os
import random
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="TechVentas - Control de Inventario",
    layout="wide",
)

st.title("TechVentas: Panel de Control y Gestión de Inventario")

ruta_archivo = (
    r"C:\Users\Usuario\OneDrive\Escritorio\INTECCSA\streamlit\examen2streamlit\InventarioTechZone.xlsx"
)


def cargar_inventario(path):
  if not os.path.exists(path):
    st.error(
        f"**Error:** No se pudo encontrar el archivo"
        f" `InventarioTechZone.xlsx` en la ruta especificada:\n\n`{path}`\n\n"
        "Por favor, verifique que el archivo exista en dicha ubicación antes"
        " de ejecutar la aplicación."
    )
    st.stop()

  df = pd.read_excel(path)

  df.columns = df.columns.str.strip().str.lower()

  if "fechaingreso" in df.columns:
    df["fechaingreso"] = pd.to_datetime(df["fechaingreso"], errors="coerce")

  return df

if "df_inventario" not in st.session_state:
  st.session_state.df_inventario = cargar_inventario(ruta_archivo)

def enriquecer_datos(df):
  df_proc = df.copy()

  df_proc["precio"] = pd.to_numeric(df_proc["precio"], errors="coerce").fillna(
      0.0
  )
  df_proc["stock"] = pd.to_numeric(df_proc["stock"], errors="coerce").fillna(0)

  if "estado" in df_proc.columns:
    mask_no_desc = df_proc["estado"] != "Descontinuado"
    df_proc.loc[mask_no_desc & (df_proc["stock"] == 0), "estado"] = "Agotado"
    df_proc.loc[
        mask_no_desc & (df_proc["stock"] > 0) & (df_proc["stock"] < 5), "estado"
    ] = "Crítico"
    df_proc.loc[mask_no_desc & (df_proc["stock"] >= 5), "estado"] = "Disponible"
  else:
    conditions = [
        df_proc["stock"] == 0,
        df_proc["stock"] < 5,
        df_proc["stock"] >= 5,
    ]
    choices = ["Agotado", "Crítico", "Disponible"]
    df_proc["estado"] = pd.select(conditions, choices, default="Disponible")

  df_proc["valortotal"] = df_proc["precio"] * df_proc["stock"]

  df_proc["margen ganancia"] = df_proc["precio"] * 0.12

  if "fechaingreso" in df_proc.columns:
    fecha_actual = pd.Timestamp(datetime.now().date())
    df_proc["dias en inventario"] = (
        fecha_actual - pd.to_datetime(df_proc["fechaingreso"])
    ).dt.days
  else:
    df_proc["dias en inventario"] = 0

  return df_proc

st.session_state.df_inventario = enriquecer_datos(
    st.session_state.df_inventario
)

with st.expander("Registrar Nuevo Producto", expanded=False):
  with st.form("form_registro_producto", clear_on_submit=True):
    st.subheader("Nuevo Registro de Producto")

    nombre_prod = st.text_input("Nombre del producto")
    categoria_prod = st.selectbox(
        "Categoría",
        ["Laptop", "Monitor", "Accesorio", "Periférico", "Componente"],
    )
    precio_prod = st.number_input(
        "Precio unitario", min_value=0.0, value=0.0, step=0.5
    )
    stock_prod = st.number_input(
        "Stock disponible", min_value=0, value=0, step=1
    )
    fecha_ingreso_prod = st.date_input(
        "Fecha de ingreso", value=date.today(), max_value=date.today()
    )
    estado_manual = st.selectbox(
        "Estado inicial", ["Disponible", "Agotado", "Crítico", "Descontinuado"]
    )

    submitted = st.form_submit_button("Guardar Producto")

    if submitted:
      errores = []

      if not nombre_prod.strip():
        errores.append("El nombre del producto no puede estar vacío.")
      if precio_prod <= 0:
        errores.append("El precio debe ser mayor que 0.")
      if stock_prod < 0:
        errores.append("El stock debe ser mayor o igual a 0.")
      if fecha_ingreso_prod > date.today():
        errores.append("La fecha de ingreso no puede ser una fecha futura.")

      if errores:
        for error in errores:
          st.error(f" {error}")
      else:
        def generar_codigo_unico():
          return f"PR-250101-{random.randint(90059, 99999)}"

        codigo_nuevo = generar_codigo_unico()

        if estado_manual == "Descontinuado":
          estado_final = "Descontinuado"
        elif stock_prod == 0:
          estado_final = "Agotado"
        elif stock_prod < 5:
          estado_final = "Crítico"
        else:
          estado_final = "Disponible"

        nuevo_registro = pd.DataFrame([{
            "codigo": codigo_nuevo,
            "producto": nombre_prod.strip(),
            "categoria": categoria_prod,
            "precio": float(precio_prod),
            "stock": int(stock_prod),
            "fechaingreso": pd.to_datetime(fecha_ingreso_prod),
            "estado": estado_final,
        }])

        st.session_state.df_inventario = pd.concat(
            [st.session_state.df_inventario, nuevo_registro], ignore_index=True
        )

        st.session_state.df_inventario = enriquecer_datos(
            st.session_state.df_inventario
        )

        st.success(
            f"¡Producto registrado con éxito! Código asignado: **{codigo_nuevo}**"
        )
        st.balloons()

st.markdown("---")
st.subheader("🔍 Panel de Filtros")

df_filtrado = st.session_state.df_inventario.copy()

col_f1, col_f2 = st.columns(2)

with col_f1:
  if "categoria" in df_filtrado.columns:
    cats = df_filtrado["categoria"].dropna().unique().tolist()
    sel_cats = st.multiselect(
        "Filtrar por Categoría(s):", options=cats, default=cats
    )
    df_filtrado = df_filtrado[df_filtrado["categoria"].isin(sel_cats)]

with col_f2:
  if "estado" in df_filtrado.columns:
    ests = df_filtrado["estado"].dropna().unique().tolist()
    sel_ests = st.multiselect(
        "Filtrar por Estado(s):", options=ests, default=ests
    )
    df_filtrado = df_filtrado[df_filtrado["estado"].isin(sel_ests)]

if "precio" in df_filtrado.columns and not df_filtrado.empty:
  p_min = float(st.session_state.df_inventario["precio"].min())
  p_max = float(st.session_state.df_inventario["precio"].max())

  if p_min < p_max:
    rango_precio = st.slider(
        "Seleccione el rango de precios:",
        min_value=p_min,
        max_value=p_max,
        value=(p_min, p_max),
    )
    df_filtrado = df_filtrado[
        (df_filtrado["precio"] >= rango_precio[0])
        & (df_filtrado["precio"] <= rango_precio[1])
    ]

busq = st.text_input(
    "Buscar por nombre o palabra clave:", placeholder="Ej. Laptop, Teclado..."
)
if busq and "producto" in df_filtrado.columns:
  df_filtrado = df_filtrado[
      df_filtrado["producto"].astype(str).str.lower().str.contains(busq.lower())
  ]

activar_stock_min = st.checkbox("Activar filtro por stock mínimo")
if activar_stock_min and "stock" in df_filtrado.columns:
  st_min_val = st.number_input(
      "Ingrese el stock mínimo requerido:", min_value=0, value=5, step=1
  )
  df_filtrado = df_filtrado[df_filtrado["stock"] >= st_min_val]


st.markdown("---")
st.subheader(
    f"Tabla de Inventario ({len(df_filtrado)} productos mostrados)"
)
st.dataframe(df_filtrado, use_container_width=True)


if not df_filtrado.empty:
  st.markdown("---")
  st.subheader("Analítica y Visualización de Datos")

  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

  cat_counts = df_filtrado["categoria"].value_counts()
  ax1.bar(
      cat_counts.index, cat_counts.values, color=["#1f77b4", "#ff7f0e", "#2ca02c"]
  )
  ax1.set_title("Cantidad de Productos por Categoría", fontsize=12, fontweight="bold")
  ax1.set_xlabel("Categoría")
  ax1.set_ylabel("Cantidad")
  ax1.tick_params(axis="x", rotation=30)

  val_cat = df_filtrado.groupby("categoria")["valortotal"].sum()
  ax2.pie(
      val_cat.values,
      labels=val_cat.index,
      autopct="%1.1f%%",
      startangle=140,
      colors=["#ff9999", "#66b3ff", "#99ff99", "#ffcc99", "#c2c2f0"],
  )
  ax2.set_title("Valor Total por Categoría ($)", fontsize=12, fontweight="bold")

  plt.tight_layout()
  st.pyplot(fig)

  st.markdown("#### TOP 5 de Productos más Valiosos")
  top_5 = df_filtrado.nlargest(5, "valortotal")

  fig_top, ax_top = plt.subplots(figsize=(10, 4))
  ax_top.barh(
      top_5["producto"],
      top_5["valortotal"],
      color="#4c72b0",
  )
  ax_top.set_xlabel("Valor Total ($)")
  ax_top.set_ylabel("Producto")
  ax_top.set_title("Top 5 Productos por Valor Total en Inventario", fontweight="bold")
  ax_top.invert_yaxis() 

  plt.tight_layout()
  st.pyplot(fig_top)
else:
  st.info(
      "ℹNo hay datos disponibles para mostrar gráficos con los filtros"
      " actuales."
  )



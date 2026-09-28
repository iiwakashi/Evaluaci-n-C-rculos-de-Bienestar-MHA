from __future__ import annotations

import streamlit as st

from bienestar.visualization import APP_CSS, LEGEND_HTML, evolution_html, summary_html
from bienestar.workbook import compare_workbooks, load_workbook, person_evolution


st.set_page_config(
    page_title="Evolución de Círculos de Bienestar",
    page_icon="🟢",
    layout="wide",
)
st.markdown(APP_CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def parse_uploaded_workbook(filename: str, content: bytes):
    return load_workbook(filename, content)


def show_validation(title: str, workbook) -> None:
    if workbook.ok:
        st.success(f"{title}: archivo válido · {len(workbook.people)} personas · {len(workbook.indicators)} indicadores")
    else:
        st.error(f"{title}: el archivo requiere revisión")
    for message in workbook.errors:
        st.error(message, icon="🚫")
    for message in workbook.warnings:
        st.warning(message, icon="⚠️")


st.title("Evolución de Círculos de Bienestar")
st.markdown(
    '<p class="app-subtitle">Compare la medición de entrada y salida de cada persona. Los archivos se procesan en memoria y no se guardan.</p>',
    unsafe_allow_html=True,
)

entry_file = st.file_uploader(
    "1. Cargue el archivo de entrada",
    type=("xlsx", "xlsm"),
    key="entry_file",
)

if entry_file is None:
    st.info("La aplicación comenzará validando las hojas RESPUESTAS y SET UP del archivo de entrada.")
    st.stop()

entry = parse_uploaded_workbook(entry_file.name, entry_file.getvalue())
show_validation("Entrada", entry)
if not entry.ok:
    st.stop()

exit_file = st.file_uploader(
    "2. Cargue el archivo de salida",
    type=("xlsx", "xlsm"),
    key="exit_file",
)
if exit_file is None:
    st.info("El archivo de entrada está listo. Cargue ahora el archivo de salida.")
    st.stop()

exit_data = parse_uploaded_workbook(exit_file.name, exit_file.getvalue())
show_validation("Salida", exit_data)
if not exit_data.ok:
    st.stop()

comparison, comparison_errors = compare_workbooks(entry, exit_data)
if comparison_errors:
    for message in comparison_errors:
        st.error(message, icon="🚫")
    st.stop()

st.success(f"Comparación lista · {len(comparison.people)} personas presentes en ambos momentos")
if comparison.only_entry or comparison.only_exit:
    st.warning(
        f"Sin pareja de comparación: {comparison.only_entry} solo en entrada y "
        f"{comparison.only_exit} solo en salida. No se incluyen en el selector."
    )

labels = {}
for _, row in comparison.people.iterrows():
    last_digits = row["_id"][-4:] if len(row["_id"]) >= 4 else row["_id"]
    labels[row["_id"]] = f"{row['_display_name']} · documento terminado en {last_digits}"

selected_id = st.selectbox(
    "Seleccione una persona",
    options=comparison.people["_id"].tolist(),
    format_func=lambda value: labels[value],
)

selected_row = comparison.people.loc[comparison.people["_id"] == selected_id].iloc[0]
st.subheader(selected_row["_display_name"])
st.markdown(LEGEND_HTML, unsafe_allow_html=True)

evolution, metrics = person_evolution(comparison, selected_id)
st.markdown(evolution_html(evolution), unsafe_allow_html=True)
st.markdown(summary_html(metrics), unsafe_allow_html=True)


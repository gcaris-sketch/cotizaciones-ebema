import io
import fitz  # PyMuPDF
import streamlit as st

# Configuración de página
st.set_page_config(
    page_title="Modificador de Cotizaciones EBEMA",
    page_icon="📄",
    layout="centered",
)

st.title("📄 Modificador de Cotizaciones EBEMA")
st.markdown(
    "Esta herramienta detecta el último ítem de la **Nota de Venta / Cotización** "
    "e inserta la leyenda en rojo justo debajo de los ítems."
)

# Texto por defecto breve, profesional y directo
TEXTO_PREDETERMINADO = (
    "NOTA: Los precios unitarios y la tarifa de flete son válidos exclusivamente "
    "para las cantidades cotizadas. Cualquier variación en el volumen de compra requerirá una recotización."
)

# Panel lateral de configuración
with st.sidebar:
    st.header("⚙️ Opciones de Estilo")

    # Selector de mayúsculas / minúsculas
    formato_texto = st.radio(
        "Formato del texto:",
        ["Original (Normal)", "MAYÚSCULAS"],
        index=0,
    )

    estilo_caja = st.radio(
        "Estilo visual:",
        ["Recuadro destacado (Recomendado)", "Solo texto rojo"],
        index=0,
    )

    alineacion_str = st.selectbox(
        "Alineación del texto:",
        ["Justificado", "Centrado", "Izquierda"],
        index=0,
    )

# Mapeo de alineaciones para PyMuPDF
dict_alineacion = {
    "Izquierda": fitz.TEXT_ALIGN_LEFT,
    "Centrado": fitz.TEXT_ALIGN_CENTER,
    "Justificado": fitz.TEXT_ALIGN_JUSTIFY,
}
align_val = dict_alineacion[alineacion_str]

# Editor del texto
texto_a_insertar = st.text_area(
    "Texto que se agregará:",
    value=TEXTO_PREDETERMINADO,
    height=110,
)

# Aplicar formato de mayúsculas si corresponde
if formato_texto == "MAYÚSCULAS":
    texto_final = texto_a_insertar.upper()
else:
    texto_final = texto_a_insertar


def detectar_posicion_items(pagina):
    """Detecta la coordenada Y exacta donde termina el último ítem de la tabla."""
    words = pagina.get_text("words")
    rect_pagina = pagina.rect

    y_header = rect_pagina.height * 0.35
    y_footer = rect_pagina.height - 100

    header_y1_list = []
    footer_y0_list = []

    header_keywords = [
        "ITEM",
        "CÓDIGO",
        "CODIGO",
        "DESCRIPCIÓN",
        "DESCRIPCION",
        "U.M.",
        "TOTAL",
        "CANTIDAD",
        "VALOR",
    ]
    footer_keywords = [
        "SUB",
        "TOTAL",
        "CONDICIONES",
        "NETO",
        "I.V.A",
        "IVA",
        "FLETE",
        "SUBTOTAL",
    ]

    for w in words:
        y0, y1, text = w[1], w[3], w[4]
        t_upper = text.upper().strip()

        if any(hk in t_upper for hk in header_keywords) and y0 < (
            rect_pagina.height * 0.55
        ):
            header_y1_list.append(y1)

        if any(fk in t_upper for fk in footer_keywords) and y0 > (
            rect_pagina.height * 0.45
        ):
            footer_y0_list.append(y0)

    if header_y1_list:
        y_header = max(header_y1_list)

    if footer_y0_list:
        y_footer = min(footer_y0_list)

    item_y1_list = []
    for w in words:
        y0, y1 = w[1], w[3]
        if (y_header + 2) < y0 and y1 < (y_footer - 5):
            item_y1_list.append(y1)

    if item_y1_list:
        max_item_y1 = max(item_y1_list)
    else:
        max_item_y1 = y_header + 20

    return max_item_y1, y_footer


def procesar_pdf(pdf_bytes, texto_clausula, usar_recuadro, alineacion):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    pagina = doc[-1]
    rect_pagina = pagina.rect

    max_item_y1, y_footer = detectar_posicion_items(pagina)

    box_height = 42
    margin_x = 38
    box_x0 = margin_x
    box_x1 = rect_pagina.width - margin_x

    box_y0 = max_item_y1 + 8
    box_y1 = box_y0 + box_height

    if box_y1 >= (y_footer - 5):
        pagina_destino = doc.new_page(
            width=rect_pagina.width, height=rect_pagina.height
        )
        box_y0 = 60
        box_y1 = box_y0 + box_height
    else:
        pagina_destino = pagina

    rect_box = fitz.Rect(box_x0, box_y0, box_x1, box_y1)

    if usar_recuadro:
        shape = pagina_destino.new_shape()
        shape.draw_rect(rect_box)
        shape.finish(
            color=(0.85, 0.15, 0.15),
            fill=(0.99, 0.94, 0.94),
            width=0.75,
        )
        shape.commit()

        rect_texto = fitz.Rect(
            box_x0 + 8, box_y0 + 4, box_x1 - 8, box_y1 - 4
        )
    else:
        rect_texto = rect_box

    fontsize = 8.5
    rc = pagina_destino.insert_textbox(
        rect_texto,
        texto_clausula,
        fontsize=fontsize,
        fontname="helv",
        color=(0.7, 0.0, 0.0),
        align=alineacion,
    )

    if rc < 0:
        pagina_destino.insert_textbox(
            rect_texto,
            texto_clausula,
            fontsize=7.5,
            fontname="helv",
            color=(0.7, 0.0, 0.0),
            align=alineacion,
        )

    buffer_salida = io.BytesIO()
    doc.save(buffer_salida)
    doc.close()
    return buffer_salida.getvalue()


# Componente para subir el PDF
archivo_subido = st.file_uploader(
    "Arrastra tu cotización en PDF aquí", type=["pdf"]
)

if archivo_subido:
    if st.button("✨ Procesar Cotización", type="primary"):
        usar_cuadro = estilo_caja == "Recuadro destacado (Recomendado)"
        pdf_modificado = procesar_pdf(
            archivo_subido.read(), texto_final, usar_cuadro, align_val
        )

        st.success("¡Cotización procesada correctamente!")
        st.download_button(
            label="📥 Descargar PDF Modificado",
            data=pdf_modificado,
            file_name=f"cotizacion_modificada_{archivo_subido.name}",
            mime="application/pdf",
        )
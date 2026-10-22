import io
import fitz  # PyMuPDF
import streamlit as st

# Configuración de la interfaz
st.set_page_config(
    page_title="Modificador de Cotizaciones EBEMA",
    page_icon="📄",
    layout="wide",
)

st.title("📄 Modificador Avanzado de Cotizaciones EBEMA")
st.markdown(
    "Añade leyendas y condiciones comerciales a tus cotizaciones con opciones de formato, "
    "previsualización inmediata y cobertura de líneas de fondo."
)

# Texto predeterminado
TEXTO_PREDETERMINADO = (
    "NOTA: Los precios unitarios y la tarifa de flete son válidos exclusivamente "
    "para las cantidades cotizadas. Cualquier variación en el volumen de compra requerirá una recotización."
)

# Diccionarios de configuración
DICCIONARIO_COLORES = {
    "Rojo Corporativo": (0.80, 0.00, 0.00),
    "Rojo Vino / Granate": (0.50, 0.00, 0.10),
    "Rojo Carmín Vivo": (0.90, 0.10, 0.10),
    "Azul EBEMA": (0.00, 0.20, 0.60),
    "Negro / Gris Oscuro": (0.15, 0.15, 0.15),
}

DICCIONARIO_FUENTES = {
    "Helvetica (Limpia)": "helv",
    "Helvetica Bold (Negrita)": "hebo",
    "Times New Roman (Clásica)": "tiro",
    "Courier (Monospaciada)": "cour",
}

DICCIONARIO_ALINEACION = {
    "Justificado": fitz.TEXT_ALIGN_JUSTIFY,
    "Centrado": fitz.TEXT_ALIGN_CENTER,
    "Izquierda": fitz.TEXT_ALIGN_LEFT,
}

# --- BARRA LATERAL CON OPCIONES DE PERSONALIZACIÓN ---
with st.sidebar:
    st.header("⚙️ Opciones de Texto")

    formato_texto = st.radio(
        "Formato de mayúsculas:",
        ["Original (Normal)", "MAYÚSCULAS"],
        index=0,
    )

    fuente_seleccionada = st.selectbox(
        "Tipografía:",
        list(DICCIONARIO_FUENTES.keys()),
        index=0,
    )

    color_seleccionado = st.selectbox(
        "Color del texto:",
        list(DICCIONARIO_COLORES.keys()),
        index=0,
    )

    alineacion_seleccionada = st.selectbox(
        "Alineación:",
        list(DICCIONARIO_ALINEACION.keys()),
        index=0,
    )

    st.divider()
    st.header("🎨 Estilo de Recuadro / Fondo")

    estilo_fondo = st.radio(
        "Apariencia del fondo:",
        [
            "Recuadro completo (Borde + Fondo suave)",
            "Fondo Blanco (Oculta líneas de tabla, sin borde)",
            "Fondo Rojo Suave (Sin borde)",
            "Solo Borde (Fondo transparente)",
            "Texto libre (Sin fondo ni borde)",
        ],
        index=0,
    )


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


def procesar_pdf(
    pdf_bytes,
    texto_clausula,
    estilo_fondo_opcion,
    color_rgb,
    font_code,
    align_val,
    es_mayuscula,
):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pagina = doc[-1]
    rect_pagina = pagina.rect

    max_item_y1, y_footer = detectar_posicion_items(pagina)

    box_height = 44
    margin_x = 38
    box_x0 = margin_x
    box_x1 = rect_pagina.width - margin_x

    box_y0 = max_item_y1 + 8
    box_y1 = box_y0 + box_height

    # Pasar a página nueva si el espacio no es suficiente
    if box_y1 >= (y_footer - 5):
        pagina_destino = doc.new_page(
            width=rect_pagina.width, height=rect_pagina.height
        )
        box_y0 = 60
        box_y1 = box_y0 + box_height
    else:
        pagina_destino = pagina

    rect_box = fitz.Rect(box_x0, box_y0, box_x1, box_y1)

    # Formato de mayúsculas
    if es_mayuscula:
        texto_clausula = texto_clausula.upper()

    # Determinar bordes y fondos según selección
    draw_border = False
    draw_fill = False
    color_borde = (0.85, 0.15, 0.15)
    color_fondo = (0.99, 0.94, 0.94)

    if estilo_fondo_opcion == "Recuadro completo (Borde + Fondo suave)":
        draw_border = True
        draw_fill = True
    elif (
        estilo_fondo_opcion
        == "Fondo Blanco (Oculta líneas de tabla, sin borde)"
    ):
        draw_fill = True
        color_fondo = (1.0, 1.0, 1.0)  # Blanco puro para tapar la cuadrícula
    elif estilo_fondo_opcion == "Fondo Rojo Suave (Sin borde)":
        draw_fill = True
        color_fondo = (0.99, 0.94, 0.94)
    elif estilo_fondo_opcion == "Solo Borde (Fondo transparente)":
        draw_border = True

    # Dibujar la figura de cobertura o recuadro
    if draw_fill or draw_border:
        shape = pagina_destino.new_shape()
        shape.draw_rect(rect_box)
        shape.finish(
            color=color_borde if draw_border else None,
            fill=color_fondo if draw_fill else None,
            width=0.75 if draw_border else 0,
        )
        shape.commit()
        rect_texto = fitz.Rect(box_x0 + 8, box_y0 + 4, box_x1 - 8, box_y1 - 4)
    else:
        rect_texto = rect_box

    # Insertar el texto
    fontsize = 8.5
    rc = pagina_destino.insert_textbox(
        rect_texto,
        texto_clausula,
        fontsize=fontsize,
        fontname=font_code,
        color=color_rgb,
        align=align_val,
    )

    if rc < 0:
        pagina_destino.insert_textbox(
            rect_texto,
            texto_clausula,
            fontsize=7.5,
            fontname=font_code,
            color=color_rgb,
            align=align_val,
        )

    # Generar imagen de vista previa
    pix = pagina_destino.get_pixmap(dpi=150)
    imagen_preview = pix.tobytes("png")

    buffer_salida = io.BytesIO()
    doc.save(buffer_salida)
    doc.close()

    return buffer_salida.getvalue(), imagen_preview


# --- ESTRUCTURA PRINCIPAL DE LA PÁGINA ---
col1, col2 = st.columns([1, 1], gap="medium")

with col1:
    st.subheader("1. Edición del Texto")
    texto_a_insertar = st.text_area(
        "Redacta o modifica la cláusula:",
        value=TEXTO_PREDETERMINADO,
        height=110,
    )

    archivo_subido = st.file_uploader(
        "2. Carga tu archivo PDF:", type=["pdf"]
    )

    if archivo_subido:
        es_mayus = formato_texto == "MAYÚSCULAS"
        color_rgb = DICCIONARIO_COLORES[color_seleccionado]
        font_code = DICCIONARIO_FUENTES[fuente_seleccionada]
        align_val = DICCIONARIO_ALINEACION[alineacion_seleccionada]

        pdf_modificado, imagen_preview = procesar_pdf(
            archivo_subido.read(),
            texto_a_insertar,
            estilo_fondo,
            color_rgb,
            font_code,
            align_val,
            es_mayus,
        )

        st.success("¡Documento procesado con éxito!")

        st.download_button(
            label="📥 Descargar PDF Modificado",
            data=pdf_modificado,
            file_name=f"cotizacion_modificada_{archivo_subido.name}",
            mime="application/pdf",
            type="primary",
        )

with col2:
    st.subheader("👁️ Vista Previa en Tiempo Real")
    if archivo_subido:
        st.image(
            imagen_preview,
            caption="Resultado de la cotización procesada",
            use_container_width=True,
        )
    else:
        st.info(
            "Carga un archivo PDF en el panel de la izquierda para ver la vista previa aquí."
        )

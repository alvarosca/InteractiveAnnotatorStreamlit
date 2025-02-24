import streamlit as st
from image_annotation import *
from annotation_correction import *

# Folders
image_dir  = "./images"
ann_dir    = "./annotations"
report_dir = "./reports"

app_list = ["Anotación de imágenes", "Corrección de anotaciones"]

# We want the wide mode to be set by default
st.set_page_config(page_title=None, page_icon=None, layout="wide", initial_sidebar_state="auto", menu_items=None)

def main():

    st.sidebar.header("Seleccionar aplicación")
    with st.sidebar:
        st.session_state['Application'] = st.selectbox("Aplicación:", app_list)

    if st.session_state['Application'] == app_list[0]:
        image_ann(st.session_state)

    if st.session_state['Application'] == app_list[1]:
        ann_correction(st.session_state)


if __name__ == "__main__":
    main()

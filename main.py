import streamlit as st
from streamlit_image_annotation import pointdet
import io
import csv
from PIL import Image
import numpy as np
import pandas as pd


# Define label list
label_list = ['Positivo', 'Negativo', 'No importante']
actions = ['Agregar', 'Borrar']

if 'label' not in st.session_state:
    st.session_state['label'] = 0  # Store selected label

if 'action' not in st.session_state:
    st.session_state['action'] = 0  # Store selected action

if 'all_points' not in st.session_state:
    st.session_state['all_points'] = set()  # Set to track unique point

if 'all_labels' not in st.session_state:
    st.session_state['all_labels'] = {}  # Dictionary to track labels for each unique point

if 'points' not in st.session_state:
    st.session_state['points'] = []

if 'labels' not in st.session_state:
    st.session_state['labels'] = []

# Initialize session state for csv and report data
if 'csv_data' not in st.session_state:
    st.session_state['csv_data'] = b""  # Use empty binary to avoid type errors

if 'report_data' not in st.session_state:
    st.session_state['report_data'] = b""  # Use empty binary to avoid type errors


def update_patch_data(session_state, scale):

    all_points = session_state['all_points'] # Set to track unique point
    all_labels = session_state['all_labels'] # Dictionary to track labels for each unique point

    all_points = list(all_points)
    all_labels = [all_labels[point] for point in all_points]

    points = []
    labels = []

    for point, label in zip(all_points, all_labels):
        x, y = point

        x *= scale[0]
        y *= scale[1]

        points.append(point)
        labels.append(label)

    session_state['points'] = points
    session_state['labels'] = labels


def update_results(session_state, file_name):

    all_points = session_state['all_points']
    all_labels = session_state['all_labels']

    all_points = list(all_points)
    all_labels = [all_labels[point] for point in all_points]

    # Create CSV content
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)
    csv_writer.writerow(["X", "Y", "Label"])
    for point, label in zip(all_points, all_labels):
        csv_writer.writerow([point[0], point[1], label_list[label]])

    # Convert CSV buffer to downloadable file
    csv_data = csv_buffer.getvalue().encode('utf-8')

    # **Generate the Annotation Report**
    num_positive = all_labels.count(0)
    num_negative = all_labels.count(1)

    total = num_positive + num_negative

    if total==0:
        total = -1

    report_content = f"""
    Reporte de anotación
    ==================
    Nombre de la imagen: {file_name}
    Número de puntos positivos: {num_positive} - Porcentaje: {100*num_positive/total}%
    Número de puntos negativos: {num_negative} - Porcentaje: {100*num_negative/total}%
    Cantidad total de elementos {total}
    """

    # Create file-like object to download the report
    report_buffer = io.StringIO()
    report_buffer.write(report_content)
    report_data = report_buffer.getvalue()

    session_state['csv_data'] = csv_data
    session_state['report_data'] = report_data


def update_annotations(new_labels, session_state, scale):

    all_points = session_state['all_points'] # Set to track unique point
    all_labels = session_state['all_labels'] # Dictionary to track labels for each unique point

    patch_points = []

    # Add new points
    for v in new_labels:
        x, y = v['point']

        x = int(x)//scale[0]
        y = int(y)//scale[1]

        label_id = v['label_id']
        patch_points.append([x, y])

        point_tuple = (x, y)

        if point_tuple not in all_points:
            all_points.add(point_tuple)
            all_labels[point_tuple] = label_id  # Store the label for this point

    # Remove points
    removed_points = []
    for global_point in all_points:
        x, y = global_point

        remove_flag = True

        for patch_point in patch_points:

            x_patch, y_patch = patch_point

            nequal_flag = not ( (x == x_patch) and (y == y_patch) )

            remove_flag = remove_flag and nequal_flag

        if remove_flag:
            removed_points.append(global_point)


    for removed_point in removed_points:
        all_points.remove(removed_point)
        del all_labels[removed_point]  # Remove the corresponding label

    session_state['all_points'] = all_points
    session_state['all_labels'] = all_labels


def main():

    display_size = [1024, 1024]

    st.sidebar.header("Seleccionar zoom")
    with st.sidebar:
        zoom = st.number_input(
            "Zoom", 
            min_value=1, 
            max_value=4, 
            value=1, 
            step=1
        )            


    # Sidebar content
    st.sidebar.header("Anotación de imágenes")

    with st.sidebar:

        col1, col2 = st.columns([2, 2])
        with col1:
            st.session_state['action'] = st.selectbox("Acción:", actions)

        with col2:
            st.session_state['label'] = st.selectbox("Clase:", label_list)




    # Image upload
    uploaded_file = st.file_uploader("Subir imagen", type=["jpg", "jpeg", "png"])

    # Check if an image is uploaded
    if uploaded_file is not None:

        uploaded_file_name = uploaded_file.name[:-4]

        # Open the uploaded image using PIL
        image = Image.open(uploaded_file)


        width, height = image.size

        scale  = [ 1,
                   1] 

        image.save(uploaded_file.name)
        
        update_patch_data(st.session_state, scale)

        img_path = uploaded_file.name

        action = st.session_state['action']
        if action == actions[1]:
            mode = 'Del'
        else:
            mode = 'Transform'
                    
        # Use pointdet to annotate the image
        new_labels = pointdet(
            image_path=img_path,
            label_list=label_list,
            points=st.session_state['points'],
            labels=st.session_state['labels'],
            width = width,
            height = height,
            use_space=True,
            key=img_path,
            mode = mode,
            label = st.session_state['label'],
            point_width=5,
            zoom=zoom,
        )
        
        # Update points and labels in session state if any changes are made
        if new_labels is not None:
            update_annotations(new_labels, st.session_state, scale)
            update_results(st.session_state, uploaded_file_name)

        st.sidebar.header("Resultados")
        # Sidebar buttons
        with st.sidebar:
            # **1st Download Button** - CSV Annotations
            st.download_button(
                label="Descargar anotaciones (CSV)",
                data=st.session_state['csv_data'],
                file_name=f"{uploaded_file_name}.csv",
                mime="text/csv"
            )

            # **2nd Download Button** - Annotation Report
            st.download_button(
                label="Descargar Reporte (txt)",
                data=st.session_state['report_data'],
                file_name=f'{uploaded_file_name}.txt',
                mime='text/plain'
            )



if __name__ == "__main__":
    main()

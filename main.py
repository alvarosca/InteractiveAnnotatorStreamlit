import streamlit as st
from streamlit_image_annotation import pointdet
import io
import csv
from PIL import Image
from PIL import Image, ImageDraw
import numpy as np
import pandas as pd
import os

# Folders
image_dir  = "./images"
ann_dir    = "./annotations"
report_dir = "./reports"

# We want the wide mode to be set by default
st.set_page_config(page_title=None, page_icon=None, layout="wide", initial_sidebar_state="auto", menu_items=None)

# Define label list
label_list = ['Positivo', 'Negativo', 'No importante']
actions = ['Agregar', 'Borrar']


def init_session(session_state):

    session_state['all_points'] = set()  # Set to track unique point
    session_state['all_labels'] = {}  # Dictionary to track labels for each unique point
    session_state['points'] = []
    session_state['labels'] = []
    session_state['csv_data'] = b""
    session_state['report_data'] = b""
    session_state['ann_image'] = b"" 


def recover_session(session_state, all_points, all_labels, image, file_name):

    session_state['all_points'] = all_points 
    session_state['all_labels'] = all_labels 

    update_patch_data(session_state)
    update_results(session_state, file_name)
    update_ann_image(session_state, image)


def update_patch_data(session_state):

    all_points = session_state['all_points']
    all_labels = session_state['all_labels']

    all_points = list(all_points)
    all_labels = [all_labels[point] for point in all_points]

    points = []
    labels = []

    for point, label in zip(all_points, all_labels):
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

    # Save CSV data to file
    csv_data = csv_buffer.getvalue()
    csv_filename = f"{ann_dir}/{file_name}.csv"
    with open(csv_filename, "w", encoding="utf-8") as csv_file:
        csv_file.write(csv_data)

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

    # Save report to file
    report_filename = f"{report_dir}/{file_name}.txt"
    with open(report_filename, "w", encoding="utf-8") as report_file:
        report_file.write(report_content)

    session_state['csv_data'] = csv_data
    session_state['report_data'] = report_data


def update_annotations(new_labels, session_state):

    all_points = session_state['all_points'] # Set to track unique point
    all_labels = session_state['all_labels'] # Dictionary to track labels for each unique point

    patch_points = []

    # Add new points
    for v in new_labels:
        x, y = v['point']

        x = int(x)
        y = int(y)

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


def update_ann_image(session_state, image):
    """
    Overlays points on the image with colors corresponding to their labels 
    and stores the result in the session state for display and download.

    Args:
        session_state: dict containing `all_points` and `all_labels`.
            - `all_points`: List of tuples representing points (x, y).
            - `all_labels`: Dictionary mapping points to labels.
        image: PIL.Image object representing the base image.
    """

    # Extract points and labels
    all_points = session_state['all_points']  # List of tuples [(x1, y1), (x2, y2), ...]
    all_labels = session_state['all_labels']  # Dict: {(x1, y1): "label1", (x2, y2): "label2", ...}

    # Define colors for each label
    label_colors = {
        0: (255, 0, 0),  # Red
        1: (0, 255, 0),  # Green
        2: (0, 0, 255),  # Blue
        # Add more labels and their colors as needed
    }

    # Create a drawable image
    ann_image = image.copy()
    draw = ImageDraw.Draw(ann_image)

    # Draw each point with the corresponding color
    point_radius = 7.5  # Radius of each point
    for point in all_points:
        x, y = point
        label = all_labels.get(point, "default")  # Get the label for the point
        color = label_colors.get(label, (255, 255, 255))  # Default to white if label not found

        # Draw the point as a filled circle
        draw.ellipse(
            [(x - point_radius, y - point_radius), (x + point_radius, y + point_radius)],
            outline=color,
            width=5,
        )

    # Convert the annotated image to a downloadable JPEG format
    image_buffer = io.BytesIO()
    ann_image.save(image_buffer, format="PNG")
    image_buffer.seek(0)

    # Store the annotated image
    session_state['ann_image'] = image_buffer


def check_files(image_file_name, folder_path="./images"):
    """
    Checks if a file (without its extension) exists in the specified folder.

    Args:
        image_file_name (str): The name of the file to check (without extension).
        folder_path (str): The path of the folder to search in. Default is "/path/to/your/folder".

    Returns:
        bool: True if the file (ignoring extensions) exists, False otherwise.
    """
    # Normalize the file name to search (strip extension if any)
    image_file_base = os.path.splitext(image_file_name)[0]

    # List all files in the folder without their extensions
    file_names_in_folder = [
        os.path.splitext(f)[0]
        for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f))
    ]

    # Check if the file exists (case-sensitive)
    return image_file_base in file_names_in_folder


def read_results_from_csv(csv_filename):
    """
    Reads the contents of a CSV file created by the `update_results` function
    and extracts all_points and all_labels.

    Args:
        csv_filename (str): Path to the CSV file to read.

    Returns:
        tuple: A tuple containing:
            - all_points (list of tuples): List of points [(x1, y1), (x2, y2), ...].
            - all_labels (list): List of labels corresponding to each point.
    """
    all_points = set()
    all_labels = {}

    try:
        with open(csv_filename, mode="r", encoding="utf-8") as csv_file:
            csv_reader = csv.DictReader(csv_file)  # Read CSV with headers
            for row in csv_reader:
                # Extract X, Y, and Label, and reconstruct all_points and all_labels
                x = int(row["X"])
                y = int(row["Y"])
                label_id = label_list.index(row["Label"])
                point_tuple = (x, y)

                all_points.add(point_tuple)
                all_labels[point_tuple] = label_id  # Store the label for this point

    except FileNotFoundError:
        print(f"Error: File '{csv_filename}' not found.")
    except Exception as e:
        print(f"Error reading the file: {e}")
    
    return all_points, all_labels


def check_latest_session_log(log_path = "latest_sesssion.log"):
    try:
        with open(log_path, 'r', encoding='utf-8') as file:
            contents = file.read()

        return contents

    except FileNotFoundError:
        return "NoImage"
    except Exception as e:
        return "NoImage"


def store_latest_session_log(file_name, log_path = "latest_sesssion.log"):
    try:
        with open(log_path, 'w', encoding='utf-8') as file:
            file.write(file_name)
    except Exception as e:
        print(f"An error occurred: {e}")


def main():

    image_file_name = None

    # Image upload
    uploaded_file = st.file_uploader("Subir imagen ", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image_file_name = uploaded_file.name
        image = Image.open(uploaded_file)
        width, height = image.size
        img_path = f"{image_dir}/{image_file_name}"

    else:
        # Check latest image
        latest_image = check_latest_session_log()
        result = check_files(latest_image)

        if result:
            # Recover the latest image
            image_file_name = latest_image
            image = Image.open(f"{image_dir}/{latest_image}")    
            width, height = image.size
            img_path = f"{image_dir}/{image_file_name}"


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

    
    if image_file_name is not None:

        # Check if a new image is uploaded
        if 'image_file_name' not in st.session_state or st.session_state['image_file_name'] != image_file_name:

            st.session_state['image_file_name'] = image_file_name

            result = check_files(image_file_name)

            if result: # Recover previous annotations
                csv_file_name = f"{ann_dir}/{image_file_name[:-4]}.csv"
                all_points, all_labels = read_results_from_csv(csv_file_name)
                recover_session(st.session_state, all_points, all_labels, image, image_file_name[:-4])

            else:
                image.save(img_path)
                init_session(st.session_state)

            store_latest_session_log(image_file_name)

        # Check if user got disconnected
        try:
            # Attempt to get session data
            all_points = st.session_state["all_points"]

        except KeyError:
            csv_file_name = f"{ann_dir}/{image_file_name[:-4]}.csv"
            all_points, all_labels = read_results_from_csv(csv_file_name)
            recover_session(st.session_state, all_points, all_labels, image, image_file_name[:-4])


        update_patch_data(st.session_state)

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
            update_annotations(new_labels, st.session_state)
            update_results(st.session_state, image_file_name[:-4])
            update_ann_image(st.session_state, image)

        st.sidebar.header("Resultados")
        # Sidebar buttons
        with st.sidebar:
            # **1st Download Button** - CSV Annotations
            st.download_button(
                label="Descargar anotaciones (CSV)",
                data=st.session_state['csv_data'],
                file_name=f"{image_file_name[:-4]}.csv",
                mime="text/csv"
            )

            # **2nd Download Button** - Annotation Report
            st.download_button(
                label="Descargar reporte (txt)",
                data=st.session_state['report_data'],
                file_name=f'{image_file_name[:-4]}.txt',
                mime='text/plain'
            )

            st.download_button(
                label="Descargar imagen anotada (png)",
                data=st.session_state['ann_image'],
                file_name=f'{image_file_name[:-4]}_annotated.png',
                mime='image/png'
            )



if __name__ == "__main__":
    main()

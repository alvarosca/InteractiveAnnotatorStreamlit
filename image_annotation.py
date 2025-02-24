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
    # session_state['ann_image'] = b"" 


def update_patch_data(session_state, all_points, all_labels):

    points = list(all_points)
    labels = [all_labels[point] for point in all_points]

    session_state['points'] = points
    session_state['labels'] = labels


def update_results(session_state, all_points, all_labels, file_name):

    points = list(all_points)
    labels = [all_labels[point] for point in all_points]

    # Create CSV content
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)
    csv_writer.writerow(["X", "Y", "Label"])
    for point, label in zip(points, labels):
        csv_writer.writerow([point[0], point[1], label_list[label]])

    # Convert CSV buffer to downloadable file
    csv_data = csv_buffer.getvalue().encode('utf-8')

    # Save CSV data to file
    csv_data = csv_buffer.getvalue()
    csv_filename = f"{ann_dir}/{file_name}.csv"
    with open(csv_filename, "w", encoding="utf-8") as csv_file:
        csv_file.write(csv_data)

    # **Generate the Annotation Report**
    num_positive = labels.count(0)
    num_negative = labels.count(1)

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


def update_annotations(new_labels, all_points, all_labels, session_state):

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

        else:
            all_labels[point_tuple] = label_id

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

    return all_points, all_labels


# def update_ann_image(session_state, all_points, all_labels, image):
#     """
#     Overlays points on the image with colors corresponding to their labels 
#     and stores the result in the session state for display and download.

#     Args:
#         session_state: dict containing `all_points` and `all_labels`.
#             - `all_points`: List of tuples representing points (x, y).
#             - `all_labels`: Dictionary mapping points to labels.
#         image: PIL.Image object representing the base image.
#     """

#     # Define colors for each label
#     label_colors = {
#         0: (255, 0, 0),  # Red
#         1: (0, 255, 0),  # Green
#         2: (0, 0, 255),  # Blue
#         # Add more labels and their colors as needed
#     }

#     # Create a drawable image
#     ann_image = image.copy()
#     draw = ImageDraw.Draw(ann_image)

#     # Draw each point with the corresponding color
#     point_radius = 7.5  # Radius of each point
#     for point in all_points:
#         x, y = point
#         label = all_labels.get(point, "default")  # Get the label for the point
#         color = label_colors.get(label, (255, 255, 255))  # Default to white if label not found

#         # Draw the point as a filled circle
#         draw.ellipse(
#             [(x - point_radius, y - point_radius), (x + point_radius, y + point_radius)],
#             outline=color,
#             width=5,
#         )

#     # Convert the annotated image to a downloadable JPEG format
#     image_buffer = io.BytesIO()
#     ann_image.save(image_buffer, format="PNG")
#     image_buffer.seek(0)

#     # Store the annotated image
#     session_state['ann_image'] = image_buffer


def recover_session(session_state, all_points, all_labels, file_name, image=None):

    session_state['all_points'] = all_points 
    session_state['all_labels'] = all_labels 

    update_patch_data(session_state, all_points, all_labels)
    update_results(session_state, all_points, all_labels, file_name)
    # update_ann_image(session_state, all_points, all_labels, image)


def check_latest_session_log(log_path = "latest_session.log"):
    try:
        with open(log_path, 'r', encoding='utf-8') as file:
            contents = file.read()

        return contents

    except FileNotFoundError:
        return "NoImage"
    except Exception as e:
        return "NoImage"


def store_latest_session_log(file_name, log_path = "latest_session.log"):
    try:
        with open(log_path, 'w', encoding='utf-8') as file:
            file.write(file_name)
    except Exception as e:
        print(f"An error occurred: {e}")


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


def get_image(session_state):

    image_file_name = None
    img_path = None

    # Image upload
    uploaded_file = st.file_uploader("Subir imagen ", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image_file_name = uploaded_file.name
        img_path = f"{image_dir}/{image_file_name}"
        image = Image.open(uploaded_file)

    # No image was uploaded - We use the latest one from a previous session
    else: 
        latest_image = check_latest_session_log()
        result = check_files(latest_image)
        if result:
            image_file_name = latest_image
            img_path = f"{image_dir}/{image_file_name}"
            image = Image.open(img_path)

        else: # No image from previous session
            return image_file_name, img_path
            
    if 'image_file_name' not in session_state or session_state['image_file_name'] != image_file_name:
        handle_new_image(session_state, image, image_file_name, img_path)
        session_state['image_file_name'] = image_file_name
        session_state['img_path'] = img_path

    else:
        image_file_name = session_state['image_file_name']
        img_path = session_state['img_path']    
        return image_file_name, img_path
        
    return image_file_name, img_path    


def handle_new_image(session_state, image, image_file_name, img_path):

    # We check if the image was previously annotated
    result = check_files(image_file_name)

    if result: # Recover previous annotations
        base_name = os.path.splitext(image_file_name)[0]
        csv_file_name = f"{ann_dir}/{base_name}.csv"
        all_points, all_labels = read_results_from_csv(csv_file_name)
        recover_session(session_state, all_points, all_labels, base_name)

    else: # We store a backup of the image
        image.save(img_path)
        init_session(session_state)


    height = image.size[1]
    width  = image.size[0]
    scale = 1280/width
    session_state['resized_image'] = image.resize((1280, int(scale*height)))
    session_state['height'] = int(scale*height)
    session_state['scale'] = scale

    # We log the name of the image for session backups
    store_latest_session_log(image_file_name)


def image_ann(session_state):

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
            session_state['action'] = st.selectbox("Acción:", actions)

        with col2:
            session_state['label'] = st.selectbox("Clase:", label_list)


    image_file_name, img_path = get_image(session_state)

    if image_file_name is not None:
        try:
            all_points = session_state['all_points']
            all_labels = session_state['all_labels']

            # Translate the selected action
            action = session_state['action']
            if action == actions[1]:
                mode = 'Del'
            else:
                mode = 'Transform'

        # User got disconnected - We recover the previous session
        except KeyError:
            image = Image.open(img_path)
            handle_new_image(session_state, image, image_file_name, img_path)

            base_name = os.path.splitext(image_file_name)[0]
            csv_file_name = f"{ann_dir}/{base_name}.csv"
            all_points, all_labels = read_results_from_csv(csv_file_name)
            recover_session(session_state, all_points, all_labels, base_name)

            mode  = 'Transform'


        update_patch_data(session_state, all_points, all_labels)
                    
        # Use pointdet to annotate the image
        new_labels = pointdet(
            image=session_state['resized_image'],
            label_list=label_list,
            points=session_state['points'],
            labels=session_state['labels'],
            width = 1280,
            height = session_state['height'],
            manual_scale = session_state['scale'],
            use_space=True,
            key=img_path,
            mode = mode,
            label = session_state['label'],
            point_width=5,
            zoom=zoom,
        )
        
        # Update points and labels in session state if any changes are made
        if new_labels is not None:

            # Incorporate the new labels
            all_points, all_labels = update_annotations(new_labels, all_points, all_labels, session_state)

            # Update results
            base_name = os.path.splitext(image_file_name)[0]
            update_results(session_state, all_points, all_labels, base_name)
            # update_ann_image(session_state, all_points, all_labels, image)



    # Download results
    if 'image_file_name' in session_state:
        st.sidebar.header("Resultados")
        with st.sidebar:
            image_name = os.path.splitext(session_state['image_file_name'])[0]
            # **1st Download Button** - CSV Annotations
            st.download_button(
                label="Descargar anotaciones (CSV)",
                data=session_state['csv_data'],
                file_name=f"{image_name}.csv",
                mime="text/csv"
            )

            # **2nd Download Button** - Annotation Report
            st.download_button(
                label="Descargar reporte (txt)",
                data=session_state['report_data'],
                file_name=f'{image_name}.txt',
                mime='text/plain'
            )

            # # **3rd Download Button** - Annotated Image
            # st.download_button(
            #     label="Descargar imagen anotada (png)",
            #     data=session_state['ann_image'],
            #     file_name=f'{image_name}_annotated.png',
            #     mime='image/png'
            # )
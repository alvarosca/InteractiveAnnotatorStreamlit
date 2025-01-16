
import numpy as np
from PIL import Image, ImageDraw
import cv2
import tifffile as tiff
import random
import json

from image_annotation import *

# Folders
image_dir  = "./images"
ann_dir    = "./annotations"
mask_dir    = "./masks"
report_dir = "./reports"

contours_options = ["Si", "No"]

def load_masks(unique_labels, masks_path="masks.tif"):

    number_of_classes = len(unique_labels)+1

    loaded_mask = tiff.imread(masks_path)

    mask_shape = loaded_mask.shape
    mask_height = mask_shape[0]
    mask_width = mask_shape[1]

    number_of_masks = np.max(loaded_mask)//number_of_classes

    masks = np.zeros((number_of_masks, mask_height, mask_width)).astype(bool)
    labels = np.zeros((number_of_masks))

    for y in range(mask_height):
        for x in range(mask_width):
            if loaded_mask[y,x]!=0:
                label_id = loaded_mask[y,x] % number_of_classes
                mask_id = loaded_mask[y,x] // number_of_classes - 1
                masks[mask_id][y,x]=True
                labels[mask_id] = label_id


    return masks, labels


def load_masks_from_json(unique_labels, input_path="masks.json", mask_shape=(512, 512)):
    """
    Loads masks and labels from a compact JSON file containing contours.

    Parameters:
        unique_labels (list): List of unique labels.
        input_path (str): Path to the JSON file.
        mask_shape (tuple): Shape of the output masks (height, width).

    Returns:
        masks (list): List of reconstructed masks as binary numpy arrays.
        labels (list): List of labels corresponding to the masks.
    """
    # Load JSON data
    with open(input_path, "r") as json_file:
        data = json.load(json_file)

    contours_list = data["contours"]
    labels_list = data["labels"]

    masks = []
    labels = []

    for contour, label in zip(contours_list, labels_list):
        # Reconstruct mask
        mask = np.zeros(mask_shape, dtype=np.uint8)
        contour_np = np.array(contour, dtype=np.int32)
        cv2.drawContours(mask, [contour_np], -1, 1, thickness=cv2.FILLED)

        masks.append(mask.astype(bool))
        labels.append(label)

    return masks, labels


# Function to generate a random color
def random_color():
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 128)  # RGBA with 50% opacity

# Create RGBA image from list of masks
def create_rgba_image(masks, image_size):
    # Initialize a transparent RGBA image
    base_image = Image.new("RGBA", image_size, (0, 0, 0, 0))  # Transparent background

    for mask in masks:
        # Convert the mask to a Pillow image if it's a NumPy array
        if isinstance(mask, np.ndarray):
            mask_image = Image.fromarray((mask * 255).astype(np.uint8))  # Scale mask to 0-255
        else:
            mask_image = mask  # Assume it's already a Pillow image

        # Generate a random color for the mask
        color = random_color()

        # Create a colored overlay
        overlay = Image.new("RGBA", image_size, color)
        # Use the mask as an alpha channel for the overlay
        base_image = Image.alpha_composite(base_image, Image.composite(overlay, base_image, mask_image))

    return base_image

# Create RGBA image with only the contours of the masks
def create_contour_image(masks, image_size, contour_thickness=2):
    """
    Create an RGBA image with contours of the masks.

    Args:
        masks: List of binary masks (NumPy arrays or Pillow images).
        image_size: Tuple indicating the size of the image (width, height).
        contour_thickness: Thickness of the contour lines.

    Returns:
        A Pillow Image object with the contours.
    """
    # Initialize a transparent RGBA image
    base_image = Image.new("RGBA", image_size, (0, 0, 0, 0))  # Transparent background
    draw = ImageDraw.Draw(base_image)

    for mask in masks:
        # Convert the mask to a NumPy array if it's a Pillow image
        if not isinstance(mask, np.ndarray):
            mask = np.array(mask)

        # Extract the contour points from the binary mask
        contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Draw each contour on the base image
        for contour in contours:
            # Generate a random color for the contour
            # color = random_color()
            color = (0,128,128)

            # Convert contour to a list of tuples for Pillow
            contour_points = [(int(point[0][0]), int(point[0][1])) for point in contour]

            # Draw the contour with the specified thickness
            draw.line(contour_points + [contour_points[0]], fill=color, width=contour_thickness)

    return base_image


def get_annotations(session_state, image_file_name):

    ann_file_name = None

    # Image upload
    uploaded_file = st.file_uploader("Subir anotaciones ", type=["csv"])

    if uploaded_file is not None:
        if 'ann_file_name' not in session_state or session_state['ann_file_name'] != uploaded_file.name: 

            session_state['ann_file_name'] = uploaded_file.name

            base_name = os.path.splitext(image_file_name)[0]
            ann_file_name = f"{ann_dir}/{base_name}.csv"

            # Overwrite the current annotations csv file
            with open(ann_file_name, "wb") as f:
                f.write(uploaded_file.read())  # Save the file locally

            # Force annotation csv retrieval
            if 'image_file_name' in session_state:
                session_state['image_file_name'] = " "


        else:
            ann_file_name = session_state['ann_file_name']

    return ann_file_name


def get_masks(session_state, image_size, label_list, mask_dir = "./masks"):

    masks = []     
    mask_labels = []
    mask_img_path = None
    contour_img_path = None

    # Image upload
    uploaded_file = st.file_uploader("Subir máscaras ", type=["tif","json"])

    if uploaded_file is not None:

        if 'mask_file_name' not in session_state or session_state['mask_file_name'] != uploaded_file.name: 

            session_state['mask_file_name'] = uploaded_file.name

            # Save tif file in 'mask_dir'
            masks_file_name = os.path.join(mask_dir, uploaded_file.name)
            with open(masks_file_name, "wb") as f:
                f.write(uploaded_file.read())  # Save the file locally

            if uploaded_file.name[-4:]==".tif":
                masks, mask_labels = load_masks(label_list, masks_file_name)

            elif uploaded_file.name[-5:]==".json":
                masks, mask_labels = load_masks_from_json(
                    label_list, masks_file_name, mask_shape=(image_size[1], image_size[0]))

            else:
                # Error
                return masks, mask_labels, mask_img_path, contour_img_path


            mask_img = create_rgba_image(masks, image_size)
            contour_img = create_contour_image(masks, image_size)

            mask_img_path = f"{mask_dir}/{uploaded_file.name}.png"
            mask_img.save(mask_img_path)

            contour_img_path = f"{mask_dir}/{uploaded_file.name}_contour.png"
            contour_img.save(contour_img_path)

            session_state['masks'] = masks        
            session_state['mask_labels'] = mask_labels 
            session_state['mask_img_path'] = mask_img_path
            session_state['contour_img_path'] = contour_img_path

        else:
            masks = session_state['masks']
            mask_labels = session_state['mask_labels']
            mask_img_path = session_state['mask_img_path']
            contour_img_path = session_state['contour_img_path']

    return masks, mask_labels, mask_img_path, contour_img_path



def ann_correction(session_state):

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

        col1, col2 = st.columns([2, 2])
        with col1:
            contours_option = st.selectbox("Contornos:", contours_options)
            if contours_options.index(contours_option)==0:
                session_state['display_contours'] = 1
            else:
                session_state['display_contours'] = 0

        with col2:
            session_state['transparency'] = st.slider("Transparencia:", 
                    min_value=0.0, max_value=1.0, value=0.5, step=0.01)


    image, image_file_name, img_path = get_image()
    if image is not None:
        ann_file_name = get_annotations(session_state, image_file_name)
        masks, mask_labels, mask_img_path, contour_img_path = \
            get_masks(session_state, image.size, label_list)


    if image_file_name is not None:

        refresh_canvas = False
        # Check if a new image is uploaded
        if 'image_file_name' not in session_state or session_state['image_file_name'] != image_file_name:
            handle_new_image(session_state, image, image_file_name, img_path)
            refresh_canvas = True

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
            base_name = os.path.splitext(image_file_name)[0]
            csv_file_name = f"{ann_dir}/{base_name}.csv"
            all_points, all_labels = read_results_from_csv(csv_file_name)
            recover_session(session_state, all_points, all_labels, image, base_name)

            mode  = 'Transform'


        update_patch_data(session_state, all_points, all_labels)

        if refresh_canvas: # Force update of the canvas by loading the default image
            img_path = "./images/example_image.jpg"

        # Use pointdet to annotate the image
        new_labels = pointdet(
            image_path=img_path,
            mask_path=mask_img_path,
            contour_path=contour_img_path,
            label_list=label_list,
            points=session_state['points'],
            labels=session_state['labels'],
            width = image.size[0],
            height = image.size[1],
            use_space=True,
            key=img_path,
            mode = mode,
            label = session_state['label'],
            point_width=5,
            zoom=zoom,
            m_transparency = session_state['transparency'],
            c_transparency = session_state['display_contours']
        )

        
        # Update points and labels in session state if any changes are made
        if new_labels is not None:

            # Incorporate the new labels
            all_points, all_labels = update_annotations(new_labels, all_points, all_labels, session_state)

            # Update results
            base_name = os.path.splitext(image_file_name)[0]
            update_results(session_state, all_points, all_labels, base_name)
            update_ann_image(session_state, all_points, all_labels, image)


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

            # **3rd Download Button** - Annotated Image
            st.download_button(
                label="Descargar imagen anotada (png)",
                data=session_state['ann_image'],
                file_name=f'{image_name}_annotated.png',
                mime='image/png'
            )
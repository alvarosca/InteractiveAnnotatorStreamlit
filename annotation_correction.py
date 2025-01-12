
import numpy as np
from PIL import Image, ImageDraw
import cv2

from image_annotation import *

def overlay_masks_on_image(pil_image, masks, mask_colors=[], transparency=0.5, thickness=1, borders=True):
    """
    Overlay annotations on a PIL image and return the modified image.

    Args:
        pil_image (PIL.Image.Image): The input image.
        anns (list): List of annotation dictionaries. Each dictionary should contain a 'segmentation' key with a boolean mask.
        mask_colors (list): List of colors for the masks in RGB format. Defaults to green for all masks.
        transparency (float): Transparency of the overlay masks (0 to 1).
        thickness (int): Thickness of the border lines.
        borders (bool): Whether to draw borders around the masks.

    Returns:
        PIL.Image.Image: The image with annotations overlayed.
    """
    if len(masks) == 0:
        return pil_image

    # Generate default mask colors if none are provided
    if len(mask_colors) == 0:
        mask_colors = np.tile(np.array([[0, 255, 0]]), (len(masks), 1))

    # Convert PIL image to RGBA if not already in that mode
    img = pil_image.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))

    for mask, fill_color in zip(masks, mask_colors):
        fill_color = [int(c) for c in fill_color]
        rgba_fill = (*fill_color, int(255 * transparency))
        # Create a mask image from the segmentation
        mask = Image.fromarray((mask * 255).astype(np.uint8), mode="L")
        overlay.paste(Image.new("RGBA", img.size, rgba_fill), mask=mask)

        if borders:
            # Draw borders
            contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            contours = [cv2.approxPolyDP(contour, epsilon=0.01, closed=True) for contour in contours]
            draw = ImageDraw.Draw(overlay)
            for contour in contours:
                points = [tuple(pt[0]) for pt in contour]
                draw.line(points + [points[0]], fill=(0, 0, 255, int(255 * 0.4)), width=thickness)

    # Combine the original image with the overlay
    combined = Image.alpha_composite(img, overlay)
    return combined



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

    if 'image_file_name' in session_state:
        st.sidebar.header("Resultados")
        # Sidebar buttons
        with st.sidebar:
            image_name = session_state['image_file_name'][:-4]
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

            st.download_button(
                label="Descargar imagen anotada (png)",
                data=session_state['ann_image'],
                file_name=f'{image_name}_annotated.png',
                mime='image/png'
            )


    # Image upload
    uploaded_image_file = st.file_uploader("Subir imagen ", type=["jpg", "jpeg", "png"])
    uploaded_ann_file = st.file_uploader("Subir anotaciones ", type=["csv"])
    uploaded_mask_file = st.file_uploader("Subir máscaras ", type=["tif"])

    if uploaded_image_file is not None:
        image_file_name = uploaded_image_file.name
        image = Image.open(uploaded_image_file)
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


    if image_file_name is not None:

        # Check if a new image is uploaded
        if 'image_file_name' not in session_state or session_state['image_file_name'] != image_file_name:

            session_state['image_file_name'] = image_file_name

            result = check_files(image_file_name)

            if result: # Recover previous annotations
                csv_file_name = f"{ann_dir}/{image_file_name[:-4]}.csv"
                all_points, all_labels = read_results_from_csv(csv_file_name)
                recover_session(session_state, all_points, all_labels, image, image_file_name[:-4])

            else:
                image.save(img_path)
                init_session(session_state)

            store_latest_session_log(image_file_name)

        # Check if user got disconnected
        try:
            # Attempt to get session data
            all_points = session_state["all_points"]

        except KeyError:
            csv_file_name = f"{ann_dir}/{image_file_name[:-4]}.csv"
            all_points, all_labels = read_results_from_csv(csv_file_name)
            recover_session(session_state, all_points, all_labels, image, image_file_name[:-4])


        update_patch_data(session_state)

        action = session_state['action']
        if action == actions[1]:
            mode = 'Del'
        else:
            mode = 'Transform'
                    
        # Use pointdet to annotate the image
        new_labels = pointdet(
            image_path=img_path,
            label_list=label_list,
            points=session_state['points'],
            labels=session_state['labels'],
            width = width,
            height = height,
            use_space=True,
            key=img_path,
            mode = mode,
            label = session_state['label'],
            point_width=5,
            zoom=zoom,
        )
        
        # Update points and labels in session state if any changes are made
        if new_labels is not None:
            update_annotations(new_labels, session_state)
            update_results(session_state, image_file_name[:-4])
            update_ann_image(session_state, image)

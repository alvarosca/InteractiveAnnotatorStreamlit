
import numpy as np
from PIL import Image, ImageDraw

from image_annotation import *
from pydrive_utils import *

checked_symbol = '(✅)'
unchecked_symbol = ''

# Folders
image_dir  = "./images"
ann_dir    = "./annotations"
report_dir = "./reports"
anns_todo_dir = 'anotaciones_a_corregir'
anns_done_dir = 'anotaciones_corregidas'

label_list = ['Positivo', 'Negativo', 'No importante']

path_to_json_key = "pydrive_credentials.json"

def setup_drive(session_state):
    drive = get_drive(path_to_json_key)

    folder_dict, todo_dict, done_dict = \
        get_dicts(drive, anns_todo_dir, anns_done_dir)

    session_state['drive']=drive
    session_state['todo_dict'] = todo_dict
    session_state['done_dict'] = done_dict
    session_state['folder_dict'] = folder_dict

    todo_sample_names = list(todo_dict.keys()) 
    done_sample_names = list(done_dict.keys())

    sample_list = {}
    for sample_name in todo_sample_names:
        sample_list[sample_name] = False
    for sample_name in done_sample_names:
        sample_list[sample_name] = True

    # Create display names reflecting annotation status
    display_samples = [f"{name} {checked_symbol if annotated else unchecked_symbol}"
                        for name, annotated in sample_list.items()]

    sample_names = list(sample_list.keys()) 

    session_state['display_samples'] = display_samples
    session_state['sample_names'] = sample_names


def load_sample(session_state, selected_sample):

    # Check if selected sample is alreaded downloaded
    img_path = None
    for file in os.listdir(image_dir):
        if os.path.splitext(file)[0].strip() == selected_sample.strip():
            img_path = f"{image_dir}/{file}" 
            ann_file_path  = f"{ann_dir}/{selected_sample}.csv"
            break

    # Download sample
    if img_path is None:
        drive = session_state['drive']
        todo_dict = session_state['todo_dict']
        done_dict = session_state['done_dict']

        if selected_sample in todo_dict.keys():
            img_path = get_gdrive_image_path(drive, 
                todo_dict[selected_sample], image_dir, selected_sample)
            ann_file_path = get_gdrive_csv_path(drive, 
                todo_dict[selected_sample], ann_dir, selected_sample)

        else:
            img_path = get_gdrive_image_path(drive, 
                done_dict[selected_sample], image_dir, selected_sample)    
            ann_file_path = get_gdrive_csv_path(drive, 
                done_dict[selected_sample], ann_dir, selected_sample)


    image_file_name = selected_sample 
    image = Image.open(img_path)
    height = image.size[1]
    width  = image.size[0]
    scale = 1280/width
    session_state['resized_image'] = image.resize((1280, int(scale*height)))
    session_state['height'] = int(scale*height)
    session_state['scale'] = scale

    with open(ann_file_path, 'r', encoding='utf-8') as ann_csv:
        annotations = ann_csv.read()

    session_state['image_file_name'] = image_file_name
    session_state['img_path'] = img_path
    session_state['annotations'] = annotations

    all_points, all_labels = read_results_from_csv(ann_file_path)
    session_state['all_points'] = all_points
    session_state['all_labels'] = all_labels

    # This must be done last
    session_state['load_succesful'] = True



def finish_annotation(session_state, selected_sample):

    drive = session_state['drive']
    done_dict = session_state['done_dict']
    todo_dict = session_state['todo_dict']
    folder_dict = session_state['folder_dict']

    done_folder_id = folder_dict[anns_done_dir]['id']

    if selected_sample in todo_dict.keys():
        file_list = todo_dict[selected_sample]
        for file in file_list:
            move_file(drive, file['id'], done_folder_id)
    else:
        file_list = done_dict[selected_sample]

    x_coords = []
    y_coords = []
    labels = []
    for point in session_state['all_points']:
        x_coords.append(point[0])
        y_coords.append(point[1])
        label_int = session_state['all_labels'][point]
        labels.append(label_list[label_int])

    update_gdrive_csv(drive, file_list, 
        x_coords, y_coords, labels)



def ann_correction(session_state):

    if 'drive' not in session_state:
        
        json_contents = st.secrets["service_account"]["credentials"]
        json_contents = json.loads(json_contents)

        with open(path_to_json_key, "w") as json_file:
            json.dump(json_contents, json_file, indent=4)  # Pretty formatting

        init_session(session_state)
        setup_drive(session_state)

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

    # Add a button to the sidebar
    st.sidebar.header("Finalizar")
    if st.sidebar.button("Finalizar correción"):
        if 'selected_sample' in session_state:
            finish_annotation(session_state, session_state['selected_sample'])
            setup_drive(session_state) # Update drive

    # Get selected sample
    display_sample = st.selectbox("Elegir una muestra:", session_state['display_samples'])
    selected_sample = session_state['sample_names'][
        session_state['display_samples'].index(display_sample)]
    
    # We check for changes on the selected sample
    if 'selected_sample' not in session_state or \
        session_state['selected_sample']!=selected_sample:

        # We update the selected sample and trigger
        # the loading of the sample 
        session_state['load_succesful'] = False
        session_state['selected_sample'] = selected_sample

    # We check if the last load was succesful
    if 'load_succesful' not in session_state or \
        session_state['load_succesful']!=True:
       load_sample(session_state, selected_sample)

    if 'image_file_name' in session_state:
        image_file_name  = session_state['image_file_name']
        img_path = session_state['img_path']

    else:
        image_file_name = None

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
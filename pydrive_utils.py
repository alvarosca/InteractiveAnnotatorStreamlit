import os
import json
from itertools import groupby
#from io import BytesIO, StringIO

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

def get_drive(path_to_json):
    """Get the Drive instance from the service account keys.
    
    Parameters
    ----------
    path_to_json : str
        Path to the json file that contains the service account credentials.

    Returns
    -------
    drive : GoogleDrive
        Drive as a PyDrive2 ``GoogleDrive`` object.

    """
    # Set scope. This particular choice makes sure to give full access.
    scope = ["https://www.googleapis.com/auth/drive"]

    # Authorization instance.
    gauth = GoogleAuth()
    gauth.auth_method = 'service'
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
        path_to_json, 
        scope
    )

    # Get drive.
    drive = GoogleDrive(gauth)
    
    # Return drive.
    return drive

def get_dicts(drive, todo_name, done_name):
    """Get dictionaries for to-do files, done files and their folders.
    
    Parameters
    ----------
    drive : GoogleDrive
        Drive as a PyDrive2 ``GoogleDrive`` object.
    todo_name : str
        Name of the folder containing to-do files.
    done_name : str
        Name of the folder containing done files.

    Returns
    -------
    folder_dict : dict
        Dictionary; folder names as keys and their associated 
        ``GoogleDriveFile`` instances as values.
    todo_dict : dict
        Dictionary; keys are file names (without file extension), and 
        values are lists of to-do files, as ``GoogleDriveFile`` 
        instances, that share a specific file name. Note that if 
        different type of files share the same file name, they'll be 
        grouped into the same list.
    done_dict : dict
        Dictionary; keys are file names (without file extension), and 
        values are lists of done files, as ``GoogleDriveFile`` 
        instances, that share a specific file name. Note that if 
        different type of files share the same file name, they'll be 
        grouped into the same list.
    """
    # Folder Dictionary. Keys are these two folder names, and their values 
    # are their associated GoogleDriveFile objects.
    folder_dict = {
        fname: gfile 
        for gfile in drive.ListFile({"q": 'trashed=false'}).GetList() 
        for fname in [todo_name, done_name] 
        if gfile['title'] == fname
    }

    # Similar dictionaries for every done and to-do files.
    # Here, keys are their filenames [no file extenson], and values are lists 
    # holding the corresponding files [images, csvs and jsons, should they exist.]
    todo_dict = {
        key: list(group) 
        for key, group in groupby(
            sorted(
                [
                    gfile 
                    for gfile in drive.ListFile({"q": 'trashed=false'}).GetList() 
                    if gfile['parents'] 
                    and folder_dict[todo_name]['id'] in gfile['parents'][0].values()
                ], 
                key = lambda x: os.path.splitext(x['title'])[0],
            ),
            key = lambda x: os.path.splitext(x['title'])[0],
        )
    }
    
    done_dict = {
        key: list(group) 
        for key, group in groupby(
            sorted(
                [
                    gfile 
                    for gfile in drive.ListFile({"q": 'trashed=false'}).GetList() 
                    if gfile['parents'] 
                    and folder_dict[done_name]['id'] in gfile['parents'][0].values()
                ], 
                key = lambda x: os.path.splitext(x['title'])[0],
            ),
            key = lambda x: os.path.splitext(x['title'])[0],
        )
    }

    return folder_dict, todo_dict, done_dict

def move_file(drive, file_id, folder_id):
    """Moves file to a specific folder.
    
    Parameters
    ----------
    drive : GoogleDrive
        Drive as a PyDrive2 ``GoogleDrive`` object.
    file_id : str
        Id of the file to be moved, obtained from it's associated 
        ``GoogleDriveFile`` instance.
    folder_id : str
        Destination folder's id, obtained from it's associated 
        ``GoogleDriveFile`` instance.

    """
    # Create GoogleDriveFile instance using file id.
    file = drive.CreateFile({'id': file_id})
    # Set parents using folder id.
    file['parents'] = [{"kind": "drive#parentReference", 
                         "id": folder_id}]
    # Update file.
    file.Upload()

# The idea here is to use this function's output with the read_points function.
def get_gdrive_csv_path(drive, file_list, dir, name='zdummy'):
    """Download csv file from GoogleDrive.
    
    Parameters
    ----------
    drive : GoogleDrive
        Drive as a PyDrive2 ``GoogleDrive`` object.
    file_list : list of GoogleDriveFile
        List containing ``GoogleDriveFile`` instances for files that
        share the same file name as the csv file. For instance, if the
        csv has the name `myfile.csv`, `file_list` should be 
        `todo_dict['myfile'].

    Returns
    -------
    dummy_path : str
        Path to csv file.

    Raises
    ------
    FileNotFoundError
        If the csv file doesn't exist.
    """
    # Filter file.
    gfile = next(
        filter(lambda x: x['mimeType'] == 'text/csv', file_list), None
    )

    # Check file.
    if gfile is None:
        raise FileNotFoundError(f"Specified csv file doesn't exist.")

    dummy_path = f'{dir}/{name}.{gfile["fileExtension"]}'
    # Download csv file to a dummy path.
    drive.CreateFile({'id': gfile['id']}).GetContentFile(dummy_path)

    return dummy_path

def get_gdrive_json_path(drive, file_list):
    """Download json file from GoogleDrive.
    
    Parameters
    ----------
    drive : GoogleDrive
        Drive as a PyDrive2 ``GoogleDrive`` object.
    file_list : list of GoogleDriveFile
        List containing ``GoogleDriveFile`` instances for files that
        share the same file name as the csv file. For instance, if the
        json has the name `myfile.json`, `file_list` should be 
        `todo_dict['myfile'].

    Returns
    -------
    dummy_path : str
        Path to json file.

    Raises
    ------
    FileNotFoundError
        If the json file doesn't exist.
    """
    # Filter file.
    gfile = next(
        filter(lambda x: x['mimeType'] == 'application/json', file_list), None
    )

    # Check file.
    if gfile is None:
        raise FileNotFoundError(f"Specified json file doesn't exist.")

    dummy_path = f'zdummy.{gfile["fileExtension"]}'
    # Download csv file to dummy path.
    drive.CreateFile({'id': gfile['id']}).GetContentFile(dummy_path)

    return dummy_path

def get_gdrive_image_path(drive, file_list, dir, name='zdummy'):
    """Download image file from GoogleDrive.
    
    Parameters
    ----------
    drive : GoogleDrive
        Drive as a PyDrive2 ``GoogleDrive`` object.
    file_list : list of GoogleDriveFile
        List containing ``GoogleDriveFile`` instances for files that
        share the same file name as the image file. For instance, if the
        image has the name `myfile.png`, `file_list` should be 
        `todo_dict['myfile'].

    Returns
    -------
    dummy_path : str
        Path to image file.

    Raises
    ------
    FileNotFoundError
        If the image file doesn't exist.
    """   
    # Filter file.
    gfile = next(
        filter(
            lambda x: x["mimeType"] in ["image/jpeg", "image/png"], file_list
        ),
        None,
    ) # For image maybe x['mimeType'].startswith('image/')? To handle all img types?

    # Check file.
    if gfile is None:
        raise FileNotFoundError(f"Specified image file doesn't exist.")

    # print(file_list)

    dummy_path = f'{dir}/{name}.{gfile["fileExtension"]}'
    # Download csv file to a dummy path.
    drive.CreateFile({'id': gfile['id']}).GetContentFile(dummy_path)

    return dummy_path

def get_gdrive_csv_bytes(drive, file_list):
    """Download csv file from GoogleDrive.
    
    Parameters
    ----------
    drive : GoogleDrive
        Drive as a PyDrive2 ``GoogleDrive`` object.
    file_list : list of GoogleDriveFile
        List containing ``GoogleDriveFile`` instances for files that
        share the same file name as the csv file. For instance, if the
        csv has the name `myfile.csv`, `file_list` should be 
        `todo_dict['myfile'].

    Returns
    -------
    csv_bytes : bytes
        A bytes object containing the csv file.

    Raises
    ------
    FileNotFoundError
        If the csv file doesn't exist.
    """
    # Filter file.
    gfile = next(
        filter(lambda x: x['mimeType'] == 'text/csv', file_list), None
    )

    # Check file.
    if gfile is None:
        raise FileNotFoundError(f"Specified csv file doesn't exist.")

    # Download csv file to bytes.
    csv_bytes = (
        drive.CreateFile({"id": gfile["id"]})
        .GetContentIOBuffer(mimetype=gfile["mimeType"])
        .read()
    )

    return csv_bytes

def get_gdrive_json_bytes(drive, file_list):
    """Download json file from GoogleDrive.
    
    Parameters
    ----------
    drive : GoogleDrive
        Drive as a PyDrive2 ``GoogleDrive`` object.
    file_list : list of GoogleDriveFile
        List containing ``GoogleDriveFile`` instances for files that
        share the same file name as the json file. For instance, if the
        json has the name `myfile.json`, `file_list` should be 
        `todo_dict['myfile'].

    Returns
    -------
    json_bytes : bytes
        A bytes object containing the json file.

    Raises
    ------
    FileNotFoundError
        If the json file doesn't exist.
    """
    # Filter file.
    gfile = next(
        filter(lambda x: x['mimeType'] == 'application/json', file_list), None
    )

    # Check file.
    if gfile is None:
        raise FileNotFoundError(f"Specified json file doesn't exist.")

    # Download json file to bytes.
    json_bytes = (
        drive.CreateFile({"id": gfile["id"]})
        .GetContentIOBuffer(mimetype=gfile["mimeType"])
        .read()
    )

    return json_bytes

def get_gdrive_image_bytes(drive, file_list):
    """Download image file from GoogleDrive.
    
    Parameters
    ----------
    drive : GoogleDrive
        Drive as a PyDrive2 ``GoogleDrive`` object.
    file_list : list of GoogleDriveFile
        List containing ``GoogleDriveFile`` instances for files that
        share the same file name as the image file. For instance, if the
        image has the name `myfile.png`, `file_list` should be 
        `todo_dict['myfile'].

    Returns
    -------
    img_bytes : bytes
        A bytes object containing the image file.

    Raises
    ------
    FileNotFoundError
        If the image file doesn't exist.
    """   
    # Filter file.
    gfile = next(
        filter(
            lambda x: x["mimeType"] in ["image/jpeg", "image/png"], todo_dict["todo"]
        ),
        None,
    ) # For image maybe x['mimeType'].startswith('image/')? To handle all img types?

    # Check file.
    if gfile is None:
        raise FileNotFoundError(f"Specified image file doesn't exist.")

    # Download image file to bytes.
    img_bytes = (
        drive.CreateFile({"id": gfile["id"]})
        .GetContentIOBuffer(mimetype=gfile["mimeType"])
        .read()
    )

    return img_bytes

def update_gdrive_csv(drive, file_list, x_coords, y_coords, labels):
    """Update csv file from GoogleDrive.
    
    Parameters
    ----------
    drive : GoogleDrive
        Drive as a PyDrive2 ``GoogleDrive`` object.
    file_list : list of GoogleDriveFile
        List containing ``GoogleDriveFile`` instances for files that
        share the same file name as the csv file. For instance, if the
        csv has the name `myfile.csv`, `file_list` should be 
        `todo_dict['myfile'].
    x_coords : array-like
        For each point, x-coordinates.
    y_coords : array-like
        For each point, y-coordinates.
    labels : array-like
        For each point, label.

    Raises
    ------
    FileNotFoundError
        If the csv file doesn't exist.
    """
    # Get string csv.
    result = [["X", "Y", "Label"]] + [
        [str(x), str(y), str(l)] for x, y, l in zip(x_coords, y_coords, labels)
    ]
    # (Comma separated)
    result_str = '\n'.join([','.join(row) for row in result])
    
    # Filter old file.
    gfile = next(
        filter(lambda x: x['mimeType'] == 'text/csv', file_list), None
    )

    # Check file.
    if gfile is None:
        raise FileNotFoundError(f"Specified csv file doesn't exist.")

    # Get old file by id.
    csvfile = drive.CreateFile({"id": gfile["id"]})

    # Modify content.
    csvfile.SetContentString(result_str)
    
    # Upload.
    csvfile.Upload()

def update_gdrive_json(drive, file_list, json_dict):
    # json dict as made here (#L162): 
    # https://github.com/Digpatho1/ki67/blob/main/Segmentator/generate_masks.py
    """Update json file from GoogleDrive.
    
    Parameters
    ----------
    drive : GoogleDrive
        Drive as a PyDrive2 ``GoogleDrive`` object.
    file_list : list of GoogleDriveFile
        List containing ``GoogleDriveFile`` instances for files that
        share the same file name as the json file. For instance, if the
        json has the name `myfile.json`, `file_list` should be 
        `todo_dict['myfile'].
    json_dict : dict
        Dictionary to save as json file.
    
    Raises
    ------
    FileNotFoundError
        If the json file doesn't exist.
    """
    # Get json string.
    result_str = json.dumps(json_dict)
    
    # Filter old file.
    gfile = next(
        filter(lambda x: x['mimeType'] == 'application/json', file_list), None
    )

    # Check file.
    if gfile is None:
        raise FileNotFoundError(f"Specified json file doesn't exist.")

    # Get old file by id.
    jsonfile = drive.CreateFile({"id": gfile["id"]})
    
    # Modify content.
    jsonfile.SetContentString(result_str)
    
    # Upload.
    jsonfile.Upload()

if __name__ == '__main__':
    # Path to keys.
    path_to_json_key = 'testing_service_key.json'
    
    # Folders where done and to-do images, csvs and jsons are stored.
    todo_name, done_name = 'F1', 'F2'

    # Get drive instance from keys.
    drive = get_drive(path_to_json_key)

    # Get dictionaries.
    folder_dict, todo_dict, done_dict = get_dicts(drive, todo_name, done_name)
    
    # Drive info.
    about = drive.GetAbout()
    
    # Print some info.
    print('Current user name: {}'.format(about['name']))
    print('Root folder ID: {}'.format(about['rootFolderId']))
    print('Total quota (bytes): {}'.format(about['quotaBytesTotal']))
    print('Used quota (bytes): {}'.format(about['quotaBytesUsed']))
import os
import secure


def validate_file(file):
    """
    Validates the uploaded file extension and size.
    Returns True if valid, else False.
    """
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    max_size = 5 * 1024 * 1024  # 5MB

    # Check file extension
    if '.' in file.filename:
        extension = file.filename.rsplit('.', 1)[1].lower()
        if extension not in allowed_extensions:
            return False
    else:
        return False

    # Check file size
    if len(file.read()) > max_size:
        return False
    file.seek(0)  # Reset file read position
    return True


def generate_secure_filename(filename):
    """
    Generates a secure version of the filename by appending a timestamp.
    """
    base, ext = os.path.splitext(filename)
    secure_filename = f"{base}_{int(time.time())}{ext}"
    return secure_filename


def save_uploaded_file(file, upload_folder):
    """
    Saves the uploaded file to the specified folder.
    """
    if not os.path.exists(upload_folder):
        create_upload_folder(upload_folder)
    filename = generate_secure_filename(file.filename)
    file.save(os.path.join(upload_folder, filename))
    return filename


def delete_file(filename, upload_folder):
    """
    Deletes a file from the specified folder if it exists.
    """
    file_path = os.path.join(upload_folder, filename)
    if os.path.isfile(file_path):
        os.remove(file_path)


def create_upload_folder(upload_folder):
    """
    Creates the upload folder if it does not exist.
    """
    os.makedirs(upload_folder, exist_ok=True)

import mimetypes

def extract_info_from_image(filename: str, upload_path: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return f"Image file {filename} (type {mime}), stored at {upload_path}"

import os


def save_file(file, folder):
    path = os.path.join(folder, file.filename)

    with open(path, "wb") as f:
        f.write(file.file.read())

    return path

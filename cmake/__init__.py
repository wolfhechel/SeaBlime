import os.path

def which(filename):
    paths = os.getenv('PATH', '').split(os.path.pathsep)

    for path in paths:
        cmake_path = os.path.join(path, filename)

        if os.path.isfile(cmake_path):
            yield cmake_path

def find_cmake_bin():
    try:
        cmake_bin = next(which('cmake'))
    except StopIteration:
        cmake_bin = None

    return cmake_bin
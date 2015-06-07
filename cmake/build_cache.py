import os.path
from tempfile import mkdtemp

import sublime

def get_cmake_cache():
    return os.path.join(
        sublime.cache_path(),
        'CMakeCache'
    )

def make_build_cache():
    return mkdtemp(dir=get_cmake_cache())

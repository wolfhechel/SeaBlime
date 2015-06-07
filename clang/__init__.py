import platform
import os.path

from ctypes import *

c_object_p = POINTER(c_void_p)

xcode_path_hints = (
    '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib',  # XCode >= 5
    '/Library/Developer/CommandLineTools/usr/lib',  # XCode < 5
)

def try_load_xcode_libclang(library_name):
    for path_hint in xcode_path_hints:
        library_path = os.path.join(
            path_hint,
            library_name
        )

        try:
            library = cdll.LoadLibrary(library_path)
        except OSError:
            pass
        else:
            return library


def load_libclang():
    system_name = platform.system()

    if system_name == 'Darwin':
        library_name = 'libclang.dylib'
    elif system_name == 'Windows':
        library_name = 'libclang.dll'
    else:
        library_name = 'libclang.so'

    try:
        library = cdll.LoadLibrary(library_name)
    except OSError:
        if system_name == 'Darwin':
            library = try_load_xcode_libclang(library_name)

            if not library:
                raise
        else:
            raise

    return library

libclang = load_libclang()

def init_declarations(*declarations):
    for declaration in declarations:
        func = getattr(libclang, declaration[0])

        for (prop, value) in zip(('argtypes', 'restype', 'errcheck'), declaration[1:]):
            setattr(func, prop, value)


libclang.clang_getClangVersion.restype = c_char_p

version = __version__ = libclang.clang_getClangVersion().decode()

from .compilation_database import *
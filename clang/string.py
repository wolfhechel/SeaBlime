from ctypes import *

from . import libclang, init_declarations

# Types

class CXString(Structure):

    _fields_ = [
        ('data', c_void_p),
        ('private_flags', c_uint)
    ]

    def __str__(self):
        return libclang.clang_getCString(self).decode()

    def __del__(self):
        libclang.clang_disposeString(self)


init_declarations(
    (
        'clang_getCString',
        (CXString,),
        c_char_p
    ),
    (
        'clang_disposeString',
        (CXString,)
    )
)


__all__ = [
    'CXString'
]

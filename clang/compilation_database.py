from ctypes import *

from . import libclang, c_object_p, init_declarations
from .string import CXString

# C library declarations

# Types

CXCompilationDatabase = c_object_p

CXCompileCommands = c_object_p

CXCompileCommand = c_object_p

# Enumerations

CXCompilationDatabase_Error = c_uint
CXCompilationDatabase_NoError = 0
CXCompilationDatabase_CanNotLoadDatabase = 1

# Functions

class CanNotLoadDatabase(ValueError):

    pass


class CompileCommand(object):

    _compile_command = None

    def __init__(self, compile_command):
        self._compile_command = compile_command

    def __len__(self):
        return int(libclang.clang_CompileCommand_getNumArgs(self._compile_command))

    def __getitem__(self, item):
        if not isinstance(item, int):
            raise KeyError('Not an integer index')

        return str(libclang.clang_CompileCommand_getArg(
            self._compile_command,
            item
        ))

    @property
    def arguments(self):
        number_of_arguments = len(self)

        for argument_index in range(number_of_arguments):
            yield self[argument_index]

    @property
    def directory(self):
        return str(libclang.clang_CompileCommand_getDirectory(self._compile_command))


class CompileCommands(object):

    _compile_commands = None

    def __init__(self, compile_commands):
        self._compile_commands = compile_commands

    def __len__(self):
        return int(libclang.clang_CompileCommands_getSize(self._compile_commands))

    def __getitem__(self, item):
        if not isinstance(item, int):
            raise KeyError('Not an integer index')

        compile_command = libclang.clang_CompileCommands_getCommand(
            self._compile_commands,
            item
        )

        return CompileCommand(compile_command)

    def __del__(self):
        libclang.clang_CompileCommands_dispose(self._compile_commands)


class CompilationDatabase(object):

    _database = None

    def __init__(self, database):
        self._database = database

    @classmethod
    def errcheck(cls, result, func, args):
        if not result:
            raise CanNotLoadDatabase

        return cls(result)

    @staticmethod
    def from_directory(build_dir):
        """
        Creates a compilation database from the database found in directory build_dir.
        For example, CMake can output a compile_commands.json which can be used to build the database.

        :param build_dir: Directory containing compile_commands.json
        :return: CompilationDatabase
        """
        error_code = CXCompilationDatabase_Error()

        database = libclang.clang_CompilationDatabase_fromDirectory(
            build_dir.encode(),
            byref(error_code)
        )

        return database

    @property
    def compile_commands(self):
        """
        Get all the compile commands in this compilation database.

        :return: CompileCommands
        """
        compile_commands = libclang.clang_CompilationDatabase_getAllCompileCommands(self._database)

        return CompileCommands(compile_commands)

    def get_compile_commands_for_file(self, filename):
        """
        Find the compile commands used for a file.

        :param filename: File to get compile commands for
        :return: CompileCommands
        """
        compile_commands = libclang.clang_CompilationDatabase_getCompileCommands(
            self._database,
            filename.encode()
        )

        return CompileCommands(compile_commands)

    def __del__(self):
        libclang.clang_CompilationDatabase_dispose(self._database)


init_declarations(
    (
        'clang_CompilationDatabase_fromDirectory',
        (c_char_p, POINTER(CXCompilationDatabase_Error)),
        CXCompilationDatabase,
        CompilationDatabase.errcheck
    ),
    (
        'clang_CompilationDatabase_dispose',
        (CXCompilationDatabase,)
    ),
    (
        'clang_CompilationDatabase_getCompileCommands',
        (CXCompilationDatabase, c_char_p),
        CXCompileCommands
    ),
    (
        'clang_CompilationDatabase_getAllCompileCommands',
        (CXCompilationDatabase,),
        CXCompileCommands
    ),
    (
        'clang_CompileCommands_dispose',
        (CXCompileCommands,)
    ),
    (
        'clang_CompileCommands_getSize',
        (CXCompileCommands,),
        c_uint
    ),
    (
        'clang_CompileCommands_getCommand',
        (CXCompileCommands, c_uint),
        CXCompileCommand
    ),
    (
        'clang_CompileCommand_getDirectory',
        (CXCompileCommand,),
        CXString
    ),
    (
        'clang_CompileCommand_getNumArgs',
        (CXCompileCommand,),
        c_uint
    ),
    (
        'clang_CompileCommand_getArg',
        (CXCompileCommand, c_uint),
        CXString
    )
)


__all__ = [
    'CompilationDatabase',
    'CanNotLoadDatabase'
]

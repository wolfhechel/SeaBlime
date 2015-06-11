from functools import partial
import re

import sublime
import sublime_plugin

from .clang import cindex

from .utils.settings import Settings

xcode_path_hints = (
    '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib',  # XCode >= 5
    '/Library/Developer/CommandLineTools/usr/lib',  # XCode < 5
)

try:
    libclang = cindex.conf.lib

    has_clang = True
except cindex.LibclangError:
    if sublime.platform() == 'osx':
        for path_hint in xcode_path_hints:
            cindex.conf.set_library_path(path_hint)

            try:
                libclang = cindex.conf.lib

                has_clang = True

                break
            except cindex.LibclangError:
                continue

language_regex = re.compile("(?<=source\.)[\w+#]+")

supported_c_languages = (
    'c++',
    'c',
    'objc++',
    'objc'
)

def is_c_language(view):
    caret = view.sel()[0].a

    current_scope = view.scope_name(caret)

    language = language_regex.search(current_scope)

    if language is not None:
        is_supported = language.group(0) in supported_c_languages
    else:
        is_supported = False

    return is_supported


class TranslationUnitDatabase(object):

    compilation_database = None

    index = None

    translation_units = None

    def __init__(self, build_directory):
        self.compilation_database = cindex.CompilationDatabase.fromDirectory(
            build_directory.encode()
        )

        commands = self.compilation_database.getAllCompileCommands()

        self.index = cindex.Index.create()

        self.translation_units = {}

        for command in commands.commands:
            translation_unit = self.index.parse(None, list(command.arguments))

            file_name = translation_unit.spelling.decode()

            self.translation_units[file_name] = translation_unit


class IndexCache(object):

    databases = None

    def __init__(self):
        self.databases = {}

    def __getitem__(self, item):
        return self.databases.get(item.window_id, None)

    def __setitem__(self, key, value):
        self.databases[key.window_id] = value


index_cache = IndexCache()


def plugin_loaded():
    if has_clang:
        print('Using clang %s from %s' % (
            libclang.clang_getClangVersion().decode(),
            libclang._name
        ))
    else:
        sublime.status_message('Failed to load libclang')

    for window in sublime.windows():
        settings = Settings(window)

        if settings.build_cache:
            index_cache[window] = TranslationUnitDatabase(settings.build_cache)


class ClangCompletion(sublime_plugin.EventListener):

    return_types = {
        cindex.CursorKind.UNION_DECL: 'union',
        cindex.CursorKind.CLASS_DECL: 'class',
        cindex.CursorKind.ENUM_DECL: 'enum',
        cindex.CursorKind.STRUCT_DECL: 'struct',
        cindex.CursorKind.MACRO_DEFINITION: 'macro',
        cindex.CursorKind.NAMESPACE: 'namespace',
        cindex.CursorKind.TYPEDEF_DECL: 'typedef',
        cindex.CursorKind.CONSTRUCTOR: 'constructor'
    }

    def parse_completion_result(self, completion_result: cindex.CodeCompletionResult):
        completion_string = completion_result.string

        return_type = None

        insertion = ''
        representation = ''
        start = False
        placeholder_count = 0

        for chunk_index in range(completion_string.num_chunks):
            chunk = completion_string[chunk_index]

            assert isinstance(chunk, cindex.CompletionChunk)

            chunk_kind = str(chunk.kind)

            chunk_string = chunk.spelling.decode()

            if not chunk_string:
                chunk_string = ""

            if chunk_kind == 'TypedText':
                start = True

            if chunk_kind == 'ResultType':
                return_type = chunk_string
            else:
                representation += chunk_string

            if start and (chunk_kind != 'Informative'):
                if chunk_kind == 'Placeholder':
                    insertion += '${%d:%s}' % (placeholder_count, chunk_string)
                else:
                    insertion += chunk_string

        if not return_type:
            return_type = self.return_types.get(completion_result.kind, None)

        if return_type:
            representation += "\t%s" % return_type

        return representation, insertion, completion_string.priority

    def on_query_completions(self, view, prefix, locations):
        database = index_cache[view.window()]

        tu = database.translation_units.get(view.file_name())

        assert isinstance(tu, cindex.TranslationUnit)

        line, column = view.rowcol(locations[0] - len(prefix))

        unsaved_files = []

        if view.is_dirty():
            unsaved_files.append(
                (
                    tu.spelling,
                    view.substr(sublime.Region(0, view.size())).encode()
                )
            )

        completions = tu.codeComplete(
            tu.spelling,
            line + 1,
            column + 1,
            unsaved_files
        )

        completions.sort()

        comp = []
        for result in completions.results:
            comp.append(self.parse_completion_result(result))

        comp = sorted(comp, key=lambda a: a[2])

        return [a[:2] for a in comp]

from functools import partial
import re

import sublime
import sublime_plugin

from .utils.settings import Settings

try:
    from . import clang
except OSError:
    has_clang = False
else:
    has_clang = True

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


def plugin_loaded():
    if has_clang:
        print('Using clang %s from %s' % (
            clang.version,
            clang.libclang._name
        ))
    else:
        sublime.status_message('Failed to load libclang')

    for window in sublime.windows():
        settings = Settings(window)

        if settings.build_cache:
            try:
                compilation_database = clang.CompilationDatabase.from_directory(settings.build_cache)

                commands = compilation_database.compile_commands
                print(list(commands[0].arguments))

            except clang.CanNotLoadDatabase:
                sublime.status_message(
                    'Could not load Compilation Database from build cache %s' % settings.build_cache
                )

class ClangCompletion(sublime_plugin.EventListener):

    def on_query_completions(self, view, prefix, locations):

        return []
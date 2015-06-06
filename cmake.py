import os.path
import shlex
import subprocess
import re
from tempfile import mkdtemp

import sublime
import sublime_plugin

from .utils.settings import set_setting, get_setting

def get_cmake_cache():
    return os.path.join(
        sublime.cache_path(),
        'CMakeCache'
    )

def make_build_cache():
    return mkdtemp(dir=get_cmake_cache())

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

common_cmake_args = shlex.split(
    '-G "Sublime Text 2 - Unix Makefiles" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON'
)

def plugin_loaded():
    cmake_cache = get_cmake_cache()

    if not os.path.exists(cmake_cache):
        os.mkdir(cmake_cache)


class CMakeCacheParser(object):

    cache_entry_re = re.compile('^([A-Za-z_0-9]*):([A-Z]*)=(.*)$')

    @staticmethod
    def value_to_bool(value):
        value = value.upper()

        if value in ('TRUE', 'ON'):
            bool_value = True
        elif value in ('FALSE', 'OFF'):
            bool_value = False
        else:
            bool_value = None

        return bool_value

    @classmethod
    def iterate(cls, cmake_cache):
        with open(cmake_cache, 'r') as cache:

            while True:
                line = cache.readline()

                if line == '':
                    break

                cache_entry = cls.cache_entry_re.match(line.strip())

                if cache_entry:
                    key, _type, value = cache_entry.groups()

                    if _type.upper() == 'BOOL':
                        value = cls.value_to_bool(value)

                    yield key, value

    @classmethod
    def parse(cls, cmake_cache):
        return {
            k: v for k, v in cls.iterate(cmake_cache)
        }

    @classmethod
    def find(cls, cmake_cache, key_to_find):
        for (key, value) in cls.iterate(cmake_cache):
            if key == key_to_find:
                return value

        raise KeyError('No cache entry for key %s' % key_to_find)


class CmakeUpdateBuildCache(sublime_plugin.WindowCommand):

    def panel_output(self, proc):
        panel = self.window.create_output_panel('cmake_build')

        panel.set_read_only(False)

        while proc.returncode is None:
            line_output = proc.stdout.readline().decode()

            if line_output:
                panel.run_command('append', {
                    'characters': line_output
                })

            proc.poll()

        panel.run_command('append', {
            'characters': '-- Exited with status code %d' % proc.returncode
        })

        panel.set_read_only(True)

        return proc.returncode == 0

    @staticmethod
    def read_build_systems_from_build(build_cache_path):
        cmake_cache_file = os.path.join(
            build_cache_path,
            'CMakeCache.txt'
        )

        project_name = CMakeCacheParser.find(cmake_cache_file, 'CMAKE_PROJECT_NAME')

        sublime_project_file = os.path.join(
            build_cache_path,
            '%s.sublime-project' % project_name
        )

        with open(sublime_project_file, 'r') as sublime_project:
            project_data = sublime.decode_value(sublime_project.read())

        if project_data:
            build_systems = project_data.get('build_systems', None)

            for build_system in build_systems:
                build_system['working_dir'] = build_cache_path
        else:
            build_systems = None

        return build_systems

    def update_build_systems(self, build_cache_path):
        build_systems = self.read_build_systems_from_build(build_cache_path)

        if build_systems:
            project_data = self.window.project_data()
            project_data['build_systems'] = build_systems

            self.window.set_project_data(project_data)

        return build_systems is not None

    def find_dependent_cmake_files(self, build_cache_path):
        makefile_cmake_path = os.path.join(
            build_cache_path,
            'CMakeFiles/Makefile.cmake'
        )

        with open(makefile_cmake_path, 'r') as makefile_cmake:
            begin_reading_files = False

            while True:
                line = makefile_cmake.readline()

                if line == '':
                    break

                if begin_reading_files:
                    if line.strip() == ')':
                        break
                    else:
                        file_path = line.strip(" \"'\n")

                        if not file_path.startswith(os.path.sep):
                            file_path = os.path.join(
                                build_cache_path,
                                file_path
                            )

                        yield file_path
                elif line.strip() == 'set(CMAKE_MAKEFILE_DEPENDS':
                    begin_reading_files = True

    def update_watched_dependencies(self, build_cache_path):
        folders = [folder for folder in self.window.folders() if folder != build_cache_path]

        files_to_watch = []

        for file in self.find_dependent_cmake_files(build_cache_path):
            for folder in folders:
                if file.startswith(folder):
                    files_to_watch.append(file)

        set_setting(self.window, 'dependencies', files_to_watch)

    def run(self):
        source_path = os.path.dirname(
            get_setting(self.window, 'CMakeLists.txt')
        )

        build_cache_path = get_setting(self.window, 'build_cache')

        args = [find_cmake_bin()]

        args.extend(common_cmake_args)
        args.append(source_path)

        def _async():
            cmake_proc = subprocess.Popen(
                args,
                cwd=build_cache_path,
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE
            )

            sublime.status_message('Refreshing CMake build cache')

            if self.panel_output(cmake_proc):
                if not self.update_build_systems(build_cache_path):
                    sublime.status_message('Failed to update build systems')

                self.update_watched_dependencies(build_cache_path)

                sublime.status_message('Finished refreshing CMake build cache')

        sublime.set_timeout_async(_async, 0)


class CMakeListsWatcher(sublime_plugin.EventListener):

    def on_post_save_async(self, view):
        files_to_watch = get_setting(view.window(), 'dependencies', [])

        if view.file_name() in files_to_watch:
            view.window().run_command('cmake_update_build_cache')
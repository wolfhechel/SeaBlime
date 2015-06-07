import os.path
import shlex
import subprocess

import sublime
import sublime_plugin

from .utils.settings import Settings, WindowCommandSettingsMixin
from .cmake import find_cmake_bin
from .cmake.cache import CMakeCacheParser
from .cmake.build_cache import get_cmake_cache, make_build_cache

common_cmake_args = shlex.split(
    '-G "Sublime Text 2 - Unix Makefiles" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON'
)


def plugin_loaded():
    cmake_cache = get_cmake_cache()

    if not os.path.exists(cmake_cache):
        os.mkdir(cmake_cache)

    window = sublime.active_window()

    if Settings(window).exists:
        window.run_command('cmake_update_build_cache')


class CmakeUpdateBuildCache(WindowCommandSettingsMixin, sublime_plugin.WindowCommand):

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

        self.settings.dependencies = files_to_watch

    def run(self):
        source_path = os.path.dirname(
            self.settings.cmake_lists
        )

        build_cache_path = self.settings.build_cache

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


class CmakeEnable(WindowCommandSettingsMixin, sublime_plugin.WindowCommand):

    cmakelists = None

    def __init__(self, window):
        super().__init__(window)

        self.cmakelists = list(self.find_cmakelists(
            window.project_data().get('folders', [])
        ))

    def find_cmakelists(self, folders):
        """
        Tries to locate any CMakeLists.txt in folders
        """

        for folder in folders:
            folder_path = folder.get('path', None)

            if folder_path is not None:
                cmakelist = os.path.join(folder_path, 'CMakeLists.txt')

                if os.path.exists(cmakelist):
                    yield cmakelist

    def is_enabled(self):
        return not Settings(self.window).exists

    def is_visible(self):
        return len(self.cmakelists) > 0

    def add_build_cache_to_folders(self, build_cache):
        project_data = self.window.project_data()

        folders = project_data.get('folders')

        has_build_cache_already = False

        for folder in folders:
            if folder.get('path', None) == build_cache:
                has_build_cache_already = True
                break

        if not has_build_cache_already:
            build_cache_folder = {
                'path': build_cache,
                'name': 'Build cache'
            }

            folders.append(build_cache_folder)

            project_data['folders'] = folders

            self.window.set_project_data(project_data)

    def enable(self, cmakelist_index):
        cmakelist = self.cmakelists[cmakelist_index]

        self.settings.cmake_lists = cmakelist

        build_cache = self.settings.build_cache

        if build_cache is None:
            build_cache = make_build_cache()

            self.settings.build_cache = build_cache

            self.add_build_cache_to_folders(build_cache)

        self.window.run_command('cmake_update_build_cache')

    def run(self):
        self.window.show_quick_panel(self.cmakelists, self.enable)


class CmakeToggleOutput(sublime_plugin.WindowCommand):

    def run(self):
        panel = self.window.get_output_panel('cmake_build')

        command = 'hide_panel' if panel.window() else 'show_panel'

        self.window.run_command(command, {
            'panel': 'output.cmake_build'
        })


class CMakeListsWatcher(sublime_plugin.EventListener):

    def on_post_save_async(self, view):
        window = view.window()
        settings = Settings(window)

        files_to_watch = settings.dependencies

        if view.file_name() in files_to_watch:
            window.run_command('cmake_update_build_cache')

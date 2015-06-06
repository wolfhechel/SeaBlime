import os.path

import sublime
import sublime_plugin

from .utils.settings import set_setting, get_setting, has_settings


class EnableCmakeSupport(sublime_plugin.WindowCommand):

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
        return not has_settings(self.window)

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
        from .cmake import make_build_cache

        cmakelist = self.cmakelists[cmakelist_index]

        set_setting(self.window, 'CMakeLists.txt', cmakelist)

        build_cache = get_setting(self.window, 'build_cache', None)

        if build_cache is None:
            build_cache = make_build_cache()

            set_setting(self.window, 'build_cache', build_cache)

            self.add_build_cache_to_folders(build_cache)

        self.window.run_command('cmake_update_build_cache')

    def run(self):
        self.window.show_quick_panel(self.cmakelists, self.enable)

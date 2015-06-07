import sublime


settings_key = 'cmake'


def set_setting(window, key, value):
    project_settings = window.project_data().get('settings', {})

    cmake_settings = project_settings.get(settings_key, {})

    cmake_settings[key] = value

    project_data = window.project_data()

    if 'settings' not in project_data:
        project_data['settings'] = {}

    project_data['settings'][settings_key] = cmake_settings

    window.set_project_data(project_data)


def get_setting(window, key, default=None):
    project_settings = window.project_data().get('settings', {})

    cmake_settings = project_settings.get(settings_key, {})

    return cmake_settings.get(key, default)


def has_settings(window):
    return settings_key not in window.project_data().get('settings', {})


class Setting(object):

    _key = None

    _default = None

    def __init__(self, key, default=None):
        self._key = key
        self._default = default

    def __get__(self, instance, owner):
        return get_setting(instance.window, self._key, self._default)

    def __set__(self, instance, value):
        set_setting(instance.window, self._key, value)


class Settings(object):

    window = None

    build_cache = Setting('build_cache')

    dependencies = Setting('dependencies', [])

    cmake_lists = Setting('CMakeLists.txt')

    def __init__(self, window=None):
        if window is None:
            window = sublime.active_window()
        self.window = window

    @property
    def exists(self):
        return has_settings(self.window)



class WindowCommandSettingsMixin(object):

    @property
    def settings(self) -> Settings:
        return Settings(self.window)

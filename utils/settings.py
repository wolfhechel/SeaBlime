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
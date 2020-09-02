from django.apps import AppConfig
from openedx.core.djangoapps.plugins.constants import (
    PluginSettings,
    PluginURLs,
    ProjectType,
    SettingsType,
)


class EolDuplicateXblockConfig(AppConfig):
    name = 'eol_duplicate_xblock'
    plugin_app = {
        PluginURLs.CONFIG: {
            ProjectType.CMS: {
                PluginURLs.NAMESPACE: "duplicate-xblock",
                PluginURLs.REGEX: r"^eolduplicate/",
                PluginURLs.RELATIVE_PATH: "urls",
            }},
        PluginSettings.CONFIG: {
            ProjectType.CMS: {
                SettingsType.COMMON: {
                    PluginSettings.RELATIVE_PATH: "settings.common"}},
        },
    }

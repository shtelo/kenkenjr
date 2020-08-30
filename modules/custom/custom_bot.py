from asyncio import get_event_loop
from os import listdir

from decouple import config
from discord.ext.commands import ExtensionAlreadyLoaded, ExtensionFailed, NoEntryPointError, ExtensionError
from discord.ext.commands.bot import Bot

from utils import get_path, get_constant, Log, singleton


@singleton
class Kenken(Bot):
    def __init__(self, args: list):
        super().__init__([get_constant('default_prefix')])
        self.load_all_extensions()
        get_event_loop().run_until_complete(self.start(config('TOKEN') if 'b' not in args else config('BETA_TOKEN')))

    def load_all_extensions(self):
        for file_name in listdir(get_path('extensions')):
            if not file_name.endswith('_cog.py') and not file_name.endswith('_cmd.py'):
                continue
            module = file_name[:-3]
            Log.auto(f'loading extension: {module}')
            try:
                self.load_extension(get_constant('extension_name') % module)
            except ExtensionAlreadyLoaded as e:
                Log.error(f'extension already loaded: {e.name}')
                self.reload_extension(e.name)
            except (ExtensionFailed, NoEntryPointError, ExtensionFailed) as e:
                Log.error(e)
                raise e

    def reload_extension(self, name):
        Log.auto(f'reloading extension: {name}')
        old = super().get_cog(name)
        try:
            super().reload_extension(name)
        except ExtensionError as e:
            Log.error(e)
            super().add_cog(old)
            return False
        return True

    def reload_all_extensions(self):
        done = True
        for extension in self.extensions.keys():
            done = done and self.reload_extension(extension)
        return done

    def group(self, *args, **kwargs):
        pass

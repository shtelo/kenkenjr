import inspect
from datetime import datetime
from os import mkdir
from os.path import isdir, isfile

from discord import Message
from slugify import slugify

from utils import get_path, get_constant


class Log:
    @classmethod
    def log(cls, log: str, path: str = '', **kwargs):
        now = datetime.now()
        stack = inspect.stack()
        try:
            class_ = stack[2][0].f_locals["self"].__class__.__name__
        except KeyError:
            class_ = None
        method_ = stack[2][0].f_code.co_name
        context = f'{now} - {class_}.{method_} : {log}'
        print(context)
        if not path:
            return
        message: Message = kwargs.get('message')
        if message is not None:
            if message.guild is not None:
                zer0ken = message.guild.get_member(get_constant('zer0ken_id'))
                if zer0ken is None:
                    print('--not logged : zer0ken not in this guilds')
                    return
            else:
                print('--not logged : DM')
                return
        if not isdir(get_path('logs')):
            mkdir(get_path('logs'))
        mode = 'at' if isfile(path) else 'wt'
        with open(path, mode=mode, encoding='utf-8-sig') as f:
            f.write(context + '\n')
        if mode == 'wt':
            cls.command('logs file separated.')

    @classmethod
    def auto(cls, log: str, **kwargs):
        cls.log(log, **kwargs)

    @classmethod
    def command(cls, log: str, **kwargs):
        cls.log(log, **kwargs)

    @classmethod
    def economy(cls, log: str, **kwargs):
        cls.log(log, **kwargs)

    @classmethod
    def error(cls, log: str, **kwargs):
        cls.log(log, path=f'{get_path("logs")}{slugify(str(datetime.now().date()))}_error.txt', **kwargs)

    @classmethod
    def casino(cls, log: str, **kwargs):
        cls.log(log, **kwargs)

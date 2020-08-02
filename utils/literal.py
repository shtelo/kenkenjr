import json

from utils import singleton


def get_constant(name: str):
    return Literal().literals[Literal.CONSTANT].get(name)


def get_brief(name: str):
    return Literal().literals[Literal.BRIEF].get(name)


def get_help(name: str):
    return Literal().literals[Literal.HELP].get(name)


def get_path(name: str):
    return Literal().literals[Literal.PATH].get(name)


def get_cog(name: str):
    return Literal().literals[Literal.COG].get(name)


def get_check(name: str):
    return Literal().literals[Literal.CHECK].get(name)


def get_emoji(name: str):
    return Literal().literals[Literal.EMOJI].get(name)


def literals(name: str = ''):
    l = Literal().literals
    return l.get(name) if name else l


def reload_literals():
    literal = Literal()
    literal.load()
    literal.format_all(literal.literals)


@singleton
class Literal:
    DEFAULT_PATH = './kenkenjr/data/literals.json'
    BRIEF = '_brief_'
    HELP = '_help_'
    PATH = '_path_'
    CONSTANT = '_constant_'
    COG = '_cog_'
    CHECK = '_check_'
    EMOJI = '_emoji_'
    PREFIX = '<P>'

    def __init__(self):
        self.literals: dict = {}
        self.load()
        self.format_all(self.literals)

    def load(self):
        with open(Literal.DEFAULT_PATH, 'r', encoding='utf-8') as f:
            self.literals = json.load(f)

    def format_all(self, d):
        if isinstance(d, str):
            return d.replace(Literal.PREFIX, str(self.literals[Literal.CONSTANT]['default_prefix']))
        if isinstance(d, dict):
            for k, v in d.items():
                d[k] = self.format_all(v)
        if isinstance(d, list):
            for i in range(len(d)):
                d[i] = self.format_all(d[i])
        return d

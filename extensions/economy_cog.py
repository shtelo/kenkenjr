from discord.ext.commands import Bot

from modules import CustomCog
from utils import get_cog


class EconomyCog(CustomCog, name=get_cog('EconomyCog')['name']):
    def __init__(self, client: Bot):
        super().__init__(client)
        self.client = client


def setup(client: Bot):
    client.add_cog(EconomyCog(client))

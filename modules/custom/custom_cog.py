from discord.ext.commands import Cog, Bot

from utils import get_cog


class CustomCog(Cog):
    def __init__(self, client: Bot):
        self.emoji: str = get_cog(self.__class__.__name__)['emoji']

        async def after_ready_():
            await client.wait_until_ready()
            await self.after_ready()

        client.loop.create_task(after_ready_())

    async def after_ready(self):
        pass

    async def is_completed(self):
        return True

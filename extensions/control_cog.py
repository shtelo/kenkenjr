from discord import NotFound, ClientException, Forbidden, HTTPException
from discord.ext.commands import Context

import modules
from modules import CustomCog, owner_only, guild_only
from modules.custom.custom_bot import Kenken
from utils import get_cog, literals, reload_literals


class ControlCog(CustomCog, name=get_cog('ControlCog')['name']):
    """
    봇의 관리와 직결되는 기능들을 포함합니다.
    """

    def __init__(self, client: Kenken):
        super().__init__(client)
        self.client: Kenken = client

    @modules.group(name='테스트', aliases=('test',))
    @owner_only()
    async def test(self, ctx: Context):
        await ctx.send('테스트!')

    @modules.command(name='따라해', aliases=('echo',))
    @owner_only()
    async def echo(self, ctx: Context, *, content: str):
        await ctx.send(content)

    @modules.command(name='삭제', aliases=('delete',))
    @owner_only()
    @guild_only()
    async def delete(self, ctx: Context, count: int):
        count = min(max(1, count), 100)
        messages = await ctx.channel.purge(limit=count, bulk=True)
        try:
            await ctx.channel.delete_messages(messages)
        except NotFound:
            if count != 1:
                await ctx.channel.send(literals('delete')['failed'])
        except (ClientException, Forbidden, HTTPException) as e:
            await ctx.channel.send(literals('delete')['failed'])
            raise e
        await ctx.channel.send(literals('delete')['done'] % count, delete_after=10)

    @modules.group(name='리로드')
    @owner_only()
    async def reload(self, ctx: Context):
        await self.reload_literals(ctx)
        await self.reload_cogs(ctx)

    @reload.command(name='리터럴')
    @owner_only()
    async def reload_literals(self, ctx: Context):
        reload_literals()
        await ctx.send(literals('reload_literals')['done'])

    @reload.command(name='코그', aliases=('기능',))
    @owner_only()
    async def reload_cogs(self, ctx: Context):
        message = await ctx.send(literals('reload_cogs')['start'])
        try:
            done = self.client.reload_all_extensions()
        except Exception as e:
            await message.edit(content=(literals('reload_cogs')['failed'] + '```\n' + e + '```'))
        else:
            if done:
                await message.edit(content=literals('reload_cogs')['done'])
            else:
                await message.edit(content=(literals('reload_cogs')['failed']))


def setup(client: Kenken):
    client.add_cog(ControlCog(client))

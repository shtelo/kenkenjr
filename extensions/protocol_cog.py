from discord import TextChannel, Message, NotFound
from discord.ext import commands
from discord.ext.commands import Bot, Context, TextChannelConverter, BadArgument

from modules import BotProtocol, Request, CustomCog
from utils import get_cog, get_constant, Log


class ProtocolCog(CustomCog, BotProtocol, name=get_cog('ProtocolCog')['name']):
    """
    다른 봇과 소통하기 위한 기능을 포함합니다.
    """

    def __init__(self, client: Bot):
        super().__init__(client)
        self.client: Bot = client
        self.deck: dict = {}

    @CustomCog.listener()
    async def on_message(self, message):
        if message.author.id == get_constant('kenken_id'):
            return
        await super().on_message(message)

    @CustomCog.listener()
    async def on_command_error(self, ctx: commands.Context, _):
        if ctx.guild is not None and ctx.prefix in self.client.command_prefix:
            Log.command('pass protocol request generated.')
            await ctx.send(f'ALL PASS {ctx.prefix} {ctx.channel.mention} {ctx.message.id}', delete_after=1)

    async def on_echo(self, request: Request):
        Log.command('detected.')
        if request.addition:
            await request.message.channel.send(request.addition)

    async def on_pass(self, request: Request):
        Log.command('detected.')
        tokens = request.addition.split(' ', 2)
        if len(tokens) < 3:
            Log.error('lack of components')
            return
        self.client.command_prefix.insert(0, tokens[0])
        request_ctx = await self.client.get_context(request.message)
        try:
            channel: TextChannel = await TextChannelConverter().convert(request_ctx, tokens[1])
            message: Message = await channel.fetch_message(int(tokens[2]))
            ctx: Context = await self.client.get_context(message)
            await self.client.invoke(ctx)
        except BadArgument:
            Log.error(f'channel {tokens[1]} not found.')
        except NotFound:
            Log.error(f'message {tokens[2]} not found.')
        self.client.command_prefix = self.client.command_prefix[-1:]


def setup(client: commands.Bot):
    client.add_cog(ProtocolCog(client))

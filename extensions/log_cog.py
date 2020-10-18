import math
import traceback

from discord import Message, User
from discord.ext.commands import Bot, Context, CommandNotFound, CheckFailure, MissingRequiredArgument, \
    DisabledCommand, CommandOnCooldown, BadUnionArgument, BadArgument

from modules.custom.custom_cog import CustomCog
from utils import wrap_codeblock
from utils.literal import get_cog, literals, get_constant
from utils.log import Log


class LogCog(CustomCog, name=get_cog('LogCog')['name']):
    """
    발생한 오류를 기록하는 기능을 포함합니다.
    """

    def __init__(self, client: Bot):
        super().__init__(client)
        self.client: Bot = client
        self.owner: User = None

    async def after_ready(self):
        self.owner = await self.client.fetch_user(get_constant('zer0ken_id'))

    @CustomCog.listener()
    async def on_message_edit(self, _, msg_after: Message):
        ctx = await self.client.get_context(msg_after)
        await self.client.invoke(ctx)

    @CustomCog.listener()
    async def on_command_error(self, ctx: Context, error: Exception):
        handled = False
        if isinstance(error, CommandOnCooldown):
            await ctx.send(literals('LogCog.on_command_error')['cooldown'] % math.ceil(error.retry_after))
            handled = True
        elif ctx.command is not None:
            ctx.command.reset_cooldown(ctx)
        if any((isinstance(error, CommandNotFound),
                isinstance(error, CheckFailure),
                isinstance(error, BadUnionArgument),
                isinstance(error, MissingRequiredArgument),
                isinstance(error, DisabledCommand),
                isinstance(error, BadArgument))):
            handled = True
        if not handled:
            error_message = f'{ctx.guild}/{ctx.channel}/{ctx.author}: {ctx.message.content}\n{ctx.message.jump_url}\n\n'
            error_message += '\n'.join(traceback.format_exception(etype=type(error), value=error,
                                                                  tb=error.__traceback__))
            for e in wrap_codeblock(error_message, markdown=''):
                await self.owner.send(e)
        raise error


def setup(client: Bot):
    client.add_cog(LogCog(client))

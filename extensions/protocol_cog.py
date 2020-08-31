import json

from discord import TextChannel, Message, NotFound
from discord.ext import commands
from discord.ext.commands import Bot, Context, TextChannelConverter, BadArgument

from extensions.shtelo_cog import get_application_sheet
from modules import BotProtocol, Request, CustomCog, doc_read
from utils import get_cog, get_constant, Log, literals, FreshData, split_by_length

MESSAGE_MAX_LENGTH = 2000

class ProtocolCog(CustomCog, BotProtocol, name=get_cog('ProtocolCog')['name']):
    """
    다른 봇과 소통하기 위한 기능을 포함합니다.
    """

    def __init__(self, client: Bot):
        super().__init__(client)
        self.client: Bot = client
        self.holding_data: dict = dict()
        self.done: list = list()

    @CustomCog.listener()
    async def on_message(self, message):
        if message.author.id == get_constant('kenken_id'):
            return
        await super().on_message(message)

    @CustomCog.listener()
    async def on_command_error(self, ctx: commands.Context, _):
        if ctx.guild is not None and ctx.prefix in self.client.command_prefix:
            Log.command('pass protocol request generated.')
            request = Request(receiver=BotProtocol.ALL, signal=BotProtocol.PASS,
                              addition=f'{ctx.prefix} {ctx.channel.mention} {ctx.message.id}')
            await ctx.send(str(request), delete_after=1)

    async def on_echo(self, request: Request):
        Log.command('detected.')
        if request.addition:
            await request.message.channel.send(request.addition)

    async def on_pass(self, request: Request):
        Log.command('detected.')
        addition = request.addition.split(' ', 2)
        if len(addition) < 3:
            Log.error('lack of components')
            return
        self.client.command_prefix.insert(0, addition[0])
        request_ctx = await self.client.get_context(request.message)
        try:
            channel: TextChannel = await TextChannelConverter().convert(request_ctx, addition[1])
            message: Message = await channel.fetch_message(int(addition[2]))
            ctx: Context = await self.client.get_context(message)
            await self.client.invoke(ctx)
        except BadArgument:
            Log.error(f'channel {addition[1]} not found')
        except NotFound:
            Log.error(f'message {addition[2]} not found')
        self.client.command_prefix = self.client.command_prefix[-1:]

    async def on_send(self, request: Request):
        literal = literals('on_send')
        key = request.addition.strip()

        async def respond(data_, key_):
            here_request = request.generate_respond(signal=BotProtocol.HERE, addition=key_ + ' ')
            addition_length = MESSAGE_MAX_LENGTH - len(str(here_request)) - 1
            here_request.addition += data_[:addition_length]
            data_ = data_[addition_length:]
            await request.message.channel.send(str(here_request), delete_after=1)
            if data_:
                for d in split_by_length(data_):
                    await request.message.channel.send(d, delete_after=1)
            done_request = request.generate_respond(signal=BotProtocol.DONE, addition=key_)
            await request.message.channel.send(str(done_request), delete_after=1)

        if key == literal['application']:
            data = json.dumps(get_application_sheet(), ensure_ascii=False)
            await respond(data, key)
        if key == literal['regulation']:
            data = doc_read(get_constant('regulation')['doc_id'])
            await respond(data, key)

    async def on_here(self, request: Request):
        addition = request.addition.split(' ', 1)
        while len(addition) < 2:
            Log.error('lack of components')
            return
        key = addition[0]
        data = addition[1]
        while not self.done or self.done[-1].addition != key:
            message = await self.client.wait_for('message', check=lambda msg: msg.author == request.message.author)
            data += message.content
        self.done.pop(-1)
        if key not in self.holding_data:
            self.holding_data[key] = list()
        self.holding_data[key].append(FreshData(data))

    async def on_done(self, request: Request):
        self.done.append(request)


def setup(client: commands.Bot):
    client.add_cog(ProtocolCog(client))

from random import choice, random

from discord import Message, User, Member
from discord.ext import commands
from discord.ext.commands import Context, Bot

import modules
from modules import CustomCog, command, tokens_len, ChainedEmbed
from utils import get_cog, get_path, Log


class BaseCog(CustomCog, name=get_cog('BaseCog')['name']):
    """
    기본적인 기능을 포함합니다.
    """

    def __init__(self, client: Bot):
        super().__init__(client)
        self.client: Bot = client
        self.reactions: list = []
        self.greetings: list = []
        self.protocol_cog = None

    async def after_ready(self):
        with open(get_path('reactions'), 'r', encoding='utf-8') as f:
            self.reactions = f.read().split('\n')
        with open(get_path('greetings'), 'r', encoding='utf-8') as f:
            self.greetings = f.read().split('\n')

    def get_greeting(self, message):
        greeting = f'{choice(self.greetings)}'
        if random() >= 0.5:
            greeting += f' **{message.author.display_name}**!'
        else:
            greeting += '!'
        return greeting

    @CustomCog.listener()
    async def on_message(self, message: Message):
        if self.protocol_cog is None:
            self.protocol_cog = self.client.get_cog(get_cog('ProtocolCog')['name'])
        ctx: commands.Context = await self.client.get_context(message)
        if ctx.valid or message.author.id == self.client.user.id or self.protocol_cog.get_request(message) is not None:
            return
        nick = self.client.user.display_name
        if (any(word in message.content.upper()
                for word in ['KENKEN', '켄켄', str(self.client.user.id), self.client.user.display_name, nick]) or
                message.content.count('켄') == 2):
            if any(word in message.content.upper() for word in self.greetings):
                Log.command('kenkenjr greeted.')
                await ctx.send(self.get_greeting(message))
            else:
                Log.command('kenkenjr called.')
                await message.channel.send(f'{choice(self.reactions)}')

    @modules.command(name='안녕', aliases=('반가워', 'ㅎㅇ', 'greet', 'hi', 'hello'))
    async def greet(self, ctx: Context):
        Log.command('detected.')
        await ctx.send(self.get_greeting(ctx.message))

    @modules.command(name='핑', aliases=('ping', 'p'))
    @tokens_len(1)
    async def ping(self, ctx: Context):
        Log.command('detected.')
        await ctx.send('???')

    @modules.command(name='프로필', aliases=('profile', '사용자', 'user'))
    @tokens_len(2)
    async def profile(self, ctx: Context, user: User):
        member: Member = ctx.guild.get_member(user.id)
        if member is not None:
            user = member
        profile_embed = ChainedEmbed(title=user.display_name, color=user.colour,
                                     description=str(user))
        profile_embed.set_thumbnail(url=user.avatar_url)
        profile_embed.set_footer(text=str(user.created_at))
        await ctx.send(embed=profile_embed)


def setup(client: commands.Bot):
    client.add_cog(BaseCog(client))

from datetime import timezone, timedelta
from random import choice, random
from re import findall, sub
from typing import Union

from discord import Message, User, Member, HTTPException, RawReactionActionEvent, Guild
from discord.ext import commands
from discord.ext.commands import Context, Bot, MemberConverter, BadArgument

import modules
from modules import CustomCog, tokens_len, ChainedEmbed, guild_only
from utils import get_cog, get_path, Log, literals, get_emoji, attach_toggle_interface, EmojiInterfaceState, \
    CHAR_MEDIALS, join_jamos_char, to_kst

NICK_MAX_LENGTH = 32

DETAIL_EMOJI = get_emoji(':question_mark:')
FOLD_EMOJI = get_emoji(':x:')


def get_profile_embed(user: User, brief: bool = True):
    literal = literals('get_profile_embed')
    profile_embed = ChainedEmbed(title=user.display_name, color=user.colour, description=str(user))
    profile_embed.set_thumbnail(url=user.avatar_url)
    if isinstance(user, Member):
        profile_embed.set_author(name=user.guild.name + ' ' + user.top_role.name, icon_url=user.guild.icon_url)
    if not brief:
        profile_embed.set_image(url=user.avatar_url)
        profile_embed.set_footer(text=f'{to_kst(user.created_at)} · {user.id}')
        if isinstance(user, Member):
            profile_embed.add_field(name=literal['join'], value=to_kst(user.joined_at))
            if user.premium_since:
                profile_embed.add_field(name=literal['boost'], value=to_kst(user.premium_since))
            if roles := user.roles[1:]:
                roles.reverse()
                profile_embed.add_field(name=literal['roles'],
                                        value='\n'.join([role.name for role in roles]))
    return profile_embed


async def get_guild_profile_embed(guild: Guild, brief: bool = True):
    literal = literals('get_guild_profile_embed')
    online_members = (await guild.widget()).members
    description = literal['description'] % (guild.region, guild.member_count)
    if guild.premium_tier:
        description += '\n' + literal['tier'] % guild.premium_tier
    guild_embed = ChainedEmbed(title=guild.name, description=description)
    guild_embed.set_author(name=literal['author'] % guild.owner.name, icon_url=guild.owner.avatar_url)
    guild_embed.set_thumbnail(url=guild.icon_url)
    if not brief:
        if guild.premium_subscription_count:
            guild_embed.add_field(name=literal['boost'] % guild.premium_subscription_count,
                                  value='\n'.join(str(subscriber) for subscriber in guild.premium_subscribers))
        if online_members:
            guild_embed.add_field(name=literal['online'] % len(online_members),
                                  value='\n'.join([member.name for member in online_members]))
        guild_embed.set_footer(text=f'{to_kst(guild.created_at)} · {guild.id}')
        guild_embed.set_image(url=guild.banner_url)
        if guild.channels:
            value = literal['category'] % len(guild.categories)
            value += '\n' + literal['text_channel'] % len(guild.text_channels)
            value += '\n' + literal['voice_channel'] % len(guild.voice_channels)
            guild_embed.add_field(name=literal['channel'] % len(guild.channels), value=value)
    return guild_embed


class BaseCog(CustomCog, name=get_cog('BaseCog')['name']):
    """
    기본적인 기능을 포함합니다.
    """

    def __init__(self, client: Bot):
        super().__init__(client)
        self.client: Bot = client
        self.reactions: list = list()
        self.greetings: list = list()
        self.characters: list = list()
        self.protocol_cog = None

    async def after_ready(self):
        with open(get_path('reactions'), 'r', encoding='utf-8') as f:
            self.reactions = f.read().split('\n')
        with open(get_path('greetings'), 'r', encoding='utf-8') as f:
            self.greetings = f.read().split('\n')
        self.protocol_cog = self.client.get_cog(get_cog('ProtocolCog')['name'])
        for initial in ('ㅁ', 'ㅇ', 'ㄹ', 'ㄴ'):
            for final in ('ㅁ', 'ㅇ', 'ㄴ', None):
                for medial in map(str, CHAR_MEDIALS):
                    self.characters.append(join_jamos_char(initial, medial, final))

    def get_greeting(self, message):
        greeting = f'{choice(self.greetings)}'
        if random() >= 0.5:
            greeting += f' **{message.author.display_name}**!'
        else:
            greeting += '!'
        return greeting

    def kenken_called(self, message: str):
        count = 0
        for ken in ('켄', '캔', '켼', '컌', '꺤', '꼔', '껜', '깬'):
            count += message.count(ken)
        if count < 2:
            count = 0
        if not count and any(word in message.upper()
                             for word in ('KENKEN', '켄켄', str(self.client.user.id), self.client.user.display_name)):
            count = 2
        return count

    @CustomCog.listener()
    async def on_message(self, message: Message):
        ctx: commands.Context = await self.client.get_context(message)
        if ctx.valid or message.author.id == self.client.user.id or self.protocol_cog.get_request(message) is not None:
            return
        if count := self.kenken_called(message.content):
            if any(word in message.content.upper() for word in self.greetings):
                Log.command('kenkenjr greeted.')
                await ctx.send(self.get_greeting(message))
            elif count <= 2:
                Log.command('kenkenjr called.')
                await message.channel.send(f'{choice(self.reactions)}')
            else:
                await message.channel.send(''.join([choice(self.characters) for _ in range(count)])[:1997]
                                           + ''.join([choice(tuple('!?.')) for _ in range(3)]))

    @CustomCog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        if payload.emoji.name == get_emoji(':wastebasket:'):
            message = await (await self.client.fetch_channel(payload.channel_id)).fetch_message(payload.message_id)
            if message.author.id == self.client.user.id:
                await message.delete()

    @modules.command(name='안녕', aliases=('반가워', 'ㅎㅇ', 'greet', 'hi', 'hello'))
    async def greet(self, ctx: Context):
        await ctx.send(self.get_greeting(ctx.message))

    @modules.command(name='핑', aliases=('ping', 'p'))
    @tokens_len(1)
    async def ping(self, ctx: Context):
        literal = literals('ping')
        message = await ctx.send(literal['start'])
        await message.edit(content=literal['done'] % (message.created_at - ctx.message.created_at))

    @modules.command(name='프로필', aliases=('profile', '사용자', 'user'))
    async def profile(self, ctx: Context, *, user: Union[Member, User] = None):
        if user is None:
            user = ctx.author
            try:
                user = await MemberConverter().convert(ctx, str(user.id))
            except BadArgument:
                pass
        profile_embed = get_profile_embed(user)
        message = await ctx.send(embed=profile_embed)
        await attach_toggle_interface(
            self.client, message,
            EmojiInterfaceState(FOLD_EMOJI, message.edit, embed=get_profile_embed(user)),
            EmojiInterfaceState(DETAIL_EMOJI, message.edit, embed=get_profile_embed(user, False)))

    @modules.command(name='거리두기', aliases=('사회적거리두기', '안전거리'))
    @guild_only()
    async def distance(self, ctx: Context):
        literal = literals('distance')
        nick = ctx.author.nick
        if nick is None:
            nick = ctx.author.name
        if ' ' in nick:
            nick = nick.replace(' ', '')
        distance_regex = '\\u2003+'
        if found := findall(distance_regex, nick):
            level = len(min(found, key=len)) + 1
            print(nick)
            nick = sub(distance_regex, ' ' * level, nick)
            print(nick)
        else:
            level = 1
            nick = ' '.join(list(nick))
        try:
            await ctx.author.edit(nick=nick)
        except HTTPException as e:
            await ctx.send(literal['failed'])
        else:
            await ctx.send((' ' * level).join(list(literal['done'] % level)))

    @modules.command(name='서버', aliases=('길드',))
    @guild_only()
    async def guild_profile(self, ctx: Context):
        message = await ctx.send(embed=await get_guild_profile_embed(ctx.guild))
        await attach_toggle_interface(
            self.client, message,
            EmojiInterfaceState(FOLD_EMOJI, message.edit, embed=await get_guild_profile_embed(ctx.guild)),
            EmojiInterfaceState(DETAIL_EMOJI, message.edit, embed=await get_guild_profile_embed(ctx.guild, False)))

    # TODO add command about color pickers


def setup(client: commands.Bot):
    client.add_cog(BaseCog(client))

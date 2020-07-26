import discord
from discord.ext.commands import Context, check

from kenkenjr.bot import Kenken
from kenkenjr.utils.literal import get_constant


def owner_only():
    def predicate(ctx: Context) -> bool:
        return ctx.author.id in (get_constant('zer0ken_id'),)

    predicate.name = 'owner_only'
    return check(predicate)


def guild_only():
    def predicate(ctx: Context) -> bool:
        return ctx.guild is not None

    predicate.name = 'guild_only'
    return check(predicate)


def dm_only():
    def predicate(ctx: Context) -> bool:
        return ctx.guild is None

    predicate.name = 'dm_only'
    return check(predicate)


def for_guilds(guild_id: tuple or int):
    if type(guild_id) != tuple:
        guild_id = (guild_id,)

    def predicate(ctx: Context) -> bool:
        if ctx.message.guild is not None:
            return ctx.message.guild.id in guild_id
        return False

    predicate.name = 'for_guilds'
    return check(predicate)


def for_channels(channel_id: tuple or int):
    if type(channel_id) != tuple:
        channel_id = (channel_id,)

    def predicate(ctx: Context) -> bool:
        return ctx.message.channel.id in channel_id

    predicate.name = 'for_channels'
    return check(predicate)


def avoid_guilds(guild_id: tuple or int):
    if type(guild_id) != tuple:
        guild_id = (guild_id,)

    def predicate(ctx: Context) -> bool:
        if ctx.message.guild:
            return ctx.message.guild.id not in guild_id
        return True

    predicate.name = 'avoid_guilds'
    return check(predicate)


def avoid_channels(channel_id: tuple or int):
    if type(channel_id) != tuple:
        channel_id = (channel_id,)

    def predicate(ctx: Context) -> bool:
        return ctx.message.channel.id not in channel_id

    predicate.name = 'avoid_channels'
    return check(predicate)


def bot_need_permissions(**permissions):
    def predicate(ctx: Context) -> bool:
        client_permissions: dict = dict(ctx.guild.get_member(Kenken().user.id).guild_permissions)
        for perm, value in permissions.items():
            if client_permissions[perm] != value:
                return False
        return True

    predicate.name = 'bot_need_permissions'
    return check(predicate)


def partner_only():
    async def predicate(ctx: Context):
        partner_role = get_constant('partner_role')
        shtelo_guild = get_constant('shtelo_guild')
        guild = await ctx.bot.fetch_guild(shtelo_guild)
        member = None
        if guild is not None:
            member = await guild.fetch_member(ctx.author.id)
        if member is None:
            return False
        if isinstance(partner_role, int):
            role = discord.utils.get(member.roles, id=partner_role)
        else:
            role = discord.utils.get(member.roles, name=partner_role)
        if role is None:
            return False
        return True

    predicate.name = 'partner_only'
    return check(predicate)


def tokens_len(count: tuple or int):
    if type(count) != tuple:
        count = (count,)

    def predicate(ctx: Context) -> bool:
        return len(ctx.message.content.split()) in count

    predicate.name = 'tokens_len'
    return check(predicate)


def tokens_len_range(minimum: int = 0, maximum: int = 0):
    def predicate(ctx: Context) -> bool:
        len_ = len(ctx.message.content.split())
        return (not minimum or len_ >= minimum) and (not maximum or len_ <= maximum)

    predicate.name = 'tokens_len_range'

    return check(predicate)

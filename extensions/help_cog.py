import asyncio
from typing import List

from discord import Reaction, User
from discord.ext.commands import Context, Cog, Command, Bot, BadArgument

import modules
from modules import CustomCog, ChainedEmbed, CustomGroup
from utils import get_cog, get_constant, literals, get_check, get_emoji, InterfaceState, attach_page_interface

COMMANDS_TIMEOUT = 60


def brief_cog(cog: Cog):
    brief = literals('cog_brief')['no_description']
    if cog.description is not None:
        brief = cog.description
    elif cog.get_commands():
        brief = ''
    if not cog.get_commands():
        return brief
    commands = ''
    for command in cog.get_commands():
        if not command.enabled:
            continue
        commands += brief_command(command) + '\n'
    if commands:
        brief += '\n' + commands
    return brief


def brief_group(group: CustomGroup):
    brief = '* `' + group.qualified_name + '`'
    if group.brief is not None:
        brief += ': ' + group.brief
    for command in group.commands:
        if not command.enabled:
            continue
        if isinstance(command, CustomGroup):
            brief += '\n' + brief_group(command)
        else:
            brief += '\n' + brief_command(command)
    return brief


def brief_command(command: Command):
    if isinstance(command, CustomGroup):
        return brief_group(command)
    brief = '* `' + command.qualified_name + '`'
    if command.brief is not None:
        brief += ': ' + command.brief
    return brief


def get_command_default_signature(command: Command):
    return (get_constant('default_prefix')
            + (command.full_parent_name + ' ' if command.full_parent_name else '')
            + command.name + ' '
            + command.signature).rstrip()


def get_command_signature(command: Command):
    parent = command.full_parent_name
    if len(command.aliases) > 0:
        aliases = '|'.join(command.aliases)
        fmt = '[%s|%s]' % (command.name, aliases)
        if parent:
            fmt = parent + ' ' + fmt
        alias = fmt
    else:
        alias = command.name if not parent else parent + ' ' + command.name
    return ('%s%s %s' % (get_constant('default_prefix'), alias, command.signature)).rstrip()


def stringify_command(command: Command):
    signature = '`' + get_command_signature(command) + '`\n'
    info = ''
    if command.brief is not None:
        info = command.brief
    if command.help is not None:
        info = '- ' + info + '\n- ' + command.help
    return signature + info


def check_correlation(command: Command, keywords: List[str], embed: ChainedEmbed):
    found = 0
    command_info = stringify_command(command)
    for keyword in keywords:
        if keyword in command_info:
            embed.add_field(name=command.qualified_name, value=command_info)
            found += 1
        break
    if isinstance(command, CustomGroup):
        for subcommand in command.commands:
            found += check_correlation(subcommand, keywords, embed)
    return found


class HelpCog(CustomCog, name=get_cog('HelpCog')['name']):
    """
    필요한 명령어를 찾거나 사용볍을 확인하기 위한 기능을 포함합니다.
    """

    def __init__(self, client: Bot):
        super().__init__(client)
        self.client: Bot = client

    @modules.command(name='검색', aliases=('찾기', 'search', 's'))
    async def search(self, ctx: Context, keyword: str, *keywords: str):
        literal = literals('search')
        keywords = list(keywords)
        keywords.append(keyword)
        description = literal['found']
        embeds = ChainedEmbed(title=literal['title'], description=description)
        embeds.set_thumbnail(url=self.client.user.avatar_url)
        found = 0
        for command in self.client.commands:
            check_correlation(command, keywords, embeds)
        embeds.description = description % (found, ', '.join(keywords)) if found \
            else literal['not_found'] % ', '.join(keywords)
        for embed in embeds.to_list():
            await ctx.send(embed=embed)

    @modules.command(name='명령어', aliases=('commands', 'cmd', 'cmds'))
    async def commands(self, ctx: Context, *, category: str = ''):
        cog: Cog = self.client.get_cog(category)
        if cog is not None:
            await self.send_cog_info(ctx, cog)
        else:
            await self.send_cog_list(ctx)

    @modules.command(name='도움말', aliases=('help', 'h'))
    async def help(self, ctx: Context, *, command_name: str = ''):
        if not command_name:
            command_name = '도움말'
        command: Command = self.client.get_command(command_name)
        cog: Cog = self.client.get_cog(command_name)
        if command is not None:
            await self.send_command_help(ctx, command)
        elif cog is not None:
            await self.send_cog_info(ctx, cog)
        else:
            raise BadArgument(f'command "{command_name}" is not found')

    async def send_cog_info(self, ctx: Context, cog: Cog):
        cog_name = cog.qualified_name
        if isinstance(cog, CustomCog):
            cog_name = cog.emoji + ' ' + cog_name
        brief = brief_cog(cog)
        embeds = ChainedEmbed(title=cog_name, description=brief)
        embeds.set_thumbnail(url=self.client.user.avatar_url)
        for embed in embeds.to_list():
            await ctx.send(embed=embed)

    async def send_cog_list(self, ctx: Context):
        literal = literals('send_cog_list')
        states = list()
        count = len(self.client.cogs)
        message = None
        for i, cog in enumerate(sorted(self.client.cogs.items(),
                                       key=lambda item: get_cog(type(item[1]).__name__)['priority'])):
            name, cog = cog
            if isinstance(cog, CustomCog):
                name = cog.emoji + ' ' + name
            page_embed = ChainedEmbed(title=literal['title'], description=literal['description'])
            page_embed.set_thumbnail(url=self.client.user.avatar_url)
            page_embed.add_field(name=name, value=brief_cog(cog))
            page_embed.set_footer(text=literal['footer'] % (i + 1, count))
            if message is None:
                message = await ctx.send(embed=page_embed)
            states.append(InterfaceState(callback=message.edit, embed=page_embed))
        await attach_page_interface(self.client, message, states, ctx.author)

    async def send_command_help(self, ctx: Context, command: Command):
        command_name = command.qualified_name
        default_signature = get_command_default_signature(command)
        footer = get_command_signature(command)
        description = ''
        if command.help is not None:
            description = command.help + '\n'
        elif command.brief is not None:
            description = command.brief + '\n'
        description += f'`{default_signature}`'
        embeds = ChainedEmbed(title=get_constant('default_prefix') + command_name, description=description)
        embeds.set_thumbnail(url=self.client.user.avatar_url)
        if isinstance(command, CustomGroup):
            embeds.add_field(name=literals('send_command_help')['subcommand'],
                             value=f'\n{brief_group(command)}\n')
        for check in command.checks:
            data = get_check(check.name)
            if data is None:
                continue
            embeds.add_field(name=f'{data["emoji"]} {data["name"]}', value=data["description"])
        if command.cog is not None:
            category = command.cog.qualified_name
            if isinstance(command.cog, CustomCog):
                category = command.cog.emoji + ' ' + category
            footer += ' · ' + category
        embeds.set_footer(text=footer)
        for embed in embeds.to_list():
            await ctx.send(embed=embed)


def setup(client: Bot):
    client.remove_command('help')
    client.add_cog(HelpCog(client))

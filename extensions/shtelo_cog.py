import asyncio
from datetime import datetime
from typing import Optional

from discord import Member
from discord.ext.commands import Bot, Context, BucketType, BadArgument

import modules
from modules import CustomCog, sheet_read, ChainedEmbed, doc_read, shared_cooldown, DeckHandler, sheet_write, \
    partner_only, guild_only
from utils import get_cog, literals, wrap_codeblock, get_constant, FreshData, get_emoji, InterfaceState, \
    attach_page_interface

TIMESTAMP = 0
EMAIL = 1
DISCORD_ID = 2
SUBACCOUNT = 3
NICKNAME = 4
INVITER = 5
KNOWLEDGE = 6
TWITTER_ID = 7
STATE = 13
REMARKS = 14
HOUR = 3600
STATE_RECEIVED = '접수됨'
STATE_APPROVED = '승인됨'
STATE_REJECTED = '기각됨'
NSFW_TIMEOUT = 60
NSFW_EMOJI = get_emoji(':underage:')

deck_cooldown = shared_cooldown(1, 60, BucketType.category)


def get_application_sheet():
    sheet = get_constant('application')
    rows = sheet_read(sheet['sheet_id'], sheet['range'])
    keys = rows.pop(0)
    for reply in rows:
        while len(reply) < len(keys):
            reply.append('')
    return keys, rows


def get_nickname(member: Member):
    _, rows = get_application_sheet()
    for row in rows:
        if str(member) in row:
            return row[NICKNAME]


async def update_application(member: Member, state: str, remarks: str, on_error=None):
    sheet = get_constant('application')
    keys, rows = get_application_sheet()
    result = False
    for row in rows:
        if str(member) in row and row[STATE] != state:
            row[STATE] = state
            if remarks is not None and not row[REMARKS]:
                row[REMARKS] = str(remarks).replace('->', '→')
            print(row)
            result = row.copy()
            break
    if not result:
        if on_error is not None:
            await on_error
        raise BadArgument(f'application not found')
    rows.insert(0, keys)
    sheet_write(sheet['sheet_id'], sheet['range'], rows)
    return result


def add_member(member: Member):
    sheet = get_constant('member_list')
    rows = sheet_read(sheet['sheet_id'], sheet['range'])
    nickname = get_nickname(member)
    result = [int(rows[-1][0]) + 1, nickname, str(member.joined_at), str(member.roles[-1])]
    rows.append(result.copy())
    if result:
        sheet_write(sheet['sheet_id'], sheet['range'], rows)
    return result


def edit_member(query: str, nickname: Optional[str] = None, state: Optional[str] = None):
    sheet = get_constant('member_list')
    rows = sheet_read(sheet['sheet_id'], sheet['range'])
    result = None
    for row in rows:
        if query in row:
            if nickname is not None:
                row[1] = nickname
            if state is not None:
                row[3] = state
            result = row.copy()
            break
    if result:
        sheet_write(sheet['sheet_id'], sheet['range'], rows)
    return result


def get_state_emoji(application: list):
    literal = literals('get_state_emoji')
    if application[STATE] == STATE_RECEIVED:
        return literal['received']
    elif application[STATE] == STATE_APPROVED:
        return literal['approved']
    elif application[STATE] == STATE_REJECTED:
        return literal['rejected']
    return literal['not_handled']


def get_application_embed(data: list):
    literal = literals('get_application_embed')
    discord_id = data[DISCORD_ID]
    title = literal['title'] % discord_id + get_state_emoji(data)
    embeds = ChainedEmbed(title=title,
                          description=literal['description'] % (data[TIMESTAMP], data[EMAIL]))
    if data[SUBACCOUNT] != literal['false']:
        embeds.add_field(name=literal['subaccount'], value=literal['mainaccount'] % data[SUBACCOUNT])
    if data[NICKNAME]:
        embeds.add_field(name=literal['nickname'], value='**' + data[NICKNAME] + '**')
    if data[DISCORD_ID]:
        embeds.add_field(name=literal['discord_id'], value='`' + data[DISCORD_ID] + '`', inline=True)
    if data[TWITTER_ID]:
        embeds.add_field(name=literal['twitter_id'], value='`' + data[TWITTER_ID] + '`', inline=True)
    if data[INVITER]:
        embeds.add_field(name=literal['inviter'], value='`' + data[INVITER] + '`', inline=True)
    if data[KNOWLEDGE]:
        embeds.add_field(name=literal['knowledge'], value='```\n' + data[KNOWLEDGE] + '\n```')
    if data[REMARKS]:
        embeds.add_field(name=literal['remarks'], value='```\n' + data[REMARKS] + '\n```')
    return embeds


def get_application_raw_embed(keys: list, data: list):
    literal = literals('get_application_raw_embed')
    discord_id = data[DISCORD_ID]
    title = literal['title'] % discord_id + get_state_emoji(data)
    embeds = ChainedEmbed(title=title, description=literal['description'])
    for i in range(len(keys)):
        if data[i]:
            embeds.add_field(name=keys[i], value='```\n' + data[i] + '\n```')
    return embeds


class ShteloCog(CustomCog, name=get_cog('ShteloCog')['name']):
    """
    슈텔로의 관리를 위한 기능을 포함합니다.
    """

    def __init__(self, client: Bot):
        super().__init__(client)
        self.client: Bot = client
        self.regulation: Optional[FreshData] = None
        self.deck_handler: DeckHandler = DeckHandler(client)

    def fetch_regulation(self):
        if self.regulation is None \
                or (datetime.now() - self.regulation.timestamp).total_seconds() > HOUR:
            paragraphs = wrap_codeblock(doc_read(get_constant('regulation')['doc_id']), split_paragraph=True)
            self.regulation = FreshData(paragraphs)
        else:
            paragraphs = self.regulation.data
        return paragraphs

    @modules.group(name='가입신청서', aliases=('가입', '신청서'))
    async def applications(self, ctx: Context, *query: str):
        literal = literals('applications')
        start_message = await ctx.send(literal['start'])
        message = None
        _, replies = get_application_sheet()
        query = tuple({q for q in query if q in (STATE_RECEIVED, STATE_APPROVED, STATE_REJECTED)})
        if not query:
            query = (STATE_RECEIVED,)
        queried = [reply for reply in replies if not reply[STATE] or reply[STATE] in query]
        count = len(queried)
        states = list()
        for i, reply in enumerate(reversed(queried)):
            reply_embed = get_application_embed(reply)
            reply_embed.set_footer(text=literal['footer'] % (i + 1, count))
            if message is None:
                await start_message.edit(content=literal['done'] % (f'({", ".join(query)})', count),
                                         embed=reply_embed)
                message = start_message
            states.append(InterfaceState(message.edit, embed=reply_embed))
        if message is None:
            await start_message.edit(content=literal['not_found'])
        else:
            await attach_page_interface(self.client, message, states, ctx.author)

    @applications.command(name='접수')
    @guild_only()
    @partner_only()
    async def application_receive(self, ctx: Context, member: Member, *, remarks: str = None):
        literal = literals('application_receive')
        message = await ctx.send(literal['start'])
        if remarks is None:
            remarks = member.id
        await update_application(member, STATE_RECEIVED, remarks, message.delete())
        tester_role = ctx.guild.get_role(get_constant('tester_role'))
        if tester_role not in member.roles:
            await member.add_roles(tester_role)
        await message.edit(content=literal['done'] % member.mention)

    @applications.command(name='승인')
    @guild_only()
    @partner_only()
    async def application_approve(self, ctx: Context, member: Member, *, remarks: str = None):
        literal = literals('application_approve')
        message = await ctx.send(literal['start'])
        if remarks is None:
            remarks = member.id
        await update_application(member, STATE_APPROVED, remarks, message.delete())
        tester_role = ctx.guild.get_role(get_constant('tester_role'))
        member_role = ctx.guild.get_role(get_constant('member_role'))
        if tester_role in member.roles:
            await member.remove_roles(tester_role)
        if member_role not in member.roles:
            await member.add_roles(member_role)
        await message.edit(content=literal['done'] % member.mention)

    @modules.group(name='회원', enabled=False)
    async def member(self, ctx: Context):
        pass

    @member.command(name='등록')
    @guild_only()
    @partner_only()
    async def member_register(self, ctx: Context, member: Member):
        literal = literals('member')
        message = await ctx.send(literal['start'])
        add_member(member)
        await message.edit(content=literal['done'])

    @member.group(name='수정', enabled=False)
    async def member_edit(self, ctx: Context):
        pass

    @member_edit.command(name='닉네임')
    async def member_edit_nickname(self, ctx: Context, query: str, *, nickname: str):
        literal = literals('member')
        message = await ctx.send(literal['start'])
        edit_member(query, nickname)
        await message.edit(content=literal['done'])

    @member_edit.command(name='상태')
    async def member_edit_state(self, ctx: Context, query: str, *, state: str):
        literal = literals('member')
        message = await ctx.send(literal['start'])
        edit_member(query, None, state)
        await message.edit(content=literal['done'])


    

    # @applications.command(name='기각')
    # @guild_only()
    # @partner_only()
    # async def application_reject(self, ctx: Context, member: Member, *, remarks: str = None):
    #     literal = literals('application_reject')
    #     message = await ctx.send(literal['start'])
    #     if remarks is None:
    #         remarks = member.id
    #     application = await update_application(member, STATE_REJECTED, remarks, message.delete())
    #     tester_role = ctx.guild.get_role(get_constant('tester_role'))
    #     if tester_role in member.roles:
    #         await member.remove_roles(tester_role)
    #     update_member_list(member, application[NICKNAME], STATE_QUIT)
    #     await message.edit(content=literal['done'] % member.mention)

    @applications.command(name='전체', aliases=('*',))
    async def applications_all(self, ctx: Context):
        await self.applications(ctx, STATE_RECEIVED, STATE_APPROVED, STATE_REJECTED)

    @modules.group(name='회칙')
    async def regulation(self, ctx: Context, *, keyword: str = ''):
        literal = literals('regulation')
        message = await ctx.send(literal['start'])
        paragraphs = self.fetch_regulation()
        await message.edit(content=literal['done'])
        if not keyword:
            await ctx.author.send(paragraphs[0])
            await ctx.author.send(literal['no_keyword'])
        else:
            found = [p for p in paragraphs[1:] if '# ' + keyword + '\n' in p]
            if not found:
                found = [p for p in paragraphs[1:] if keyword in p]
            if not found:
                await ctx.author.send(literal['not_found'] % keyword)
            else:
                for p in found:
                    await ctx.author.send(p)

    @regulation.command(name='전체', aliases=('*',))
    async def regulation_all(self, ctx: Context):
        literal = literals('regulation_all')
        message = await ctx.send(literal['start'])
        paragraphs = wrap_codeblock(doc_read(get_constant('regulation')['doc_id']), split_paragraph=True)
        await message.edit(content=literal['done'])
        for p in paragraphs:
            await ctx.author.send(p)

    @modules.command(name='회의록')
    async def meeting_log(self, ctx: Context):
        await ctx.send(literals('meeting_log')['message'])


def setup(client: Bot):
    client.add_cog(ShteloCog(client))

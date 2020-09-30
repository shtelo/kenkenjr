import asyncio
from datetime import datetime
from typing import Optional

from discord import Member, Message, TextChannel, Role, Reaction, User, Guild
from discord.ext.commands import Bot, Context, BucketType, BadArgument, MemberConverter

import modules
from modules import CustomCog, sheet_read, ChainedEmbed, doc_read, shared_cooldown, DeckHandler, sheet_write, \
    partner_only, guild_only
from utils import get_cog, literals, wrap_codeblock, get_constant, FreshData, get_emoji, InterfaceState, \
    attach_page_interface

NO = '아니오'

APPLICATION_TIMESTAMP = 0
APPLICATION_EMAIL = 1
APPLICATION_DISCORD_ID = 2
APPLICATION_SUBACCOUNT = 3
APPLICATION_NICKNAME = 4
APPLICATION_INVITER = 5
APPLICATION_KNOWLEDGE = 6
APPLICATION_TWITTER_ID = 7
APPLICATION_STATE = 13
APPLICATION_REMARKS = 14

MEMBER_LIST_NUMBER = 0
MEMBER_LIST_NICKNAME = 1
MEMBER_LIST_STATE = 2
MEMBER_LIST_JOINED_AT = 3

APPLICATION_RECEIVED = '접수됨'
APPLICATION_APPROVED = '승인됨'
APPLICATION_REJECTED = '기각됨'

SECOND_PER_HOUR = 3600

NSFW_TIMEOUT = 60
NSFW_EMOJI = get_emoji(':underage:')

CONFIRM_EMOJI = get_emoji(':white_check_mark:')

deck_cooldown = shared_cooldown(1, 60, BucketType.category)


def get_application_sheet():
    sheet = get_constant('application')
    rows = sheet_read(sheet['sheet_id'], sheet['range'])
    keys = rows.pop(0)
    for reply in rows:
        while len(reply) < len(keys):
            reply.append('')
    return keys, rows


def get_application_of(member: Member, rows=None):
    if rows is None:
        _, rows = get_application_sheet()
    for row in reversed(rows):
        if str(member) in row:
            return row
    return None


def get_nickname(member: Member, rows=None):
    if rows is None:
        _, rows = get_application_sheet()
    for row in rows:
        if str(member) in row:
            return row[APPLICATION_NICKNAME]


async def update_application(member: Member, state: str, remarks: str, on_error=None, keys=None, rows=None):
    sheet = get_constant('application')
    if keys is None or rows is None:
        keys, rows = get_application_sheet()
    result = False
    for row in rows:
        if str(member) in row and row[APPLICATION_STATE] != state:
            row[APPLICATION_STATE] = state
            if remarks is not None and not row[APPLICATION_REMARKS]:
                row[APPLICATION_REMARKS] = str(remarks).replace('->', '→')
            result = row.copy()
            break
    if not result:
        if on_error is not None:
            await on_error()
        raise BadArgument(f'application not found')
    rows.insert(0, keys)
    sheet_write(sheet['sheet_id'], sheet['range'], rows)
    return result


def add_member(member: Member, nickname=None, rows=None):
    sheet = get_constant('member_list')
    if rows is None:
        rows = sheet_read(sheet['sheet_id'], sheet['range'])
    if nickname is None:
        nickname = get_nickname(member)
    result = [int(rows[-1][0]) + 1, nickname, str(member.roles[-1]), str(member.joined_at)]
    rows.append(result.copy())
    if result:
        sheet_write(sheet['sheet_id'], sheet['range'], rows)
    return result


def edit_member(query: str, nickname: Optional[str] = None, state: Optional[str] = None, rows=None):
    sheet = get_constant('member_list')
    if rows is None:
        rows = sheet_read(sheet['sheet_id'], sheet['range'])
    result = None
    for row in rows:
        if query in row:
            if nickname is not None:
                row[MEMBER_LIST_NICKNAME] = nickname
            if state is not None:
                row[MEMBER_LIST_STATE] = state
            result = row.copy()
            break
    if result:
        sheet_write(sheet['sheet_id'], sheet['range'], rows)
    return result


def get_application_state_emoji(application: list):
    literal = literals('get_state_emoji')
    if application[APPLICATION_STATE] == APPLICATION_RECEIVED:
        return literal['received']
    elif application[APPLICATION_STATE] == APPLICATION_APPROVED:
        return literal['approved']
    elif application[APPLICATION_STATE] == APPLICATION_REJECTED:
        return literal['rejected']
    return literal['not_handled']


def get_application_embed(data: list):
    literal = literals('get_application_embed')
    discord_id = data[APPLICATION_DISCORD_ID]
    title = literal['title'] % discord_id + get_application_state_emoji(data)
    embeds = ChainedEmbed(title=title,
                          description=literal['description'] % (data[APPLICATION_TIMESTAMP], data[APPLICATION_EMAIL]))
    if data[APPLICATION_SUBACCOUNT] != literal['false']:
        embeds.add_field(name=literal['subaccount'], value=literal['mainaccount'] % data[APPLICATION_SUBACCOUNT])
    if data[APPLICATION_NICKNAME]:
        embeds.add_field(name=literal['nickname'], value='**' + data[APPLICATION_NICKNAME] + '**')
    if data[APPLICATION_DISCORD_ID]:
        embeds.add_field(name=literal['discord_id'], value='`' + data[APPLICATION_DISCORD_ID] + '`', inline=True)
    if data[APPLICATION_TWITTER_ID]:
        embeds.add_field(name=literal['twitter_id'], value='`' + data[APPLICATION_TWITTER_ID] + '`', inline=True)
    if data[APPLICATION_INVITER]:
        embeds.add_field(name=literal['inviter'], value='`' + data[APPLICATION_INVITER] + '`', inline=True)
    if data[APPLICATION_KNOWLEDGE]:
        embeds.add_field(name=literal['knowledge'], value='```\n' + data[APPLICATION_KNOWLEDGE] + '\n```')
    if data[APPLICATION_REMARKS]:
        embeds.add_field(name=literal['remarks'], value='```\n' + data[APPLICATION_REMARKS] + '\n```')
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
        self.shtelo_guild: Optional[Guild] = None
        self.partner_channel: Optional[TextChannel] = None
        self.member_role: Optional[Role] = None
        self.tester_role: Optional[Role] = None
        self.title_div_role: Optional[Role] = None
        self.deck_div_role: Optional[Role] = None
        self.partner_role: Optional[Role] = None

    async def after_ready(self):
        self.shtelo_guild = self.client.get_guild(get_constant('shtelo_guild'))
        self.partner_channel = self.client.get_channel(get_constant('partner_channel'))
        self.member_role = self.shtelo_guild.get_role(get_constant('member_role'))
        self.tester_role = self.shtelo_guild.get_role(get_constant('tester_role'))
        self.title_div_role = self.shtelo_guild.get_role(get_constant('title_div_role'))
        self.deck_div_role = self.shtelo_guild.get_role(get_constant('deck_div_role'))
        self.partner_role = self.shtelo_guild.get_role(get_constant('partner_role'))

    def fetch_regulation(self):
        if self.regulation is None \
                or self.regulation.data is None:
            paragraphs = wrap_codeblock(doc_read(get_constant('regulation')['doc_id']), split_paragraph=True)
            self.regulation = FreshData(paragraphs, SECOND_PER_HOUR)
        else:
            paragraphs = self.regulation.data
        return paragraphs

    async def receive_application(self, member: Member, remarks: str, on_error=None, keys=None, rows=None):
        await update_application(member, APPLICATION_RECEIVED, remarks, on_error, keys, rows)
        tasks = list()
        if self.tester_role not in member.roles:
            tasks.append(member.add_roles(self.tester_role))
        if self.title_div_role not in member.roles:
            tasks.append(member.add_roles(self.title_div_role))
        if self.deck_div_role not in member.roles:
            tasks.append(member.add_roles(self.deck_div_role))
        if tasks:
            await asyncio.wait(tasks)

    @modules.CustomCog.listener(name='on_message')
    async def receive_automatically(self, message: Message):
        literal = literals('receive_automatically')

        async def failed():
            await self.partner_channel.send(literal['failed'] % message.author.mention)

        if message.channel.id != get_constant('self_introduction_channel') or len(message.content) < 10:
            return
        keys, rows = get_application_sheet()
        application = get_application_of(message.author, rows)
        if application is None or application[APPLICATION_STATE]:
            return
        trigger_member_name = application[APPLICATION_INVITER]
        trigger_role = self.member_role
        if not trigger_member_name:
            trigger_member_name = application[APPLICATION_SUBACCOUNT]
            trigger_role = None
        try:
            trigger_member = await MemberConverter().convert(await self.client.get_context(message),
                                                             trigger_member_name)
        except BadArgument as e:
            await failed()
            raise e
        if trigger_role is not None and trigger_role not in trigger_member.roles:
            await failed()
            return
        remark = str(message.author.id)
        if not application[APPLICATION_INVITER]:
            remark = literal['subaccount'] % (trigger_member.id, remark)
        await self.receive_application(message.author, remark, None, keys, rows)
        await message.add_reaction(CONFIRM_EMOJI)
        if application[APPLICATION_INVITER]:
            add_member(message.author, application[APPLICATION_NICKNAME])
        await self.partner_channel.send(literal['done'] % (message.author.mention, message.jump_url),
                                        embed=get_application_embed(application))

    @modules.group(name='가입신청서', aliases=('가입', '신청서'))
    async def applications(self, ctx: Context, *query: str):
        literal = literals('applications')
        start_message = await ctx.send(literal['start'])
        message = None
        _, replies = get_application_sheet()
        query = tuple({q for q in query if q in (APPLICATION_RECEIVED, APPLICATION_APPROVED, APPLICATION_REJECTED)})
        if not query:
            query = (APPLICATION_RECEIVED,)
        queried = [reply for reply in replies if not reply[APPLICATION_STATE] or reply[APPLICATION_STATE] in query]
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
        await self.receive_application(member, remarks, message.delete)
        await ctx.message.edit(content=literal['done'] % member.mention)

    @applications.command(name='승인')
    @guild_only()
    @partner_only()
    async def application_approve(self, ctx: Context, member: Member, *, remarks: str = None):
        literal = literals('application_approve')
        message = await ctx.send(literal['start'])
        if remarks is None:
            remarks = member.id
        await update_application(member, APPLICATION_APPROVED, remarks, message.delete)
        tester_role = ctx.guild.get_role(get_constant('tester_role'))
        member_role = ctx.guild.get_role(get_constant('member_role'))
        tasks = list()
        if tester_role in member.roles:
            tasks.append(member.remove_roles(tester_role))
        if member_role not in member.roles:
            tasks.append(member.add_roles(member_role))
        tasks.append(message.edit(content=literal['done'] % member.mention))
        await asyncio.wait(tasks)

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
    @guild_only()
    @partner_only()
    async def member_edit(self, ctx: Context):
        pass

    @member_edit.command(name='닉네임')
    @guild_only()
    @partner_only()
    async def member_edit_nickname(self, ctx: Context, query: str, *, nickname: str):
        literal = literals('member')
        message = await ctx.send(literal['start'])
        edit_member(query, nickname)
        await message.edit(content=literal['done'])

    @member_edit.command(name='상태')
    @guild_only()
    @partner_only()
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
        await self.applications(ctx, APPLICATION_RECEIVED, APPLICATION_APPROVED, APPLICATION_REJECTED)

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

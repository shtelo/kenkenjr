from datetime import datetime
from typing import Optional

from discord.ext.commands import Bot, Context, BucketType

import modules
from modules import CustomCog, sheet_read, ChainedEmbed, doc_read, shared_cooldown, DeckHandler
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
    constant = get_constant('application')
    rows = sheet_read(constant['sheet_id'], constant['read_range'])
    keys = rows.pop(0)
    for reply in rows:
        while len(reply) < len(keys):
            reply.append('')
    return keys, rows


def get_state_of_application(application: list):
    literal = literals('get_state')
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
    title = literal['title'] % discord_id + get_state_of_application(data)
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
    title = literal['title'] % discord_id + get_state_of_application(data)
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

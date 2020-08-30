from datetime import datetime

from discord.ext.commands import Bot, Context, BucketType

import modules
from modules import CustomCog, sheet_read, ChainedEmbed, doc_read, shared_cooldown, DeckHandler
from utils import get_cog, literals, wrap_codeblock, get_constant, FreshData, get_emoji

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
RECEIVED = '접수됨'
APPROVED = '승인됨'
REJECTED = '기각됨'
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


def state_of_application(application: list):
    literal = literals('get_state')
    if application[STATE] == RECEIVED:
        return literal['received']
    elif application[STATE] == APPROVED:
        return literal['approved']
    elif application[STATE] == REJECTED:
        return literal['rejected']
    return ''


def get_application_embed(data: list):
    literal = literals('get_application_embed')
    discord_id = data[DISCORD_ID]
    title = literal['title'] % discord_id + state_of_application(data)
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
    title = literal['title'] % discord_id + state_of_application(data)
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
        self.regulation: FreshData = None
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
    async def applications(self, ctx: Context):
        literal = literals('applications')
        message = await ctx.send(literal['start'])
        _, replies = get_application_sheet()
        count = len(replies)
        for reply in replies:
            if reply[STATE]:
                count -= 1
                continue
            embeds = get_application_embed(reply)
            for embed in embeds.to_list():
                await ctx.author.send(embed=embed)
        await message.edit(content=literal['done'] % count if count else literal['not_found'])

    @applications.command(name='전체', aliases=('*',))
    async def applications_all(self, ctx: Context):
        literal = literals('applications_all')
        message = await ctx.send(literal['start'])
        _, replies = get_application_sheet()
        count = len(replies)
        for reply in replies:
            embeds = get_application_embed(reply)
            for embed in embeds.to_list():
                await ctx.author.send(embed=embed)
        await message.edit(content=literal['done'] % count if count else literal['not_found'])

    @applications.group(name='원본')
    async def application_raw(self, ctx: Context):
        literal = literals('application_raw')
        message = await ctx.send(literal['start'])
        keys, replies = get_application_sheet()
        count = len(replies)
        for reply in replies:
            if reply[STATE]:
                count -= 1
                continue
            embeds = get_application_raw_embed(keys, reply)
            for embed in embeds.to_list():
                await ctx.author.send(embed=embed)
        await message.edit(content=literal['done'] % count if count else literal['not_found'])

    @application_raw.command(name='전체', aliases=('*',))
    async def application_raw_all(self, ctx: Context):
        literal = literals('application_raw_all')
        message = await ctx.send(literal['start'])
        keys, replies = get_application_sheet()
        count = len(replies)
        for reply in replies:
            embeds = get_application_raw_embed(keys, reply)
            for embed in embeds.to_list():
                await ctx.author.send(embed=embed)
        await message.edit(content=literal['done'] % count if count else literal['not_found'])

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

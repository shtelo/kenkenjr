from datetime import datetime
from typing import Optional

from discord.ext.commands import Bot, Context

from kenkenjr import modules
from kenkenjr.modules import CustomCog, sheet_read, get_constant, ChainedEmbed, doc_read
from kenkenjr.utils import get_cog, literals, wrap_codeblock

TIMESTAMP = 0
EMAIL = 1
DISCORD_ID = 2
SUBACCOUNT = 3
NICKNAME = 4
INVITER = 5
KNOWLEDGE = 6
TWITTER_ID = 7
DONE = 13
TRUE = ('TRUE', '네', True)
FALSE = ('FALSE', '아니오', False, '')
HOUR = 3600


class FreshData:
    def __init__(self, data):
        self.data = data
        self.timestamp = datetime.now()


class ShteloCog(CustomCog, name=get_cog('ShteloCog')['name']):
    """
    슈텔로의 관리를 위한 기능을 포함합니다.
    """

    def __init__(self, client: Bot):
        super().__init__(client)
        self.client: Bot = client
        self.keys: list = []
        self.recent_regulation: Optional[FreshData] = None

    def get_sheet(self):
        constant = get_constant('application')
        replies = sheet_read(constant['sheet_id'], constant['read_range'])
        self.keys = replies.pop(0)
        return replies

    def get_application_embed(self, data: list):
        literal = literals('get_application_embed')
        while len(data) < len(self.keys):
            data.append('')
        discord_id = data[DISCORD_ID]
        title = literal['title'] % discord_id
        if data[DONE] in TRUE:
            title += literal['done']
        embeds = ChainedEmbed(title=title,
                              description=literal['description'] % (data[TIMESTAMP], data[EMAIL]))
        if data[SUBACCOUNT] not in FALSE:
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
        return embeds

    def get_application_raw_embed(self, data: list):
        literal = literals('get_application_raw_embed')
        while len(data) < len(self.keys):
            data.append('')
        discord_id = data[DISCORD_ID]
        title = literal['title'] % discord_id
        if data[DONE] in TRUE:
            title += literal['done']
        embeds = ChainedEmbed(title=title, description=literal['description'])
        for i in range(len(self.keys) - 1):
            if data[i]:
                embeds.add_field(name=self.keys[i], value='```\n' + data[i] + '\n```')
        return embeds

    @modules.group(name='가입신청서', aliases=('가입', '신청서'))
    async def applications(self, ctx: Context):
        literal = literals('applications')
        message = await ctx.send(literal['start'])
        replies = self.get_sheet()
        count = len(replies)
        for reply in replies:
            if reply[DONE] in TRUE:
                count -= 1
                continue
            embeds = self.get_application_embed(reply)
            for embed in embeds.to_list():
                await ctx.author.send(embed=embed)
        await message.edit(content=literal['done'] % count if count else literal['not_found'])

    @applications.command(name='전체', aliases=('*',))
    async def applications_all(self, ctx: Context):
        literal = literals('applications_all')
        message = await ctx.send(literal['start'])
        replies = self.get_sheet()
        count = len(replies)
        for reply in replies:
            embeds = self.get_application_embed(reply)
            for embed in embeds.to_list():
                await ctx.author.send(embed=embed)
        await message.edit(content=literal['done'] % count if count else literal['not_found'])

    @applications.group(name='원본')
    async def application_raw(self, ctx: Context):
        literal = literals('application_raw')
        message = await ctx.send(literal['start'])
        replies = self.get_sheet()
        count = len(replies)
        for reply in replies:
            if reply[DONE] in TRUE:
                count -= 1
                continue
            embeds = self.get_application_raw_embed(reply)
            for embed in embeds.to_list():
                await ctx.author.send(embed=embed)
        await message.edit(content=literal['done'] % count if count else literal['not_found'])

    @application_raw.command(name='전체', aliases=('*',))
    async def application_raw_all(self, ctx: Context):
        literal = literals('application_raw_all')
        message = await ctx.send(literal['start'])
        replies = self.get_sheet()
        count = len(replies)
        for reply in replies:
            embeds = self.get_application_raw_embed(reply)
            for embed in embeds.to_list():
                await ctx.author.send(embed=embed)
        await message.edit(content=literal['done'] % count if count else literal['not_found'])

    @modules.group(name='회칙')
    async def regulation(self, ctx: Context, *, keyword: str = ''):
        literal = literals('regulation')
        message = await ctx.send(literal['start'])
        if self.recent_regulation is None \
                or (datetime.now() - self.recent_regulation.timestamp).total_seconds() > HOUR:
            paragraphs = wrap_codeblock(doc_read(get_constant('regulation')['doc_id']), split_paragraph=True)
            self.recent_regulation = FreshData(paragraphs)
        else:
            paragraphs = self.recent_regulation.data
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


def setup(client: Bot):
    client.add_cog(ShteloCog(client))

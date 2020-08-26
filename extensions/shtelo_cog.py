import asyncio
from datetime import datetime
from typing import Optional

import discord
from discord import Member, Reaction, User
from discord.ext.commands import Bot, Context, BadArgument, check

import modules
from modules import CustomCog, sheet_read, ChainedEmbed, doc_read
from modules.custom.check_decorator import guild_only, partner_only
from modules.deck import DeckHandler, DeckConverter, Deck
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
    if data[SUBACCOUNT]:
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


def wait_until_deck_handler_ready():
    async def predicate(ctx: Context) -> bool:
        deck_handler = DeckHandler(ctx.bot)
        if not deck_handler.ready:
            message = await ctx.send(literals('wait_until_deck_handler_ready.predicate')['start'])
            await deck_handler.wait_until_ready()
            await message.delete()
        return True

    predicate.name = 'wait_until_deck_handler_ready'

    return check(predicate)


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

    async def get_deck_embed(self, deck: Deck) -> ChainedEmbed:
        literal = literals('get_deck_embed')
        deck_embed = ChainedEmbed(title=literal['title'] % deck.name, description=deck.topic)
        deck_role = discord.utils.get(await self.deck_handler.guild.fetch_roles(), name=deck.name)
        deck_members = []
        async for member in self.deck_handler.guild.fetch_members():
            if deck_role in member.roles:
                deck_members.append('@' + str(member))
        deck_embed.add_field(name=literal['manager'], value='@' + str(deck.manager))
        if deck.public:
            deck_embed.add_field(name=literal['public_name'], value=literal['public_value'])
        if deck.nsfw:
            deck_embed.add_field(name=literal['nsfw_name'], value=literal['nsfw_value'])
        if deck.auto:
            deck_embed.add_field(name=literal['auto_name'], value=literal['auto_value'])
        if deck.lock:
            deck_embed.add_field(name=literal['lock_name'], value=literal['lock_value'])
        if deck.pending:
            deck_embed.add_field(name=literal['pending'] % len(deck.pending),
                                 value=' '.join([str(member) for member in deck.pending]))
        deck_embed.add_field(name=literal['members'] % len(deck_members), value='\n'.join(deck_members))
        deck_embed.set_footer(text=literal['id'] % deck.id)
        return deck_embed

    async def accept_joining(self, ctx: Context, deck: Deck, *members: Member):
        if ctx.author.id != deck.manager.id:
            raise BadArgument(f'"{ctx.author}" is not a manager of deck {deck.name}')
        literal = literals('accept_joining')

        async def accept_joining_(member: Member):
            await member.add_roles(deck.role)
            deck.pending.remove(member)

        pending = [member for member in members if member in deck.pending]
        if not pending:
            raise BadArgument('no pending found')
        tasks = [accept_joining_(member) for member in pending]
        if tasks:
            message = await ctx.send(literal['start'] % len(tasks))
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
            for coro in done:
                if (e := coro.exception()) is not None:
                    await self.deck_handler.fetch_deck(deck.default_channel)
                    raise e
            await message.edit(content=literal['done'] % (' '.join([member.mention for member in pending]), deck.name))
            await self.deck_handler.save_deck(deck)

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

    @modules.group(name='데크')
    @wait_until_deck_handler_ready()
    async def deck_(self, ctx: Context, *, deck: DeckConverter = None):
        if deck is None:
            deck = self.deck_handler.get_deck_by_channel(ctx.channel)
        if deck is None:
            await self.deck_list(ctx)
        else:
            await self.deck_info(ctx, deck=deck)

    @deck_.command(name='갱신', aliases=('동기화', '리로드', '초기화', '로드', '새로고침'))
    async def deck_refresh(self, ctx: Context):
        literal = literals('deck_refresh')
        message = await ctx.send(literal['start'])
        if not self.deck_handler.ready:
            await self.deck_handler.wait_until_ready()
        else:
            await self.deck_handler.fetch_decks()
        await message.edit(content=literal['done'])

    @deck_.command(name='정보')
    @wait_until_deck_handler_ready()
    async def deck_info(self, ctx: Context, *, deck: DeckConverter = None):
        if deck is None:
            if (deck := self.deck_handler.get_deck_by_channel(ctx.channel)) is None:
                await self.deck_list(ctx)
                return
        await ctx.send(embed=await self.get_deck_embed(deck))

    @deck_.command(name='목록', aliases=('리스트', '전체'))
    @wait_until_deck_handler_ready()
    async def deck_list(self, ctx: Context):
        literal = literals('deck_list')
        list_embeds = ChainedEmbed(title=literal['title'],
                                   description='\n'.join([deck.get_brief()
                                                          for deck in self.deck_handler.decks.values()]))
        for embed in list_embeds.to_list():
            await ctx.send(embed=embed)

    @deck_.command(name='가입', aliases=('신청', '가입신청', '들어가기'))
    @wait_until_deck_handler_ready()
    async def deck_join(self, ctx: Context, *, deck: DeckConverter):
        literal = literals('deck_join')
        if not isinstance(author := ctx.author, Member):
            author = await self.deck_handler.guild.fetch_member(author.id)
        if deck.role in author.roles:
            await ctx.send(literal['already'] % author.mention)
            return
        if deck.lock:
            await ctx.send(literal['locked'] % deck.name)
            return
        if deck.nsfw:
            message = await ctx.send(literal['warn'] % (deck.name, author.mention))
            await message.add_reaction(NSFW_EMOJI)

            def check_(reaction: Reaction, user: User):
                return reaction.message.id == message.id and user.id == author.id and reaction.emoji == NSFW_EMOJI

            try:
                await self.client.wait_for('reaction_add', check=check_, timeout=NSFW_TIMEOUT)
            except asyncio.TimeoutError:
                await asyncio.wait([message.clear_reactions(),
                                    message.add_reaction(get_emoji(':negative_squared_cross_mark:'))])
                return
        if deck.auto:
            tasks = [ctx.send(literal['done'] % deck.name), author.add_roles(deck.role)]
            await asyncio.wait(tasks)
        elif ctx.author.id in [member.id for member in deck.pending]:
            await ctx.send(literal['already_applied'])
        else:
            deck.pending.append(author)
            tasks = [ctx.send(literal['applied'] % author.mention),
                     deck.manager.send(literal['pending'] % (author.mention, deck.name, deck.id, str(author))),
                     self.deck_handler.save_deck(deck)]
            await asyncio.wait(tasks)

    @deck_.command(name='승인', aliases=('가입승인',))
    @wait_until_deck_handler_ready()
    async def deck_accept(self, ctx: Context, deck: DeckConverter, member: Member, *members: Member):
        await self.accept_joining(ctx, deck, *(member,) + members)

    @deck_.command(name='빠른승인')
    @guild_only()
    @wait_until_deck_handler_ready()
    async def deck_quick_accept(self, ctx: Context, *members: Member):
        literal = literals('deck_quick_accept')
        if (deck := self.deck_handler.get_deck_by_channel(ctx.channel)) is None:
            await ctx.send(literal['failed'])
            return
        if not members:
            members = deck.pending
        await self.accept_joining(ctx, deck, *members)

    @deck_.command(name='거절', aliases=('거부', '기각'))
    @wait_until_deck_handler_ready()
    async def deck_rejected(self, ctx: Context, deck: DeckConverter, member: Member, *members: Member):
        if ctx.author.id != deck.manager.id:
            raise BadArgument(f'"{ctx.author}" is not a manager of deck {deck.name}')
        literal = literals('deck_rejected')
        members = (member,) + members
        pending = [member for member in members if member in deck.pending]
        if not pending:
            raise BadArgument('no pending found')
        for member in pending:
            deck.pending.remove(member)
        await ctx.send(literal['done'] % (' '.join([member.mention for member in pending]), deck.name))
        await self.deck_handler.save_deck(deck)

    @deck_.command(name='탈퇴', aliases=('나가기',))
    @wait_until_deck_handler_ready()
    async def deck_leave(self, ctx: Context, *, deck: DeckConverter = None):
        literal = literals('deck_leave')
        if deck is None:
            if (deck := self.deck_handler.get_deck_by_channel(ctx.channel)) is None:
                await ctx.send(literal['failed'])
                return
        if not isinstance(author := ctx.author, Member):
            author = await self.deck_handler.guild.fetch_member(author.id)
        if deck.role not in author.roles:
            if author in deck.pending:
                deck.pending.remove(author)
                await ctx.send(literal['cancelled'] % deck.name)
                await self.deck_handler.save_deck(deck)
                return
            await ctx.send(literal['already'])
            return
        if author.id == deck.manager.id:
            await ctx.send(literal['disabled'] % deck.name)
            return
        await author.remove_roles(deck.role)
        await author.send(literal['done'] % deck.name)

    # TODO: code up the commands below
    @deck_.command(name='개설', aliases=('추가',), enabled=False)
    @wait_until_deck_handler_ready()
    async def deck_start(self, ctx: Context):
        pass

    @deck_.command(name='폐쇄', aliases=('삭제',), enabled=False)
    @wait_until_deck_handler_ready()
    async def deck_end(self, ctx: Context):
        pass

    @deck_.group(name='설정', enabled=False)
    @partner_only()
    @wait_until_deck_handler_ready()
    async def deck_setting(self, ctx: Context):
        pass


def setup(client: Bot):
    client.add_cog(ShteloCog(client))

import asyncio
from typing import Coroutine, Union

import discord
from discord import Member, Reaction, User, Role, Message, VoiceChannel, TextChannel
from discord.abc import GuildChannel
from discord.ext.commands import Bot, Context, BadArgument, check, BucketType, MemberConverter

import modules
from modules import CustomCog, ChainedEmbed, shared_cooldown, DeckHandler, Deck, DeckConverter, guild_only
from utils import get_cog, literals, get_emoji, wrap_codeblock, get_constant, check_length, attach_toggle_interface, \
    EmojiInterfaceState

FAILED_EMOJI = get_emoji(':negative_squared_cross_mark:')
CONFIRM_EMOJI = get_emoji(':white_check_mark:')
NSFW_EMOJI = get_emoji(':underage:')

NSFW_TIMEOUT = 60
DECK_START_TIMEOUT = 60
DECK_END_TIMEOUT = 30

CHANNEL_DELETE_DELAY = 120

deck_cooldown = shared_cooldown(1, 60, BucketType.category)


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


def check_deck_manager(deck: Deck, user: User):
    if user.id != deck.manager.id:
        raise BadArgument(f'{user} is not a manager of deck {deck.name}')


class DeckCog(CustomCog, name=get_cog('DeckCog')['name']):
    """
    슈텔로 데크의 운영을 위한 기능을 포함합니다.
    """

    def __init__(self, client: Bot):
        super().__init__(client)
        self.client: Bot = client
        self.deck_handler: DeckHandler = DeckHandler(client)

    async def get_deck_embed(self, deck: Deck, brief: bool = True) -> ChainedEmbed:
        literal = literals('get_deck_embed')
        deck_embed = ChainedEmbed(title=literal['title'] % deck.name, description=deck.topic)
        deck_role = discord.utils.get(await self.deck_handler.guild.fetch_roles(), name=deck.name)
        deck_members = list()
        async for member in self.deck_handler.guild.fetch_members():
            if deck_role in member.roles:
                deck_members.append(str(member))
        deck_embed.set_thumbnail(url=deck.manager.avatar_url)
        deck_embed.add_field(name=literal['manager'], value=str(deck.manager))
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
        if not brief:
            if deck_members:
                deck_embed.add_field(name=literal['members'] % len(deck_members), value='\n'.join(deck_members),
                                     inline=True)
            channels = list()
            for channel in deck.category_channel.channels:
                channels.append((literal['voice'] if isinstance(channel, VoiceChannel) else '')
                                + (channel.name if channel != deck.default_channel else f'**__{channel.name}__**'))
            deck_embed.add_field(name=literal['channels'] % len(deck.category_channel.channels),
                                 value='\n'.join(channels), inline=True)
        deck_embed.set_footer(text=literal['id'] % deck.id)
        return deck_embed

    async def accept_joining(self, ctx: Context, deck: Deck, *members: Member):
        check_deck_manager(deck, ctx.author)
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
            done, yet = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
            for coro in done:
                if (e := coro.exception()) is not None:
                    await self.deck_handler.fetch_deck(deck.default_channel)
                    raise e
            await self.deck_handler.save_deck(deck)
            await message.edit(content=literal['done'] % (' '.join([str(member) for member in pending]), deck.name))

    async def edit_deck_topic(self, ctx: Context, deck: Deck, new_topic: str):
        literal = literals('edit_deck_topic')
        old_topic = wrap_codeblock(deck.topic, markdown='')[0]
        deck.topic = new_topic
        deck_embed = await self.get_deck_embed(deck)
        deck_embed.clear_fields()
        deck_embed.add_field(name=literal['before'], value=old_topic)
        await self.save_deck(ctx, deck, deck_embed)

    async def change_deck_id(self, ctx: Context, deck: Deck, new_id: str):
        literal = literals('change_deck_id')
        old_id = '`' + deck.id + '`'
        deck.id = new_id
        deck_embed = await self.get_deck_embed(deck)
        deck_embed.clear_fields()
        deck_embed.add_field(name=literal['before'], value=old_id)
        await self.save_deck(ctx, deck, deck_embed)

    async def change_deck_name(self, ctx: Context, deck: Deck, new_name: str):
        literal = literals('change_deck_name')
        old_name = wrap_codeblock(deck.name, markdown='')[0]
        deck.name = new_name
        deck_embed = await self.get_deck_embed(deck)
        deck_embed.clear_fields()
        deck_embed.add_field(name=literal['before'], value=old_name)

        async def change_deck_name_():
            await asyncio.wait([deck.category_channel.edit(name=new_name), deck.role.edit(name=new_name)])

        await self.save_deck(ctx, deck, deck_embed, change_deck_name_())

    async def save_deck(self, ctx: Context, deck: Deck, deck_embed: ChainedEmbed = None, save: Coroutine = None):
        literal = literals('save_deck')
        if deck_embed is None:
            deck_embed = await self.get_deck_embed(deck)
        if save is None:
            save = self.deck_handler.save_deck(deck)
        message = await ctx.send(literal['start'], embed=deck_embed)
        await save
        await message.edit(content=literal['done'] % deck.name)

    @CustomCog.listener()
    async def on_guild_channel_update(self, before: GuildChannel, _: GuildChannel):
        if self.deck_handler.get_deck_by_channel(before) is not None and self.deck_handler.ready:
            await self.deck_handler.fetch_decks()

    @modules.group(name='데크')
    @wait_until_deck_handler_ready()
    async def deck_(self, ctx: Context, *, deck: DeckConverter = None):
        if deck is None:
            deck = self.deck_handler.get_deck_by_channel(ctx.channel)
        if deck is None:
            await self.deck_list(ctx)
        else:
            await self.deck_info(ctx, deck=deck)

    @deck_.command(name='갱신', aliases=('동기화', '초기화', '새로고침'))
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
        message = await ctx.send(embed=await self.get_deck_embed(deck))
        await attach_toggle_interface(
            self.client, message,
            EmojiInterfaceState(get_emoji(':x:'), message.edit, embed=await self.get_deck_embed(deck)),
            EmojiInterfaceState(get_emoji(':question_mark:'), message.edit, embed=await self.get_deck_embed(deck, False)))

    @deck_.command(name='목록', aliases=('리스트', '전체'))
    @wait_until_deck_handler_ready()
    async def deck_list(self, ctx: Context):
        literal = literals('deck_list')
        list_embeds = ChainedEmbed(title=literal['title'],
                                   description='\n'.join([deck.get_brief()
                                                          for deck in sorted(self.deck_handler.decks.values(),
                                                                             key=lambda item: item.id)]))
        list_embeds.set_thumbnail(url=self.client.user.avatar_url)
        for embed in list_embeds.to_list():
            await ctx.send(embed=embed)

    @deck_.command(name='가입', aliases=('신청', '가입신청', '들어가기'))
    @wait_until_deck_handler_ready()
    async def deck_join(self, ctx: Context, *, deck: DeckConverter):
        literal = literals('deck_join')
        if not isinstance(author := ctx.author, Member):
            author = await self.deck_handler.guild.fetch_member(author.id)
        if deck.role in author.roles:
            await ctx.send(literal['already_done'])
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
                await ctx.message.add_reaction(FAILED_EMOJI)
                return
            finally:
                await message.delete()
        if deck.auto:
            tasks = [ctx.send(literal['done'] % (ctx.author.mention, deck.name)), author.add_roles(deck.role),
                     deck.manager.send(literal['done'] % (ctx.author, deck.name))]
            await asyncio.wait(tasks)
        elif ctx.author.id in [member.id for member in deck.pending]:
            await ctx.send(literal['already_applied'])
        else:
            deck.pending.append(author)
            tasks = [ctx.send(literal['applied'] % deck.name),
                     deck.manager.send(literal['pending'] % (str(author), deck.name, deck.id, str(author))),
                     self.deck_handler.save_deck(deck)]
            await asyncio.wait(tasks)

    @deck_.command(name='수락', aliases=('가입승인', '가입수락', '승인'))
    @wait_until_deck_handler_ready()
    async def deck_accept(self, ctx: Context, deck: DeckConverter, member: Member, *members: Member):
        await self.accept_joining(ctx, deck, *(member,) + members)

    @deck_cooldown
    @deck_.command(name='간편수락', aliases=('간편승인',))
    @guild_only()
    @wait_until_deck_handler_ready()
    async def deck_quick_accept(self, ctx: Context, *members: Member):
        literal = literals('deck_quick_accept')
        if (deck := self.deck_handler.get_deck_by_channel(ctx.channel)) is None:
            await ctx.send(literal['failed'])
            ctx.command.reset_cooldown(ctx)
            return
        if not members:
            members = deck.pending
        await self.accept_joining(ctx, deck, *members)

    @deck_.command(name='거절', aliases=('거부', '기각'))
    @wait_until_deck_handler_ready()
    async def deck_rejected(self, ctx: Context, deck: DeckConverter, member: Member, *members: Member):
        check_deck_manager(deck, ctx.author)
        literal = literals('deck_rejected')
        members = (member,) + members
        pending = [member for member in members if member in deck.pending]
        if not pending:
            raise BadArgument('no pending found')
        for member in pending:
            deck.pending.remove(member)
        await ctx.send(literal['done'] % (' '.join([str(member) for member in pending]), deck.name))
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

    @deck_cooldown
    @deck_.group(name='주제', aliases=('설명',))
    @wait_until_deck_handler_ready()
    async def deck_topic(self, ctx: Context, *, new_topic: str = ''):
        if not new_topic:
            await self.deck_info(ctx)
            ctx.command.reset_cooldown(ctx)
            return
        deck = await DeckConverter().convert(ctx, str(ctx.channel.id))
        check_deck_manager(deck, ctx.author)
        check_length(new_topic, Deck.TOPIC_MAX_LENGTH)
        await self.edit_deck_topic(ctx, deck, new_topic)

    @deck_cooldown
    @deck_topic.command(name='삭제', aliases=('제거',))
    @wait_until_deck_handler_ready()
    async def deck_topic_remove(self, ctx: Context):
        deck = await DeckConverter().convert(ctx, str(ctx.channel.id))
        check_deck_manager(deck, ctx.author)
        await self.edit_deck_topic(ctx, deck, '')

    @deck_cooldown
    @deck_.command(name='아이디', aliases=('id',))
    @wait_until_deck_handler_ready()
    async def deck_id(self, ctx: Context, new_id: str = ''):
        if not new_id:
            await self.deck_info(ctx)
            ctx.command.reset_cooldown(ctx)
            return
        deck = await DeckConverter().convert(ctx, str(ctx.channel.id))
        check_deck_manager(deck, ctx.author)
        literal = literals('deck_id')
        if (deck_with_same_id := self.deck_handler.get_deck_by_id(new_id)) is not None:
            await ctx.send(literal['already'] % deck_with_same_id.name)
            ctx.command.reset_cooldown(ctx)
            return
        if self.deck_handler.is_valid_id(new_id):
            await self.change_deck_id(ctx, deck, new_id)
        else:
            await ctx.send(literal['failed'] % new_id)
            ctx.command.reset_cooldown(ctx)

    @deck_cooldown
    @deck_.command(name='이름')
    @wait_until_deck_handler_ready()
    async def deck_name(self, ctx: Context, *, new_name: str = ''):
        if not new_name:
            await self.deck_info(ctx)
            ctx.command.reset_cooldown(ctx)
            return
        deck = await DeckConverter().convert(ctx, str(ctx.channel.id))
        check_deck_manager(deck, ctx.author)
        check_length(new_name, Deck.NAME_MAX_LENGTH)
        literal = literals('deck_name')
        if (deck_with_same_name := self.deck_handler.get_deck_by_name(new_name)) is not None:
            await ctx.send(literal['already'] % deck_with_same_name.name)
            ctx.command.reset_cooldown(ctx)
            return
        await self.change_deck_name(ctx, deck, new_name)

    @deck_.command(name='개설', aliases=('추가',))
    @wait_until_deck_handler_ready()
    async def deck_start(self, ctx: Context, *, description: str):
        literal = literals('deck_start')
        partner_role: Role = discord.utils.get(await self.deck_handler.guild.fetch_roles(),
                                               id=get_constant('partner_role'))
        partner_channel = await self.client.fetch_channel(get_constant('partner_channel'))
        if not isinstance(author := ctx.author, Member):
            author = await self.deck_handler.guild.fetch_member(ctx.author.id)
        if partner_role in author.roles:
            await ctx.send(literal['manager'])

            def is_reply(message_: Message):
                return message_.author.id == author.id

            while True:
                try:
                    message = await self.client.wait_for('message', timeout=DECK_START_TIMEOUT, check=is_reply)
                except asyncio.TimeoutError:
                    await asyncio.wait([ctx.message.add_reaction(FAILED_EMOJI),
                                        ctx.message.delete()])
                    return
                try:
                    manager = await MemberConverter().convert(ctx, message.content)
                except BadArgument:
                    await ctx.send(literal['manager_failed'])
                    continue
                break
            message = await ctx.send(literal['start'])
            deck = await self.deck_handler.add_deck(description, manager)
            deck_embed = await self.get_deck_embed(deck)
            tasks = [message.edit(content=(done_str := literal['done'] % description), embed=deck_embed)]
            if message.channel != partner_channel:
                tasks.append(partner_channel.send(done_str, embed=deck_embed))
            tasks.extend([manager.send(done_str, embed=deck_embed),
                          deck.default_channel.send(literal['greeting'] % (manager.mention, deck.name))])
            await asyncio.wait(tasks)
        else:
            check_length(description, Deck.TOPIC_MAX_LENGTH)
            await asyncio.wait([partner_channel.send(literal['pending'] % (author.mention, description)),
                                ctx.send(literal['applied'] % description)])

    @deck_.command(name='삭제', aliases=('폐쇄', '종료'))
    @guild_only()
    @wait_until_deck_handler_ready()
    async def deck_end(self, ctx: Context, *, deck: DeckConverter = None):
        literal = literals('deck_end')
        partner_role: Role = discord.utils.get(await self.deck_handler.guild.fetch_roles(),
                                               id=get_constant('partner_role'))
        partner_channel = await self.client.fetch_channel(get_constant('partner_channel'))
        if deck is None:
            deck = await DeckConverter().convert(ctx, str(ctx.channel.id))
        if not isinstance(author := ctx.author, Member):
            author = await self.deck_handler.guild.fetch_member(ctx.author.id)
        if partner_role in author.roles:
            message = await ctx.send(literal['confirm'] % deck.name)
            await message.add_reaction(CONFIRM_EMOJI)

            def is_reaction(reaction_: Reaction, user_: User):
                return user_.id == author.id and reaction_.message.id == message.id and reaction_.emoji == CONFIRM_EMOJI

            try:
                await self.client.wait_for('reaction_add', check=is_reaction, timeout=DECK_END_TIMEOUT)
            except asyncio.TimeoutError:
                await ctx.message.add_reaction(FAILED_EMOJI)
                return
            finally:
                await message.delete()

            message = await ctx.send(literal['start'] % deck.name)
            deck_embed = await self.get_deck_embed(deck)
            await self.deck_handler.remove_deck(deck)
            await asyncio.wait([
                message.delete(), author.send(done_str := literal['done'] % deck.name, embed=deck_embed),
                deck.manager.send(done_str, embed=deck_embed),
                partner_channel.send(done_str, embed=deck_embed)])
        else:
            await asyncio.wait([partner_channel.send(literal['pending'].format(deck.name)),
                                ctx.send(literal['applied'] % deck.name)])

    @modules.group(name='채널')
    @guild_only()
    @wait_until_deck_handler_ready()
    async def channel(self, ctx: Context, *, deck: DeckConverter = None):
        await self.deck_info(ctx, deck)

    @channel.group(name='생성', aliases=('추가', '개설'))
    @guild_only()
    @wait_until_deck_handler_ready()
    async def channel_create(self, ctx: Context, *, name: str):
        await self.channel_create_text(ctx, name=name)

    @channel_create.command(name='텍스트', aliases=('기본', '일반'))
    @guild_only()
    @wait_until_deck_handler_ready()
    async def channel_create_text(self, ctx: Context, *, name: str):
        literal = literals('channel_create_text')
        deck: Deck = await DeckConverter().convert(ctx, str(ctx.channel.id))
        check_deck_manager(deck, ctx.author)
        channel = await deck.category_channel.create_text_channel(name)
        await ctx.send(literal['done'] % channel.mention)

    @channel_create.command(name='음성', aliases=('보이스', '통화'))
    @guild_only()
    @wait_until_deck_handler_ready()
    async def channel_create_voice(self, ctx: Context, *, name: str):
        literal = literals('channel_create_voice')
        deck: Deck = await DeckConverter().convert(ctx, str(ctx.channel.id))
        check_deck_manager(deck, ctx.author)
        channel = await deck.category_channel.create_voice_channel(name)
        await ctx.send(literal['done'] % channel.mention)

    @channel.group(name='삭제', aliases=('제거', '폐쇄'))
    @guild_only()
    @wait_until_deck_handler_ready()
    async def channel_delete(self, ctx: Context, *, channel: Union[TextChannel, VoiceChannel] = None):
        literal = literals('channel_delete')
        if channel is None:
            channel = ctx.channel
        deck: Deck = await DeckConverter().convert(ctx, str(channel.id))
        if channel == deck.default_channel:
            await ctx.send(literal['failed'])
            raise BadArgument('default channel of deck is not removable')
        check_deck_manager(deck, ctx.author)
        await ctx.send(literal['done'] % channel.name)
        await self.deck_handler.remove_channel(channel, deck)


def setup(client: Bot):
    client.add_cog(DeckCog(client))

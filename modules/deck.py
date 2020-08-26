from __future__ import annotations

import asyncio
from re import match, findall, sub

import discord
from discord import Guild, Client, TextChannel, CategoryChannel, VoiceChannel, Member, Role
from discord.abc import GuildChannel
from discord.ext.commands import Converter, Context, TextChannelConverter, BadArgument, \
    VoiceChannelConverter, CategoryChannelConverter, CommandError

from utils import singleton


def mention_to_id(mention: str) -> int:
    return int(sub('[<>@!#]', '', mention))


class Deck:
    PUBLIC = ':white_check_mark:'
    NSFW = ':underage:'
    AUTO = ':robot:'
    LOCK = ':lock:'
    MANAGER = '매니저'
    PENDING = '보류된 가입'

    def __init__(self, **kwargs):
        self.public: bool = kwargs.get('public')
        self.nsfw: bool = kwargs.get('nsfw')
        self.auto: bool = kwargs.get('auto')
        self.lock: bool = kwargs.get('lock')
        self.id: str = kwargs.get('id')
        self.manager: Member = kwargs.get('manager')
        self.pending: list = kwargs.get('pending')
        self.name: str = kwargs.get('name')
        self.topic: str = kwargs.get('topic')
        self.category_channel: CategoryChannel = kwargs.get('category_channel')
        self.default_channel: TextChannel = kwargs.get('default_channel')
        self.role: Role = kwargs.get('role')

    def __repr__(self):
        return f'<Deck public={self.public} nswf={self.nsfw} auto={self.auto} id={self.id} manager={self.manager} ' \
               f'pending={self.pending} name={self.name} topic={self.topic} chategory_channel={self.category_channel}' \
               f' default_channel={self.default_channel} role={self.role}>'

    def to_channel_topic(self):
        deck_str = '​'
        setting = []
        if self.public:
            setting.append(self.PUBLIC)
        if self.nsfw:
            setting.append(self.NSFW)
        if self.auto:
            setting.append(self.AUTO)
        if self.lock:
            setting.append(self.LOCK)
        deck_str += (' '.join(setting) + '\n' if setting else '')
        deck_str += 'id: ' + self.id
        deck_str += '\n' + self.MANAGER + ': ' + self.manager.mention
        deck_str += ('\n' + self.PENDING + ': ' + '\n'.join([member.mention for member in self.pending])
                     if self.pending else '')
        deck_str += '\n\n' + self.topic
        return deck_str

    def get_brief(self):
        return '' \
               + '***`' + self.id + '`*** ' \
               + '**__' + self.name + '__** ' \
               + '@' + str(self.manager) \
               + (' ' + self.PUBLIC if self.public else '') \
               + (' ' + self.NSFW if self.nsfw else '') \
               + (' ' + self.AUTO if self.auto else '') \
               + (' ' + self.LOCK if self.lock else '')


@singleton
class DeckHandler:
    SHTELO_ID = 650533223520010261

    PUBLIC_REGEX = '(:white_check_mark:)'
    NSFW_REGEX = '(:underage:)'
    AUTO_REGEX = '(:robot:)'
    LOCK_REGEX = '(:lock:)'
    SETTING_REGEX = '({0}|{1}|{2}|{3})'.format(PUBLIC_REGEX, NSFW_REGEX, AUTO_REGEX, LOCK_REGEX)

    ID_REGEX = '(id: [0-9a-zA-Z]{4,})'
    MENTION_REGEX = '(<@!?\\d+>)'
    MANAGER_REGEX = '(\\n매니저: {0})'.format(MENTION_REGEX)
    PENDING_REGEX = '(\\n보류된 가입:( {0})+)'.format(MENTION_REGEX)
    TOPIC_REGEX = '(\\n\\n(.|\\n)+$)'
    FULL_REGEX = '^​({0}( {0})*\\n)?{1}{2}({3})?({4}|$)' \
        .format(SETTING_REGEX, ID_REGEX, MANAGER_REGEX, PENDING_REGEX, TOPIC_REGEX)

    def __init__(self, client: Client):
        self.client: Client = client
        self.guild: Guild = None
        self.decks: dict = None
        self.ready: bool = False
        client.loop.create_task(self.__fetch_all__())

    async def __fetch_all__(self):
        await self.client.wait_until_ready()
        await self.__fetch_guild__()
        await self.__fetch_decks__()
        self.ready = True

    async def wait_until_ready(self):
        while not self.ready:
            await asyncio.sleep(0.1)

    async def __fetch_guild__(self):
        self.guild = await self.client.fetch_guild(self.SHTELO_ID)

    async def fetch_decks(self):
        self.ready = False
        await self.__fetch_decks__()
        self.ready = True

    async def __fetch_decks__(self):
        self.decks = {}  # TODO change all '{}' and '[]' to 'dict()' and 'list()'!
        tasks = []
        for channel in await self.guild.fetch_channels():
            if isinstance(channel, TextChannel) \
                    and channel.category_id is not None \
                    and channel.topic is not None \
                    and match(self.FULL_REGEX, channel.topic) is not None:
                tasks.append(self.__fetch_deck__(channel))
        if tasks:
            await asyncio.wait(tasks)

    async def fetch_deck(self, default_channel: TextChannel):
        self.ready = False
        await self.__fetch_deck__(default_channel)
        self.ready = True

    async def __fetch_deck__(self, default_channel: TextChannel):
        raw = default_channel.topic[1:]
        category_channel = await self.client.fetch_channel(default_channel.category_id)
        deck_name = category_channel.name
        deck_role = discord.utils.get(await self.guild.fetch_roles(), name=deck_name)
        deck_public = Deck.PUBLIC in (firstline := default_channel.topic.split('\n', 1)[0])
        deck_nsfw = Deck.NSFW in firstline
        deck_auto = Deck.AUTO in firstline
        deck_lock = Deck.LOCK in firstline
        if any((deck_public, deck_nsfw, deck_auto, deck_lock)):
            raw = '\n'.join(raw.split('\n')[1:])
        deck_id = findall('^' + self.ID_REGEX, raw)[0]
        raw = raw[len(deck_id):]
        deck_id = deck_id[4:]
        deck_manager = findall('^' + self.MANAGER_REGEX, raw)[0][0]
        raw = raw[len(deck_manager):]
        deck_manager = await self.guild.fetch_member(mention_to_id(deck_manager.split(' ', 1)[1]))
        if deck_pending := findall('^' + self.PENDING_REGEX, raw):
            raw = raw[len(deck_pending[0][0]):]
            deck_pending = [await self.guild.fetch_member(mention_to_id(mention))
                            for mention in deck_pending[0][0].split()[2:]]
        if deck_topic := findall('^' + self.TOPIC_REGEX, raw):
            deck_topic = deck_topic[0][0][2:]
        self.decks[category_channel.id] = Deck(public=deck_public,
                                               nsfw=deck_nsfw,
                                               auto=deck_auto,
                                               lock=deck_lock,
                                               id=deck_id,
                                               manager=deck_manager,
                                               pending=deck_pending,
                                               name=deck_name,
                                               topic=deck_topic,
                                               category_channel=category_channel,
                                               default_channel=default_channel,
                                               role=deck_role)

    @staticmethod
    async def save_deck(deck: Deck):
        await deck.default_channel.edit(topic=deck.to_channel_topic())

    def get_deck_by_channel(self, channel: GuildChannel):
        if isinstance(channel, TextChannel) or isinstance(channel, VoiceChannel):
            return self.decks.get(channel.category_id)
        if isinstance(channel, CategoryChannel):
            return self.decks.get(channel.id)

    def get_deck_by_id(self, id_: str):
        deck = [deck for deck in self.decks.values() if deck.id == id_]
        if deck:
            return deck[0]

    def get_deck_by_name(self, name: str):
        deck = [deck for deck in self.decks.values() if deck.name == name]
        if deck:
            return deck[0]

    def find_decks_by_topic(self, keyword: str):
        decks = [deck for deck in self.decks.values() if keyword in deck.topic]
        return decks


class DeckConverter(Converter):
    """
    Converts to a corresponding instance of Deck.

    The lookup strategy is as follows (in order):

    1. Lookup by ID.
    2. Lookup by name.
    3. Lookup by TextChannel via TextChannelConverter.
    4. Lookup by VoiceChannel via VoiceChannelConverter.
    5. Lookup by CategoryChannel via CategoryChannelConverter.
    """

    async def convert(self, ctx: Context, argument):
        if isinstance(argument, Deck):
            return argument
        deck_handler = DeckHandler(ctx.bot)
        if not deck_handler.ready:
            raise CommandError('deck handler is not ready')
        deck = deck_handler.get_deck_by_id(argument)
        if deck is not None:
            return deck
        deck = deck_handler.get_deck_by_name(argument)
        if deck is not None:
            return deck

        async def convert_with(converter: Converter):
            try:
                return await converter.convert(ctx, argument)
            except BadArgument:
                pass

        channel = await convert_with(TextChannelConverter())
        if channel is None:
            channel = await convert_with(VoiceChannelConverter())
        if channel is None:
            channel = await convert_with(CategoryChannelConverter())
        if channel is not None:
            deck = deck_handler.get_deck_by_channel(channel)
        if deck is not None:
            return deck
        raise BadArgument(message=f'cannot convert argument "{argument}" to deck')

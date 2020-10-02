from __future__ import annotations

import asyncio
from random import choice
from re import match, sub
from typing import Optional, Union

import discord
from discord import Guild, Client, TextChannel, CategoryChannel, VoiceChannel, Member, Role, PermissionOverwrite
from discord.abc import GuildChannel
from discord.ext.commands import Converter, Context, TextChannelConverter, BadArgument, \
    VoiceChannelConverter, CategoryChannelConverter, CommandError

from utils import singleton, get_constant


def mention_to_id(mention: str) -> int:
    return int(sub('[<>@!#]', '', mention))


class Deck:
    PUBLIC_EMOJI = ':white_check_mark:'
    NSFW_EMOJI = ':underage:'
    AUTO_EMOJI = ':robot:'
    LOCK_EMOJI = ':lock:'
    PENDING_EMOJI = ':raised_hand:'

    MANAGER = '매니저'
    PENDING = '가입신청자'

    VALID_ID = '0123456789_acdefghijkmnprstvwxyzACEFGHJKLMNPRTVWXY'

    TOPIC_MAX_LENGTH = 512
    NAME_MAX_LENGTH = 64
    ID_LENGTH = 4

    def __init__(self, **kwargs):
        kwargs.setdefault('settings', list())
        kwargs.setdefault('pending', list())
        kwargs.setdefault('topic', '')
        self.public: bool = self.PUBLIC_EMOJI in (settings := kwargs.get('settings'))
        self.nsfw: bool = self.NSFW_EMOJI in settings
        self.auto: bool = self.AUTO_EMOJI in settings
        self.lock: bool = self.LOCK_EMOJI in settings
        self.id: str = kwargs.get('id')
        self.manager: Member = kwargs.get('manager')
        self.pending: list = kwargs.get('pending')
        self.name: str = kwargs.get('name')
        self.topic: str = kwargs.get('topic')[:self.TOPIC_MAX_LENGTH]
        self.category_channel: CategoryChannel = kwargs.get('category_channel')
        self.default_channel: TextChannel = kwargs.get('default_channel')
        self.role: Role = kwargs.get('role')

    def __repr__(self):
        return f'<Deck public={self.public} nswf={self.nsfw} auto={self.auto} lock={self.lock} id={self.id} ' \
               f'manager={self.manager} pending={self.pending} name={self.name} topic={self.topic} ' \
               f'category_channel={self.category_channel} default_channel={self.default_channel} role={self.role}>'

    def to_channel_topic(self):
        deck_str = '*id: ' + self.id
        setting = list()
        if self.public:
            setting.append(self.PUBLIC_EMOJI)
        if self.nsfw:
            setting.append(self.NSFW_EMOJI)
        if self.auto:
            setting.append(self.AUTO_EMOJI)
        if self.lock:
            setting.append(self.LOCK_EMOJI)
        deck_str += ('\n' + ' '.join(setting) if setting else '')
        deck_str += '\n' + self.MANAGER + ': ' + self.manager.mention
        deck_str += ('\n' + self.PENDING + ': ' + ' '.join([member.mention for member in self.pending])
                     if self.pending else '')
        deck_str += '\n\n' + self.topic[:self.TOPIC_MAX_LENGTH]
        return deck_str

    def get_brief(self):
        return '' \
               + '***`' + self.id + '`*** ' \
               + '**__' + self.name + '__** ' \
               + '@' + str(self.manager) \
               + (' ' + self.PUBLIC_EMOJI if self.public else '') \
               + (' ' + self.NSFW_EMOJI if self.nsfw else '') \
               + (' ' + self.AUTO_EMOJI if self.auto else '') \
               + (' ' + self.LOCK_EMOJI if self.lock else '') \
               + (' ' + self.PENDING_EMOJI if self.pending else '')


@singleton
class DeckHandler:
    RECYCLE_BIN_CATEGORY = 757466502202130512
    MANAGER_ROLE = 650534578880118820
    SHTELO_GUILD = 650533223520010261

    MENTION_REGEX = '<@!?\\d+>'
    ID_REGEX = '\\*id: [a-zA-Z0-9]{4,}'
    SETTING_REGEX = '({0}|{1}|{2}|{3})( ({0}|{1}|{2}|{3}))*'\
        .format(Deck.PUBLIC_EMOJI, Deck.NSFW_EMOJI, Deck.AUTO_EMOJI, Deck.LOCK_EMOJI)
    MANAGER_REGEX = '매니저: {0}'.format(MENTION_REGEX)
    PENDING_REGEX = '가입신청자:( {0})+'.format(MENTION_REGEX)
    TOPIC_REGEX = '(.|\\n)+'
    ENTIRE_REGEX = '^{0}(\\n{1})?\\n{2}(\\n{3})?(\\n{4})?$' \
        .format(ID_REGEX, SETTING_REGEX, MANAGER_REGEX, PENDING_REGEX, TOPIC_REGEX)

    VALID_ID_REGEX = '^[0123456789_acdefghijkmnprstvwxyzACEFGHJKLMNPRTVWXY]{4}$'

    def __init__(self, client: Client):
        self.client: Client = client
        self.guild: Optional[Guild] = None
        self.manager_role: Optional[Role] = None
        self.decks: Optional[dict] = None
        self.ready: bool = False
        self.recycle_bin: Optional[CategoryChannel] = None
        client.loop.create_task(self._fetch_all())

    async def _fetch_all(self):
        await self.client.wait_until_ready()
        await self._fetch_decks()
        self.guild = await self.client.fetch_guild(self.SHTELO_GUILD)
        self.recycle_bin = await self.client.fetch_channel(self.RECYCLE_BIN_CATEGORY)
        self.manager_role = discord.utils.get(await self.guild.fetch_roles(), id=self.MANAGER_ROLE)
        self.ready = True

    async def wait_until_ready(self):
        while not self.ready:
            await asyncio.sleep(0.1)

    async def fetch_decks(self):
        self.ready = False
        await self._fetch_decks()
        self.ready = True

    async def _fetch_decks(self):
        self.decks = dict()
        tasks = list()
        for channel in await self.guild.fetch_channels():
            if isinstance(channel, TextChannel) \
                    and channel.category_id is not None \
                    and channel.category_id != self.RECYCLE_BIN_CATEGORY \
                    and channel.topic is not None \
                    and match(self.ENTIRE_REGEX, channel.topic) is not None:
                tasks.append(self._fetch_deck(channel))
        if tasks:
            await asyncio.wait(tasks)

    async def fetch_deck(self, default_channel: TextChannel):
        self.ready = False
        await self._fetch_deck(default_channel)
        self.ready = True

    async def _fetch_deck(self, default_channel: TextChannel):
        if (category_id := default_channel.category_id) in self.decks:
            del self.decks[category_id]
        category_channel = await self.client.fetch_channel(category_id)
        deck_name = category_channel.name
        deck_role = discord.utils.get(await self.guild.fetch_roles(), name=deck_name)
        raw = default_channel.topic
        deck_id = match('^' + self.ID_REGEX, raw).group()[5:]
        raw = raw.split('\n', 1)[-1]
        if deck_settings := match('^' + self.SETTING_REGEX, raw):
            deck_settings = deck_settings.group().split()
            raw = raw.split('\n', 1)[-1]
        else:
            deck_settings = tuple()
        deck_manager = await self.guild.fetch_member(mention_to_id(match('^' + self.MANAGER_REGEX, raw).group()[5:]))
        if '\n' in raw:
            raw = raw.split('\n', 1)[-1]
        deck_pending = list()
        if pending := match('^' + self.PENDING_REGEX, raw):

            async def append_after_fetch(member_id):
                deck_pending.append(await self.guild.fetch_member(member_id))

            await asyncio.wait([append_after_fetch(mention_to_id(member)) for member in pending.group()[8:].split()])
            if '\n' in raw:
                raw = raw.split('\n', 1)[-1]
        deck_topic = raw.split('\n', 1)[-1] if '\n' in raw else ''
        deck = Deck(settings=deck_settings, default_channel=default_channel, category_channel=category_channel,
                    pending=deck_pending, topic=deck_topic, id=deck_id, manager=deck_manager, name=deck_name,
                    role=deck_role)
        self.decks[category_id] = deck

    async def save_deck(self, deck: Deck):
        await deck.default_channel.edit(topic=deck.to_channel_topic())
        self.decks[deck.category_channel.id] = deck

    async def add_deck(self, name: str, manager: Member):
        role: object = await self.guild.create_role(name=name)
        roles = [role]
        if self.manager_role not in manager.roles:
            roles.append(self.manager_role)
        category_channel = await self.guild.create_category(
            name, overwrites={self.guild.default_role: PermissionOverwrite(read_messages=False),
                              role: PermissionOverwrite(read_messages=True)})
        default_channel = await self.guild.create_text_channel(name, category=category_channel)
        deck = Deck(id=self.generate_new_id(), manager=manager, name=name, category_channel=category_channel,
                    default_channel=default_channel, role=role)
        await asyncio.wait([self.save_deck(deck), manager.add_roles(*roles)])
        return deck

    async def remove_deck(self, deck: Deck):
        tasks = [self.remove_channel(channel, deck) for channel in deck.category_channel.channels]
        tasks.extend([deck.role.delete()])
        del self.decks[deck.category_channel.id]
        remove_manager_role = True
        for d in self.decks.values():
            if deck.manager == d.manager:
                remove_manager_role = False
                break
        if remove_manager_role:
            tasks.append(deck.manager.remove_roles(self.manager_role))
        await asyncio.wait(tasks)
        await deck.category_channel.delete()

    async def remove_channel(self, channel: Union[TextChannel, VoiceChannel], deck: Deck = None):
        if deck is None:
            deck = self.get_deck_by_channel(channel)
        await channel.edit(name=deck.name + '__' + channel.name, category=self.recycle_bin, sync_permissions=True)

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

    def is_valid_id(self, id_: str):
        return match(self.VALID_ID_REGEX, id_) is not None

    def generate_new_id(self) -> str:
        def generate() -> str:
            string = Deck.VALID_ID
            result = ''
            for i in range(Deck.ID_LENGTH):
                result += choice(string)

            return result

        while True:
            id_ = generate()
            if self.get_deck_by_id(id_) is None:
                break

        return id_


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

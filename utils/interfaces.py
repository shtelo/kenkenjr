import asyncio
from typing import Coroutine, Iterable, Sequence, Union, Collection

from discord import Message, Reaction, User, Client
from discord.ext.commands import Bot

from utils import try_to_clear_reactions, get_emoji

DEFAULT_TIMEOUT = 60

PAGE_NEXT_EMOJI = get_emoji(':arrow_right:')
PAGE_PREV_EMOJI = get_emoji(':arrow_left:')


class InterfaceState:
    def __init__(self, callback, *args, **kwargs):
        self.callback = callback
        self.args = args
        self.kwargs = kwargs


class EmojiInterfaceState(InterfaceState):
    def __init__(self, emoji: str, callback, *args, **kwargs):
        super().__init__(callback, *args, **kwargs)
        self.emoji = emoji


def check_reaction(bot: Client, message: Message, user: User, emojis: Sequence):
    def check(reaction_: Reaction, user_: User):
        return user_ != bot.user and reaction_.message.id == message.id and (user is None or user_ == user) \
               and reaction_.emoji in emojis
    return check


async def update_state(message: Message, state: InterfaceState):
    await asyncio.wait([try_to_clear_reactions(message), state.callback(*state.args, **state.kwargs)])


async def attach_toggle_interface(bot: Bot, message: Message, primary_state: EmojiInterfaceState,
                                  secondary_state: EmojiInterfaceState, user: User = None, timeout=DEFAULT_TIMEOUT):
    await message.add_reaction(secondary_state.emoji)
    while True:
        try:
            reaction, _ = await bot.wait_for(
                'reaction_add', timeout=timeout,
                check=check_reaction(bot, message, user, (primary_state.emoji, secondary_state.emoji)))
        except asyncio.TimeoutError:
            await try_to_clear_reactions(message)   # todo remove specific emojis instead of clear every emojis
            break
        else:
            if reaction.emoji == primary_state.emoji:
                await update_state(message, primary_state)
                await message.add_reaction(secondary_state.emoji)
            else:
                await update_state(message, secondary_state)
                await message.add_reaction(primary_state.emoji)


async def attach_page_interface(bot: Bot, message: Message, states: Collection, user: User = None,
                                timeout=DEFAULT_TIMEOUT):
    await message.add_reaction(PAGE_PREV_EMOJI)
    await message.add_reaction(PAGE_NEXT_EMOJI)
    page = 0
    pages = len(states)
    if pages > 1:
        while True:
            try:
                reaction, _ = await bot.wait_for(
                    'reaction_add', timeout=timeout,
                    check=check_reaction(bot, message, user, (PAGE_NEXT_EMOJI, PAGE_PREV_EMOJI)))
            except asyncio.TimeoutError:
                await try_to_clear_reactions(message)
                break
            else:
                if reaction.emoji == PAGE_PREV_EMOJI:
                    page = (page - 1) % pages
                else:
                    page = (page + 1) % pages
                await update_state(message, states[page])
                await message.add_reaction(PAGE_PREV_EMOJI)
                await message.add_reaction(PAGE_NEXT_EMOJI)




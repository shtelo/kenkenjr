import asyncio
from typing import Collection

from discord import Message, Reaction, User, Client
from discord.ext.commands import Bot

from utils import try_to_clear_reactions, get_emoji

DEFAULT_TIMEOUT = 60

TOGGLE_EXPAND_EMOJI = get_emoji(':question_mark:')
TOGGLE_COLLAPSE_EMOJI = get_emoji(':x:')
TOGGLE_EMOJIS = (TOGGLE_EXPAND_EMOJI, TOGGLE_COLLAPSE_EMOJI)

PAGE_NEXT_EMOJI = get_emoji(':arrow_right:')
PAGE_PREV_EMOJI = get_emoji(':arrow_left:')
PAGE_EMOJIS = (PAGE_NEXT_EMOJI, PAGE_PREV_EMOJI)


class InterfaceState:
    def __init__(self, callback, *args, **kwargs):
        self.callback = callback
        self.args = args
        self.kwargs = kwargs


# class EmojiInterfaceState(InterfaceState):
#     def __init__(self, emoji: str, callback, *args, **kwargs):
#         super().__init__(callback, *args, **kwargs)
#         self.emoji = emoji


def check_reaction(bot: Client, message: Message, user: User, *emojis):
    def check(reaction_: Reaction, user_: User):
        return user_ != bot.user and reaction_.message.id == message.id and (user is None or user_ == user) \
               and reaction_.emoji in emojis
    return check


async def update_state(message: Message, state: InterfaceState):
    await asyncio.wait([try_to_clear_reactions(message), state.callback(*state.args, **state.kwargs)])


async def attach_toggle_interface(bot: Bot, message: Message, primary_state: InterfaceState,
                                  secondary_state: InterfaceState, *,
                                  user: User = None, timeout=DEFAULT_TIMEOUT, after=None):
    await message.add_reaction(TOGGLE_EXPAND_EMOJI)
    while True:
        try:
            reaction, _ = await bot.wait_for(
                'reaction_add', timeout=timeout,
                check=check_reaction(bot, message, user, *TOGGLE_EMOJIS))
        except asyncio.TimeoutError:
            await try_to_clear_reactions(message, TOGGLE_EMOJIS)
            break
        else:
            if reaction.emoji == TOGGLE_EXPAND_EMOJI:
                await update_state(message, primary_state)
                await message.add_reaction(TOGGLE_COLLAPSE_EMOJI)
            else:
                await update_state(message, secondary_state)
                await message.add_reaction(TOGGLE_EXPAND_EMOJI)
    if after is not None:
        await after


async def attach_page_interface(bot: Bot, message: Message, states: Collection, *,
                                user: User = None, timeout=DEFAULT_TIMEOUT, after=None):
    page = 0
    pages = len(states)
    if pages > 1:
        await message.add_reaction(PAGE_PREV_EMOJI)
        await message.add_reaction(PAGE_NEXT_EMOJI)
        while True:
            try:
                reaction, _ = await bot.wait_for(
                    'reaction_add', timeout=timeout,
                    check=check_reaction(bot, message, user, *PAGE_EMOJIS))
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
    else:
        await asyncio.sleep(timeout)
    if after is not None:
        await after

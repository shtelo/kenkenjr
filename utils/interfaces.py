import asyncio
from typing import Coroutine

from discord import Message, Reaction, User, Client

from utils import try_to_clear_reactions

DEFAULT_TIMEOUT = 60


class InterfaceState:
    def __init__(self, emoji: str, callback, *args, **kwargs):
        self.emoji = emoji
        self.callback = callback
        self.args = args
        self.kwargs = kwargs


async def attach_toggle_interface(bot: Client, message: Message,
                                  primary_state: InterfaceState, secondary_state: InterfaceState,
                                  user: User = None, timeout=DEFAULT_TIMEOUT):
    def is_reaction(reaction_: Reaction, user_: User):
        return user_ != bot.user and reaction_.message.id == message.id and (user is None or user_ == user) \
               and reaction_.emoji in (primary_state.emoji, secondary_state.emoji)

    await message.add_reaction(secondary_state.emoji)
    while True:
        try:
            reaction, _ = await bot.wait_for('reaction_add', check=is_reaction, timeout=timeout)
        except asyncio.TimeoutError:
            await try_to_clear_reactions(message)
        else:
            if reaction.emoji == primary_state.emoji:
                await primary_state.callback(*primary_state.args, **primary_state.kwargs)
                await try_to_clear_reactions(message)
                await message.add_reaction(secondary_state.emoji)
            else:
                await secondary_state.callback(*secondary_state.args, **secondary_state.kwargs)
                await try_to_clear_reactions(message)
                await message.add_reaction(primary_state.emoji)

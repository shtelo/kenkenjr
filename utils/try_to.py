import asyncio

from discord import Message


async def try_to_clear_reactions(message: Message, *emojis):
    try:
        if emojis:
            await asyncio.wait([message.clear_reaction(emoji) for emoji in emojis])
        else:
            await message.clear_reactions()
    except Exception:
        pass

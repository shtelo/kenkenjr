from discord import Message


async def try_to_clear_reactions(message: Message):
    try:
        await message.clear_reactions()
    except Exception:
        pass

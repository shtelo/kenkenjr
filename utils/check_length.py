from discord.ext.commands import BadArgument


def check_length(argument: str, limit: int):
    if len(argument) > limit:
        raise BadArgument(f'argument length is over {limit}')
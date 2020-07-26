import asyncio
from random import randint

from discord import Member
from discord.ext.commands import Bot, Context

from kenkenjr import modules
from kenkenjr.modules import CustomCog, guild_only, ChainedEmbed
from kenkenjr.utils import get_cog, literals


class GameCog(CustomCog, name=get_cog('GameCog')['name']):
    """
    심심할 때 한 번 쯤 시험삼아 써 볼만한 기능들을 포함합니다.
    """

    def __init__(self, client: Bot):
        super().__init__(client)
        self.client: Bot = client

    @modules.command(name='왕', aliases=('왕게임', 'king'))
    @guild_only()
    async def king(self, ctx: Context, player1: Member, player2: Member, player3: Member, *players: Member):
        players = list(players)
        players.extend((player1, player2, player3))
        tasks = []
        king = None
        i = 0
        count = literals('king')['count'] % (len(players) - 1)
        footer = literals('king')['footer']
        while len(players):
            player1 = players.pop(randint(0, len(players) - 1))
            if i == 0:
                king = player1
            else:
                embed = ChainedEmbed(title=literals('king')['number'] % i, description=count)
                embed.set_footer(text=footer)
                tasks.append(player1.send(embed=embed))
            i = i + 1
        embed = ChainedEmbed(title=literals('king')['king'] % king.display_name, description=count)
        embed.set_image(url=king.avatar_url)
        embed.set_footer(text=footer)
        tasks.append(ctx.send(' '.join([member.mention for member in ctx.message.mentions]), embed=embed))
        tasks.append(ctx.message.delete())
        await asyncio.wait(tasks)


def setup(client: Bot):
    client.add_cog(GameCog(client))

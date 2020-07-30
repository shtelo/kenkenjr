import asyncio
from random import randrange

from discord import Member, User
from discord.ext.commands import Bot, Context

from kenkenjr import modules
from kenkenjr.modules import CustomCog, guild_only, ChainedEmbed, Yacht, IndianPoker
from kenkenjr.modules.games.game import Game
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
        count_description = literals('king')['count'] % (len(players) - 1)
        footer = literals('king')['footer']
        while len(players):
            player1 = players.pop(randrange(0, len(players)))
            if i == 0:
                king = player1
            else:
                embed = ChainedEmbed(title=literals('king')['number'] % i, description=count_description)
                embed.set_footer(text=footer)
                tasks.append(player1.send(embed=embed))
            i = i + 1
        embed = ChainedEmbed(title=literals('king')['king'] % king.display_name, description=count_description)
        embed.set_image(url=king.avatar_url)
        embed.set_footer(text=footer)
        tasks.append(ctx.send(' '.join([member.mention for member in ctx.message.mentions]), embed=embed))
        tasks.append(ctx.message.delete())
        await asyncio.wait(tasks)

    @modules.command(name='인디언포커', aliases=('인디언',))
    @guild_only()
    async def indian_poker(self, ctx: Context, player1: User, player2: User, chip: int = 15):
        literal = literals('indian_poker')
        if IndianPoker.get_game(player1) is not None:
            await ctx.send(literal['already_playing'] % player1)
        elif IndianPoker.get_game(player2) is not None:
            await ctx.send(literal['already_playing'] % player2)
        else:
            game = IndianPoker(ctx, player1, player2, chip)
            await ctx.send(literal['start'])
            await game.run()

    @modules.group(name='요트')
    async def yacht(self, ctx: Context):
        game = Yacht.get_game(ctx.author)
        if game is not None and isinstance(game, Yacht):
            await ctx.send()
        else:
            game = Yacht(ctx, ctx.author)
            await game.run()

    @yacht.command(name='도움말', aliases=('규칙',))
    async def yacht_help(self, ctx: Context):
        literal = literals('yacht_help')
        help_embed: ChainedEmbed = ChainedEmbed(title=literal['title'], description=literal['description'])
        for field in literal['fields']:
            help_embed.add_field(name=field['name'], value=field['value'])
        await ctx.send(embed=help_embed)

    @modules.group(name='게임')
    async def game(self, ctx: Context):
        pass

    @game.command(name='중단', aliases=('종료', '포기'))
    async def game_close(self, ctx: Context):
        literal = literals('game_close')
        game = Game.get_game(ctx.author)
        if game is None or not game.stop():
            await ctx.send(literal['not_found'])
        else:
            await ctx.send(literal['done'] % ' '.join([player.mention for player in game.players]))


def setup(client: Bot):
    client.add_cog(GameCog(client))

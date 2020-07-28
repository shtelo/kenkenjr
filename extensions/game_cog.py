import asyncio
from asyncio import Task
from random import randrange
from typing import Optional, List

from discord import Member, TextChannel, Message
from discord.ext.commands import Bot, Context

from kenkenjr import modules
from kenkenjr.modules import CustomCog, guild_only, ChainedEmbed
from kenkenjr.utils import get_cog, literals


class Game:
    _instances: list = []

    def __init__(self, *players: Member):
        Game._instances.append(self)
        self.players: List[Member] = list(players)

    def close(self) -> bool:
        if self in Game._instances:
            Game._instances.remove(self)
            return True
        return False

    @staticmethod
    def get_game(player: Member):
        for game in Game._instances:
            if player in game.players:
                return game
        return None


class IndianPoker(Game):
    CALL = ('콜', 'call')
    ALL_IN = ('올인', '올 인', 'all in', 'allin')
    RAISE = ('레이즈', 'raise')
    FOLD = ('폴드', 'fold')

    class Indian:
        def __init__(self, member: Member):
            self.member = member
            self.chip = 10
            self.betting = 0
            self.card = 0

        def bet(self, count: int) -> bool:
            if self.chip < count:
                return False
            self.chip -= count
            self.betting += count
            return True

    def __init__(self, ctx: Context, player1: Member, player2: Member):
        super().__init__(player1, player2)
        self.indian1: IndianPoker.Indian = IndianPoker.Indian(player1)
        self.indian2: IndianPoker.Indian = IndianPoker.Indian(player2)
        self.deck: list = [i for i in range(1, 11)] * 2
        self.turn: Optional[IndianPoker.Indian] = None
        self.ctx: Context = ctx
        self.client: Bot = ctx.bot
        self.task: Optional[Task] = None

    def close(self) -> bool:
        if super().close():
            if self.task is not None:
                self.task.cancel()
            return True
        return False

    @staticmethod
    def get_chip_str(chip: int):
        literal = literals('get_chip_str')
        if chip > 5:
            return literal['emoji'] + '**× ' + str(chip) + '**'
        if chip > 0:
            return literal['emoji'] * chip
        return '-'

    @staticmethod
    def get_card_embed(player: Indian):
        literal = literals('get_card_embed')
        if player.card:
            return ChainedEmbed(title=literal['card_title'] % player.member,
                                description=literal['emoji'][player.card - 1])
        return None

    def get_chip_embed(self):
        literal = literals('get_chip_embed')
        chip_embed = ChainedEmbed(title=literal['chip_title'], description=literal['chip_description'])
        chip_embed.add_field(name=literal['chip_name'] % self.indian1.member,
                             value=IndianPoker.get_chip_str(self.indian1.chip))
        chip_embed.add_field(name=literal['betting_name'] % self.indian1.member,
                             value=IndianPoker.get_chip_str(self.indian1.betting))
        chip_embed.add_field(name=literal['chip_name'] % self.indian2.member,
                             value=IndianPoker.get_chip_str(self.indian2.chip))
        chip_embed.add_field(name=literal['betting_name'] % self.indian2.member,
                             value=IndianPoker.get_chip_str(self.indian2.betting))
        return chip_embed

    def get_random_indian(self):
        return [self.indian1, self.indian2][randrange(2)]

    def pop_card(self) -> int:
        if not self.deck:
            self.deck: list = [i for i in range(1, 11)] * 2
        return self.deck.pop(randrange(len(self.deck)))

    def count_betting(self) -> int:
        return self.indian1.betting + self.indian2.betting

    def win_round(self, indian: Indian):
        indian.chip += self.count_betting()
        self.indian1.betting = 0
        self.indian2.betting = 0

    async def start(self) -> Member:
        async def start_():
            winner = None
            while winner is None:
                winner = await self.start_round()
            await self.ctx.send(literals('IndianPoker.start.start_')['winner'] % winner.member.mention)
        self.task = asyncio.create_task(start_())
        await self.task

    async def start_round(self) -> Optional[Indian]:
        literal = literals('start_round')
        await self.ctx.send(literal['start'])
        # set default betting
        if not self.count_betting():
            self.indian1.bet(1)
            self.indian2.bet(1)
        # set priority of betting
        if self.turn is self.indian1:
            self.turn = self.indian2
        elif self.turn is self.indian2:
            self.turn = self.indian1
        else:
            self.turn = self.get_random_indian()
        # pop cards
        if self.turn is self.indian1:
            self.indian2.card = self.pop_card()
            self.indian1.card = self.pop_card()
        else:
            self.indian1.card = self.pop_card()
            self.indian2.card = self.pop_card()
        tasks = [self.indian1.member.send(embed=self.get_card_embed(self.indian2)),
                 self.indian2.member.send(embed=self.get_card_embed(self.indian1))]
        await asyncio.wait(tasks)
        # betting phase
        winner = await self.start_betting()
        # open phase
        tasks = [self.ctx.send(embed=self.get_card_embed(self.indian1)),
                 self.ctx.send(embed=self.get_card_embed(self.indian2))]
        await asyncio.wait(tasks)
        if winner is None:
            winner = self.indian1 if self.indian1.card > self.indian2.card else self.indian2
        if winner is self.indian1:
            self.win_round(self.indian1)
        elif winner is self.indian2:
            self.win_round(self.indian2)
        if winner is not None:
            await self.ctx.send(literal['winner'] % winner.member.mention)
        else:
            await self.ctx.send(literal['draw'])
        if not self.indian1.chip:
            return self.indian2
        elif not self.indian2.chip:
            return self.indian1
        return None

    async def start_betting(self) -> Optional[Indian]:
        literal = literals('start_betting')
        betting_queue = [self.turn, self.indian2 if self.turn is self.indian1 else self.indian1]
        winner = None
        dealer_message: Optional[Message] = None
        first = True
        while True:
            current_indian = betting_queue[0]
            next_indian = betting_queue[1]
            betting_type = None
            betting_count = 0
            if dealer_message is not None:
                await dealer_message.delete()
            dealer_message = await self.ctx.send(literal['turn'] % current_indian.member.mention,
                                                 embed=self.get_chip_embed())

            def is_betting(message_: Message):
                return message_.author is current_indian.member and message_.channel is self.ctx.channel

            message: Message = await self.client.wait_for('message', check=is_betting)
            content = message.content.strip().lower()

            if content in IndianPoker.ALL_IN or content in IndianPoker.FOLD or content in IndianPoker.CALL:
                betting_type = content
            else:
                try:
                    betting_count = int(content)
                except ValueError:
                    if any([keyword in content for keyword in IndianPoker.RAISE]):
                        await self.ctx.send(literal['invalid_raise'], delete_after=10)
                    continue
            if betting_type is None:
                expected_betting = current_indian.betting + betting_count
                if expected_betting == next_indian.betting:
                    betting_count = next_indian.betting - current_indian.betting
                    betting_type = IndianPoker.CALL[0]
                elif expected_betting > next_indian.betting:
                    betting_type = IndianPoker.RAISE[0]
                elif current_indian.chip + current_indian.betting < next_indian.betting:
                    betting_type = IndianPoker.ALL_IN[0]
                else:
                    await self.ctx.send(literal["invalid_betting"], delete_after=10)
            if betting_type in IndianPoker.RAISE:
                if current_indian.bet(betting_count):
                    betting_queue.append(betting_queue.pop(0))
                    first = False
                else:
                    await self.ctx.send(literal['chip_not_enough'], delete_after=10)
            elif betting_type in IndianPoker.FOLD:
                if not first or current_indian.chip == 1:
                    winner = next_indian
                    break
                else:
                    await self.ctx.send(literal['invalid_fold'])
            elif betting_type in IndianPoker.ALL_IN:
                if current_indian.chip + current_indian.betting < next_indian.betting:
                    current_indian.bet(current_indian.chip)
                    break
                else:
                    await self.ctx.send(literal['invalid_all_in'], delete_after=10)
            elif betting_type in IndianPoker.CALL:
                if current_indian.bet(next_indian.betting - current_indian.betting):
                    break
                else:
                    await self.ctx.send(literal['chip_not_enough'], delete_after=10)
        await dealer_message.delete()
        await self.ctx.send(literal['done'])
        return winner


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
    async def indian_poker(self, ctx: Context, player1: Member, player2: Member):
        literal = literals('indian_poker')
        if Game.get_game(player1) is not None:
            await ctx.send(literal['already_playing'] % player1)
        elif Game.get_game(player2) is not None:
            await ctx.send(literal['already_playing'] % player2)
        else:
            game = IndianPoker(ctx, player1, player2)
            await ctx.send(literal['start'])
            await game.start()

    @modules.group(name='게임')
    async def game(self, ctx: Context):
        pass

    @game.command(name='중단', aliases=('종료', '포기'))
    async def game_close(self, ctx: Context):
        literal = literals('game_close')
        game = Game.get_game(ctx.author)
        if game is None or not game.close():
            await ctx.send(literal['not_found'])
        else:
            await ctx.send(literal['done'] % ' '.join([player.mention for player in game.players]))


def setup(client: Bot):
    client.add_cog(GameCog(client))

import asyncio
from random import randrange
from typing import Dict, List, Optional

from discord import Message, User, Reaction
from discord.ext.commands import Bot, Context

from kenkenjr.modules import ChainedEmbed
from kenkenjr.modules.games.game import Game
from kenkenjr.utils import literals, get_emoji

ONES = ('Ones', get_emoji(':one:'))
TWOS = ('Twos', get_emoji(':two:'))
THREES = ('Threes', get_emoji(':three:'))
FOURS = ('Fours', get_emoji(':four:'))
FIVES = ('Fives', get_emoji(':five:'))
SIXES = ('Sixes', get_emoji(':six:'))
FULL_HOUSE = ('Full house', get_emoji(':eject:'))
FOUR_OF_A_KIND = ('4 of a kind', get_emoji(':capital_abcd:'))
LITTLE_STRAIGHT = ('Little straight', get_emoji(':track_previous:'))
BIG_STRAIGHT = ('Big straight', get_emoji(':track_next:'))
CHOICE = ('Choice', get_emoji(':asterisk:'))
YACHT = ('Yacht', get_emoji(':cruise_ship:'))

CATEGORIES = [ONES, TWOS, THREES, FOURS, FIVES, SIXES, FULL_HOUSE, FOUR_OF_A_KIND, LITTLE_STRAIGHT, BIG_STRAIGHT,
              CHOICE, YACHT]

DICE_ID = [
    get_emoji(':regional_indicator_a:'),
    get_emoji(':regional_indicator_b:'),
    get_emoji(':regional_indicator_c:'),
    get_emoji(':regional_indicator_d:'),
    get_emoji(':regional_indicator_e:')
]
DICE_DIE = [
    get_emoji(':one:'),
    get_emoji(':two:'),
    get_emoji(':three:'),
    get_emoji(':four:'),
    get_emoji(':five:'),
    get_emoji(':six:')
]

REROLL_EMOJI = get_emoji(':arrows_counterclockwise:')
CONFIRM_EMOJI = get_emoji(':white_check_mark:')


async def add_reactions(message: Message, emojis: list):
    for e in emojis:
        await message.add_reaction(e)


class Yacht(Game):
    def __init__(self, ctx: Context, player: User):
        super().__init__(player)
        self.player: User = player
        self.ctx: Context = ctx
        self.client: Bot = ctx.bot
        self.dice: Dict[str, int] = {d: 1 for d in DICE_ID}
        self.scores: dict = {category: -1 for category in CATEGORIES}
        self.round: int = 0
        self.task: Optional = None

    @staticmethod
    def roll_dice() -> int:
        return randrange(1, 7)

    def reroll_all(self, dice_id: list = None) -> Optional[List[int]]:
        if dice_id is None:
            dice_id = DICE_ID
        failed = []
        for d in dice_id:
            if d in self.dice.keys():
                self.dice[d] = Yacht.roll_dice()
            else:
                failed.append(d)
        if failed:
            return failed

    def get_total_score(self):
        return sum([v for v in self.scores.values() if v >= 0])

    def get_score_of_category(self, category: str) -> Optional[int]:
        dice = list(self.dice.values())
        if category == ONES:
            return sum([dice for dice in dice if dice == 1])
        elif category == TWOS:
            return sum([dice for dice in dice if dice == 2])
        elif category == THREES:
            return sum([dice for dice in dice if dice == 3])
        elif category == FOURS:
            return sum([dice for dice in dice if dice == 4])
        elif category == FIVES:
            return sum([dice for dice in dice if dice == 5])
        elif category == SIXES:
            return sum([dice for dice in dice if dice == 6])
        elif category == FULL_HOUSE:
            return sum(dice) if len(set(dice)) == 2 and dice.count(dice[0]) in (2, 3) else 0
        elif category == FOUR_OF_A_KIND:
            dice_kinds = list(set(dice))
            if len(dice_kinds) != 2:
                return 0
            same = dice_kinds[0]
            if dice.count(same) != 4:
                same = dice_kinds[1]
            if dice.count(same) != 4:
                return 0
            return same * 4
        elif category == LITTLE_STRAIGHT:
            return 30 if set(dice) == {1, 2, 3, 4, 5} else 0
        elif category == BIG_STRAIGHT:
            return 30 if set(dice) == {2, 3, 4, 5, 6} else 0
        elif category == CHOICE:
            return sum(dice)
        elif category == YACHT:
            return 50 if len(set(dice)) == 1 else 0

    def get_dice_embed(self, rerolled: int = 3) -> ChainedEmbed:
        literal = literals('get_dice_embed')
        sorted_dice = sorted(self.dice.items(), key=lambda item: item[1])
        description = ' '.join([d[0] for d in sorted_dice]) + '\n' + ' '.join([DICE_DIE[d[1] - 1] for d in sorted_dice])
        dice_embed: ChainedEmbed = ChainedEmbed(
            title=literal['title'] % (self.round, literal['rerolled'][rerolled]),
            description=description)
        return dice_embed

    def get_score_embed(self) -> ChainedEmbed:
        literal = literals('get_score_embed')
        score_embed = ChainedEmbed(title=literal['title'] % self.round,
                                   description=literal['description'] % self.get_total_score())
        for i in range(len(CATEGORIES)):
            score = self.scores[CATEGORIES[i]]
            if score == -1:
                score = self.get_score_of_category(CATEGORIES[i])
                name = literal['name']
                value = literal['value']
            else:
                name = literal['done_name']
                value = literal['done_value']
            score_embed.add_field(name=name % (CATEGORIES[i][1], CATEGORIES[i][0]), inline=True,
                                  value=value % score)
        return score_embed

    async def start(self):
        for _ in range(len(self.scores)):
            self.round += 1
            await self.start_round()
        await self.player.send(literals('Yacht.start')["done"] % (self.player.mention, self.get_total_score()))

    async def start_round(self):
        literal = literals('Yacht.start_round')
        await self.player.send(literal['start'] % self.round)
        self.reroll_all()
        for i in range(2):
            dice_message: Message = await self.player.send(embed=self.get_dice_embed(i))
            selected = await self.get_dice_reaction(dice_message)
            if selected:
                self.reroll_all(selected)
            else:
                break
        await self.player.send(embed=self.get_dice_embed())
        score_embed = self.get_score_embed()
        score_message = await self.player.send(embed=score_embed)
        selected = await self.get_category_reaction(score_message)
        for category in CATEGORIES:
            if selected in category:
                self.scores[category] = self.get_score_of_category(category)
                break
        await score_message.edit(embed=self.get_score_embed())

    async def wait_for_reaction_change(self, check):
        on_reaction_add = asyncio.create_task(self.client.wait_for('reaction_add', check=check))
        on_reaction_remove = asyncio.create_task(self.client.wait_for('reaction_remove', check=check))
        pending_tasks = [on_reaction_add, on_reaction_remove]
        done_tasks, pending_tasks = await asyncio.wait(pending_tasks, return_when=asyncio.FIRST_COMPLETED)
        for pending_task in pending_tasks:
            pending_task.cancel()
        reaction_ = None
        user_ = None
        added_ = False
        for done_task in done_tasks:
            reaction_, user_ = await done_task
            added_ = done_task is on_reaction_add
        return reaction_, user_, added_

    async def get_dice_reaction(self, message: Message):

        emojis = [dice[0] for dice in sorted(self.dice.items(), key=lambda item: item[1])] \
                 + [REROLL_EMOJI, CONFIRM_EMOJI]
        asyncio.create_task(add_reactions(message, emojis))

        def is_dice_reaction(reaction_: Reaction, user_: User):
            return user_ == self.player and reaction_.message.id == message.id \
                   and (str(reaction_) in (REROLL_EMOJI, CONFIRM_EMOJI) or str(reaction_) in DICE_ID)

        selected = []
        last_emoji = ''
        while not (selected and last_emoji == REROLL_EMOJI) and not (last_emoji == CONFIRM_EMOJI):
            reaction, _, added = await self.wait_for_reaction_change(is_dice_reaction)
            last_emoji = str(reaction)
            if last_emoji in DICE_ID:
                if added:
                    selected.append(last_emoji)
                elif last_emoji in selected:
                    selected.remove(last_emoji)
        asyncio.create_task(message.delete(delay=1))
        return selected if last_emoji == REROLL_EMOJI else []

    async def get_category_reaction(self, message: Message):
        selectable_categories = [item[0][1] for item in self.scores.items() if item[1] == -1]
        asyncio.create_task(add_reactions(message, selectable_categories + [CONFIRM_EMOJI]))

        def is_category_reaction(reaction_: Reaction, user_: User):
            return user_ == self.player and reaction_.message.id == message.id \
                   and str(reaction_) in selectable_categories + [CONFIRM_EMOJI]

        selected = []
        while True:
            reaction, _, added = await self.wait_for_reaction_change(is_category_reaction)
            if str(reaction) == CONFIRM_EMOJI:
                for category in CATEGORIES:
                    if selected[-1] in category:
                        self.scores[category] = self.get_score_of_category(category)
                        break
                break
            elif added:
                selected.append(str(reaction))
            elif str(reaction) in selected:
                selected.remove(str(reaction))
        message = await self.player.fetch_message(message.id)
        return str(reaction)

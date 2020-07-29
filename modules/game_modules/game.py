from typing import List

from discord import Member


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

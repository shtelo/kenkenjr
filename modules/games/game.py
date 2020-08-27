import asyncio
from abc import ABC, abstractmethod
from asyncio import Task
from typing import List, Optional

from discord import User


class Game(ABC):
    _instances: list = list()

    def __init__(self, *players: User):
        Game._instances.append(self)
        self.players: List[User] = list(players)
        self.task: Optional[Task] = None

    async def run(self):
        self.task = asyncio.create_task(self.start())
        await self.task
        self.stop()

    @abstractmethod
    async def start(self):
        pass

    def stop(self) -> bool:
        if self in Game._instances:
            Game._instances.remove(self)
            if self.task is not None and not self.task.cancelled():
                self.task.cancel()
            return True
        return False

    @staticmethod
    def get_game(player: User):
        for game in Game._instances:
            if player in game.players:
                return game
        return None

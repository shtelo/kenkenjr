from discord.ext.commands import Cooldown, CooldownMapping


class SharedCooldown(Cooldown):
    def __init__(self, rate, per, type):
        super().__init__(rate, per, type)

    def copy(self):
        return self


class SharedCooldownMapping(CooldownMapping):
    def __init__(self, original):
        super().__init__(original)

    def copy(self):
        return self

    @property
    def cooldwon(self):
        return self._cooldown

    @classmethod
    def from_cooldown(cls, rate, per, type):
        return cls(SharedCooldown(rate, per, type))

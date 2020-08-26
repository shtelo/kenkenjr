from typing import Optional

from discord import Embed, Colour
from discord.embeds import EmptyEmbed


class ChainedEmbed(Embed):
    MAX_LEN = 6000
    MAX_FIELD = 25
    KENKEN_CYAN = Colour.from_rgb(130, 195, 195)
    SHTELO_YELLOW = Colour.from_rgb(253, 222, 89)

    def __init__(self, *, depth: int = 0, color: Colour = KENKEN_CYAN, **kwargs):
        super().__init__(color=color, **kwargs)
        self.depth: int = depth
        self.color: Colour = color
        self.next: Optional[ChainedEmbed] = None

    def add_field(self, *, name, value, inline=False):
        super().add_field(name=name, value=value, inline=inline)
        if len(self.fields) > ChainedEmbed.MAX_FIELD or len(self) > ChainedEmbed.MAX_LEN:
            self.remove_field(-1)
            if self.next is None:
                self.next = ChainedEmbed(title=self.title, color=self.color, footer=self.footer, depth=self.depth + 1)
            self.next.add_field(name=name, value=value, inline=inline)

    def set_footer(self, *, text=EmptyEmbed, icon_url=EmptyEmbed):
        if self.next is None:
            super().set_footer(text=text, icon_url=icon_url)
        else:
            self.next.set_footer(text=text, icon_url=icon_url)

    def to_list(self):
        embed_list = []
        embed = self
        while embed is not None:
            embed_list.append(embed)
            embed = embed.next
        return embed_list

from discord import Bot, SlashCommandGroup

from asyncio import AbstractEventLoop
from typing import Optional

from config import TOKEN

bot = Bot()
bot.load_extension("cogs.system")


@bot.event
async def on_ready():
    print(f"{bot.user.display_name} has connected to discord.")


def start(loop: Optional[AbstractEventLoop] = None):
    if loop is not None:
        bot.loop = loop
    bot.run(token=TOKEN)

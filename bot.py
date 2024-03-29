from discord import Bot, ApplicationContext

from asyncio import AbstractEventLoop, open_connection
from typing import Optional

from config import TOKEN

bot = Bot()
bot.load_extension("cogs.system")


@bot.event
async def on_ready():
    print(f"{bot.user.display_name} has connected to discord.")


@bot.slash_command("call")
async def call(ctx: ApplicationContext):
    try:
        _, w = await open_connection("100.0.0.110", 8888, timeout=1)
        w.close()
        await ctx.respond("Send success.")
    except:
        await ctx.respond("Send failed.")



def start(loop: Optional[AbstractEventLoop] = None):
    if loop is not None:
        bot.loop = loop
    bot.run(token=TOKEN)

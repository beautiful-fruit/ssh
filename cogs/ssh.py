from aiofiles import open as async_open
from discord import (
    ApplicationContext,
    Bot,
    Embed,
    SlashCommand,
    SlashCommandGroup
)
from orjson import dumps, loads, OPT_INDENT_2
from pydantic import BaseModel, Field

from datetime import datetime, timezone
from os.path import isfile, join
from typing import get_args, Literal

from config import DATA_DIR, TIMEZONE

from .base import GroupCog

YEARS = ["元"]
FBNC = [0, 1, 1]

class SSHData(BaseModel):
    type: Literal["WAKE_UP", "SLEEP"]
    year: str = Field(default=YEARS[-1])
    month: int
    day: int
    timestamp: int = Field(
        default_factory=lambda: int(datetime.utcnow().timestamp())
    )

def get_user_file(ctx: ApplicationContext) -> str:
    return join(DATA_DIR, f"{ctx.author.id}.json")


def get_fbnc_num(n: int) -> int:
    if n < len(FBNC):
        return FBNC[n]
    result = get_fbnc_num(n - 2) + get_fbnc_num(n - 1)
    FBNC.append(result)
    return result


def check_signed(sign_up_command: SlashCommand) -> bool:
    async def wrap(ctx: ApplicationContext) -> bool:
        if isfile(get_user_file(ctx)):
            return True
        await ctx.respond(f"請先使用{sign_up_command.mention}進行註冊。")
        return False
    return wrap


class SleepSleepHistory(GroupCog):
    group = SlashCommandGroup(
        name="ssh",
        description="Sleep Sleep History"
    )

    @group.command(
        name="sign_up",
        description="將今天註冊為起始日。"
    )
    async def sign_up(self, ctx: ApplicationContext):
        async with async_open(get_user_file(ctx), "wb") as record_file:
            await record_file.write(dumps([
                SSHData(
                    type="WAKE_UP",
                    year=YEARS[-1],
                    month=1,
                    day=1,
                ).model_dump()
            ], option=OPT_INDENT_2))
        embed = Embed(
            colour=0x86c166,
            title="註冊成功",
            description=f"今天是你的 {YEARS[-1]}年 1 月 1 日",
            timestamp=datetime.now(timezone.utc)
        )
        avatar = ctx.author.avatar or ctx.author.default_avatar
        embed.set_thumbnail(url=avatar.url)
        await ctx.respond(embed=embed)

    @group.command(
        name="ohiyo",
        description="開始新的一天。",
        checks=[check_signed(sign_up)]
    )
    async def ohiyo(
        self,
        ctx: ApplicationContext
    ):
        async with async_open(get_user_file(ctx), "rb") as record_file:
            data = loads(await record_file.read())
        data: list[SSHData] = list(map(lambda d: SSHData(**d), data))
        last_data = data[-1]

        if last_data.type == "WAKE_UP":
            delta = datetime.utcnow() - datetime.fromtimestamp(last_data.timestamp)
            total_seconds = int(delta.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60

            embed = Embed(
                colour=0xffb11b,
                title="你不是起床了嗎",
                description=f"你在 {hours} 小時 {str(minutes).zfill(2)} 分 {str(seconds).zfill(2)} 秒前就起床了。",
                timestamp=datetime.now(timezone.utc)
            )
            avatar = ctx.author.avatar or ctx.author.default_avatar
            embed.set_thumbnail(url=avatar.url)
            await ctx.respond(embed=embed)
            return
        
        new_month = last_data.month
        new_day = last_data.day + 1
        if last_data.year != last_data.year:
            new_month = 1
            new_day = 1
        elif new_day > get_fbnc_num(new_month):
            new_month += 1
            new_day = 1
        data.append(SSHData(
            type="WAKE_UP",
            year=YEARS[-1],
            month=new_month,
            day=new_day,
        ))
        async with async_open(get_user_file(ctx), "wb") as record_file:
            await record_file.write(dumps(
                data,
                default=lambda d: d.model_dump(),
                option=OPT_INDENT_2
            ))
        embed = Embed(
            colour=0x24936e,
            title="早安，馬卡巴卡",
            description=f"今天是你的 {YEARS[-1]} 年 {new_month} 月 {new_day} 日",
            timestamp=datetime.now(timezone.utc)
        )
        avatar = ctx.author.avatar or ctx.author.default_avatar
        embed.set_thumbnail(url=avatar.url)
        await ctx.respond(embed=embed)

    @group.command(
        name="oyasumi",
        description="登出舊的一天。",
        checks=[check_signed(sign_up)]
    )
    async def oyasumi(
        self,
        ctx: ApplicationContext
    ):
        async with async_open(get_user_file(ctx), "rb") as record_file:
            data = loads(await record_file.read())
        data: list[SSHData] = list(map(lambda d: SSHData(**d), data))
        last_data = data[-1]

        delta = datetime.utcnow() - datetime.fromtimestamp(last_data.timestamp)
        total_seconds = int(delta.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if last_data.type == "SLEEP":
            embed = Embed(
                colour=0xffb11b,
                title="沒想到你是那種說晚安之後去滑手機的人",
                description=f"你在 {hours} 小時 {str(minutes).zfill(2)} 分 {str(seconds).zfill(2)} 秒前就離開了。",
                timestamp=datetime.now(timezone.utc)
            )
            avatar = ctx.author.avatar or ctx.author.default_avatar
            embed.set_thumbnail(url=avatar.url)
            await ctx.respond(embed=embed)
            return
        
        data.append(SSHData(
            type="SLEEP",
            year=last_data.year,
            month=last_data.month,
            day=last_data.day,
        ))
        async with async_open(get_user_file(ctx), "wb") as record_file:
            await record_file.write(dumps(
                data,
                default=lambda d: d.model_dump(),
                option=OPT_INDENT_2
            ))
        embed = Embed(
            colour=0x24936e,
            title="晚安，馬卡巴卡",
            description=f"你結束了你的 {last_data.year}年 {last_data.month} 月 {last_data.day} 日，共 {hours} 小時 {str(minutes).zfill(2)} 分 {str(seconds).zfill(2)} 秒",
            timestamp=datetime.now(timezone.utc)
        )
        avatar = ctx.author.avatar or ctx.author.default_avatar
        embed.set_thumbnail(url=avatar.url)
        await ctx.respond(embed=embed)


def setup(bot: Bot):
    bot.add_cog(SleepSleepHistory(bot))

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
from random import choice
from typing import Literal, Union

from config import DATA_DIR

from .base import GroupCog

YEARS = ["元"]
FBNC = [0, 1, 1]
COLOR_MAP = {
    "SIGN_UP": 0xDC9FB4,  # https://nipponcolors.com/#nadeshiko
    "WAKE_UP": 0xFC9F4D,  # https://nipponcolors.com/#kanzo
    "SLEEP": 0x0C4842,   # https://nipponcolors.com/#onando
    "WARN": 0xFBE251,    # https://nipponcolors.com/#kihada
    "INFO": 0x51A8DD,    # https://nipponcolors.com/#gunjyo
}
COLOR_TYPE = Literal["SIGN_UP", "WAKE_UP", "SLEEP", "WARN", "INFO"]
RESPONSE_MESSAGE = {
    "WAKE_UP": [
        "早安，馬卡巴卡",
    ],
    "SLEEP": [
        "晚安，馬卡巴卡",
    ],
    "ALREADY_WAKE_UP": [
        "你不是起床了嗎",
    ],
    "ALREADY_SLEEP": [
        "沒想到你是那種說晚安之後去滑手機的人",
    ],
    "STATUS_WAKE_UP": [
        "你仍未離開今天"
    ],
    "STATUS_SLEEP": [
        "你正在等待明天的到來"
    ],
}


class SSHData(BaseModel):
    type: Literal["WAKE_UP", "SLEEP"]
    year: str = YEARS[-1]
    month: int = 1
    day: int = 1
    timestamp: int = Field(
        default_factory=lambda: int(datetime.utcnow().timestamp())
    )


def get_fbnc_num(n: int) -> int:
    if n < len(FBNC):
        return FBNC[n]
    result = get_fbnc_num(n - 2) + get_fbnc_num(n - 1)
    FBNC.append(result)
    return result


def get_user_file(ctx: ApplicationContext) -> str:
    return join(DATA_DIR, f"{ctx.author.id}.json")


async def read_user_data(ctx: ApplicationContext) -> list[SSHData]:
    file_path = get_user_file(ctx)
    if not isfile(file_path):
        return []
    async with async_open(file_path, "rb") as f:
        data: list[dict] = loads(await f.read())
    return list(map(lambda d: SSHData(**d), data))


async def write_user_data(ctx: ApplicationContext, data: list[SSHData]) -> None:
    file_path = get_user_file(ctx)
    async with async_open(file_path, "wb") as f:
        await f.write(dumps(
            data,
            default=lambda d: d.model_dump(),
            option=OPT_INDENT_2
        ))


def format_delta_time(delta: int) -> tuple[str, str, str]:
    return (
        str(delta // 3600).zfill(2),
        str((delta % 3600) // 60).zfill(2),
        str(delta % 60).zfill(2),
    )


def check_signed(sign_up_command: SlashCommand) -> bool:
    async def wrap(ctx: ApplicationContext) -> bool:
        if isfile(get_user_file(ctx)):
            return True
        await ctx.respond(f"請先使用{sign_up_command.mention}進行註冊。")
        return False
    return wrap


def generate_embed(
    ctx: ApplicationContext,
    color: Union[int, COLOR_TYPE],
    title: str,
    description: str = ""
) -> Embed:
    embed = Embed(
        colour=color if type(color) == int else COLOR_MAP.get(color, 0),
        title=title,
        description=description,
        timestamp=datetime.now(timezone.utc)
    )
    avatar = ctx.author.avatar or ctx.author.default_avatar
    embed.set_thumbnail(url=avatar.url)
    return embed


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
        if isfile(get_user_file(ctx)):
            await ctx.respond("你已經註冊過了。")
            return

        await write_user_data(
            ctx=ctx,
            data=[SSHData(type="WAKE_UP").model_dump()]
        )
        await ctx.respond(embed=generate_embed(
            ctx=ctx,
            color="SIGN_UP",
            title="註冊成功",
            description=f"今天是你的 {YEARS[-1]}年 1 月 1 日。",
        ))

    @group.command(
        name="ohiyo",
        description="開始新的一天。",
        checks=[check_signed(sign_up)]
    )
    async def ohiyo(
        self,
        ctx: ApplicationContext
    ):
        data = await read_user_data(ctx)
        latest = data[-1]
        time_delta = datetime.utcnow() - datetime.fromtimestamp(latest.timestamp)
        hours, minutes, seconds = format_delta_time(
            int(time_delta.total_seconds()))

        if latest.type == "WAKE_UP":
            await ctx.respond(embed=generate_embed(
                ctx=ctx,
                color="WARN",
                title=choice(RESPONSE_MESSAGE["ALREADY_WAKE_UP"]),
                description=f"你在 {hours} 小時 {minutes} 分 {seconds} 秒前就起床了。"
            ))
            return

        n_month = latest.month if latest.year == YEARS[-1] else 1
        n_day = latest.day + 1 if latest.year == YEARS[-1] else 1
        if n_day > get_fbnc_num(n_month):
            n_month += 1
            n_day = 1
        data.append(SSHData(
            type="WAKE_UP",
            month=n_month,
            day=n_day,
        ))
        await write_user_data(ctx=ctx, data=data)
        await ctx.respond(embed=generate_embed(
            ctx=ctx,
            color="WAKE_UP",
            title=choice(RESPONSE_MESSAGE["WAKE_UP"]),
            description=f"今天是你的 {YEARS[-1]} 年 {n_month} 月 {n_day} 日，你的昨天已離去 {hours} 小時 {minutes} 分 {seconds} 秒之久。"
        ))

    @group.command(
        name="oyasumi",
        description="登出舊的一天。",
        checks=[check_signed(sign_up)]
    )
    async def oyasumi(
        self,
        ctx: ApplicationContext
    ):
        data = await read_user_data(ctx)
        latest = data[-1]
        time_delta = datetime.utcnow() - datetime.fromtimestamp(latest.timestamp)
        hours, minutes, seconds = format_delta_time(
            int(time_delta.total_seconds()))

        if latest.type == "SLEEP":
            await ctx.respond(embed=generate_embed(
                ctx=ctx,
                color="WARN",
                title=choice(RESPONSE_MESSAGE["ALREADY_SLEEP"]),
                description=f"你在 {hours} 小時 {minutes} 分 {seconds} 秒前就離開了。"
            ))
            return

        data.append(SSHData(
            type="SLEEP",
            year=latest.year,
            month=latest.month,
            day=latest.day,
        ))
        await write_user_data(ctx=ctx, data=data)
        await ctx.respond(embed=generate_embed(
            ctx=ctx,
            color="SLEEP",
            title=choice(RESPONSE_MESSAGE["SLEEP"]),
            description=f"你結束了你的 {latest.year}年 {latest.month} 月 {latest.day} 日，共 {hours} 小時 {minutes} 分 {seconds} 秒。"
        ))

    @group.command(
        name="current",
        description="查看現在是哪一天。",
        checks=[check_signed(sign_up)]
    )
    async def current(
        self,
        ctx: ApplicationContext
    ):
        data = await read_user_data(ctx)
        latest = data[-1]
        time_delta = datetime.utcnow() - datetime.fromtimestamp(latest.timestamp)
        hours, minutes, seconds = format_delta_time(
            int(time_delta.total_seconds()))

        if latest.type == "WAKE_UP":
            embed = generate_embed(
                ctx=ctx,
                color="INFO",
                title=choice(RESPONSE_MESSAGE["STATUS_WAKE_UP"]),
                description=f"現在是 {latest.year}年 {latest.month} 月 {latest.day} 日 {hours} 時 {minutes} 分 {seconds} 秒。"
            )
        else:
            embed = generate_embed(
                ctx=ctx,
                color="INFO",
                title=choice(RESPONSE_MESSAGE["STATUS_SLEEP"]),
                description=f"你離開 {latest.year}年 {latest.month} 月 {latest.day} 日 已有 {hours} 時 {minutes} 分 {seconds} 秒之久。"
            )
        await ctx.respond(embed=embed)

    @group.command(
        name="cancel",
        description="取消上一筆紀錄。",
        checks=[check_signed(sign_up)]
    )
    async def cancel(
        self,
        ctx: ApplicationContext
    ):
        data = await read_user_data(ctx)
        await write_user_data(ctx=ctx, data=data[:-1])
        await ctx.respond(embed=generate_embed(
            ctx=ctx,
            color="INFO",
            title="已取消上一筆紀錄",
        ))


def setup(bot: Bot):
    bot.add_cog(SleepSleepHistory(bot))

from aiofiles import open as async_open
from discord import (
    ApplicationContext,
    Bot,
    Embed,
    File,
    Option,
    SlashCommand,
    SlashCommandGroup,
)
from orjson import dumps, loads, OPT_INDENT_2
from pydantic import BaseModel, Field

from datetime import (
    date,
    datetime,
    time,
    timedelta,
    timezone,
)
from io import BytesIO
from os.path import isfile, join
from random import choice
from typing import Literal, Optional, Union

from config import DATA_DIR

from .base import GroupCog

YEAR_DATA = {
    "元": 1704038400
}
YEARS = list(YEAR_DATA.keys())
YEARS.sort(key=lambda k: YEAR_DATA[k])
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


def rebuild(data: list[SSHData]) -> list[SSHData]:
    if len(data) == 0:
        return []
    data.sort(key=lambda d: d.timestamp)
    day = 1
    month = 1
    year_index = YEARS.index(data[0].year)
    for i in range(len(data)):
        data[i].day = day
        data[i].month = month
        data[i].year = YEARS[year_index]
        if data[i].type == "WAKE_UP":
            if year_index + 1 >= len(YEARS):
                continue
            if data[i].timestamp >= YEAR_DATA[YEARS[year_index + 1]]:
                year_index += 1
                data[i].year = YEARS[year_index]
            continue
        day += 1
        if day > get_fbnc_num(month):
            day = 1
            month += 1
    return data


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
    description: str = "",
    fields: Optional[dict[str, str]] = {},
) -> Embed:
    embed = Embed(
        colour=color if type(color) == int else COLOR_MAP.get(color, 0),
        title=title,
        description=description,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    for key, value in fields.items():
        embed.add_field(name=key, value=value, inline=False)
    return embed


async def get_utc_datetime(
    ctx: ApplicationContext,
    latest_datetime: datetime,
    time_: Optional[str] = None,
    date_: Optional[str] = None,
    timezone_: float = 8,
) -> Optional[datetime]:
    if time_ is None:
        utc_datetime = datetime.utcnow()
    else:
        try:
            time_ = time.fromisoformat(time_)
            date_ = datetime.now().date() if date_ is None else date.fromisoformat(date_)
        except:
            await ctx.respond(embed=generate_embed(
                ctx=ctx,
                color="WARN",
                title="輸入時間格式錯誤",
                description="請重新檢查時間輸入是否符合格式"
            ))
            return None
        datetime_ = datetime.combine(date_, time_)
        utc_datetime = datetime_ - timedelta(hours=timezone_)
        if utc_datetime < latest_datetime:
            await ctx.respond(embed=generate_embed(
                ctx=ctx,
                color="WARN",
                title="僅能將資料新增至尾端"
            ))
            return None
        if utc_datetime > datetime.utcnow():
            await ctx.respond(embed=generate_embed(
                ctx=ctx,
                color="WARN",
                title="不可將資料新增至未來"
            ))
            return None
    return utc_datetime


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
        checks=[check_signed(sign_up)],
    )
    async def ohiyo(
        self,
        ctx: ApplicationContext,
        time_: Option(str, name="時間", description="時間 格式為HH:MM:SS", required=False),
        date_: Option(str, name="日期", description="日期 格式為YYYY-MM-DD", required=False),
        timezone_: Option(float, name="時區", description="時區", default=8, min_value=-12, max_value=12),
    ):
        data = await read_user_data(ctx)
        latest = data[-1]
        latest_datetime = datetime.fromtimestamp(latest.timestamp)
        utc_datetime = await get_utc_datetime(
            ctx=ctx,
            latest_datetime=latest_datetime,
            time_=time_,
            date_=date_,
            timezone_=timezone_
        )
        if utc_datetime is None:
            return
        time_delta = utc_datetime - latest_datetime
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
            timestamp=int(utc_datetime.timestamp())
        ))
        await write_user_data(ctx=ctx, data=data)
        await ctx.respond(embed=generate_embed(
            ctx=ctx,
            color="WAKE_UP",
            title=choice(RESPONSE_MESSAGE["WAKE_UP"]),
            description=f"今天是你的 {YEARS[-1]} 年 {n_month} 月 {n_day} 日，你的昨天已離去 {hours} 小時 {minutes} 分 {seconds} 秒之久。",
            fields={
                "紀錄時間": f"<t:{int((utc_datetime + timedelta(hours=timezone_)).timestamp())}:F>"
            },
        ))

    @group.command(
        name="oyasumi",
        description="登出舊的一天。",
        checks=[check_signed(sign_up)],
    )
    async def oyasumi(
        self,
        ctx: ApplicationContext,
        time_: Option(str, name="時間", description="時間 格式為HH:MM:SS", required=False),
        date_: Option(str, name="日期", description="日期 格式為YYYY-MM-DD", required=False),
        timezone_: Option(float, name="時區", description="時區", default=8, min_value=-12, max_value=12),
    ):
        data = await read_user_data(ctx)
        latest = data[-1]
        latest_datetime = datetime.fromtimestamp(latest.timestamp)
        utc_datetime = await get_utc_datetime(
            ctx=ctx,
            latest_datetime=latest_datetime,
            time_=time_,
            date_=date_,
            timezone_=timezone_
        )
        if utc_datetime is None:
            return
        time_delta = utc_datetime - latest_datetime
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
            timestamp=int(utc_datetime.timestamp())
        ))
        await write_user_data(ctx=ctx, data=data)
        await ctx.respond(embed=generate_embed(
            ctx=ctx,
            color="SLEEP",
            title=choice(RESPONSE_MESSAGE["SLEEP"]),
            description=f"你結束了你的 {latest.year}年 {latest.month} 月 {latest.day} 日，共 {hours} 小時 {minutes} 分 {seconds} 秒。",
            fields={
                "紀錄時間": f"<t:{int((utc_datetime + timedelta(hours=timezone_)).timestamp())}:F>"
            },
        ))

    # @group.command(
    #     name="insert",
    #     description="登出舊的一天。",
    #     checks=[check_signed(sign_up)],
    # )
    # async def insert(
    #     self,
    #     ctx: ApplicationContext,
    #     start_time: Option(str, name="起始時間", description="起床時的時間 格式為HH:MM:SS", required=True),
    #     end_time: Option(str, name="結束時間", description="睡覺時的時間 格式為HH:MM:SS", required=True),
    #     start_date: Option(str, name="起始日期", description="起床時的日期 格式為YYYY-MM-DD", required=False),
    #     end_date: Option(str, name="結束日期", description="睡覺時的日期 格式為YYYY-MM-DD", required=False),
    #     time_zone: Option(float, name="時區", description="時區", default=8, min_value=12, max_value=12)
    # ):
    #     try:
    #         now_time = datetime.now()
    #         start_date = now_time.date() if start_date is None else date.fromisoformat(start_date)
    #         start_time = time.fromisoformat(start_time)
    #         end_date = now_time.date() if end_date is None else date.fromisoformat(end_date)
    #         end_time = time.fromisoformat(end_time)
    #         time_delta = timedelta(hours=time_zone)

    #         start_datetime = datetime.combine(start_date, start_time) - time_delta
    #         end_datetime = datetime.combine(end_date, end_time) - time_delta
    #         assert end_datetime > start_datetime
    #         assert end_datetime < now_time - time_delta

    #         data = await read_user_data(ctx)
    #         data.append(SSHData(
    #             type="WAKE_UP",
    #             timestamp=int(start_datetime.timestamp())
    #         ))
    #         data.append(SSHData(
    #             type="SLEEP",
    #             timestamp=int(end_datetime.timestamp())
    #         ))
    #         data = rebuild(data)
    #         await write_user_data(ctx=ctx, data=data)
    #         await ctx.respond(embed=generate_embed(
    #             ctx=ctx,
    #             color="INFO",
    #             title="新增成功",
    #         ))
    #     except:
    #         await ctx.respond(embed=generate_embed(
    #             ctx=ctx,
    #             color="WARN",
    #             title="格式錯誤",
    #             description="輸入格式錯誤，請重新檢查。"
    #         ))

    @group.command(
        name="current",
        description="查看現在是哪一天。",
        checks=[check_signed(sign_up)],
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
        checks=[check_signed(sign_up)],
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

    @group.command(
        name="dump",
        description="取得自己的紀錄檔",
        checks=[check_signed(sign_up)],
    )
    async def dump(
        self,
        ctx: ApplicationContext
    ):
        file_path = get_user_file(ctx)
        async with async_open(file_path, "rb") as f:
            context = await f.read()
        await ctx.respond(file=File(BytesIO(context), f"{ctx.author.display_name}.json"))


def setup(bot: Bot):
    bot.add_cog(SleepSleepHistory(bot))

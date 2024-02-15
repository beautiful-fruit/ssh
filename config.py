from orjson import loads, dumps, OPT_INDENT_2
from pydantic import BaseModel, ConfigDict, field_validator

from datetime import timedelta, timezone
from os import makedirs
from os.path import isdir, isfile

class Config(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    token: str
    data_dir: str = "data"
    managers: list[int] = []
    tz: float = 8

if not isfile("config.json"):
    token = input("Discord Token: ")
    with open("config.json", "wb") as config_file:
        config_file.write(dumps(Config(**{
            "token": token,
            "data_dir": "data",
            "managers": [],
            "tz": 8,
        }).model_dump(), option=OPT_INDENT_2))

with open("config.json", "rb") as config_file:
    config: Config = Config(**loads(config_file.read()))

TOKEN = config.token
DATA_DIR = config.data_dir
MANAGERS = config.managers
TIMEZONE = config.tz

if TOKEN is None:
    raise RuntimeError("Token not found")

if not isdir(DATA_DIR):
    makedirs(DATA_DIR)

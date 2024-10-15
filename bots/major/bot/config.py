from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
from global_data.global_config import global_settings

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int = global_settings.API_ID
    API_HASH: str = global_settings.API_HASH

    LOGIN_SLEEP: list[int] = global_settings.LOGIN_SLEEP
    MINI_SLEEP: list[int] = global_settings.MINI_SLEEP
    BIG_SLEEP: list[int] = global_settings.BIG_SLEEP
    ACCOUNTS_MOOD_SEQUENTIAL: bool= global_settings.ACCOUNTS_MOOD_SEQUENTIAL


    REF_ID: str = global_settings.ACTIVE_BOTS['major']['REF_ID']

    AUTO_TASKS: bool = True
    TASKS_WITH_JOIN_CHANNEL: bool = False # Not working for now

    AUTO_HOLD_COIN: bool = True
    HOLD_COIN: list[int] = [800, 915]
    AUTO_SWIPE_COIN: bool = True
    SWIPE_COIN: list[int] = [2000, 3000]
    AUTO_ROULETTE: bool = True
    AUTO_PUZZLE: bool = False # Not working for now
    
    AUTO_TASKS: bool = True

settings = Settings()

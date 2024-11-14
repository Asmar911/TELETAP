from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
from global_data.global_config import global_settings

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int = global_settings.API_ID
    API_HASH: str = global_settings.API_HASH
    WORKDIR: str = 'bots/notpixel/sessions/'

    LOGIN_SLEEP: list[int] = global_settings.LOGIN_SLEEP
    MINI_SLEEP: list[int] = global_settings.MINI_SLEEP
    BIG_SLEEP: list[int] = global_settings.BIG_SLEEP
    ACCOUNTS_MOOD_SEQUENTIAL: bool= global_settings.ACCOUNTS_MOOD_SEQUENTIAL

    REF_ID: str = global_settings.ACTIVE_BOTS['notpixel']['REF_ID']

    
    SLEEP_TIME: list[int] = [6000, 7200]
    AUTO_DRAW: bool = True
    AUTO_TASK: bool = True
    JOIN_TG_CHANNELS: bool = True
    CLAIM_REWARD: bool = True
    
    AUTO_UPGRADE: bool = True
    PAINT_REWARD_MAX_LEVEL: int = 7
    RECHARGE_SPEED_MAX_LEVEL: int = 11
    ENERGY_LIMIT_MAX_LEVEL: int = 7
    
    IGNORED_BOOSTS: list[str] = []
    IN_USE_SESSIONS_PATH: str = './bots/notpixel/bot/used_sessions.txt'

    NIGHT_MODE: bool = True
    NIGHT_TIME: list[int] = [0, 7] #UTC HOURS
    NIGHT_CHECKING: list[int] = [3600, 7200]
    

settings = Settings()

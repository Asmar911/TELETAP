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

    REF_ID: str = global_settings.ACTIVE_BOTS['notpixel']['REF_ID']

    
    AUTO_PAINT: bool = True
    AUTO_MINING: bool = True
    AUTO_TASK: bool = True
    AUTO_UPGRADE: bool = False
    AUTO_UPGRADE_PAINT: bool = True
    MAX_PAINT_LEVEL: int = 7
    AUTO_UPGRADE_CHARGE: bool = True
    MAX_CHARGE_LEVEL: int = 11
    AUTO_UPGRADE_ENERGY: bool = True
    MAX_ENERGY_LEVEL: int = 6
    TASKS: list[str] = ["paint20pixels", "leagueBonusSilver", "x:notcoin", "x:notpixel"]
    COLORS: list[str] = ["#6A5CFF", "#e46e6e", "#FFD635", "#7EED56", "#00CCC0", "#51E9F4", "#94B3FF",
                         "#9C6926", "#6D001A", "#bf4300", "#000000", "#FFFFFF"]
    

settings = Settings()

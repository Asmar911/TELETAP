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


    REF_ID: str = global_settings.ACTIVE_BOTS['cexio']['REF_ID']

    AUTO_TAP: bool = False
    MIN_ENERGY: int = 200

    RANDOM_TAPS_COUNT: list[int] = [25, 50]
    SLEEP_BETWEEN_TAPS: list[int] = [3, 10] #[25, 35]

    AUTO_CONVERT: bool = True
    MINIMUM_TO_CONVERT: float = 0.1

    AUTO_BUY_UPGRADE: bool = True
    BALANCE_TO_SAVE: int = 100

    AUTO_TASK: bool = True
    AUTO_CLAIM_SQUAD_BONUS: bool = True


settings = Settings()

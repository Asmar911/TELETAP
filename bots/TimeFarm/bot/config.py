from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
from global_data.global_config import global_settings

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int = global_settings.API_ID
    API_HASH: str = global_settings.API_HASH
    WORKDIR: str = 'bots/TimeFarm/sessions/'

    LOGIN_SLEEP: list[int] = global_settings.LOGIN_SLEEP
    MINI_SLEEP: list[int] = global_settings.MINI_SLEEP
    BIG_SLEEP: list[int] = global_settings.BIG_SLEEP
    ACCOUNTS_MOOD_SEQUENTIAL: bool= global_settings.ACCOUNTS_MOOD_SEQUENTIAL
    
    REF_ID: str = global_settings.ACTIVE_BOTS['TimeFarm']['REF_ID']

    AUTO_CLAIM_REFERRAL: bool = True
    AUTO_FARM: bool = True
    AUTO_TASK: bool = False # Not working for now
    JOIN_CHANNELS: bool = True 
    AUTO_STAKING: bool = True
    PROTECTED_BALANCE: int = 100000 # minimum balance before staking
    
    

    AUTO_UPGRADE_FARM: bool = True # Not working for now
    MAX_UPGRADE_LEVEL: int = 6 # Not working for now


settings = Settings()

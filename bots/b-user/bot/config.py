from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
from global_data.global_config import global_settings

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int = global_settings.API_ID
    API_HASH: str = global_settings.API_HASH
    WORKDIR: str = "bots/b-user/sessions/"

    LOGIN_SLEEP: list[int] = global_settings.LOGIN_SLEEP
    MINI_SLEEP: list[int] = global_settings.MINI_SLEEP
    BIG_SLEEP: list[int] = global_settings.BIG_SLEEP
    ACCOUNTS_MOOD_SEQUENTIAL: bool= global_settings.ACCOUNTS_MOOD_SEQUENTIAL
    
    REF_ID: str = global_settings.ACTIVE_BOTS['b-user']['REF_ID']

    AUTO_TASK: bool = True
    JOIN_TG_CHANNELS: bool = True
    DISABLED_TASKS: list[str] = ['CONNECT_WALLET', 'INVITE_FRIENDS', 'BOOST_TG', 'SEND_SIMPLE_TON_TRX']

    
    

settings = Settings()

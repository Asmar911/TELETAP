from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
from global_data.global_config import global_settings

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int = global_settings.API_ID
    API_HASH: str = global_settings.API_HASH
    WORKDIR: str = 'bots/boinkers/sessions/'

    LOGIN_SLEEP: list[int] = global_settings.LOGIN_SLEEP
    MINI_SLEEP: list[int] = global_settings.MINI_SLEEP
    BIG_SLEEP: list[int] = global_settings.BIG_SLEEP
    ACCOUNTS_MOOD_SEQUENTIAL: bool= global_settings.ACCOUNTS_MOOD_SEQUENTIAL
    
    REF_ID: str = global_settings.ACTIVE_BOTS['blum']['REF_ID']

    AD_TASK_PREFIX: str = 'AdTask'

    ENABLE_AUTO_TASKS: bool = True
    ENABLE_AUTO_WHEEL_FORTUNE: bool = True
    ENABLE_AUTO_ELEVATOR: bool = True
    ELEVATOR_MAX_LEVEL: int = 4
    ENABLE_AUTO_SPIN: bool = True
    ENABLE_AUTO_UPGRADE: bool = True

    BLACK_LIST_TASKS: list[str] = [
         'telegramShareStory',
         'emojiOnPostTelegramNewsChannel',
         'NotGoldReward',
         'NotPlatinumReward',
         'connectTonWallet',
         'telegramJoinBoinkersNewsChannel',
         'telegramBoost',
         'telegramJoinAcidGames',
         'AnimalsAndCoins',
         'AnimalsAndCoinsIsland',
         'AnimalsAndCoinsInstall',
         'playCornBattle',
         'NBPSep',
         'inviteAFriend',
         'MergePalsQuests',
         'playAAO',
         'playPiggyPiggy',
         'dailyVIPEnergyPerk',
         'vipGoldPerk',
         'dailyVIPWheelSpins',
         'foxCoinEnergy',
         'DiamoreSep18',
    ]

    
    

settings = Settings()

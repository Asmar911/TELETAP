from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int 
    API_HASH: str 

    LOGIN_SLEEP: list[int] = [60, 360]
    MINI_SLEEP: list[int] = [5, 15]
    BIG_SLEEP: list[int] = [10800, 18000]

    BOT_MOOD_SEQUENTIAL: bool= False
    ACCOUNTS_MOOD_SEQUENTIAL: bool= True



    ACTIVE_BOTS: dict[str, bool] = {
    "blum" : True,
    "catsgang" : False,
    "catsvsdogs" : True,
    "cexio" : True,
    "goats" : True,
    "major" : True,
    "notpixel" : True,
    "tomarket" : True
    }  


global_settings = Settings()
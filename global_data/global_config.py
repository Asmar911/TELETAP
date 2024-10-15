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



    ACTIVE_BOTS: dict[str, dict] = {
        "blum": {"Active": True, "REF_ID": "ref_P4Rbg063KM"},
        "catsgang": {"Active": False, "REF_ID": "VcEZmxM20ef4jbRAn1ppe"},
        "catsvsdogs": {"Active": True, "REF_ID": "153623395"},
        "cexio": {"Active": True, "REF_ID": "1716712060572190"},
        "goats": {"Active": True, "REF_ID": "68bd4bd3-172c-4f22-aa90-e092517e12b5"},
        "major": {"Active": True, "REF_ID": "153623395"},
        "notpixel": {"Active": True, "REF_ID": "f153623395"},
        "tomarket": {"Active": True, "REF_ID": "0000omgl"}
    }
    


global_settings = Settings()
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int 
    API_HASH: str 
    WORKDIR: str = 'global_data/sessions/'

    LOGIN_SLEEP: list[int] = [60, 360]
    MINI_SLEEP: list[int] = [5, 15]
    BIG_SLEEP: list[int] = [10800, 18000]

    BOT_MOOD_SEQUENTIAL: bool= False
    ACCOUNTS_MOOD_SEQUENTIAL: bool= True

    ACTIVE_BOTS: dict[str, dict] = {
        "blum": {"Active": True, "REF_ID": "ref_P4Rbg063KM"},
        "catsvsdogs": {"Active": False, "REF_ID": "153623395"}, # Need Update
        "cexio": {"Active": False, "REF_ID": "1716712060572190"}, # Need Update
        "goats": {"Active": True, "REF_ID": "68bd4bd3-172c-4f22-aa90-e092517e12b5"},
        "notpixel": {"Active": False, "REF_ID": "f153623395"}, # Need Update
        "boinkers": {"Active": True, "REF_ID": "boink153623395"}, # Need Update
        "b-user": {"Active": True, "REF_ID": "ref-cskJfjtbUhT8Uw2h8JyDHa"},
        "fintopio": {"Active": True, "REF_ID": "reflink-reflink_lkihScR7z5HVlZlM-"},
        "moonbix": {"Active": False, "REF_ID": "ref_1536233950"}, # Not Working yet
        "okxracer": {"Active": True, "REF_ID": "linkCode_93102758"}, 
        "TrustApp": {"Active": True, "REF_ID": "1345ea46-52fc-41bb-afde-f820bcadab38"}, 
        "TimeFarm": {"Active": True, "REF_ID": "1eYFkqTqjduuyi4DN"},
        "bool": {"Active": True, "REF_ID": "1E8C0"},
    }
    
global_settings = Settings()
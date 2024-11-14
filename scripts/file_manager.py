import json
import os
import shutil
from global_data.global_config import global_settings 
from scripts.logger import logger


def load_from_json(path: str):
    if os.path.isfile(path):
        with open(path, encoding='utf-8') as file:
            return json.load(file)
    else:
        with open(path, 'x', encoding='utf-8') as file:
            example = {
                 "session_name": "name_example",
                 "user_agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.165 Mobile Safari/537.36",
                 "proxy": "type://user:pass:ip:port"
            }
            json.dump([example], file, ensure_ascii=False, indent=2)
            return [example]


def save_to_json(path: str, dict_):
    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        data.append(dict_)
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
    else:
        with open(path, 'x', encoding='utf-8') as file:
            json.dump([dict_], file, ensure_ascii=False, indent=2)




async def update_sessions_file():
    await delete_session_folders()
    bots_path = 'bots/'
    try:
        for bot_folder in os.listdir(bots_path):
            bot_folder_path = os.path.join(bots_path, bot_folder)
            if os.path.isdir(bot_folder_path):
                bot_sessions_path = os.path.join(bot_folder_path, 'sessions')
                os.makedirs(bot_sessions_path, exist_ok=True)
                for file_name in os.listdir(global_settings.WORKDIR):
                    source_file_path = os.path.join(global_settings.WORKDIR, file_name)
                    destination_file_path = os.path.join(bot_sessions_path, file_name)
                    if file_name.endswith('.session') and os.path.isfile(source_file_path) and not os.path.exists(destination_file_path):
                        shutil.copy(source_file_path, destination_file_path)
        logger.info("Sessions files updated successfully.")
    except Exception as e:
        logger.error(f"Error updating sessions files: {e}")



async def delete_session_folders():
    bots_path = 'bots/'
    try:
        for bot_folder in os.listdir(bots_path):
            bot_folder_path = os.path.join(bots_path, bot_folder)
            
            # Ensure we are working with a directory
            if os.path.isdir(bot_folder_path):
                bot_sessions_path = os.path.join(bot_folder_path, 'sessions')
                if os.path.exists(bot_sessions_path):
                    shutil.rmtree(bot_sessions_path)
    except Exception as e:
        logger.error(f"Error deleting sessions folders: {e}")
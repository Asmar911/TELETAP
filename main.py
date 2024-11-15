import os
import sys
import asyncio
import argparse
import tgcrypto

from global_data.global_config import global_settings
from scripts.registrator import create_session, validate_account
from scripts.accounts import Accounts
from scripts.runner import run_bots, run_bot
from scripts.logger import logger
from scripts.file_manager import update_sessions_file, delete_session_folders

MESSAGE = """
   
    ████████╗███████╗██╗     ███████╗████████╗ █████╗ ██████╗ 
    ╚══██╔══╝██╔════╝██║     ██╔════╝╚══██╔══╝██╔══██╗██╔══██╗
       ██║   █████╗  ██║     █████╗     ██║   ███████║██████╔╝
       ██║   ██╔══╝  ██║     ██╔══╝     ██║   ██╔══██║██╔═══╝ 
       ██║   ███████╗███████╗███████╗   ██║   ██║  ██║██║     
       ╚═╝   ╚══════╝╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝     
                                                   
    Telegram MiniApps Autoclicker
    Developed by @Asmar911               
    GitHub Repository: https://github.com/Asmar911/TELETAP
    """


async def main():
    print(MESSAGE)
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--action', type=int, help='Action')
    parser.add_argument('-b', '--bot', type=str, help='Bot name (only for action 3)')
    args = parser.parse_args()

    startAction = args.action
    bot_name = args.bot

    if not os.path.exists('./global_data/sessions'):
        os.mkdir('./global_data/sessions')
    
    while True:
        if startAction is not None:
            action = startAction
            startAction = None
        else:
            action = int(input("TELETAP Actions:\n    1 -> Actions with sessions\n    2 -> Run Clicker (all bots)\n    3 -> Run Clicker (specific bot)\n    4 -> Exit\nSelect an action: "))

        if action == 1:
            await actions_with_sessions()
        
        elif action == 2:
            await update_sessions_file()
            accounts = await Accounts().get_accounts()
            # await validate_account(accounts)            
            await run_bots()

        elif action == 3:
            if not bot_name:
                bot_name = input("Enter the bot name: ")
            bot_path = os.path.join('bots', bot_name, f'{bot_name}.py')
            await update_sessions_file()
            await Accounts().get_accounts()
            if os.path.isfile(bot_path):
                await run_bot(bot_name, bot_path)
            else:
                print(f"{bot_name} does not have a {bot_name}.py file!")
            bot_name = None  

        elif action == 5:
            print("Goodbye!")
            await asyncio.sleep(2)
            sys.exit(2)
        else:
            break

async def actions_with_sessions():
    x = 0
    while True:
        if x == 0:
            clear_last_n_lines(6)
        action = int(input("Sessions Actions:\n    1 -> Create session\n    2 -> Update sessions files\n    3 -> Delete all sessions folders\n    4 -> Back to main menu\nSelect an action: "))

        if action == 1:
            await create_session()

        elif action == 2:
            await update_sessions_file()
        
        elif action == 3:
            clear_last_n_lines(6)
            await delete_session_folders(log=True)
        
        elif action == 4:
            clear_last_n_lines(6)
            break

        x += 1

def clear_last_n_lines(n):
    for _ in range(n):
        print("\033[F\033[K", end="")



if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning(f"<red>Bot stopped by user...</red>")
        sys.exit(2)
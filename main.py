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
from scripts.file_manager import update_sessions_file

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
            action = int(input("TELETAP Actions:\n    1 -> Create session\n    2 -> Update sessions files\n    3 -> Run Clicker (all bots)\n    4 -> Run Clicker (specific bot)\n    5 -> Exit\nSelect an action: "))

        if action == 1:
            await create_session()

        elif action == 2:
            await update_sessions_file()
        
        elif action == 3:
            await update_sessions_file()
            accounts = await Accounts().get_accounts()
            # await validate_account(accounts)            
            await run_bots()

        elif action == 4:
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

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning(f"<red>Bot stopped by user...</red>")
        sys.exit(2)
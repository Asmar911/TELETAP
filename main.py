import os
import sys
import asyncio
import argparse

from global_data.global_config import global_settings
from scripts.registrator import create_session, validate_account
from scripts.accounts import Accounts
from scripts.runner import run_bots, run_bot
from scripts.logger import logger

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
    parser.add_argument('-a', '--action', type=str, help='Action')
    startAction = parser.parse_args().action
    if (startAction): startAction = int(startAction)

    if not os.path.exists('./global_data/sessions'):
        os.mkdir('./global_data/sessions')
    

    while True:
        if (startAction != None): 
            action = startAction
            startAction = None
        else: action = int(input("TELETAP Actions:\n    1 -> Create session\n    2 -> Run Clicker (all bots)\n    3 -> Run Clicker (specific bot)\n    4 -> Exit\nSelect an action: "))

        if (action == 1):
            await create_session()

        elif (action == 2):
            accounts = await Accounts().get_accounts()
            await validate_account(accounts)            
            await run_bots()

        elif (action == 3):
            bot_name = input("Enter the bot name: ")
            bot_path = os.path.join('bots', bot_name, f'{bot_name}.py')
            await Accounts().get_accounts()
            if os.path.isfile(bot_path):
                await run_bot(bot_name, bot_path)
            else:
                print(f"{bot_name} does not have a {bot_name}.py file!")
        elif (action == 4):
            print("Goodbye!")
            await asyncio.sleep(2)
            sys.exit(2)
        else: break

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning(f"<red>Bot stopped by user...</red>")
        sys.exit(2)
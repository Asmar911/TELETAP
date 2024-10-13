import os
import asyncio
from random import randint
from global_data.global_config import global_settings
from scripts.logger import logger


# Function to stream stdout output
async def stream_output(process, folder):
    folder_name = f"{folder:<10}"
    while True:
        line = await process.stdout.readline()
        if line:
            message = line.decode('cp1251' if os.name == 'nt' else 'utf-8').rstrip().replace("<", "\\<").replace(">", "\\>")
            formatted_message = f"[{folder_name}] | {message}"
            print(formatted_message)
        else:
            break
    # Capture stderr as well
    while True:
        error_line = await process.stderr.readline()
        if error_line:
            error_message = error_line.decode('cp1251' if os.name == 'nt' else 'utf-8').rstrip().replace("<", "\\<").replace(">", "\\>")
            formatted_error = f"[{folder_name}] [ERROR] | {error_message}"
            print(formatted_error)
        else:
            break


async def run_bot(bot_name, bot_path):
    # if global_settings.BOT_MOOD_SEQUENTIAL:
    #     _sleep = randint(*global_settings.LOGIN_SLEEP)
    #     logger.info(f"{bot_name} will start in {_sleep}s ...")
    #     await asyncio.sleep(_sleep)
    # else:
    #     logger.info(f"{bot_name} will start NOW")
    # await asyncio.sleep(randint(5, 15))

    while True:
        # Create subprocess to run the bot, passing the accounts list as a command-line argument
        process = await asyncio.create_subprocess_exec(
            'python' if os.name == 'nt' else 'python3.11',  # Adjust for OS
            bot_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Create tasks to stream stdout and stderr asynchronously
        asyncio.create_task(stream_output(process, bot_name))

        # Wait for the process to complete
        await process.wait()

        # print(f"{bot_name}.py has finished. Restarting in 5 seconds...")
        # await asyncio.sleep(5)  # Delay before restarting

async def run_bots():
    bots_dir = 'bots'  # Define the bots folder
    tasks = []
    delay = 0

    # Fetch accounts here (Assuming you have a function to get accounts)
    # accounts = await get_accounts()  # Replace with your actual function to fetch accounts
    if global_settings.BOT_MOOD_SEQUENTIAL:
        logger.info(f"Bots SEQUENTIAL MOOD: <lg>Active</lg>")
    else:
        logger.info(f"Bots SEQUENTIAL MOOD: <lr>Not Active</lr>")
    if global_settings.ACCOUNTS_MOOD_SEQUENTIAL:
        logger.info(f"Accounts SEQUENTIAL MOOD: <lg>Active</lg>")
    else:
        logger.info(f"Accounts SEQUENTIAL MOOD: <lr>Not Active</lr>")
    
    active_bots = [bot_name for bot_name in global_settings.ACTIVE_BOTS if global_settings.ACTIVE_BOTS[bot_name]]
    logger.info(f"Active bots: <lg>{len(active_bots)}</lg>")
    print("============================================================================")

    await asyncio.sleep(5)
    # Iterate through the bots and run the ones that are enabled
    for bot_name, should_run in global_settings.ACTIVE_BOTS.items():
        if should_run:
            bot_file = f'{bot_name}.py'
            bot_path = os.path.join(bots_dir, bot_name, bot_file)  # Adjust path based on folder structure

            if os.path.isfile(bot_path):
                # print(f"Running bot: {bot_name}, Path: {bot_path}")  # Debugging statement
                
                if global_settings.BOT_MOOD_SEQUENTIAL:
                    delay = randint(*global_settings.LOGIN_SLEEP)
                    logger.info(f"{bot_name:<10} | <lg>active</lg> | will start in {delay}s ...")
                    await asyncio.sleep(delay=delay)
                    tasks.append(asyncio.create_task(run_bot(bot_name, bot_path)))
                else:
                    logger.info(f"{bot_name:<10} | <lg>active</lg> | will start NOW")
                    tasks.append(asyncio.create_task(run_bot(bot_name, bot_path)))
            else:
                print(f"{bot_name} does not have a {bot_file} file!")
    print("============================================================================")

    # Wait for all bots to finish (although they are designed to run indefinitely)
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(run_bots())

import os
import asyncio
from random import randint
from global_data.global_config import global_settings
from scripts.logger import logger


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
    while True:
        error_line = await process.stderr.readline()
        if error_line:
            error_message = error_line.decode('cp1251' if os.name == 'nt' else 'utf-8').rstrip().replace("<", "\\<").replace(">", "\\>")
            formatted_error = f"[{folder_name}] [ERROR] | {error_message}"
            print(formatted_error)
        else:
            break


async def run_bot(bot_name, bot_path):
    while True:
        process = await asyncio.create_subprocess_exec(
            'python' if os.name == 'nt' else 'python3.11',
            bot_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        asyncio.create_task(stream_output(process, bot_name))
        await process.wait()

async def run_bots():
    bots_dir = 'bots'  
    tasks = []
    delay = 0

    if global_settings.BOT_MOOD_SEQUENTIAL:
        logger.info(f"Bots SEQUENTIAL MOOD: <lg>Active</lg>")
    else:
        logger.info(f"Bots SEQUENTIAL MOOD: <lr>Not Active</lr>")
    if global_settings.ACCOUNTS_MOOD_SEQUENTIAL:
        logger.info(f"Accounts SEQUENTIAL MOOD: <lg>Active</lg>")
    else:
        logger.info(f"Accounts SEQUENTIAL MOOD: <lr>Not Active</lr>")
    
    active_bots = [bot_name for bot_name, bot_info in global_settings.ACTIVE_BOTS.items() if bot_info['Active']]
    logger.info(f"Active bots: <lg>{len(active_bots)}</lg>")
    print("============================================================================")
    await asyncio.sleep(5)

    for bot_name, bot_info in global_settings.ACTIVE_BOTS.items():
        if bot_info['Active']:
            bot_file = f'{bot_name}.py'
            bot_path = os.path.join(bots_dir, bot_name, bot_file)

            if os.path.isfile(bot_path):                
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
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(run_bots())

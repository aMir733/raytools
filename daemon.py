from raytools.func import *
import asyncio
import aiocron
import aiofiles

async def log_tail(f):
    global users
    async for line in tail(await aiofiles.open(f)):
        user = await log_parseline(line)
        if user:
            try:
                users[user[0]].add(user[1])
            except KeyError:
                users[user[0]] = {user[1]}

async def check_count():
    global users
    while True:
        await asyncio.sleep(30)
        for user, ips in users.items():
            print(user, len(ips))
        users = {}

@aiocron.crontab('00 00 * * *')
async def check_expire():
    pass

async def main():
    global users
    users = {}
    read1 = asyncio.create_task(log_tail("/tmp/t"))
    read2 = asyncio.create_task(log_tail("/tmp/a"))
    check = asyncio.create_task(check_count())

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
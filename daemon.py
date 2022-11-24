from raytools.func import *
import asyncio

async def read(f):
    print("listening on " + f)
    async for i in tail(open(f)):
        print(i)
        
async def main():
    read1 = asyncio.create_task(read("/tmp/t"))
    read2 = asyncio.create_task(read("/tmp/a"))
    await read1
    print("task 1 finished")
    await read2
    print("task 2 finished")

if __name__ == "__main__":
    asyncio.run(main())
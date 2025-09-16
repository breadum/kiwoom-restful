import asyncio
import time

from kiwoom import REAL, Bot


def timer(fn):
    def timer(*args, **kwargs):
        start = time.time()
        res = fn(*args, **kwargs)
        elapsed = time.time() - start
        print(fn.__name__, f"{elapsed:.2f} sec", "\n")
        return res

    return timer


async def test_real():
    appkey = "../keys/appkey.txt"
    scretkey = "../keys/secretkey.txt"

    async with Bot(REAL, appkey, scretkey) as bot:
        await bot.connect()
        await asyncio.sleep(1)

        # Fetch codes
        market_code = "0"  # KOSPI
        codes = await bot.stock_list(market_code)

        # Register
        print("Registered Hoga and Tick")
        await bot.api.register_hoga("1", codes[:100])
        await bot.api.register_tick("1", codes[:100])

        # Watch Registered
        await asyncio.sleep(10)

        # Remove codes
        print("Remove Registered")
        await bot.api.remove_register("1", codes[:100], type=["0B", "0D"])

        # Watch Removed
        await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(test_real())

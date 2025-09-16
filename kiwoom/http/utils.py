import asyncio
import contextlib
from typing import Callable

from kiwoom.config.http import REQ_LIMIT_PER_SECOND
from kiwoom.config.real import RealData

__all__ = ["cancel", "RateLimiter", "wrap_async_callback", "wrap_sync_callback"]


class RateLimiter:
    def __init__(self, rps: int = REQ_LIMIT_PER_SECOND):
        """
        Globally limits requests per second.

        Args:
            rps (float): requests per second
        """
        self._period = 1.0 / rps
        self._lock = asyncio.Lock()
        self._next = 0.0

    async def acquire(self):
        async with self._lock:
            now = asyncio.get_running_loop().time()
            if self._next < now:
                self._next = now
            wait = self._next - now
            self._next += self._period

        if wait > 0:
            await asyncio.sleep(wait)


def wrap_async_callback(semaphore: asyncio.Semaphore, callback: Callable) -> Callable:
    """
    Wrap async callback to run in async context.

    Args:
        semaphore (asyncio.Semaphore): semaphore to limit the number of callbacks
        callback (Callable): callback to be wrapped

    Returns:
        Callable: wrapped callback
    """

    async def wrapper(msg: RealData | dict):
        async with semaphore:
            await callback(msg)

    return wrapper


def wrap_sync_callback(semaphore: asyncio.Semaphore, callback: Callable) -> Callable:
    """
    Wrap sync callback to run in async context.

    Args:
        semaphore (asyncio.Semaphore): semaphore to limit the number of callbacks
        callback (Callable): callback to be wrapped

    Returns:
        Callable: wrapped callback
    """

    async def wrapper(msg: RealData | dict):
        async with semaphore:
            await asyncio.get_running_loop().run_in_executor(None, callback, msg)

    return wrapper


async def cancel(task: asyncio.Task | None) -> None:
    """
    Cancel a task if it exists.

    Args:
        task (asyncio.Task | None): task to be cancelled
    """
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

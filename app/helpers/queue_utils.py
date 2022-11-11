import asyncio
import functools
import itertools
import logging
import time
from asyncio import CancelledError, Task
from typing import Any, Callable, Dict, List, Tuple

from sentry_sdk import capture_exception

logger = logging.getLogger(__name__)

_bg_task_name_counter = itertools.count(1).__next__
MAX_SHUTDOWN_WAIT_SECONDS = 5


def timed_task():
    def wrapper(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapped(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                process_time = (time.time() - start_time) * 1000
                formatted_process_time = "{:.2f}".format(process_time)

                log_line_data = {
                    "duration": formatted_process_time,
                    "type": "task",
                    "task": getattr(func, "__name__", repr(func)),
                }

                sorted_dict = dict(sorted(log_line_data.items(), key=lambda x: x[0].lower()))
                log_line = " ".join([f"{key}={value}" for key, value in sorted_dict.items()])
                logger.info("canonical-log %s", log_line)

        return wrapped

    return wrapper


async def _get_bg_task_name():
    return f"BackgroundTask-{_bg_task_name_counter}"


async def _build_coro_from_function_tuple(f: Tuple[Any, ...]):
    kwargs: Dict[Any, Any] = {}
    if len(f) == 2:
        method, args = f
    else:
        method, args, kwargs = f
    return method(*args, **kwargs)


async def _get_running_bg_tasks():
    return [task for task in asyncio.all_tasks() if task.get_name().startswith("BackgroundTask")]


async def stop_background_tasks():
    if not await _get_running_bg_tasks():
        return

    wait_time = 0
    while True:
        running_bg_tasks = await _get_running_bg_tasks()
        if not running_bg_tasks:
            break

        await asyncio.sleep(0.1)
        wait_time += 0.1

        if wait_time > MAX_SHUTDOWN_WAIT_SECONDS:
            break

    running_bg_tasks = await _get_running_bg_tasks()
    if not running_bg_tasks:
        return

    [task.cancel() for task in running_bg_tasks]
    logger.info(f"Cancelling {len(running_bg_tasks)} outstanding tasks")
    try:
        await asyncio.gather(*running_bg_tasks)
    except CancelledError:
        pass
    except Exception as e:
        logger.error(f"problem waiting for tasks to cancel: {e}")
        raise e


async def handle_results(results, tasks: List[Task]):
    for index, result in enumerate(results):
        task = tasks[index]
        if isinstance(result, CancelledError):
            logger.warning(f"Task was cancelled: {result} | task: {task}")
        elif isinstance(result, Exception):
            logger.error(f"Handling exception: {result} | task: {task}")
            logger.exception(result)
            capture_exception(result)


async def dispatch_concurrent_fs(fs: List[tuple[Callable, tuple[Any, ...], dict]]):
    coros = [await _build_coro_from_function_tuple(f) for f in fs]
    tasks = [asyncio.create_task(coro, name=await _get_bg_task_name()) for coro in coros]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    await handle_results(results, tasks)


async def dispatch_serial_fs(fs: List[tuple[Callable, tuple[Any, ...], dict]]):
    for f in fs:
        coro = await _build_coro_from_function_tuple(f)
        task = asyncio.create_task(coro, name=await _get_bg_task_name())
        try:
            await task
        except CancelledError:
            logger.error(f"Task was cancelled | task: {task}")
            break
        except Exception as e:
            logger.error(f"Handling exception: {e} | task: {task}")
            capture_exception(e)
            logger.exception(e)
            break


async def queue_bg_task(f: Callable, *args: Any, **kwargs: Any):
    asyncio.create_task(dispatch_concurrent_fs([(f, args, kwargs)]))


async def queue_bg_tasks(fs: List[tuple[Callable, tuple[Any, ...], dict]], concurrent=True):
    if not concurrent:
        asyncio.create_task(dispatch_serial_fs(fs))
    else:
        asyncio.create_task(dispatch_concurrent_fs(fs))

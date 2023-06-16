import asyncio
import websockets
import signal
import json

from multiprocessing import Manager

from judger import Judger, JudgeResult
from exceptions import JudgeServiceError


def judge(task, result_queue):
    try:
        Judger(
            task_id=task['task_id'],
            case_id=task['case_id'],
            test_case_config=task['test_case_config'],
            subcheck_config=task['subcheck_config'],
            result_queue=result_queue
        ).judge(
            task['code'],
            task['lang'],
            task['limit']
        )
    except JudgeServiceError as e:
        result_queue.put(Judger.make_report(
            status=JudgeResult.SYSTEM_ERROR,
            score=0,
            max_time=0,
            max_memory=0,
            log=str(e),
            detail=[]
        ))
    result_queue.put(None)


async def handler(websocket):
    while True:
        try:
            message = await websocket.recv()
        except (websockets.ConnectionClosedOK, websockets.exceptions.ConnectionClosedError):
            break
        try:
            task = json.loads(message)
        except json.decoder.JSONDecodeError:
            print(f'Decode failed: {message}')
            continue
        result_queue = Manager().Queue()
        loop = asyncio.get_event_loop()
        judger = loop.run_in_executor(
            None, judge, task, result_queue)
        while True:
            item = await loop.run_in_executor(None, result_queue.get)
            if item is None:
                break
            data = json.dumps(item)
            await websocket.send(data)


async def main():
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

    async with websockets.serve(handler, "", 8080):
        await stop

if __name__ == "__main__":
    asyncio.run(main())

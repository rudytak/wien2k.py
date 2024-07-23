import asyncio
import queue
class Result:
    pass

class OBJ:
    content: None
    wait_time: int

    async def execute(self) -> Result:
        pass


def add_to_queue(obj: OBJ, mf_id: str, loop: asyncio.BaseEventLoop) -> asyncio.Future:
    lcf = mf_info[mf_id]["last_command_finished"]

    nbf = max(time(), lcf)
    mf_info[mf_id]["last_command_finished"] = nbf + obj.wait_time

    future = loop.create_future()

    add_to_pq(obj, nbf, future)

    return future


mf_info = {
    "mf1": {
        "last_command_finished": 0,
    }
}


def time() -> int:
    pass

def add_to_pq(obj: OBJ, nbf: int, on_finished_future: asyncio.Future) -> None:
    pass

def sleep(time: int) -> None:
    pass

class PQ_Entry:
    obj: OBJ
    nbf: int
    on_finished_future: asyncio.Future


def get_first_from_pq() -> PQ_Entry:
    pass

async def loop_body(entry: PQ_Entry) -> None:
    ret = await entry.obj.execute()
    sleep(entry.obj.wait_time)
    entry.on_finished_future.set_result(ret)

async def pq_loop():
    while True:
        entry = get_first_from_pq()
        if entry == None: 
            sleep(10)
            continue

        time_to_wait = entry.nbf - time()
        sleep(time_to_wait)

        loop_body(entry)



    
async def main():
    pq_loop()

    obj = OBJ()

    loop = asyncio.get_running_loop()
    add_to_queue(obj, "mf1", loop)



    add_to_queue(obj, "mf1", loop)




    add_to_queue(obj, "mf1", loop)



main()
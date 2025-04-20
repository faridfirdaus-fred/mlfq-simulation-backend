import logging

logging.basicConfig(level=logging.INFO)

def simulate_mlfq(processes):
    queues = [[], [], []]
    time_quantum = [4, 8, None]  # Q0, Q1, Q2 (FCFS)

    clock = 0
    finished = []
    process_queue = sorted(processes, key=lambda p: p["arrival_time"])
    active = []

    def enqueue(proc, level):
        proc.update({"queue": level, "remaining": proc["burst_time"], "start": None})
        queues[level].append(proc)
        logging.info(f"Process {proc['pid']} added to queue {level}")

    for p in process_queue:
        enqueue(p, 0)

    while any(queues) or active:
        for level, q in enumerate(queues):
            if not q:
                continue
            proc = q.pop(0)
            tq = time_quantum[level]
            if proc["start"] is None:
                proc["start"] = clock

            run_time = min(proc["remaining"], tq) if tq else proc["remaining"]
            clock += run_time
            proc["remaining"] -= run_time

            if proc["remaining"] > 0:
                next_level = min(level + 1, 2)
                queues[next_level].append(proc)
                logging.info(f"Process {proc['pid']} moved to queue {next_level}")
            else:
                proc["finish"] = clock
                finished.append(proc)
                logging.info(f"Process {proc['pid']} finished at time {clock}")
            break
        else:
            clock += 1  # idle
            logging.info("CPU idle")

    return finished
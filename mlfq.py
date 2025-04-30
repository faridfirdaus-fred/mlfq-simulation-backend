import logging

logging.basicConfig(level=logging.INFO)

def simulate_mlfq(processes):
    queues = [[], [], []]
    time_quantum = [4, 8, None]  # Q0, Q1, Q2 (FCFS)

    clock = 0
    finished = []
    ready = []
    waiting = sorted(processes, key=lambda p: p["arrival_time"])

    # Tambahkan field default
    for p in waiting:
        p["remaining"] = p["burst_time"]
        p["start"] = None
        p["queue"] = 0

    while waiting or any(queues) or ready:
        # Pindahkan proses dari waiting ke queue 0 saat waktunya
        while waiting and waiting[0]["arrival_time"] <= clock:
            p = waiting.pop(0)
            logging.info(f"Process {p['pid']} arrived at time {clock}")
            queues[0].append(p)

        executed = False
        for level, q in enumerate(queues):
            if q:
                proc = q.pop(0)
                if proc["start"] is None:
                    proc["start"] = clock

                tq = time_quantum[level]
                run_time = min(proc["remaining"], tq) if tq else proc["remaining"]

                logging.info(f"Process {proc['pid']} running in queue {level} for {run_time} units")
                for t in range(run_time):
                    clock += 1
                    # Periksa apakah ada proses baru masuk selama eksekusi
                    while waiting and waiting[0]["arrival_time"] <= clock:
                        new_p = waiting.pop(0)
                        logging.info(f"Process {new_p['pid']} arrived at time {clock}")
                        queues[0].append(new_p)

                proc["remaining"] -= run_time

                if proc["remaining"] == 0:
                    proc["finish"] = clock
                    finished.append(proc)
                    logging.info(f"Process {proc['pid']} finished at time {clock}")
                else:
                    next_level = min(level + 1, 2)
                    proc["queue"] = next_level
                    queues[next_level].append(proc)
                    logging.info(f"Process {proc['pid']} moved to queue {next_level}")
                executed = True
                break

        if not executed:
            # Jika tidak ada proses dijalankan, sistem idle
            clock += 1
            logging.info("CPU idle")

    return finished

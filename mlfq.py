import logging
from collections import deque

logging.basicConfig(level=logging.INFO)

def simulate_mlfq(processes):
    # Inisialisasi antrian dan time quantum
    queues = [deque(), deque(), deque()]
    time_quantum = [4, 8, None]  # Q0, Q1, Q2 (FCFS)
    aging_threshold = 10  # Waktu maksimum sebelum aging

    clock = 0
    finished = []
    waiting = sorted([p for p in processes if p["burst_time"] > 0], key=lambda p: p["arrival_time"])

    # Tambahkan field default ke setiap proses
    for p in waiting:
        p["remaining"] = p["burst_time"]
        p["start"] = None
        p["queue"] = 0
        p["waiting_time"] = 0

    while waiting or any(queues):
        # Pindahkan proses dari waiting ke queue 0 saat waktunya
        while waiting and waiting[0]["arrival_time"] <= clock:
            p = waiting.pop(0)
            logging.info(f"Process {p['pid']} arrived at time {clock}")
            queues[0].append(p)

        executed = False

        # Aging: Promosikan proses di antrian prioritas rendah jika menunggu terlalu lama
        for level in range(1, len(queues)):
            for proc in list(queues[level]):
                proc["waiting_time"] += 1
                if proc["waiting_time"] >= aging_threshold:
                    queues[level].remove(proc)
                    queues[level - 1].append(proc)
                    proc["queue"] = level - 1
                    logging.info(f"Process {proc['pid']} promoted to queue {level - 1} due to aging")

        # Eksekusi proses dari antrian prioritas tertinggi
        for level, q in enumerate(queues):
            if q:
                proc = q.popleft()
                if proc["start"] is None:
                    proc["start"] = clock  # Set waktu mulai eksekusi

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
                        # Preemption: Jika proses baru masuk ke Q0, hentikan proses saat ini
                        if level > 0:
                            proc["remaining"] -= (t + 1)
                            queues[level].appendleft(proc)
                            logging.info(f"Process {proc['pid']} preempted by {new_p['pid']}")
                            executed = True
                            break
                    if executed:
                        break

                if executed:
                    break

                proc["remaining"] -= run_time

                if proc["remaining"] == 0:
                    proc["finish"] = clock
                    proc["turnaround_time"] = proc["finish"] - proc["arrival_time"]
                    proc["waiting_time"] = proc["turnaround_time"] - proc["burst_time"]
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
import logging
import random
from collections import deque

logging.basicConfig(level=logging.INFO)

def simulate_mlfq(processes):
    # Initialize queues and time quantum
    ready_queues = [deque(), deque(), deque()]  # CPU ready queues
    io_queue = deque()  # I/O waiting queue
    time_quantum = [4, 8, None]  # Q0, Q1, Q2 (FCFS)
    aging_threshold = 10  # Maximum time before aging
    
    clock = 0
    finished = []
    waiting = sorted([p for p in processes if p["burst_time"] > 0], 
                    key=lambda p: p["arrival_time"])
    
    # Add default fields to each process
    for p in waiting:
        p["remaining_cpu"] = p["burst_time"]
        p["remaining_io"] = p["io_burst"] if "io_burst" in p else 0
        p["io_bursts_completed"] = 0
        p["cpu_bursts_completed"] = 0
        p["start"] = None
        p["finish"] = None
        p["queue"] = 0
        p["waiting_time"] = 0
        p["io_time"] = 0
        p["state"] = "waiting"  # waiting, ready, running, io, finished
        p["current_burst_remaining"] = 0
        
        # Set total time if not provided
        if not p.get("total_time"):
            p["total_time"] = p["burst_time"] + p.get("io_burst", 0)
            
        # Make sure variance parameters exist
        if "cpu_variance" not in p:
            p["cpu_variance"] = 0.0
        if "io_variance" not in p:
            p["io_variance"] = 0.0
    
    def apply_variance(base_time, variance_factor):
        """Apply variance to burst times"""
        if variance_factor <= 0:
            return base_time
        
        # Generate variance between -variance_factor and +variance_factor
        variance = random.uniform(-variance_factor, variance_factor)
        varied_time = max(1, int(base_time * (1 + variance)))
        return varied_time
    
    while waiting or any(ready_queues) or io_queue:
        # Move processes from waiting to queue 0 when it's time
        while waiting and waiting[0]["arrival_time"] <= clock:
            p = waiting.pop(0)
            p["state"] = "ready"
            logging.info(f"Process {p['pid']} arrived at time {clock}")
            ready_queues[0].append(p)
        
        # Process I/O operations
        completed_io = []
        for proc in io_queue:
            proc["current_burst_remaining"] -= 1
            proc["io_time"] += 1
            if proc["current_burst_remaining"] <= 0:
                completed_io.append(proc)
                proc["remaining_io"] = max(0, proc["remaining_io"] - proc.get("io_burst", 0))
                proc["io_bursts_completed"] += 1
                logging.info(f"Process {proc['pid']} completed I/O at time {clock}")
        
        # Move completed I/O processes back to ready queue
        for proc in completed_io:
            io_queue.remove(proc)
            proc["state"] = "ready"
            # Reset to lowest queue if io_queue starvation prevention is desired
            proc["queue"] = 0  
            ready_queues[proc["queue"]].append(proc)
        
        executed = False
        
        # Aging: Promote processes in lower priority queues if they've waited too long
        for level in range(1, len(ready_queues)):
            for proc in list(ready_queues[level]):
                proc["waiting_time"] += 1
                if proc["waiting_time"] >= aging_threshold:
                    ready_queues[level].remove(proc)
                    proc["queue"] = max(0, level - 1)
                    ready_queues[proc["queue"]].append(proc)
                    proc["waiting_time"] = 0
                    logging.info(f"Process {proc['pid']} promoted to queue {proc['queue']} due to aging")
        
        # Execute process from highest priority queue
        for level, q in enumerate(ready_queues):
            if q:
                proc = q.popleft()
                proc["state"] = "running"
                
                if proc["start"] is None:
                    proc["start"] = clock  # Set start time of first execution
                
                # Apply CPU variance for this burst
                cpu_burst = apply_variance(
                    min(proc["remaining_cpu"], time_quantum[level] or proc["remaining_cpu"]),
                    proc.get("cpu_variance", 0)
                )
                
                proc["current_burst_remaining"] = cpu_burst
                logging.info(f"Process {proc['pid']} running in queue {level} for {cpu_burst} units")
                
                for t in range(cpu_burst):
                    clock += 1
                    proc["current_burst_remaining"] -= 1
                    proc["remaining_cpu"] -= 1
                    
                    # Check for new arrivals during execution
                    while waiting and waiting[0]["arrival_time"] <= clock:
                        new_p = waiting.pop(0)
                        new_p["state"] = "ready"
                        logging.info(f"Process {new_p['pid']} arrived at time {clock}")
                        ready_queues[0].append(new_p)
                        
                        # Preemption: If new process enters Q0, stop current process if it's in lower queue
                        if level > 0 and proc["current_burst_remaining"] > 0:
                            proc["state"] = "ready"
                            ready_queues[level].appendleft(proc)
                            logging.info(f"Process {proc['pid']} preempted by {new_p['pid']}")
                            executed = True
                            break
                    
                    # Break if preempted or if CPU burst completed
                    if executed or proc["remaining_cpu"] <= 0:
                        break
                
                if executed:
                    break
                
                # Check if process needs I/O
                if proc["remaining_cpu"] <= 0:
                    # Process has completed
                    proc["state"] = "finished"
                    proc["finish"] = clock
                    proc["turnaround_time"] = proc["finish"] - proc["arrival_time"]
                    proc["waiting_time"] = proc["turnaround_time"] - proc["burst_time"] - proc["io_time"]
                    finished.append(proc)
                    logging.info(f"Process {proc['pid']} finished at time {clock}")
                elif proc.get("io_burst", 0) > 0:
                    # Process needs I/O
                    proc["state"] = "io"
                    # Apply I/O variance
                    io_time = apply_variance(proc.get("io_burst", 0), proc.get("io_variance", 0))
                    proc["current_burst_remaining"] = io_time
                    logging.info(f"Process {proc['pid']} performing I/O for {io_time} units")
                    io_queue.append(proc)
                    proc["cpu_bursts_completed"] += 1
                else:
                    # No I/O needed, move to next queue
                    proc["state"] = "ready"
                    next_level = min(level + 1, 2)
                    proc["queue"] = next_level
                    ready_queues[next_level].append(proc)
                    proc["cpu_bursts_completed"] += 1
                    logging.info(f"Process {proc['pid']} moved to queue {next_level}")
                
                executed = True
                break
        
        if not executed:
            # If no process executed, system is idle
            clock += 1
            logging.info(f"CPU idle at time {clock}")
    
    return finished
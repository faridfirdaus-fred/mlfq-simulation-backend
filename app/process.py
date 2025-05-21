# process.py
from enum import Enum
from typing import List, Tuple, Optional

class ProcessState(Enum):
    NEW = "new"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    FINISHED = "finished"

class Process:
    def __init__(self, pid: str, arrival_time: int, burst_time: int, priority: int = 0, io_time: int = 0):
        self.pid = pid
        self.arrival_time = arrival_time
        self.burst_time = burst_time
        self.priority = priority
        
        # Original I/O time for the process's I/O bursts
        self.io_time = io_time 
        self.original_io_time = io_time 
        self.remaining_io_time = io_time # Remaining time for the current I/O burst

        # Simulator-specific attributes, will be re-initialized by MLFQSimulator
        self.state: ProcessState = ProcessState.NEW
        self.queue: int = -1 
        self.start_time: Optional[int] = None
        self.finish_time: Optional[int] = None
        self.waiting_time: int = 0
        self.turnaround_time: int = 0
        self.remaining_time: int = burst_time 
        self.context_switches: int = 0
        self.execution_history: List[Tuple[int, int]] = [] 
        self.queue_history: List[Tuple[int, int]] = [] 
        self.io_bursts_completed: int = 0
        self.cpu_bursts_completed: int = 0

        # This will be used for output, representing the original io_time
        self.io_time_output: int = io_time 

    def to_dict(self) -> dict:
        """Convert process object to dictionary for JSON output."""
        return {
            "pid": self.pid,
            "arrival_time": self.arrival_time,
            "burst_time": self.burst_time,
            "priority": self.priority,
            "io_time": self.io_time_output, # Use this for output
            "state": self.state.value,
            "queue": self.queue,
            "start_time": self.start_time,
            "finish_time": self.finish_time,
            "waiting_time": self.waiting_time,
            "turnaround_time": self.turnaround_time,
            "remaining_time": self.remaining_time,
            "context_switches": self.context_switches,
            "execution_history": self.execution_history,
            "queue_history": self.queue_history,
            "io_bursts_completed": self.io_bursts_completed,
            "cpu_bursts_completed": self.cpu_bursts_completed
        }
"""
Process class for MLFQ simulation.
Represents a process in the system with its properties and state.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from enum import Enum

class ProcessState(Enum):
    """Enum for process states"""
    NEW = "new"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    FINISHED = "finished"

@dataclass
class Process:
    """Represents a process in the MLFQ simulation"""
    pid: str
    arrival_time: int
    burst_time: int
    priority: int = 0
    io_time: int = 0
    state: ProcessState = ProcessState.NEW
    queue: int = 0
    start_time: Optional[int] = None
    finish_time: Optional[int] = None
    waiting_time: int = 0
    turnaround_time: int = 0
    remaining_time: int = 0
    context_switches: int = 0
    execution_history: List[Tuple[int, int]] = field(default_factory=list)
    queue_history: List[Tuple[int, int]] = field(default_factory=list)
    io_bursts_completed: int = 0
    cpu_bursts_completed: int = 0
    original_io_time: int = 0

    def __post_init__(self):
        """Initialize remaining time after instance creation"""
        self.remaining_time = self.burst_time
        self.original_io_time = self.io_time

    def to_dict(self) -> dict:
        """Convert process to dictionary for JSON serialization"""
        return {
            "pid": self.pid,
            "arrival_time": self.arrival_time,
            "burst_time": self.burst_time,
            "priority": self.priority,
            "io_time": self.io_time,
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

    @classmethod
    def from_dict(cls, data: dict) -> 'Process':
        """Create a Process instance from a dictionary"""
        process = cls(
            pid=data["pid"],
            arrival_time=data["arrival_time"],
            burst_time=data["burst_time"],
            priority=data.get("priority", 0),
            io_time=data.get("io_time", 0)
        )
        process.state = ProcessState(data.get("state", "new"))
        process.queue = data.get("queue", 0)
        process.start_time = data.get("start_time")
        process.finish_time = data.get("finish_time")
        process.waiting_time = data.get("waiting_time", 0)
        process.turnaround_time = data.get("turnaround_time", 0)
        process.remaining_time = data.get("remaining_time", process.burst_time)
        process.context_switches = data.get("context_switches", 0)
        process.execution_history = data.get("execution_history", [])
        process.queue_history = data.get("queue_history", [])
        process.io_bursts_completed = data.get("io_bursts_completed", 0)
        process.cpu_bursts_completed = data.get("cpu_bursts_completed", 0)
        process.original_io_time = data.get("io_time", 0)
        return process 
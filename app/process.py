# process.py
from enum import Enum
from typing import List, Tuple, Optional

# Enum untuk merepresentasikan status proses
class ProcessState(Enum):
    NEW = "new"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    FINISHED = "finished"

# Kelas utama untuk merepresentasikan sebuah proses
class Process:
    def __init__(self, pid: str, arrival_time: int, burst_time: int, priority: int = 0, io_time: int = 0):
        # Basic attributes
        self.pid = pid
        self.arrival_time = arrival_time
        self.burst_time = burst_time
        self.priority = priority
        self.io_time = io_time
        self.original_io_time = io_time
        self.remaining_io_time = io_time

        # Runtime attributes
        self.state = ProcessState.NEW
        # QueueLevel = nilai prioritas awal proses (sesuai permintaan)
        self.queue = priority  
        self.remaining_time = burst_time
        
        # Performance metrics
        self.start_time = None
        self.finish_time = None
        # Untuk perhitungan waiting time tradisional (waktu total di status READY)
        self.traditional_waiting_time = 0
        # Untuk model baru: WaitingTime = StartTime - ArrivalTime
        self.waiting_time = 0
        self.turnaround_time = 0
        self.context_switches = 0
        self.response_time = 0
        self.cpu_usage_time = 0
        
        # Tracking histories
        self.execution_history: List[Tuple[int, int]] = []
        self.queue_history: List[Tuple[int, int]] = []
        self.io_bursts_completed = 0
        self.cpu_bursts_completed = 0
        
        # Efficiency metrics
        self.cpu_efficiency = 0.0
        self.io_efficiency = 0.0
        self.waiting_ratio = 0.0
        
        # Untuk output
        self.io_time_output = io_time
    
    def calculate_derived_metrics(self):
        """Calculate derived metrics after simulation is complete"""
        if self.finish_time is not None:
            # Basic time metrics
            self.turnaround_time = self.finish_time - self.arrival_time
            
            if self.start_time is not None:
                # Wait time based on new model: StartTime - ArrivalTime
                self.waiting_time = self.start_time - self.arrival_time
                # Response time same as waiting time in this model
                self.response_time = self.waiting_time

                # Calculate CPU usage time from execution history
                self.cpu_usage_time = sum(end - start for start, end in self.execution_history)
                
                # Efficiency metrics
                if self.turnaround_time > 0:
                    self.cpu_efficiency = self.burst_time / self.turnaround_time
                    self.io_efficiency = self.original_io_time / self.turnaround_time
                    self.waiting_ratio = self.waiting_time / self.turnaround_time

    def to_dict(self) -> dict:
        """Convert process object to dictionary for output"""
        # Calculate derived metrics before outputting
        self.calculate_derived_metrics()
        
        return {
            "pid": self.pid,
            "arrival_time": self.arrival_time,
            "burst_time": self.burst_time,
            "priority": self.priority,
            "io_time": self.io_time_output,
            "state": self.state.value,
            "queue": self.queue,
            "start_time": self.start_time,
            "finish_time": self.finish_time,
            "waiting_time": self.waiting_time,  # Using new model: StartTime - ArrivalTime
            "traditional_waiting_time": self.traditional_waiting_time,  # Old model for reference
            "turnaround_time": self.turnaround_time,
            "response_time": self.response_time,
            "remaining_time": self.remaining_time,
            "context_switches": self.context_switches,
            "execution_history": self.execution_history,
            "queue_history": self.queue_history,
            "io_bursts_completed": self.io_bursts_completed,
            "cpu_bursts_completed": self.cpu_bursts_completed,
            "cpu_usage_time": self.cpu_usage_time,
            "cpu_efficiency": round(self.cpu_efficiency, 2),
            "io_efficiency": round(self.io_efficiency, 2),
            "waiting_ratio": round(self.waiting_ratio, 2)
        }
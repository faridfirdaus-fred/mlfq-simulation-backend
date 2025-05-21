"""
MLFQ Scheduler implementation.
Implements the Multi-Level Feedback Queue scheduling algorithm.
"""

from typing import List, Dict, Optional, Set
from collections import deque
from .process import Process, ProcessState

class MLFQSimulator:
    """Multi-Level Feedback Queue Scheduler implementation"""
    
    def __init__(
        self,
        processes: List[Process],
        num_queues: int = 3,
        time_slice: int = 2,
        boost_interval: int = 100,
        aging_threshold: int = 5
    ):
        """
        Initialize MLFQ Scheduler
        
        Args:
            processes: List of processes to schedule
            num_queues: Number of priority queues
            time_slice: Base time quantum for the highest priority queue
            boost_interval: Time interval for priority boost
            aging_threshold: Number of time units before aging occurs
        """
        self.processes = processes
        self.num_queues = num_queues
        self.time_slice = time_slice
        self.boost_interval = boost_interval
        self.aging_threshold = aging_threshold
        
        # Initialize queues (0 is highest priority)
        self.queues: List[deque[Process]] = [deque() for _ in range(num_queues)]
        self.current_time = 0
        self.current_process: Optional[Process] = None
        self.aging_counters: Dict[str, int] = {}
        self.io_processes: Dict[str, Process] = {}  # Track processes in I/O
        self.idle_time = 0
        
        # Initialize process states
        for process in self.processes:
            process.remaining_time = process.burst_time # This represents total CPU time remaining
            process.original_io_time = process.io_time  # Store original I/O time

    def _get_time_quantum(self, queue_level: int) -> int:
        """Get time quantum for a given queue level"""
        # Linear increase in time quantum for lower priority queues
        return self.time_slice * (queue_level + 1)
    
    def _add_to_queue(self, process: Process, queue_level: int) -> None:
        """Add process to specified queue and update its state"""
        process.queue = queue_level
        process.state = ProcessState.READY
        self.queues[queue_level].append(process)
        process.queue_history.append((self.current_time, queue_level))
    
    def _handle_arrivals(self) -> None:
        """Handle newly arrived processes"""
        for process in self.processes:
            if process.arrival_time <= self.current_time and process.state == ProcessState.NEW:
                self._add_to_queue(process, 0)  # New processes start in highest priority queue
                self._debug_log(f"Process {process.pid} arrived at time {self.current_time}")
    
    def _handle_aging(self) -> None:
        """Handle process aging"""
        for queue_idx in range(1, self.num_queues): # Start from queue 1 (second highest)
            aged_processes = []
            # Iterate over a copy to allow removal
            for process in list(self.queues[queue_idx]): 
                self.aging_counters[process.pid] = self.aging_counters.get(process.pid, 0) + 1
                if self.aging_counters[process.pid] >= self.aging_threshold:
                    aged_processes.append(process)
                    self.aging_counters[process.pid] = 0 # Reset aging counter after boost
            
            # Remove aged processes and add them to higher priority queue
            for process in aged_processes:
                if process in self.queues[queue_idx]: # Ensure it's still there
                    self.queues[queue_idx].remove(process)
                    self._add_to_queue(process, queue_idx - 1)
                    self._debug_log(f"Process {process.pid} aged, moved from queue {queue_idx} to {queue_idx - 1}")
    
    def _handle_priority_boost(self) -> None:
        """Handle priority boost for all processes"""
        if self.current_time > 0 and self.current_time % self.boost_interval == 0:
            self._debug_log(f"Priority Boost initiated at time {self.current_time}")
            # Move all processes from lower priority queues to highest priority queue
            for queue_idx in range(1, self.num_queues):
                while self.queues[queue_idx]:
                    process = self.queues[queue_idx].popleft()
                    self._add_to_queue(process, 0)
                    self._debug_log(f"Process {process.pid} boosted to queue 0.")
            # Also, if there's a current running process and it's not in queue 0, it should be preempted and boosted
            # This implementation assumes preemption by time quantum handles this for the running process
            # and a new process will be selected from Q0.
            # However, if it's simpler, you could re-add current_process to Q0 if not None and its queue is > 0
            if self.current_process and self.current_process.queue > 0:
                self._debug_log(f"Current process {self.current_process.pid} preempted by boost, moved to queue 0.")
                self._add_to_queue(self.current_process, 0)
                self.current_process = None # Force re-selection from Q0
    
    def _update_waiting_times(self) -> None:
        """Update waiting times for all ready processes"""
        for queue in self.queues:
            for process in queue:
                if process.state == ProcessState.READY:
                    process.waiting_time += 1
    
    def _handle_io_completion(self) -> None:
        """Handle I/O completion for processes"""
        completed_io = []
        for pid, process in list(self.io_processes.items()):
            # Decrement I/O time
            process.io_time -= 1
            if process.io_time <= 0:
                completed_io.append(pid)
                process.io_bursts_completed += 1
                
                # Reset I/O time for potential future I/O bursts if the process isn't fully finished
                process.io_time = process.original_io_time 
                
                # If a process has finished all its CPU work (remaining_time <= 0) AND its current I/O burst, it's truly finished.
                if process.remaining_time <= 0:
                    process.state = ProcessState.FINISHED
                    process.finish_time = self.current_time
                    process.turnaround_time = process.finish_time - process.arrival_time
                    self._debug_log(f"Process {process.pid} FINISHED after completing final I/O at time {self.current_time}")
                else:
                    # Process completed I/O and still has CPU time remaining. Goes back to highest priority queue.
                    self._add_to_queue(process, 0)
                    self._debug_log(f"Process {process.pid} completed I/O at time {self.current_time}, back to ready queue 0.")
        
        # Remove completed I/O processes from the tracking dictionary
        for pid in completed_io:
            del self.io_processes[pid]
    
    def simulate(self) -> None:
        """Run the MLFQ simulation"""
        max_iterations = 10000  # Increased iterations for potentially longer simulations
        iterations = 0
        
        self._debug_log(f"Starting simulation with {len(self.processes)} processes")
        
        while iterations < max_iterations:
            iterations += 1
            
            self._debug_log(f"\n[Time {self.current_time}] --- Iteration {iterations} ---")
            self._debug_log(f"Queue states: {[len(q) for q in self.queues]}, IO processes: {len(self.io_processes)}, Current Process: {self.current_process.pid if self.current_process else 'None'}")
            
            # Handle new arrivals
            self._handle_arrivals()
            
            # Handle aging
            self._handle_aging()
            
            # Handle priority boost
            self._handle_priority_boost()
            
            # Handle I/O completion (before selecting a new process, as I/O completion can make processes ready)
            self._handle_io_completion()
            
            # Update waiting times for all ready processes (those in queues)
            self._update_waiting_times()
            
            # Try to find next process to run if CPU is idle or current process finished its quantum/burst
            if self.current_process is None:
                process_selected_for_run = False
                for queue_idx, queue in enumerate(self.queues):
                    if queue: # If a queue is not empty
                        self.current_process = queue.popleft()
                        self.current_process.state = ProcessState.RUNNING
                        if self.current_process.start_time is None:
                            self.current_process.start_time = self.current_time
                        self.current_process.context_switches += 1
                        process_selected_for_run = True
                        self._debug_log(f"Selected {self.current_process.pid} from queue {queue_idx} to run.")
                        break # Found a process, exit loop
                
                if not process_selected_for_run:
                    # CPU is idle. Increment idle time and current time.
                    # This check is crucial: if no ready processes AND no I/O processes, we should terminate.
                    # Otherwise, we wait for arrivals or I/O completions.
                    if not any(p.state != ProcessState.FINISHED for p in self.processes) and len(self.io_processes) == 0:
                        # All processes finished or nothing left to do.
                        self._debug_log("No active processes or I/O pending. Terminating simulation.")
                        break
                    
                    self.idle_time += 1
                    self.current_time += 1
                    self._debug_log(f"CPU is idle. Current time advanced to {self.current_time}.")
                    continue # Nothing to execute in this iteration, go to next time step

            # Execute the current process (only if one was selected)
            if self.current_process:
                time_quantum = self._get_time_quantum(self.current_process.queue)
                execution_start = self.current_time
                
                # The execution amount is the minimum of time quantum and remaining total CPU time
                execution_duration = min(time_quantum, self.current_process.remaining_time)
                
                if execution_duration > 0: # Ensure we actually execute time
                    self.current_time += execution_duration
                    self.current_process.remaining_time -= execution_duration
                    
                    # Record execution history
                    self.current_process.execution_history.append((execution_start, self.current_time))
                    self.current_process.cpu_bursts_completed += 1 # Count a CPU burst/slice completion
                    
                    self._debug_log(f"Process {self.current_process.pid} ran from {execution_start} to {self.current_time}. Remaining CPU: {self.current_process.remaining_time}")

                    # Handle process completion or preemption
                    if self.current_process.remaining_time <= 0:
                        # Process has completed all its required CPU time (burst_time)
                        self._debug_log(f"Process {self.current_process.pid} completed ALL its CPU work.")
                        
                        if self.current_process.io_time > 0:
                            # It completed CPU and needs I/O. Move to BLOCKED state.
                            self.current_process.state = ProcessState.BLOCKED
                            self.io_processes[self.current_process.pid] = self.current_process
                            self._debug_log(f"Process {self.current_process.pid} blocked for I/O.")
                        else:
                            # It completed CPU and has no I/O. It's truly FINISHED.
                            self.current_process.state = ProcessState.FINISHED
                            self.current_process.finish_time = self.current_time
                            self.current_process.turnaround_time = (
                                self.current_process.finish_time - self.current_process.arrival_time
                            )
                            self._debug_log(f"Process {self.current_process.pid} FINISHED at {self.current_time}.")
                        
                        self.current_process = None # CPU is now free
                    else:
                        # Process was preempted by time quantum but still has CPU time remaining.
                        # Move to the next lower priority queue.
                        next_queue = min(self.current_process.queue + 1, self.num_queues - 1)
                        self._debug_log(f"Process {self.current_process.pid} preempted (quantum), moved to queue {next_queue}.")
                        self._add_to_queue(self.current_process, next_queue)
                        self.current_process = None # CPU is now free
                else:
                    # This case should ideally not happen if selection logic is correct,
                    # but if it does, it means a process with 0 remaining time was selected.
                    self._debug_log(f"Warning: Process {self.current_process.pid} selected but has 0 remaining_time. State: {self.current_process.state}. Skipping execution for this iteration.")
                    # It might be an edge case of an already finished process or one that just returned from I/O and has 0 CPU.
                    # Ensure it's marked finished if its total CPU time is done and I/O is done.
                    if self.current_process.remaining_time <=0 and self.current_process.io_time <=0 and self.current_process.state != ProcessState.FINISHED:
                        self.current_process.state = ProcessState.FINISHED
                        self.current_process.finish_time = self.current_time # Should be set at last useful event
                        self.current_process.turnaround_time = (
                            self.current_process.finish_time - self.current_process.arrival_time
                        )
                        self._debug_log(f"Process {self.current_process.pid} marked FINISHED at {self.current_time} due to 0 remaining time and no I/O.")
                    self.current_process = None # Clear for next selection

            # Check if all processes are finished or there's nothing more to do
            all_finished_true = all(p.state == ProcessState.FINISHED for p in self.processes)
            all_queues_empty_true = all(len(queue) == 0 for queue in self.queues)
            no_io_processes_true = len(self.io_processes) == 0
            
            if all_finished_true or (all_queues_empty_true and no_io_processes_true and self.current_process is None):
                self._debug_log(f"Simulation terminated at time {self.current_time}. All processes finished: {all_finished_true}, Queues empty: {all_queues_empty_true}, No I/O processes: {no_io_processes_true}, No current process: {self.current_process is None}")
                break

            # Safety check to prevent hangs (moved to end of loop for more complete info)
            if iterations >= max_iterations: # Check against actual max_iterations
                print(f"WARNING: Reached maximum iterations ({max_iterations}). Simulation may be stuck.")
                print(f"Current time: {self.current_time}")
                print(f"Processes states: {[(p.pid, p.state.value, p.remaining_time, p.io_time) for p in self.processes]}")
                print(f"Queue lengths: {[len(q) for q in self.queues]}")
                print(f"IO processes: {[(p.pid, p.io_time) for p in self.io_processes.values()]}")
                break # Ensure loop terminates

    def _debug_log(self, message: str) -> None:
        """Log debug messages"""
        # Uncomment the following line to enable debug logging
        print(f"[MLFQ DEBUG] {message}")
    
    def get_results(self) -> dict:
        """Get simulation results"""
        # Ensure that current_time is not zero before calculating CPU utilization to avoid division by zero
        cpu_utilization = 1 - (self.idle_time / self.current_time if self.current_time > 0 else 0)
        
        # Filter for finished processes to avoid division by zero if some processes are stuck
        finished_processes = [p for p in self.processes if p.state == ProcessState.FINISHED]
        
        avg_turnaround = sum(p.turnaround_time for p in finished_processes) / len(finished_processes) if finished_processes else 0
        avg_waiting = sum(p.waiting_time for p in finished_processes) / len(finished_processes) if finished_processes else 0
        
        # Calculate avg_response_time only for processes that actually started
        started_processes = [p for p in self.processes if p.start_time is not None]
        avg_response = sum(
            (p.start_time - p.arrival_time) for p in started_processes
        ) / len(started_processes) if started_processes else 0
        
        return {
            "processes": [process.to_dict() for process in self.processes],
            "metrics": {
                "avg_turnaround_time": avg_turnaround,
                "avg_waiting_time": avg_waiting,
                "avg_response_time": avg_response,
                "cpu_utilization": cpu_utilization,
                "total_time": self.current_time
            }
        }
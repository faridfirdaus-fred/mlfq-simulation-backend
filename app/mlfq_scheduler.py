from typing import List, Dict, Optional, Set
from collections import deque
from .process import Process, ProcessState # Pastikan Process diimpor dari file process.py Anda

class MLFQSimulator:
    """Multi-Level Feedback Queue Scheduler implementation with extended metrics"""
    
    def __init__(
        self,
        processes: List[Process], # Seharusnya List[ProcessInput] atau konversi di sini
        num_queues: int = 3,
        time_slice: int = 2,
        boost_interval: int = 100,
        aging_threshold: int = 5,
        debug: bool = True
    ):
        # Create copies of processes with reset simulation attributes
        self.processes: List[Process] = []
        for p_input in processes: # Asumsi p_input adalah objek dengan atribut yang diperlukan Process
            new_p = Process(
                pid=p_input.pid,
                arrival_time=p_input.arrival_time,
                burst_time=p_input.burst_time,
                priority=p_input.priority if hasattr(p_input, 'priority') else 0,
                io_time=p_input.io_time if hasattr(p_input, 'io_time') else 0
            )
            # Reset simulation attributes
            new_p.state = ProcessState.NEW
            # Set initial queue to process priority as per requirements
            new_p.queue = new_p.priority
            new_p.start_time = None
            new_p.finish_time = None
            new_p.traditional_waiting_time = 0
            new_p.waiting_time = 0
            new_p.turnaround_time = 0
            new_p.remaining_time = new_p.burst_time
            new_p.context_switches = 0
            new_p.execution_history = []
            new_p.queue_history = []
            new_p.io_bursts_completed = 0
            new_p.cpu_bursts_completed = 0
            new_p.remaining_io_time = new_p.io_time
            new_p.io_time_output = new_p.original_io_time

            self.processes.append(new_p)

        # Initialize MLFQ parameters
        self.num_queues = num_queues
        self.time_slice = time_slice
        self.boost_interval = boost_interval
        self.aging_threshold = aging_threshold
        self.debug = debug
        
        # Create queues for each priority level
        self.queues: List[deque[Process]] = [deque() for _ in range(num_queues)]
        self.current_time = 0
        self.current_process: Optional[Process] = None
        self.aging_counters: Dict[str, int] = {}
        self.io_processes: Dict[str, Process] = {} 
        self.idle_time = 0
        
        # Additional tracking for the requested metrics
        self.total_cpu_time = 0
        self.total_io_time = 0
        self.total_waiting_time = 0
        self.queue_distribution = {i: 0 for i in range(num_queues)}

    def _get_time_quantum(self, queue_level: int) -> int:
        """Calculate time quantum for specific queue level"""
        return self.time_slice * (queue_level + 1)
    
    def _add_to_queue(self, process: Process, queue_level: int) -> None:
        """Add a process to the specified queue level"""
        # Add to history if queue level changed
        if not process.queue_history or process.queue_history[-1][1] != queue_level:
            process.queue_history.append((self.current_time, queue_level))
        
        process.queue = queue_level
        process.state = ProcessState.READY
        process.time_entered_ready_state = self.current_time
        self.queues[queue_level].append(process)
        self.aging_counters[process.pid] = 0  # Reset aging counter

    def _handle_arrivals(self) -> None:
        """Handle processes arriving at current time"""
        # Sort by PID for deterministic behavior if arrival times are the same
        sorted_new_processes = sorted(
            [p for p in self.processes if p.arrival_time <= self.current_time and p.state == ProcessState.NEW],
            key=lambda x: x.pid
        )
        
        for process in sorted_new_processes:
            # Add to queue based on initial priority (as per requirements)
            initial_queue = min(process.priority, self.num_queues - 1)
            self._add_to_queue(process, initial_queue)
            self._debug_log(f"Process {process.pid} arrived at time {self.current_time}, added to queue {initial_queue} based on priority")

    def _handle_aging(self) -> None:
        """Handle aging (promote processes that wait too long)"""
        for queue_idx in range(1, self.num_queues):
            aged_processes = []
            
            for process in list(self.queues[queue_idx]):
                self.aging_counters[process.pid] = self.aging_counters.get(process.pid, 0) + 1
                
                if self.aging_counters[process.pid] >= self.aging_threshold:
                    aged_processes.append(process)
                    self._debug_log(f"Process {process.pid} aging counter: {self.aging_counters[process.pid]} (≥ {self.aging_threshold})")
            
            for process in aged_processes:
                if process in self.queues[queue_idx]:
                    self.queues[queue_idx].remove(process)
                    self._add_to_queue(process, queue_idx - 1) # Promosi ke antrian lebih tinggi
                    self._debug_log(f"Process {process.pid} aged, moved from queue {queue_idx} to {queue_idx - 1}")

    def _handle_priority_boost(self) -> None:
        """Handle priority boost (move all processes to highest priority queue)"""
        if self.current_time > 0 and self.current_time % self.boost_interval == 0:
            self._debug_log(f"Priority Boost initiated at time {self.current_time}")
            
            # Boost current process if not in top queue
            if self.current_process and self.current_process.queue > 0:
                self._debug_log(f"Current process {self.current_process.pid} preempted by boost, will be moved to queue 0.")
                # Kembalikan ke antrian asalnya dulu agar _add_to_queue bisa set time_entered_ready_state
                original_queue = self.current_process.queue
                self.current_process.state = ProcessState.READY
                # _add_to_queue akan dipanggil nanti untuk semua proses termasuk ini
                # Untuk sementara, kita tambahkan ke depan antrian asalnya
                self.queues[original_queue].appendleft(self.current_process)
                self.current_process = None 
                
                # Move all processes from lower queues to top queue
                for queue_idx in range(1, self.num_queues):
                    while self.queues[queue_idx]:
                        process = self.queues[queue_idx].popleft()
                        self._add_to_queue(process, 0)
                        self._debug_log(f"Process {process.pid} boosted to queue 0.")
                
                # Reset all aging counters after boost
                self.aging_counters.clear()

    def _update_waiting_times(self) -> None:
        """Update traditional waiting times for processes in READY state"""
        for queue in self.queues:
            for process in queue:
                if process.state == ProcessState.READY:
                    process.traditional_waiting_time += 1

    def _handle_io_completion(self) -> None:
        """Handle processes completing I/O operations"""
        completed_io = []
        
        self._debug_log(f"I/O processes at time {self.current_time}: "
                      f"{[(pid, p.pid, p.remaining_io_time) for pid, p in self.io_processes.items()]}")
        
        for pid, process in list(self.io_processes.items()):
            process.remaining_io_time -= 1
            if process.remaining_io_time <= 0:
                completed_io.append(pid)
                process.io_bursts_completed += 1
                self.total_io_time += process.original_io_time
                
                # Reset I/O time for next burst
                process.remaining_io_time = process.original_io_time
                
                if process.remaining_time <= 0:  # All CPU work is done
                    process.state = ProcessState.FINISHED
                    process.finish_time = self.current_time
                    process.turnaround_time = process.finish_time - process.arrival_time
                    self._debug_log(f"Process {process.pid} FINISHED at time {self.current_time} after completing final I/O.")
                else:
                    # Return to top queue if still has CPU work
                    self._add_to_queue(process, 0)
                    self._debug_log(f"Process {process.pid} completed I/O at time {self.current_time}, back to ready queue 0.")
        
        for pid in completed_io:
            del self.io_processes[pid]

    def simulate(self) -> None:
        """Run the MLFQ simulation"""
        max_iterations = 10000
        iterations = 0
        
        self._debug_log(f"Starting simulation with {len(self.processes)} processes")
        
        while iterations < max_iterations:
            iterations += 1
            self._debug_log(f"\n[Time {self.current_time}] --- Iteration {iterations} ---")
            self._debug_log(f"Queue states: {[len(q) for q in self.queues]}, "
                          f"I/O processes: {len(self.io_processes)}, "
                          f"Current Process: {self.current_process.pid if self.current_process else 'None'}")
            
            # 1. Handle new process arrivals
            self._handle_arrivals()
            
            # 2. Handle aging
            self._handle_aging()
            
            # 3. Handle priority boost
            self._handle_priority_boost()
            
            # 4. Handle I/O completion
            self._handle_io_completion()
            
            # 5. Update waiting times for READY processes
            self._update_waiting_times()
            
            # 6. Handle preemption or select next process
            preempted = False
            
            if self.current_process and self.current_process.state == ProcessState.RUNNING:
                current_proc_queue_level = self.current_process.queue
                highest_ready_queue_level = -1
                
                for q_idx in range(self.num_queues):
                    if self.queues[q_idx]:
                        highest_ready_queue_level = q_idx
                        break
                
                # Preempt if there's a process in a higher priority queue
                if highest_ready_queue_level != -1 and highest_ready_queue_level < current_proc_queue_level:
                    self._debug_log(f"Process {self.current_process.pid} (Q{current_proc_queue_level}) "
                                  f"preempted by higher priority process from Q{highest_ready_queue_level}.")
                    self.queues[current_proc_queue_level].appendleft(self.current_process)
                    self.current_process.state = ProcessState.READY
                    self.current_process = None
                    preempted = True

            # Select next process if none is running
            if self.current_process is None:
                process_selected = False
                
                for queue_idx, queue in enumerate(self.queues):
                    if queue:  # If queue is not empty
                        self.current_process = queue.popleft()
                        self.current_process.state = ProcessState.RUNNING
                        
                        # Set start time if first execution (for response time)
                        if self.current_process.start_time is None:
                            self.current_process.start_time = self.current_time
                        
                        self.current_process.context_switches += 1
                        process_selected = True
                        self._debug_log(f"Selected {self.current_process.pid} from queue {queue_idx} to run.")
                        break
                
                if not process_selected:
                    # CPU is idle, check if simulation can end
                    all_finished = all(p.state == ProcessState.FINISHED for p in self.processes)
                    no_io_pending = len(self.io_processes) == 0
                    
                    if all_finished and no_io_pending:
                        self._debug_log(f"All processes finished and no I/O pending. "
                                      f"Terminating simulation at current_time {self.current_time}.")
                        break
                    
                    # Advance time if CPU is idle
                    self.idle_time += 1
                    self.current_time += 1
                    self._debug_log(f"CPU is idle. Current time advanced to {self.current_time}.")
                    continue

            # 7. Execute current process
            if self.current_process:
                time_quantum = self._get_time_quantum(self.current_process.queue)
                execution_start_time_slice = self.current_time # Waktu mulai slice ini
                
                run_duration_this_slice = min(time_quantum, self.current_process.remaining_time)
                
                if execution_duration > 0:
                    # Update time and process state
                    self.current_time += execution_duration
                    self.current_process.remaining_time -= execution_duration
                    
                    # Record execution in history
                    self.current_process.execution_history.append((execution_start, self.current_time))
                    self.current_process.cpu_bursts_completed += 1
                    
                    # Update queue distribution statistics
                    self.queue_distribution[self.current_process.queue] += execution_duration
                    
                    # Update total CPU time
                    self.total_cpu_time += execution_duration
                    
                    self._debug_log(f"Process {self.current_process.pid} ran from {execution_start} to {self.current_time}. "
                                  f"Remaining CPU: {self.current_process.remaining_time}")
                    
                    if self.current_process.remaining_time <= 0:
                        self._debug_log(f"Process {self.current_process.pid} completed ALL its CPU work.")
                        
                        # Check if process needs I/O
                        if self.current_process.original_io_time > 0 and self.current_process.io_bursts_completed == 0:
                            self.current_process.state = ProcessState.BLOCKED
                            self.current_process.remaining_io_time = self.current_process.original_io_time # Set ulang durasi I/O
                            self.io_processes[self.current_process.pid] = self.current_process
                            self._debug_log(f"Process {self.current_process.pid} moved to blocked state for I/O "
                                          f"after CPU burst {self.current_process.cpu_bursts_completed}")
                        else:
                            # Process has completed all CPU and I/O
                            self.current_process.state = ProcessState.FINISHED
                            self.current_process.finish_time = self.current_time
                            self.current_process.turnaround_time = self.current_process.finish_time - self.current_process.arrival_time
                            self._debug_log(f"Process {self.current_process.pid} FINISHED at time {self.current_time} "
                                          f"after completing all CPU and required I/O.")
                        
                        self.current_process = None
                    else:
                        # If not finished, move to lower queue
                        next_queue = min(self.current_process.queue + 1, self.num_queues - 1)
                        self._add_to_queue(self.current_process, next_queue)
                        self._debug_log(f"Process {self.current_process.pid} preempted. Moving to queue {next_queue}")
                        self.current_process = None
                else:
                    # Handle case where process has no remaining time
                    self._debug_log(f"Warning: Process {self.current_process.pid} selected but has 0 remaining_time. "
                                  f"State: {self.current_process.state}. Skipping execution for this iteration.")
                    
                    if self.current_process.remaining_time <= 0 and self.current_process.remaining_io_time <= 0:
                        self.current_process.state = ProcessState.FINISHED
                        self.current_process.finish_time = self.current_time
                        self.current_process.turnaround_time = self.current_process.finish_time - self.current_process.arrival_time
                        self._debug_log(f"Process {self.current_process.pid} marked as finished at time {self.current_time}")
                    
                    self.current_process = None
            
            # Check if simulation can end
            if self._is_simulation_complete():
                self._debug_log(f"Final check: All processes finished. Simulation terminated at current_time {self.current_time}.")
                break
            
            # Safety check for infinite loops
            if iterations >= max_iterations:
                print(f"WARNING: Reached maximum iterations ({max_iterations}). Simulation may be stuck.")
                print(f"Current time: {self.current_time}")
                print(f"Process states: {[(p.pid, p.state.value) for p in self.processes]}")
                break
    
    def _is_simulation_complete(self) -> bool:
        """Check if the simulation has completed (all processes finished)"""
        all_finished = all(p.state == ProcessState.FINISHED for p in self.processes)
        all_queues_empty = all(len(queue) == 0 for queue in self.queues)
        no_io_processes = len(self.io_processes) == 0
        no_current_process = self.current_process is None
        
        return all_finished and all_queues_empty and no_io_processes and no_current_process

    def _debug_log(self, message: str) -> None:
        """Log debug messages if debug mode is enabled"""
        if self.debug:
            print(f"[MLFQ DEBUG] {message}")
    
    def get_results(self) -> dict:
        """Get simulation results with all required metrics"""
        # Calculate process-level metrics
        for process in self.processes:
            process.calculate_derived_metrics()
        
        # Calculate system-wide metrics
        finished_processes = [p for p in self.processes if p.state == ProcessState.FINISHED]
        started_processes = [p for p in self.processes if p.start_time is not None]
        
        # Calculate metrics according to the specified model
        avg_turnaround = sum(p.turnaround_time for p in finished_processes) / len(finished_processes) if finished_processes else 0
        avg_waiting = sum(p.waiting_time for p in finished_processes) / len(finished_processes) if finished_processes else 0
        avg_io_time = sum(p.original_io_time for p in finished_processes) / len(finished_processes) if finished_processes else 0
        
        # Calculate response time (same as waiting time in this model)
        avg_response = avg_waiting
        
        # CPU utilization according to the specified formula
        cpu_utilization = self.total_cpu_time / self.current_time if self.current_time > 0 else 0
        
        # Throughput calculation
        throughput = len(finished_processes) / self.current_time if self.current_time > 0 else 0
        
        # Calculate total waiting time (Sum of StartTime - ArrivalTime for all processes)
        self.total_waiting_time = sum(p.waiting_time for p in started_processes) if started_processes else 0
        
        return {
            "processes": [process.to_dict() for process in self.processes],
            "metrics": {
                "avg_turnaround_time": round(avg_turnaround, 2),
                "avg_waiting_time": round(avg_waiting, 2),
                "avg_response_time": round(avg_response, 2),
                "avg_io_time": round(avg_io_time, 2),
                "cpu_utilization": round(cpu_utilization, 2),
                "throughput": round(throughput, 4),
                "queue_distribution": self.queue_distribution,
                "total_cpu_time": self.total_cpu_time,
                "total_io_time": self.total_io_time,
                "total_waiting_time": self.total_waiting_time,
                "total_time": self.current_time
            }
        }
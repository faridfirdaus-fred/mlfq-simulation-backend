# mlfq_scheduler.py
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
        # Membuat salinan proses dan reset semua atribut simulasi
        self.processes: List[Process] = []
        for p_input in processes:
            new_p = Process(
                pid=p_input.pid,
                arrival_time=p_input.arrival_time,
                burst_time=p_input.burst_time,
                priority=p_input.priority,
                io_time=p_input.io_time
            )
            # Reset atribut simulasi
            new_p.state = ProcessState.NEW
            new_p.queue = -1
            new_p.start_time = None
            new_p.finish_time = None
            new_p.waiting_time = 0
            new_p.turnaround_time = 0
            new_p.remaining_time = new_p.burst_time
            new_p.context_switches = 0
            new_p.execution_history = []
            new_p.queue_history = []
            new_p.io_bursts_completed = 0
            new_p.cpu_bursts_completed = 0
            new_p.remaining_io_time = new_p.io_time # Reset waktu IO
            new_p.io_time_output = new_p.original_io_time # Untuk output

            self.processes.append(new_p)

        # Inisialisasi parameter MLFQ
        self.num_queues = num_queues
        self.time_slice = time_slice
        self.boost_interval = boost_interval
        self.aging_threshold = aging_threshold
        
        # Membuat antrian untuk setiap level prioritas
        self.queues: List[deque[Process]] = [deque() for _ in range(num_queues)]
        self.current_time = 0
        self.current_process: Optional[Process] = None
        self.aging_counters: Dict[str, int] = {}
        self.io_processes: Dict[str, Process] = {} 
        self.idle_time = 0

    def _get_time_quantum(self, queue_level: int) -> int:
        """Menghitung time quantum untuk level queue tertentu"""
        return self.time_slice * (queue_level + 1)
    
    def _add_to_queue(self, process: Process, queue_level: int) -> None:
        """Menambahkan proses ke queue tertentu dan update state-nya"""
        # Tambahkan ke history jika level queue berubah
        if not process.queue_history or process.queue_history[-1][1] != queue_level:
            process.queue_history.append((self.current_time, queue_level))
        process.queue = queue_level
        process.state = ProcessState.READY
        self.queues[queue_level].append(process)
        self.aging_counters[process.pid] = 0 # Reset aging counter

    def _handle_arrivals(self) -> None:
        """Menangani proses yang baru datang"""
        # Urutkan berdasarkan PID untuk deterministik jika waktu datang sama
        sorted_new_processes = sorted([p for p in self.processes if p.arrival_time <= self.current_time and p.state == ProcessState.NEW], key=lambda x: x.pid)
        for process in sorted_new_processes:
            self._add_to_queue(process, 0) # Proses baru masuk ke queue prioritas tertinggi
            self._debug_log(f"Process {process.pid} arrived at time {self.current_time}")
    
    def _handle_aging(self) -> None:
        """Menangani aging (promosi proses yang terlalu lama menunggu)"""
        for queue_idx in range(1, self.num_queues):
            aged_processes_to_promote = []
            for process in list(self.queues[queue_idx]): # Copy agar aman saat modifikasi
                self.aging_counters[process.pid] = self.aging_counters.get(process.pid, 0) + 1
                if self.aging_counters[process.pid] >= self.aging_threshold:
                    aged_processes_to_promote.append(process)
                    self._debug_log(f"Process {process.pid} aging counter: {self.aging_counters[process.pid]} (>= {self.aging_threshold})")
            
            for process in aged_processes_to_promote:
                # Pastikan proses masih ada di queue sebelum dipromosikan
                if process in self.queues[queue_idx]: 
                    self.queues[queue_idx].remove(process)
                    self._add_to_queue(process, queue_idx - 1)
                    self._debug_log(f"Process {process.pid} aged, moved from queue {queue_idx} to {queue_idx - 1}")
    
    def _handle_priority_boost(self) -> None:
        """Menangani priority boost (semua proses kembali ke queue tertinggi)"""
        if self.current_time > 0 and self.current_time % self.boost_interval == 0:
            self._debug_log(f"Priority Boost initiated at time {self.current_time}")
            
            # Boost proses yang sedang berjalan jika bukan di Q0
            if self.current_process and self.current_process.queue > 0:
                self._debug_log(f"Current process {self.current_process.pid} preempted by boost, moved to queue 0.")
                self.current_process.state = ProcessState.READY 
                self._add_to_queue(self.current_process, 0) 
                self.current_process = None 

            # Pindahkan semua proses dari queue bawah ke queue 0
            for queue_idx in range(1, self.num_queues):
                while self.queues[queue_idx]:
                    process = self.queues[queue_idx].popleft()
                    self._add_to_queue(process, 0) 
                    self._debug_log(f"Process {process.pid} boosted to queue 0.")
            
            # Reset aging counter setelah boost
            self.aging_counters.clear() 

    def _update_waiting_times(self) -> None:
        """Update waktu tunggu semua proses yang READY"""
        for queue in self.queues:
            for process in queue:
                if process.state == ProcessState.READY:
                    process.waiting_time += 1
    
    def _handle_io_completion(self) -> None:
        """Menangani proses yang selesai I/O"""
        completed_io = []
        
        self._debug_log(f"I/O processes at time {self.current_time}: {[(pid, process.pid, process.remaining_io_time) for pid, process in self.io_processes.items()]}")
        
        for pid, process in list(self.io_processes.items()): # Copy agar aman
            process.remaining_io_time -= 1
            self._debug_log(f"Process {process.pid} I/O progress: {process.remaining_io_time} remaining after decrement")
            
            if process.remaining_io_time <= 0:
                completed_io.append(pid)
                process.io_bursts_completed += 1
                
                # Reset waktu IO untuk burst berikutnya (jika ada)
                process.remaining_io_time = process.original_io_time 
                
                # Jika CPU sudah selesai, set proses ke FINISHED
                if process.remaining_time <= 0: # Semua CPU selesai
                    if process.finish_time is None: # Pastikan belum di-set
                        process.state = ProcessState.FINISHED
                        process.finish_time = self.current_time
                        process.turnaround_time = process.finish_time - process.arrival_time
                        self._debug_log(f"Process {process.pid} FINISHED at time {self.current_time} after completing final I/O.")
                else:
                    # Jika masih ada CPU, proses kembali ke queue 0
                    self._add_to_queue(process, 0)
                    self._debug_log(f"Process {process.pid} completed I/O at time {self.current_time}, back to ready queue 0.")
        
        for pid in completed_io:
            del self.io_processes[pid]
    
    def simulate(self) -> None:
        """Menjalankan simulasi MLFQ"""
        max_iterations = 10000 
        iterations = 0
        
        self._debug_log(f"Starting simulation with {len(self.processes)} processes")
        
        while iterations < max_iterations:
            iterations += 1
            
            self._debug_log(f"\n[Time {self.current_time}] --- Iteration {iterations} ---")
            self._debug_log(f"Queue states: {[len(q) for q in self.queues]}, IO processes: {len(self.io_processes)}, Current Process: {self.current_process.pid if self.current_process else 'None'}")
            
            # 1. Tangani proses yang baru datang
            self._handle_arrivals()
            
            # 2. Aging (promosi proses yang terlalu lama menunggu)
            self._handle_aging()
            
            # 3. Priority boost (reset prioritas proses)
            self._handle_priority_boost()
            
            # 4. Selesaikan proses I/O jika ada yang selesai
            self._handle_io_completion()
            
            # 5. Update waktu tunggu proses yang READY
            self._update_waiting_times()
            
            # 6. Pilih proses berikutnya untuk dijalankan atau preemption
            preempted = False
            if self.current_process and self.current_process.state == ProcessState.RUNNING:
                current_proc_queue_level = self.current_process.queue
                highest_ready_queue_level = -1
                for q_idx in range(self.num_queues):
                    if self.queues[q_idx]:
                        highest_ready_queue_level = q_idx
                        break
                
                # Preempt jika ada proses di queue lebih tinggi
                if highest_ready_queue_level != -1 and highest_ready_queue_level < current_proc_queue_level:
                    self._debug_log(f"Process {self.current_process.pid} (Q{current_proc_queue_level}) preempted by higher priority process from Q{highest_ready_queue_level}.")
                    self.queues[current_proc_queue_level].appendleft(self.current_process)
                    self.current_process.state = ProcessState.READY
                    self.current_process = None
                    preempted = True

            # Pilih proses berikutnya jika tidak ada yang berjalan
            if self.current_process is None and not preempted:
                process_selected_for_run = False
                for queue_idx, queue in enumerate(self.queues):
                    if queue: # Jika queue tidak kosong
                        self.current_process = queue.popleft()
                        self.current_process.state = ProcessState.RUNNING
                        if self.current_process.start_time is None:
                            self.current_process.start_time = self.current_time
                        self.current_process.context_switches += 1
                        process_selected_for_run = True
                        self._debug_log(f"Selected {self.current_process.pid} from queue {queue_idx} to run.")
                        break
                
                if not process_selected_for_run:
                    # CPU idle, cek apakah simulasi selesai
                    all_finished_at_current_time = all(p.state == ProcessState.FINISHED for p in self.processes)
                    no_io_processes_left = len(self.io_processes) == 0
                    
                    if all_finished_at_current_time and no_io_processes_left:
                        self._debug_log(f"All processes finished and no I/O pending. Terminating simulation at current_time {self.current_time}.")
                        break 

                    self.idle_time += 1
                    self.current_time += 1
                    self._debug_log(f"CPU is idle. Current time advanced to {self.current_time}.")
                    continue 

            # 7. Eksekusi proses yang sedang berjalan
            if self.current_process:
                time_quantum = self._get_time_quantum(self.current_process.queue)
                execution_start = self.current_time
                
                execution_duration = min(time_quantum, self.current_process.remaining_time)
                
                if execution_duration > 0: 
                    self.current_time += execution_duration
                    self.current_process.remaining_time -= execution_duration
                    
                    self.current_process.execution_history.append((execution_start, self.current_time))
                    self.current_process.cpu_bursts_completed += 1
                    
                    self._debug_log(f"Process {self.current_process.pid} ran from {execution_start} to {self.current_time}. Remaining CPU: {self.current_process.remaining_time}")

                    if self.current_process.remaining_time <= 0:
                        self._debug_log(f"Process {self.current_process.pid} completed ALL its CPU work.")
                        
                        # Jika proses butuh I/O setelah CPU burst
                        if self.current_process.original_io_time > 0 and self.current_process.io_bursts_completed == 0:
                            self.current_process.state = ProcessState.BLOCKED
                            self.io_processes[self.current_process.pid] = self.current_process
                            self._debug_log(f"Process {self.current_process.pid} moved to blocked state for I/O after CPU burst {self.current_process.cpu_bursts_completed}")
                        else:
                            # Proses selesai semua CPU dan I/O
                            if self.current_process.finish_time is None: 
                                self.current_process.state = ProcessState.FINISHED
                                self.current_process.finish_time = self.current_time
                                self.current_process.turnaround_time = self.current_process.finish_time - self.current_process.arrival_time
                                self._debug_log(f"Process {self.current_process.pid} FINISHED at time {self.current_time} after completing all CPU and all required I/O.")
                        
                        self.current_process = None  
                    else:
                        # Jika belum selesai, turunkan ke queue lebih rendah
                        next_queue = min(self.current_process.queue + 1, self.num_queues - 1)
                        self._add_to_queue(self.current_process, next_queue)
                        self._debug_log(f"Process {self.current_process.pid} preempted. Moving to queue {next_queue}")
                        self.current_process = None 
                else:
                    # Jika proses terpilih tapi tidak punya waktu sisa
                    self._debug_log(f"Warning: Process {self.current_process.pid} selected but has 0 remaining_time. State: {self.current_process.state}. Skipping execution for this iteration.")
                    if self.current_process.remaining_time <= 0 and self.current_process.remaining_io_time <= 0 and self.current_process.state != ProcessState.FINISHED:
                        if self.current_process.finish_time is None:
                            self.current_process.state = ProcessState.FINISHED
                            self.current_process.finish_time = self.current_time
                            self.current_process.turnaround_time = self.current_process.finish_time - self.current_process.arrival_time
                            self._debug_log(f"Process {self.current_process.pid} marked as finished at time {self.current_time}")
                    self.current_process = None 

            # Cek akhir apakah simulasi bisa dihentikan
            all_finished_true = all(p.state == ProcessState.FINISHED for p in self.processes)
            all_queues_empty_true = all(len(queue) == 0 for queue in self.queues)
            no_io_processes_true = len(self.io_processes) == 0
            
            if all_finished_true and all_queues_empty_true and no_io_processes_true and self.current_process is None:
                self._debug_log(f"Final check: All processes finished. Simulation terminated at current_time {self.current_time}.")
                self._debug_log(f"Process states at termination: {[(p.pid, p.state.value, p.remaining_time, p.remaining_io_time, p.finish_time) for p in self.processes]}")
                self._debug_log(f"IO processes at termination: {[(pid, p.remaining_io_time) for pid, p in self.io_processes.items()]}")
                break

            if iterations >= max_iterations:
                print(f"WARNING: Reached maximum iterations ({max_iterations}). Simulation may be stuck.")
                print(f"Current time: {self.current_time}")
                print(f"Processes states: {[(p.pid, p.state.value, p.remaining_time, p.remaining_io_time, p.finish_time) for p in self.processes]}")
                print(f"Queue lengths: {[len(q) for q in self.queues]}")
                print(f"IO processes: {[(p.pid, p.remaining_io_time) for p in self.io_processes.values()]}")
                break

    def _debug_log(self, message: str) -> None:
        """Log debug messages"""
        debug_mode = True 
        if debug_mode:
            print(f"[MLFQ DEBUG] {message}")
    
    def get_results(self) -> dict:
        """Mengambil hasil simulasi"""
        cpu_utilization = 1 - (self.idle_time / self.current_time if self.current_time > 0 else 0)
        
        finished_processes = [p for p in self.processes if p.state == ProcessState.FINISHED]
        
        avg_turnaround = sum(p.turnaround_time for p in finished_processes) / len(finished_processes) if finished_processes else 0
        avg_waiting = sum(p.waiting_time for p in finished_processes) / len(finished_processes) if finished_processes else 0
        
        started_processes = [p for p in self.processes if p.start_time is not None]
        avg_response = sum(
            (p.start_time - p.arrival_time) for p in started_processes
        ) / len(started_processes) if started_processes else 0
        
        # Pastikan io_time_output sudah di-set untuk semua proses
        for p in self.processes:
            p.io_time_output = p.original_io_time 

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

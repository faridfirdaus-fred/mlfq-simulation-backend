# mlfq_scheduler.py
"""
MLFQ Scheduler implementation.
Implements the Multi-Level Feedback Queue scheduling algorithm.
"""

from typing import List, Dict, Optional, Set
from collections import deque
from .process import Process, ProcessState # Pastikan Process diimpor dari file process.py Anda

class MLFQSimulator:
    """Multi-Level Feedback Queue Scheduler implementation"""
    
    def __init__(
        self,
        processes: List[Process], # Seharusnya List[ProcessInput] atau konversi di sini
        num_queues: int = 3,
        time_slice: int = 2,
        boost_interval: int = 100,
        aging_threshold: int = 5
    ):
        self.processes: List[Process] = []
        for p_input in processes: # Asumsi p_input adalah objek dengan atribut yang diperlukan Process
            new_p = Process(
                pid=p_input.pid,
                arrival_time=p_input.arrival_time,
                burst_time=p_input.burst_time,
                priority=p_input.priority if hasattr(p_input, 'priority') else 0,
                io_time=p_input.io_time if hasattr(p_input, 'io_time') else 0
            )
            # Reset atribut simulasi
            new_p.state = ProcessState.NEW
            new_p.queue = -1
            new_p.start_time = None
            new_p.finish_time = None
            new_p.waiting_time = 0 # Inisialisasi waiting_time
            new_p.turnaround_time = 0
            new_p.remaining_time = new_p.burst_time
            new_p.context_switches = 0
            new_p.execution_history = []
            new_p.queue_history = []
            new_p.io_bursts_completed = 0
            new_p.cpu_bursts_completed = 0
            new_p.remaining_io_time = new_p.original_io_time
            new_p.io_time_output = new_p.original_io_time
            
            # --- PERUBAHAN DIMULAI DI SINI ---
            new_p.time_entered_ready_state = None # Inisialisasi atribut baru
            # --- PERUBAHAN SELESAI DI SINI ---
            
            self.processes.append(new_p)

        self.num_queues = num_queues
        self.time_slice = time_slice
        self.boost_interval = boost_interval
        self.aging_threshold = aging_threshold
        
        self.queues: List[deque[Process]] = [deque() for _ in range(num_queues)]
        self.current_time = 0
        self.current_process: Optional[Process] = None
        self.aging_counters: Dict[str, int] = {}
        self.io_processes: Dict[str, Process] = {} 
        self.idle_time = 0

    def _get_time_quantum(self, queue_level: int) -> int:
        return self.time_slice * (queue_level + 1)
    
    def _add_to_queue(self, process: Process, queue_level: int) -> None:
        if not process.queue_history or process.queue_history[-1][1] != queue_level:
            process.queue_history.append((self.current_time, queue_level))
        process.queue = queue_level
        process.state = ProcessState.READY
        
        # --- PERUBAHAN DIMULAI DI SINI ---
        # Catat waktu ketika proses masuk ke state READY
        process.time_entered_ready_state = self.current_time
        # --- PERUBAHAN SELESAI DI SINI ---
        
        self.queues[queue_level].append(process)
        self.aging_counters[process.pid] = 0

    def _handle_arrivals(self) -> None:
        sorted_new_processes = sorted([p for p in self.processes if p.arrival_time <= self.current_time and p.state == ProcessState.NEW], key=lambda x: x.pid)
        for process in sorted_new_processes:
            # --- PERUBAHAN DIMULAI DI SINI ---
            # Jika proses baru tiba, waktu masuk ready state juga adalah waktu tibanya
            # Namun, _add_to_queue akan mengesetnya ke self.current_time saat itu,
            # yang mana sudah tepat jika ia langsung masuk antrian.
            # Jika ada logika khusus untuk arrival_time vs current_time untuk waiting time awal,
            # bisa dipertimbangkan di sini, tapi _add_to_queue sudah cukup.
            # --- PERUBAHAN SELESAI DI SINI ---
            self._add_to_queue(process, 0)
            self._debug_log(f"Process {process.pid} arrived at time {self.current_time}, added to Q0.")
    
    def _handle_aging(self) -> None:
        for queue_idx in range(1, self.num_queues):
            aged_processes_to_promote = []
            # Iterasi pada salinan list untuk modifikasi aman
            for process in list(self.queues[queue_idx]): 
                # --- PERUBAHAN DIMULAI DI SINI ---
                # Logika aging counter perlu hati-hati agar tidak salah hitung
                # Jika proses sedang tidak menunggu (misal baru kembali dari I/O dan belum dieksekusi)
                # aging counter mungkin tidak relevan, atau perlu di-reset saat dieksekusi.
                # Untuk saat ini, kita biarkan logika aging counter Anda,
                # karena fokus utama adalah waiting time.
                # --- PERUBAHAN SELESAI DI SINI ---
                self.aging_counters[process.pid] = self.aging_counters.get(process.pid, 0) + 1 # Ini mungkin perlu disesuaikan
                if self.aging_counters[process.pid] >= self.aging_threshold:
                    aged_processes_to_promote.append(process)
                    self._debug_log(f"Process {process.pid} aging counter: {self.aging_counters[process.pid]} (>= {self.aging_threshold})")
            
            for process in aged_processes_to_promote:
                if process in self.queues[queue_idx]: 
                    self.queues[queue_idx].remove(process)
                    self._add_to_queue(process, queue_idx - 1) # Promosi ke antrian lebih tinggi
                    self._debug_log(f"Process {process.pid} aged, moved from queue {queue_idx} to {queue_idx - 1}")
    
    def _handle_priority_boost(self) -> None:
        if self.current_time > 0 and self.current_time % self.boost_interval == 0:
            self._debug_log(f"Priority Boost initiated at time {self.current_time}")
            
            if self.current_process and self.current_process.queue > 0:
                self._debug_log(f"Current process {self.current_process.pid} preempted by boost, will be moved to queue 0.")
                # Kembalikan ke antrian asalnya dulu agar _add_to_queue bisa set time_entered_ready_state
                original_queue = self.current_process.queue
                self.current_process.state = ProcessState.READY
                # _add_to_queue akan dipanggil nanti untuk semua proses termasuk ini
                # Untuk sementara, kita tambahkan ke depan antrian asalnya
                self.queues[original_queue].appendleft(self.current_process)
                self.current_process = None 

            # Kumpulkan semua proses dari antrian bawah
            processes_to_boost = []
            for queue_idx in range(self.num_queues): # Termasuk Q0 untuk reset aging
                while self.queues[queue_idx]:
                    processes_to_boost.append(self.queues[queue_idx].popleft())
            
            # Tambahkan kembali semua proses ke Q0
            for process in processes_to_boost:
                self._add_to_queue(process, 0) 
                self._debug_log(f"Process {process.pid} boosted/re-added to queue 0.")
            
            self.aging_counters.clear() 

    # --- PERUBAHAN DIMULAI DI SINI ---
    # Metode _update_waiting_times() DIHAPUS karena tidak akurat
    # def _update_waiting_times(self) -> None:
    #     """Update waktu tunggu semua proses yang READY"""
    #     for queue in self.queues:
    #         for process in queue:
    #             if process.state == ProcessState.READY:
    #                 process.waiting_time += 1
    # --- PERUBAHAN SELESAI DI SINI ---
    
    def _handle_io_completion(self) -> None:
        completed_io = []
        for pid, process in list(self.io_processes.items()):
            process.remaining_io_time -= 1
            if process.remaining_io_time <= 0:
                completed_io.append(pid)
                process.io_bursts_completed += 1
                process.remaining_io_time = process.original_io_time 
                if process.remaining_time <= 0:
                    if process.finish_time is None:
                        process.state = ProcessState.FINISHED
                        process.finish_time = self.current_time
                        process.turnaround_time = process.finish_time - process.arrival_time
                        self._debug_log(f"Process {process.pid} FINISHED at {self.current_time} after final I/O.")
                else:
                    self._add_to_queue(process, 0) # Kembali ke Q0 setelah I/O
                    self._debug_log(f"Process {process.pid} completed I/O at {self.current_time}, back to Q0.")
        for pid in completed_io:
            del self.io_processes[pid]
    
    def simulate(self) -> None:
        max_iterations = 10000 
        iterations = 0
        
        self._debug_log(f"Starting simulation with {len(self.processes)} processes")
        
        while iterations < max_iterations:
            iterations += 1
            self._debug_log(f"\n[Time {self.current_time}] --- Iteration {iterations} ---")
            
            self._handle_arrivals()
            self._handle_aging() # Panggil sebelum boost agar aging diproses dulu
            self._handle_priority_boost() # Fix: Added missing underscore
            self._handle_io_completion()
            
            # --- PERUBAHAN DIMULAI DI SINI ---
            # Panggilan ke _update_waiting_times() DIHAPUS
            # --- PERUBAHAN SELESAI DI SINI ---
            
            preempted_for_higher_priority = False
            if self.current_process and self.current_process.state == ProcessState.RUNNING:
                current_proc_queue_level = self.current_process.queue
                highest_ready_queue_level = -1
                for q_idx in range(current_proc_queue_level): # Hanya cek antrian yang LEBIH TINGGI
                    if self.queues[q_idx]:
                        highest_ready_queue_level = q_idx
                        break
                
                if highest_ready_queue_level != -1: # Ada proses di antrian lebih tinggi
                    self._debug_log(f"Process {self.current_process.pid} (Q{current_proc_queue_level}) preempted by higher priority process from Q{highest_ready_queue_level}.")
                    # Kembalikan current_process ke antriannya dan set state READY
                    # _add_to_queue akan mencatat time_entered_ready_state
                    self._add_to_queue(self.current_process, current_proc_queue_level) 
                    self.current_process = None
                    preempted_for_higher_priority = True

            if self.current_process is None: # Jika tidak ada proses berjalan atau baru saja di-preempt
                process_selected_this_cycle = False
                for queue_idx in range(self.num_queues):
                    if self.queues[queue_idx]:
                        self.current_process = self.queues[queue_idx].popleft()
                        
                        # --- PERUBAHAN DIMULAI DI SINI ---
                        # Hitung waiting time saat proses dipilih untuk RUNNING
                        if self.current_process.time_entered_ready_state is not None:
                            wait_this_segment = self.current_time - self.current_process.time_entered_ready_state
                            if wait_this_segment > 0: # Hanya jika benar-benar menunggu
                                self.current_process.waiting_time += wait_this_segment
                            # Reset agar tidak dihitung ganda jika proses kembali ke ready state nanti
                            self.current_process.time_entered_ready_state = None 
                        # --- PERUBAHAN SELESAI DI SINI ---

                        self.current_process.state = ProcessState.RUNNING
                        if self.current_process.start_time is None:
                            self.current_process.start_time = self.current_time
                        self.current_process.context_switches += 1
                        self._debug_log(f"Selected {self.current_process.pid} from queue {queue_idx} to run at time {self.current_time}. WT accumulated: {self.current_process.waiting_time}")
                        process_selected_this_cycle = True
                        break
                
                if not process_selected_this_cycle: # Tidak ada proses di semua antrian
                    if all(p.state == ProcessState.FINISHED for p in self.processes) and not self.io_processes:
                        self._debug_log(f"All processes finished. Terminating at time {self.current_time}.")
                        break 
                    self.idle_time += 1
                    self.current_time += 1 # Majukan waktu jika CPU idle
                    self._debug_log(f"CPU is idle. Time advanced to {self.current_time}.")
                    continue # Lanjut ke iterasi berikutnya

            if self.current_process: # Jika ada proses yang berjalan
                time_quantum = self._get_time_quantum(self.current_process.queue)
                execution_start_time_slice = self.current_time # Waktu mulai slice ini
                
                run_duration_this_slice = min(time_quantum, self.current_process.remaining_time)
                
                if run_duration_this_slice > 0:
                    # Log sebelum eksekusi
                    self.current_process.execution_history.append((execution_start_time_slice, execution_start_time_slice + run_duration_this_slice))
                    
                    # Majukan waktu sejumlah durasi eksekusi slice ini
                    self.current_time += run_duration_this_slice
                    self.current_process.remaining_time -= run_duration_this_slice
                    
                    # Tidak ada cpu_bursts_completed di sini, itu dihitung saat I/O atau finish

                    self._debug_log(f"Process {self.current_process.pid} ran from {execution_start_time_slice} to {self.current_time}. Remaining CPU: {self.current_process.remaining_time}")

                    if self.current_process.remaining_time <= 0: # Proses selesai semua CPU burst
                        self.current_process.cpu_bursts_completed +=1 # Anggap 1 burst besar selesai
                        self._debug_log(f"Process {self.current_process.pid} completed its CPU burst(s).")
                        
                        if self.current_process.original_io_time > 0 and self.current_process.io_bursts_completed == 0 : # Jika ada I/O dan belum dilakukan
                            self.current_process.state = ProcessState.BLOCKED
                            self.current_process.remaining_io_time = self.current_process.original_io_time # Set ulang durasi I/O
                            self.io_processes[self.current_process.pid] = self.current_process
                            self._debug_log(f"Process {self.current_process.pid} moved to BLOCKED for I/O.")
                        else: # Tidak ada I/O atau I/O sudah selesai
                            if self.current_process.finish_time is None:
                                self.current_process.state = ProcessState.FINISHED
                                self.current_process.finish_time = self.current_time
                                self.current_process.turnaround_time = self.current_process.finish_time - self.current_process.arrival_time
                                self._debug_log(f"Process {self.current_process.pid} FINISHED at time {self.current_time}.")
                        self.current_process = None
                    
                    else: # Quantum habis, proses belum selesai, tidak ada I/O segera
                        next_queue = min(self.current_process.queue + 1, self.num_queues - 1)
                        self._add_to_queue(self.current_process, next_queue)
                        self._debug_log(f"Process {self.current_process.pid} time slice expired. Moving to queue {next_queue}")
                        self.current_process = None 
                else: # run_duration_this_slice <= 0, bisa terjadi jika remaining_time sudah 0 tapi belum di-flag FINISHED
                    self._debug_log(f"Process {self.current_process.pid} selected but has 0 or less remaining CPU time ({self.current_process.remaining_time}). Forcing finish check.")
                    if self.current_process.remaining_time <= 0 and self.current_process.state != ProcessState.FINISHED :
                         if self.current_process.original_io_time > 0 and self.current_process.io_bursts_completed == 0 :
                            self.current_process.state = ProcessState.BLOCKED
                            self.current_process.remaining_io_time = self.current_process.original_io_time
                            self.io_processes[self.current_process.pid] = self.current_process
                            self._debug_log(f"Process {self.current_process.pid} with 0 CPU remaining moved to BLOCKED for I/O.")
                         else:
                            if self.current_process.finish_time is None:
                                self.current_process.state = ProcessState.FINISHED
                                self.current_process.finish_time = self.current_time
                                self.current_process.turnaround_time = self.current_process.finish_time - self.current_process.arrival_time
                                self._debug_log(f"Process {self.current_process.pid} with 0 CPU remaining marked FINISHED at {self.current_time}.")
                    self.current_process = None

            # Cek kondisi akhir simulasi
            if all(p.state == ProcessState.FINISHED for p in self.processes) and not self.io_processes and self.current_process is None:
                all_queues_empty = all(not q for q in self.queues)
                if all_queues_empty:
                    self._debug_log(f"All processes finished and queues empty. Simulation terminated at {self.current_time}.")
                    break

            if iterations >= max_iterations:
                self._debug_log(f"WARNING: Max iterations reached ({max_iterations}).")
                break
        
        # Pastikan semua proses yang seharusnya selesai memiliki finish_time dan turnaround_time
        for p in self.processes:
            if p.state == ProcessState.FINISHED and p.finish_time is None:
                p.finish_time = self.current_time # Waktu terakhir simulasi
                p.turnaround_time = p.finish_time - p.arrival_time
            # Pastikan WT tidak negatif jika ada anomali
            if p.waiting_time < 0: p.waiting_time = 0


    def _debug_log(self, message: str) -> None:
        debug_mode = False # Set ke True untuk melihat log detail
        if debug_mode:
            print(f"[MLFQ DEBUG] {message}")
    
    def get_results(self) -> dict:
        cpu_utilization = ( (self.current_time - self.idle_time) / self.current_time if self.current_time > 0 else 0 )
        
        finished_processes = [p for p in self.processes if p.state == ProcessState.FINISHED and p.finish_time is not None]
        
        # Handle kasus tidak ada proses yang selesai
        if not finished_processes:
             avg_turnaround = 0
             avg_waiting = 0
        else:
            avg_turnaround = sum(p.turnaround_time for p in finished_processes) / len(finished_processes)
            avg_waiting = sum(p.waiting_time for p in finished_processes) / len(finished_processes)
        
        # Handle kasus tidak ada proses yang pernah mulai (untuk avg_response)
        started_processes = [p for p in self.processes if p.start_time is not None]
        if not started_processes:
            avg_response = 0
        else:
            avg_response = sum(
                (p.start_time - p.arrival_time) for p in started_processes
            ) / len(started_processes)
        
        for p in self.processes:
            p.io_time_output = p.original_io_time 

        return {
            "processes": [process.to_dict() for process in self.processes],
            "metrics": {
                "avg_turnaround_time": avg_turnaround,
                "avg_waiting_time": avg_waiting,
                "avg_response_time": avg_response,
                "cpu_utilization": cpu_utilization, # Menggunakan perhitungan yang lebih umum
                "total_time": self.current_time # total_time seharusnya adalah self.current_time
            }
        }
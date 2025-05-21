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
        # ID unik proses
        self.pid = pid
        # Waktu kedatangan proses
        self.arrival_time = arrival_time
        # Total waktu CPU yang dibutuhkan proses
        self.burst_time = burst_time
        # Prioritas proses (default 0)
        self.priority = priority
        
        # Waktu I/O asli untuk burst I/O proses
        self.io_time = io_time 
        self.original_io_time = io_time 
        # Sisa waktu untuk burst I/O saat ini
        self.remaining_io_time = io_time 

        # Atribut khusus simulator, akan diinisialisasi ulang oleh MLFQSimulator
        self.state: ProcessState = ProcessState.NEW  # Status proses saat ini
        self.queue: int = -1  # Indeks queue MLFQ tempat proses berada
        self.start_time: Optional[int] = None  # Waktu mulai eksekusi pertama kali
        self.finish_time: Optional[int] = None  # Waktu proses selesai
        self.waiting_time: int = 0  # Total waktu menunggu di ready queue
        self.turnaround_time: int = 0  # Total waktu dari datang hingga selesai
        self.remaining_time: int = burst_time  # Sisa waktu CPU yang dibutuhkan
        self.context_switches: int = 0  # Jumlah context switch yang dialami proses
        self.execution_history: List[Tuple[int, int]] = []  # Riwayat eksekusi (start, end)
        self.queue_history: List[Tuple[int, int]] = []  # Riwayat perpindahan queue (queue, waktu)
        self.io_bursts_completed: int = 0  # Jumlah burst I/O yang selesai
        self.cpu_bursts_completed: int = 0  # Jumlah burst CPU yang selesai

        # Untuk output, merepresentasikan io_time asli
        self.io_time_output: int = io_time 

        # --- PERUBAHAN DIMULAI DI SINI ---
        # Atribut baru untuk melacak kapan proses terakhir kali masuk ke state READY
        self.time_entered_ready_state: Optional[int] = None 
        # --- PERUBAHAN SELESAI DI SINI ---

    def to_dict(self) -> dict:
        """Konversi objek proses ke dictionary untuk output JSON."""
        # Konversi execution_history ke format yang diharapkan frontend
        execution_log = [{"start_time": start, "end_time": end} for start, end in self.execution_history]
        
        return {
            "pid": self.pid,
            "arrival_time": self.arrival_time,
            "burst_time": self.burst_time,
            "priority": self.priority,
            "io_time": self.io_time_output, # Gunakan ini untuk output
            "state": self.state.value,
            "queue": self.queue,
            "start_time": self.start_time,
            "finish_time": self.finish_time,
            "waiting_time": self.waiting_time,
            "turnaround_time": self.turnaround_time,
            "remaining_time": self.remaining_time,
            "context_switches": self.context_switches,
            "execution_log": execution_log,  # Ganti execution_history dengan execution_log
            "queue_history": self.queue_history,
            "io_bursts_completed": self.io_bursts_completed,
            "cpu_bursts_completed": self.cpu_bursts_completed,
            "first_execution_time": self.start_time,  # Gunakan start_time sebagai first_execution_time
        }
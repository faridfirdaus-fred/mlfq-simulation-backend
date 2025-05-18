Berikut versi yang diperbaiki dan lebih profesional dari README untuk **MLFQ Simulation Backend** menggunakan **FastAPI**:

---

# ⚙️ MLFQ Simulation API

A **FastAPI-based backend service** for simulating CPU scheduling using the **Multi-Level Feedback Queue (MLFQ)** algorithm.

---

## 📄 Description

This project exposes a **RESTful API** that allows users to simulate CPU process scheduling using the **MLFQ algorithm**. The simulation supports detailed process parameters, including:

* Arrival time
* CPU burst time
* I/O burst time
* Variance for CPU/I/O bursts
* Aging mechanisms to prevent starvation

It is designed to integrate seamlessly with the [MLFQ Simulation Frontend](#), allowing real-time visualization of scheduling behavior.

---

## ✨ Features

* ✅ **Three-Level MLFQ Simulation**

  * Q0: Time quantum = 4ms
  * Q1: Time quantum = 8ms
  * Q2: FCFS (First-Come-First-Served)

* ⏱️ **Time Quantum-Based Scheduling**

* 🔁 **Aging Mechanism** (to prevent starvation)

* 💡 **I/O Operations Support**

* 🔧 **Variance Handling** for burst times

* 📡 **RESTful API** with clean JSON input/output

* 🧪 Ready for testing with `pytest`

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/mlfq-simulation-backend.git
cd mlfq-simulation-backend
```

### 2. Create and Activate Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ Usage

### 1. Start the Server

```bash
uvicorn main:app --reload
```

### 2. Access API

* Base URL: `http://localhost:8000`
* Swagger Docs: `http://localhost:8000/docs`
* ReDoc: `http://localhost:8000/redoc`

---

## 📌 API Endpoints

### `GET /`

Returns a simple HTML message to confirm the API is running.

### `POST /simulate`

Simulates the MLFQ scheduling algorithm.

#### 🔽 Request Body (JSON)

```json
{
  "processes": [
    {
      "pid": "P1",
      "arrival_time": 0,
      "cpu_burst": [5, 3],
      "io_burst": [2],
      "priority": 0
    },
    ...
  ],
  "settings": {
    "aging": true,
    "cpu_variance": 0.2,
    "io_variance": 0.1
  }
}
```

#### 🔼 Response (JSON)

Returns simulation results including scheduling order, wait times, turnaround times, and Gantt chart data.

---

## 🧪 Running Tests

Run all tests using:

```bash
pytest
```

Make sure the virtual environment is activated and dependencies are installed.

---

## 📚 MLFQ Algorithm Overview

The **Multi-Level Feedback Queue (MLFQ)** is a preemptive CPU scheduling algorithm designed to favor short processes and ensure fairness:

* Multiple priority queues (Q0 > Q1 > Q2)
* New processes start in the highest-priority queue
* If a process exhausts its time quantum, it is demoted
* Processes that wait (e.g., perform I/O) are kept in higher queues
* Aging promotes long-waiting processes to prevent starvation

---

## 📬 Contact

For questions or feedback:

* Open an issue on [GitHub](https://github.com/faridfirdaus-fred/mlfq-simulation-backend/issues)
* Or contact via the frontend application

---

## 📄 License

This project is licensed under the [MIT License](./LICENSE)



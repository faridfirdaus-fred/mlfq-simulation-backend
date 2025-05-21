# main.py
"""
FastAPI backend for MLFQ simulation.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from .process import Process # Pastikan impor Process dan ProcessState dari process.py
from .mlfq_scheduler import MLFQSimulator
from typing import List, Optional
from pydantic import BaseModel

app = FastAPI(
    title="MLFQ Simulation API",
    description="API for simulating Multi-Level Feedback Queue scheduling algorithm",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProcessInput(BaseModel):
    """Input model for process creation"""
    pid: str
    arrival_time: int
    burst_time: int
    priority: Optional[int] = 0
    io_time: Optional[int] = 0

class SimulationConfig(BaseModel):
    """Configuration for MLFQ simulation"""
    num_queues: Optional[int] = 3
    time_slice: Optional[int] = 2
    boost_interval: Optional[int] = 100
    aging_threshold: Optional[int] = 5

class SimulationRequest(BaseModel):
    """Request model for simulation"""
    processes: List[ProcessInput]
    config: Optional[SimulationConfig] = SimulationConfig()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <title>MLFQ Simulation API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 800px; margin: 0 auto; }
                .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
                code { background: #e8e8e8; padding: 2px 4px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 MLFQ Simulation API</h1>
                <p>Multi-Level Feedback Queue Scheduling Algorithm Simulation</p>
                
                <h2>Available Endpoints:</h2>
                <div class="endpoint">
                    <strong>GET /docs</strong> - Interactive API documentation
                </div>
                <div class="endpoint">
                    <strong>POST /simulate</strong> - Run MLFQ simulation
                </div>
                <div class="endpoint">
                    <strong>GET /health</strong> - Health check
                </div>
                <div class="endpoint">
                    <strong>GET /info</strong> - Algorithm information
                </div>
                
                <h2>Quick Start:</h2>
                <p>1. Visit <a href="/docs">/docs</a> for interactive testing</p>
                <p>2. POST process data to <code>/simulate</code></p>
                
                <h2>Example Process Data:</h2>
                <pre><code>{
  "processes": [
    {
      "pid": "P1",
      "arrival_time": 0,
      "burst_time": 4,
      "priority": 0,
      "io_time": 0
    },
    {
      "pid": "P2",
      "arrival_time": 1,
      "burst_time": 3,
      "priority": 0,
      "io_time": 0
    }
  ],
  "config": {
    "num_queues": 3,
    "time_slice": 2,
    "boost_interval": 100,
    "aging_threshold": 5
  }
}</code></pre>
            </div>
        </body>
    </html>
    """

@app.post("/simulate")
async def simulate_mlfq(request: SimulationRequest):
    """
    Run MLFQ simulation with given processes and configuration
    """
    try:
        if not request.processes:
            return JSONResponse(
                status_code=400,
                content={"detail": "Process list cannot be empty"}
            )
        
        pids = [p.pid for p in request.processes]
        if len(pids) != len(set(pids)):
            return JSONResponse(
                status_code=400,
                content={"detail": "Process IDs must be unique"}
            )
        
        # CRITICAL FIX: Pass the raw ProcessInput objects to MLFQSimulator.
        # The MLFQSimulator.__init__ will handle creating fresh Process objects internally.
        # This ensures a clean state for each simulation run.
        simulator = MLFQSimulator(
            processes=request.processes, # Pass ProcessInput directly
            num_queues=request.config.num_queues,
            time_slice=request.config.time_slice,
            boost_interval=request.config.boost_interval,
            aging_threshold=request.config.aging_threshold
        )
        
        simulator.simulate()
        results = simulator.get_results()
        
        return {
            "results": results,
            "total_time": simulator.current_time
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal simulation error: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "MLFQ Simulation API",
            "version": "1.0.0"
        }
    )

@app.get("/info")
async def get_algorithm_info():
    """Get information about the MLFQ algorithm implementation"""
    default_config = SimulationConfig()
    time_quantums_example = [
        default_config.time_slice * (i + 1) for i in range(default_config.num_queues)
    ]
    return JSONResponse(
        content={
            "algorithm": "Multi-Level Feedback Queue (MLFQ)",
            "queues_default": default_config.num_queues,
            "time_quantum_progression": "Linear: base_time_slice * (queue_level + 1)",
            "default_time_quantums_example": time_quantums_example,
            "aging_threshold_default": default_config.aging_threshold,
            "boost_interval_default": default_config.boost_interval,
            "features": [
                "Multiple priority queues",
                "Round-robin scheduling within each queue (FIFO for lowest)",
                "Processes demote to lower priority queues after exhausting time slice",
                "Processes return to highest priority queue after I/O completion",
                "Aging mechanism to prevent starvation by promoting long-waiting processes",
                "Priority boost at regular intervals to move all processes to top queue",
                "Dynamic time quantum (linearly increasing for lower queues)",
                "Context switching tracking",
                "CPU and I/O burst handling"
            ],
            "metrics_calculated": [
                "Response Time",
                "Turnaround Time", 
                "Waiting Time",
                "CPU Utilization",
                "Total Simulation Time",
                "Context Switches (per process)",
                "CPU Bursts Completed (per process)",
                "I/O Bursts Completed (per process)"
            ],
            "process_states": [
                "NEW (baru tiba)",
                "READY (menunggu CPU di antrean)",
                "RUNNING (sedang dieksekusi CPU)",
                "BLOCKED (menunggu I/O)",
                "FINISHED (selesai total)"
            ]
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
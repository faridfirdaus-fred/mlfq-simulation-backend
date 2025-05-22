"""
FastAPI backend for MLFQ simulation.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from .process import Process
from .mlfq_scheduler import MLFQSimulator
from typing import List, Optional
from pydantic import BaseModel

# Initialize FastAPI app with metadata
app = FastAPI(
    title="MLFQ Simulation API",
    description="API for simulating Multi-Level Feedback Queue scheduling algorithm",
    version="1.0.0"
)

# Configure CORS to allow access from any frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Input model for processes to be simulated
class ProcessInput(BaseModel):
    pid: str
    arrival_time: int
    burst_time: int
    priority: Optional[int] = 0
    io_time: Optional[int] = 0

# Configuration model for MLFQ simulation
class SimulationConfig(BaseModel):
    num_queues: Optional[int] = 3
    time_slice: Optional[int] = 2
    boost_interval: Optional[int] = 100
    aging_threshold: Optional[int] = 5
    debug: Optional[bool] = False

# Main request model for simulation endpoint
class SimulationRequest(BaseModel):
    processes: List[ProcessInput]
    config: Optional[SimulationConfig] = SimulationConfig()

# Root endpoint: displays simple HTML documentation
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
                pre { background: #f8f8f8; padding: 15px; overflow-x: auto; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 MLFQ Simulation API - Modified Model</h1>
                <p>Multi-Level Feedback Queue Scheduling Algorithm with Modified Metrics</p>
                
                <h2>Available Endpoints:</h2>
                <div class="endpoint">
                    <strong>GET /docs</strong> - Interactive API documentation
                </div>
                <div class="endpoint">
                    <strong>POST /simulate</strong> - Run MLFQ simulation
                </div>
                
                <h2>Modified Metrics Model:</h2>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Formula</th>
                    </tr>
                    <tr>
                        <td>QueueLevel</td>
                        <td>Initial value = process priority</td>
                    </tr>
                    <tr>
                        <td>WaitingTime</td>
                        <td>StartTime - ArrivalTime</td>
                    </tr>
                    <tr>
                        <td>TurnaroundTime</td>
                        <td>FinishTime - ArrivalTime</td>
                    </tr>
                    <tr>
                        <td>CPUUtilization</td>
                        <td>Σ (CPUBurstTime) / FinishTime</td>
                    </tr>
                    <tr>
                        <td>CPUEfficiency</td>
                        <td>CPUBurstTime / TurnaroundTime</td>
                    </tr>
                    <tr>
                        <td>IOEfficiency</td>
                        <td>IOTime / TurnaroundTime</td>
                    </tr>
                    <tr>
                        <td>WaitingRatio</td>
                        <td>WaitingTime / TurnaroundTime</td>
                    </tr>
                </table>
                
                <h2>Example Request:</h2>
                <pre><code>{
  "processes": [
    {
      "pid": "P1",
      "arrival_time": 0,
      "burst_time": 5,
      "priority": 1,
      "io_time": 2
    },
    {
      "pid": "P2",
      "arrival_time": 1,
      "burst_time": 3,
      "priority": 0,
      "io_time": 0
    },
    {
      "pid": "P3",
      "arrival_time": 2,
      "burst_time": 8,
      "priority": 2,
      "io_time": 3
    }
  ],
  "config": {
    "num_queues": 3,
    "time_slice": 2,
    "boost_interval": 15,
    "aging_threshold": 4
  }
}</code></pre>
            </div>
        </body>
    </html>
    """

# Main simulation endpoint
@app.post("/simulate")
async def simulate_mlfq(request: SimulationRequest):
    """
    Run MLFQ simulation with the given processes and configuration
    """
    try:
        # Validate: process list must not be empty
        if not request.processes:
            return JSONResponse(
                status_code=400,
                content={"detail": "Process list cannot be empty"}
            )
        
        # Validate: PIDs must be unique
        pids = [p.pid for p in request.processes]
        if len(pids) != len(set(pids)):
            return JSONResponse(
                status_code=400,
                content={"detail": "Process IDs must be unique"}
            )
        
        # Convert Pydantic models to Process objects
        processes = []
        for p_input in request.processes:
            processes.append(Process(
                pid=p_input.pid,
                arrival_time=p_input.arrival_time,
                burst_time=p_input.burst_time,
                priority=p_input.priority,
                io_time=p_input.io_time
            ))
        
        # Create and run MLFQ simulator
        simulator = MLFQSimulator(
            processes=processes,
            num_queues=request.config.num_queues,
            time_slice=request.config.time_slice,
            boost_interval=request.config.boost_interval,
            aging_threshold=request.config.aging_threshold,
            debug=request.config.debug
        )
        
        # Run simulation
        simulator.simulate()
        
        # Get results
        results = simulator.get_results()
        
        # Return simulation results
        return {
            "results": results,
            "metrics_description": {
                "QueueLevel": "Initial queue level set to process priority",
                "WaitingTime": "StartTime - ArrivalTime",
                "TurnaroundTime": "FinishTime - ArrivalTime",
                "CPUUtilization": "Total CPU time / Total simulation time",
                "Throughput": "Processes completed / Total simulation time",
                "CPUEfficiency": "CPU burst time / Turnaround time for each process"
            }
        }
        
    except ValueError as ve:
        # Handle validation errors
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Handle internal errors
        raise HTTPException(status_code=500, detail=f"Internal simulation error: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "Modified MLFQ Simulation API",
            "version": "1.0.0"
        }
    )

# Run the server if this file is executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
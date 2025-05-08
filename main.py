from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import List, Optional
from mlfq import simulate_mlfq
from fastapi.responses import HTMLResponse
from fastapi import HTTPException


app = FastAPI() 

@app.get("/", response_class=HTMLResponse)
def read_root():
    return "<h1>MLFQ Simulation API is Running 🚀</h1><p>Use /docs to test the API.</p>"
# Allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ganti dengan frontend URL untuk production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Process(BaseModel):
    pid: str
    arrival_time: int
    burst_time: int
    io_burst: int = 0
    total_time: Optional[int] = None
    io_variance: float = 0.0
    cpu_variance: float = 0.0

    @validator('arrival_time', 'burst_time', 'io_burst')
    def validate_positive_values(cls, v, values, **kwargs):
        if v < 0:
            raise ValueError("Time values must be non-negative")
        return v
    
    @validator('io_variance', 'cpu_variance')
    def validate_variance_range(cls, v, values, **kwargs):
        if not 0 <= v <= 1:
            raise ValueError("Variance values must be between 0.0 and 1.0")
        return v
    
@app.post("/simulate")
def simulate(processes: List[Process]):
    try:
        data = [p.dict() for p in processes]
        result = simulate_mlfq(data)
        return {"processes": result, "total_time": max(p.get("finish", 0) for p in result)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
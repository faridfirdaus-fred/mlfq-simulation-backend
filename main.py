from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
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

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_positive_values

    @staticmethod
    def validate_positive_values(process):
        if process["arrival_time"] < 0 or process["burst_time"] < 0:
            raise ValueError("arrival_time and burst_time must be non-negative")
        return process
    
@app.post("/simulate")
def simulate(processes: List[Process]):
    try:
        data = [p.dict() for p in processes]
        result = simulate_mlfq(data)
        return {"result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")
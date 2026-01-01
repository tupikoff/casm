"""FastAPI web adapter for Cambridge Assembly Emulator."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import run_program, RunOptions


# Constants
MAX_PROGRAM_SIZE = 50 * 1024  # 50KB
STATIC_DIR = Path(__file__).parent.parent / "static"


# Request/Response models
class RunOptionsModel(BaseModel):
    memory_size: int = Field(default=256, ge=1, le=65536)
    start_address: int = Field(default=200, ge=0)
    max_steps: int = Field(default=10000, ge=1, le=1000000)
    word_bits: int = Field(default=16, ge=8, le=64)
    signed: bool = True
    trace: bool = True
    trace_watch: list[int] = Field(default_factory=list)
    trace_include_ix: bool = False
    trace_include_flag: bool = False
    trace_include_io: bool = True
    initial_memory: dict[str, int] = Field(default_factory=dict)


class RunRequest(BaseModel):
    program: str
    input: str = ""
    options: Optional[RunOptionsModel] = None


class ErrorResponse(BaseModel):
    type: str
    message: str
    step: int
    addr: int
    source_line_no: Optional[int] = None
    source_text: Optional[str] = None


class FinalState(BaseModel):
    acc: int
    ix: int
    pc: int
    flag: Optional[bool]


class RunResponse(BaseModel):
    status: str
    output_text: str
    steps_executed: int
    final_state: dict
    trace_watch: list[int]
    trace: list[dict]
    error: Optional[dict] = None


# Create FastAPI app
app = FastAPI(
    title="Cambridge Assembly Emulator",
    description="Web API for executing Cambridge Assembly programs with tracing",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/run", response_model=RunResponse)
async def run_code(request: RunRequest):
    """Execute a Cambridge Assembly program.
    
    Args:
        request: Program code, input buffer, and execution options
    
    Returns:
        Execution result with output, trace, and final state
    """
    # Validate program size
    if len(request.program) > MAX_PROGRAM_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Program size exceeds limit of {MAX_PROGRAM_SIZE} bytes",
        )
    
    # Build options
    opts = request.options or RunOptionsModel()
    
    # Convert initial_memory keys from string to int
    initial_memory = {}
    for k, v in opts.initial_memory.items():
        try:
            initial_memory[int(k)] = v
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid memory address key: {k}",
            )
    
    run_opts = RunOptions(
        memory_size=opts.memory_size,
        start_address=opts.start_address,
        max_steps=opts.max_steps,
        word_bits=opts.word_bits,
        signed=opts.signed,
        trace=opts.trace,
        trace_watch=opts.trace_watch,
        trace_include_ix=opts.trace_include_ix,
        trace_include_flag=opts.trace_include_flag,
        trace_include_io=opts.trace_include_io,
        initial_memory=initial_memory,
    )
    
    # Execute program
    result = run_program(
        program_text=request.program,
        input_text=request.input,
        options=run_opts,
    )
    
    return result.to_dict()


# Mount static files AFTER API routes to prevent shadowing
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

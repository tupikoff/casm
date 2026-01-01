"""Program runner with tracing for Cambridge Assembly Emulator."""

from dataclasses import dataclass, field
from typing import Optional
from .cpu import CPU
from .memory import Memory
from .parser import parse_program, ParsedProgram, Instruction
from .instructions import execute_instruction, IOBuffer
from .errors import (
    CASMError,
    CASMRuntimeError,
    StepLimitExceeded,
    ErrorInfo,
)


@dataclass
class RunOptions:
    """Options for program execution."""
    memory_size: int = 256
    start_address: int = 200
    max_steps: int = 10000
    word_bits: int = 16
    signed: bool = True
    trace: bool = True
    trace_watch: list[int] = field(default_factory=list)
    trace_include_ix: bool = False
    trace_include_flag: bool = False
    trace_include_io: bool = True
    initial_memory: dict[int, int] = field(default_factory=dict)


@dataclass
class TraceRow:
    """Single row of execution trace."""
    step: int
    addr: int
    acc: int
    mem: dict[str, int]
    ix: Optional[int] = None
    flag: Optional[bool] = None
    in_code: Optional[int] = None
    out_code: Optional[int] = None
    instr_text: str = ""

    def to_dict(self, include_ix: bool, include_flag: bool, include_io: bool) -> dict:
        result = {
            "step": self.step,
            "addr": self.addr,
            "acc": self.acc,
            "mem": self.mem,
        }
        if include_ix:
            result["ix"] = self.ix
        if include_flag:
            result["flag"] = self.flag
        if include_io:
            result["in_code"] = self.in_code
            result["out_code"] = self.out_code
        result["instr_text"] = self.instr_text
        return result


@dataclass
class RunResult:
    """Result of program execution."""
    status: str  # "ok" | "error"
    output_text: str
    steps_executed: int
    final_state: dict
    trace_watch: list[int]
    trace: list[dict]
    error: Optional[ErrorInfo] = None

    def to_dict(self) -> dict:
        result = {
            "status": self.status,
            "output_text": self.output_text,
            "steps_executed": self.steps_executed,
            "final_state": self.final_state,
            "trace_watch": self.trace_watch,
            "trace": self.trace,
        }
        if self.error:
            result["error"] = self.error.to_dict()
        return result


def run_program(
    program_text: str,
    input_text: str = "",
    options: Optional[RunOptions] = None,
) -> RunResult:
    """Run a Cambridge Assembly program.
    
    Args:
        program_text: Program source code
        input_text: Input buffer for IN instructions
        options: Execution options
    
    Returns:
        RunResult with execution status, output, and trace
    """
    if options is None:
        options = RunOptions()

    trace_rows: list[dict] = []
    error_info: Optional[ErrorInfo] = None
    steps_executed = 0
    
    # Initialize CPU
    cpu = CPU(word_bits=options.word_bits, signed=options.signed)
    
    # Initialize Memory
    memory = Memory(
        size=options.memory_size,
        word_bits=options.word_bits,
        signed=options.signed,
        initial_values=options.initial_memory,
    )
    
    # Initialize I/O
    io_buffer = IOBuffer(input_text)
    
    # Parse program
    try:
        program = parse_program(program_text, start_address=options.start_address)
    except CASMError as e:
        return RunResult(
            status="error",
            output_text="",
            steps_executed=0,
            final_state=cpu.get_state(),
            trace_watch=options.trace_watch,
            trace=[],
            error=e.to_error_info(),
        )

    # Merge initial memory from program code
    for addr, val in program.initial_memory.items():
        memory.write(addr, val)
        if addr not in options.trace_watch:
            options.trace_watch.append(addr)
    
    options.trace_watch.sort()
    
    # Set starting PC
    cpu.pc = program.start_address
    
    current_instr: Optional[Instruction] = None
    
    try:
        while not cpu.halted and steps_executed < options.max_steps:
            # Fetch instruction
            if cpu.pc not in program.instructions:
                raise CASMRuntimeError(
                    f"No instruction at address {cpu.pc}",
                    step=steps_executed + 1,
                    addr=cpu.pc,
                )
            
            current_instr = program.instructions[cpu.pc]
            cpu.ir = f"{current_instr.opcode} {current_instr.operand or ''}".strip()
            
            # Store current PC before execution (for trace)
            instr_addr = cpu.pc
            
            # Reset I/O codes for this instruction
            io_buffer.reset_io_codes()
            
            # Execute
            new_pc = execute_instruction(current_instr, cpu, memory, io_buffer)
            
            # Update PC
            if new_pc is not None:
                cpu.pc = new_pc
            else:
                cpu.pc = cpu.pc + 1
            
            steps_executed += 1
            
            # Record trace
            if options.trace:
                row = TraceRow(
                    step=steps_executed,
                    addr=instr_addr,
                    acc=cpu.acc,
                    mem=memory.get_watched(options.trace_watch),
                    ix=cpu.ix if options.trace_include_ix else None,
                    flag=cpu.flag if options.trace_include_flag else None,
                    in_code=io_buffer.last_in_code if options.trace_include_io else None,
                    out_code=io_buffer.last_out_code if options.trace_include_io else None,
                    instr_text=current_instr.clean_text if current_instr else "",
                )
                trace_rows.append(row.to_dict(
                    include_ix=options.trace_include_ix,
                    include_flag=options.trace_include_flag,
                    include_io=options.trace_include_io,
                ))
        
        # Check step limit
        if steps_executed >= options.max_steps and not cpu.halted:
            raise StepLimitExceeded(
                f"Step limit exceeded: {options.max_steps}",
                step=steps_executed,
                addr=cpu.pc,
            )
    
    except CASMError as e:
        # Attach context to error
        e.step = steps_executed
        if current_instr:
            e.addr = current_instr.addr
            e.source_line_no = current_instr.source_line_no
            e.source_text = current_instr.source_text
        error_info = e.to_error_info()
    
    return RunResult(
        status="ok" if error_info is None else "error",
        output_text=io_buffer.get_output(),
        steps_executed=steps_executed,
        final_state=cpu.get_state(),
        trace_watch=options.trace_watch,
        trace=trace_rows,
        error=error_info,
    )

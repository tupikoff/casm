"""Instruction execution for Cambridge Assembly Emulator."""

from typing import Callable, Optional
from .cpu import CPU
from .memory import Memory
from .parser import Instruction
from .errors import JumpWithoutCompare, InputUnderflow


class IOBuffer:
    """Input/Output buffer for IN/OUT instructions."""

    def __init__(self, input_text: str = ""):
        self._input = list(input_text)
        self._input_pos = 0
        self._output: list[str] = []
        self.last_in_code: Optional[int] = None
        self.last_out_code: Optional[int] = None

    def read_char(self) -> int:
        """Read next character from input buffer as ASCII code."""
        self.last_in_code = None
        if self._input_pos >= len(self._input):
            raise InputUnderflow("Input buffer is empty")
        char = self._input[self._input_pos]
        self._input_pos += 1
        self.last_in_code = ord(char)
        return self.last_in_code

    def write_char(self, code: int) -> None:
        """Write character to output buffer."""
        self.last_out_code = code & 0xFF
        self._output.append(chr(self.last_out_code))

    def get_output(self) -> str:
        """Get accumulated output as string."""
        return "".join(self._output)

    def reset_io_codes(self) -> None:
        """Reset last I/O codes for new instruction."""
        self.last_in_code = None
        self.last_out_code = None


# Instruction executor type
InstructionExecutor = Callable[[Instruction, CPU, Memory, IOBuffer], Optional[int]]


def execute_ldm(instr: Instruction, cpu: CPU, mem: Memory, io: IOBuffer) -> Optional[int]:
    """LDM #n: ACC := n"""
    cpu.set_acc(instr.operand_value)
    return None


def execute_ldd(instr: Instruction, cpu: CPU, mem: Memory, io: IOBuffer) -> Optional[int]:
    """LDD a: ACC := MEM[a]"""
    cpu.set_acc(mem.read(instr.operand_value))
    return None


def execute_ldi(instr: Instruction, cpu: CPU, mem: Memory, io: IOBuffer) -> Optional[int]:
    """LDI a: ACC := MEM[MEM[a]]"""
    indirect_addr = mem.read(instr.operand_value)
    cpu.set_acc(mem.read(indirect_addr))
    return None


def execute_ldx(instr: Instruction, cpu: CPU, mem: Memory, io: IOBuffer) -> Optional[int]:
    """LDX a: ACC := MEM[a + IX]"""
    addr = instr.operand_value + cpu.ix
    cpu.set_acc(mem.read(addr))
    return None


def execute_ldr(instr: Instruction, cpu: CPU, mem: Memory, io: IOBuffer) -> Optional[int]:
    """LDR #n: IX := n, or LDR ACC: IX := ACC"""
    if instr.operand_type == "immediate":
        cpu.set_ix(instr.operand_value)
    elif instr.operand == "ACC":
        cpu.set_ix(cpu.acc)
    return None


def execute_mov(instr: Instruction, cpu: CPU, mem: Memory, io: IOBuffer) -> Optional[int]:
    """MOV IX: IX := ACC"""
    cpu.set_ix(cpu.acc)
    return None


def execute_sto(instr: Instruction, cpu: CPU, mem: Memory, io: IOBuffer) -> Optional[int]:
    """STO a: MEM[a] := ACC"""
    mem.write(instr.operand_value, cpu.acc)
    return None


def execute_end(instr: Instruction, cpu: CPU, mem: Memory, io: IOBuffer) -> Optional[int]:
    """END: halt execution"""
    cpu.halted = True
    return None


def execute_in(instr: Instruction, cpu: CPU, mem: Memory, io: IOBuffer) -> Optional[int]:
    """IN: ACC := ASCII code of input character"""
    cpu.set_acc(io.read_char())
    return None


def execute_out(instr: Instruction, cpu: CPU, mem: Memory, io: IOBuffer) -> Optional[int]:
    """OUT: output chr(ACC & 0xFF)"""
    io.write_char(cpu.acc)
    return None


def execute_add(instr: Instruction, cpu: CPU, mem: Memory, io: IOBuffer) -> Optional[int]:
    """ADD #n or ADD a: ACC := ACC + operand"""
    if instr.operand_type == "immediate":
        cpu.set_acc(cpu.acc + instr.operand_value)
    else:
        cpu.set_acc(cpu.acc + mem.read(instr.operand_value))
    return None


def execute_sub(instr: Instruction, cpu: CPU, mem: Memory, io: IOBuffer) -> Optional[int]:
    """SUB #n or SUB a: ACC := ACC - operand"""
    if instr.operand_type == "immediate":
        cpu.set_acc(cpu.acc - instr.operand_value)
    else:
        cpu.set_acc(cpu.acc - mem.read(instr.operand_value))
    return None


def execute_inc(instr: Instruction, cpu: CPU, mem: Memory, io: IOBuffer) -> Optional[int]:
    """INC ACC or INC IX: increment register"""
    if instr.operand == "IX":
        cpu.set_ix(cpu.ix + 1)
    else:  # ACC or no operand (default ACC)
        cpu.set_acc(cpu.acc + 1)
    return None


def execute_dec(instr: Instruction, cpu: CPU, mem: Memory, io: IOBuffer) -> Optional[int]:
    """DEC ACC or DEC IX: decrement register"""
    if instr.operand == "IX":
        cpu.set_ix(cpu.ix - 1)
    else:  # ACC or no operand (default ACC)
        cpu.set_acc(cpu.acc - 1)
    return None


def execute_cmp(instr: Instruction, cpu: CPU, mem: Memory, io: IOBuffer) -> Optional[int]:
    """CMP #n or CMP a: FLAG := (ACC == operand)"""
    if instr.operand_type == "immediate":
        cpu.flag = cpu.acc == instr.operand_value
    else:
        cpu.flag = cpu.acc == mem.read(instr.operand_value)
    return None


def execute_cmi(instr: Instruction, cpu: CPU, mem: Memory, io: IOBuffer) -> Optional[int]:
    """CMI a: FLAG := (ACC == MEM[MEM[a]])"""
    indirect_addr = mem.read(instr.operand_value)
    cpu.flag = cpu.acc == mem.read(indirect_addr)
    return None


def execute_jmp(instr: Instruction, cpu: CPU, mem: Memory, io: IOBuffer) -> Optional[int]:
    """JMP a: PC := a"""
    return instr.operand_value


def execute_jpe(instr: Instruction, cpu: CPU, mem: Memory, io: IOBuffer) -> Optional[int]:
    """JPE a: if FLAG == True, PC := a"""
    if cpu.flag is None:
        raise JumpWithoutCompare("JPE executed without prior comparison")
    if cpu.flag:
        return instr.operand_value
    return None


def execute_jpn(instr: Instruction, cpu: CPU, mem: Memory, io: IOBuffer) -> Optional[int]:
    """JPN a: if FLAG == False, PC := a"""
    if cpu.flag is None:
        raise JumpWithoutCompare("JPN executed without prior comparison")
    if not cpu.flag:
        return instr.operand_value
    return None


# Instruction dispatch table
INSTRUCTION_EXECUTORS: dict[str, InstructionExecutor] = {
    "LDM": execute_ldm,
    "LDD": execute_ldd,
    "LDI": execute_ldi,
    "LDX": execute_ldx,
    "LDR": execute_ldr,
    "MOV": execute_mov,
    "STO": execute_sto,
    "END": execute_end,
    "IN": execute_in,
    "OUT": execute_out,
    "ADD": execute_add,
    "SUB": execute_sub,
    "INC": execute_inc,
    "DEC": execute_dec,
    "CMP": execute_cmp,
    "CMI": execute_cmi,
    "JMP": execute_jmp,
    "JPE": execute_jpe,
    "JPN": execute_jpn,
}


def execute_instruction(
    instr: Instruction,
    cpu: CPU,
    mem: Memory,
    io: IOBuffer,
) -> Optional[int]:
    """Execute a single instruction.
    
    Returns:
        New PC value if instruction is a jump, None otherwise
    """
    executor = INSTRUCTION_EXECUTORS.get(instr.opcode)
    if executor is None:
        raise ValueError(f"No executor for opcode: {instr.opcode}")
    return executor(instr, cpu, mem, io)

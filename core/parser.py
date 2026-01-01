"""Program parser for Cambridge Assembly language."""

import re
from dataclasses import dataclass
from typing import Optional
from .errors import ParseError, UnknownOpcode, InvalidOperand, AddressConflict


# Valid opcodes
VALID_OPCODES = {
    "LDM", "LDD", "LDI", "LDX", "LDR", "MOV", "STO", "END",
    "IN", "OUT",
    "ADD", "SUB", "INC", "DEC",
    "CMP", "CMI",
    "JMP", "JPE", "JPN",
}

# Opcodes that require operand
OPCODES_WITH_OPERAND = {
    "LDM", "LDD", "LDI", "LDX", "LDR", "STO",
    "ADD", "SUB",
    "CMP", "CMI",
    "JMP", "JPE", "JPN",
}

# Opcodes with optional/register operand
OPCODES_WITH_REGISTER_OPERAND = {"INC", "DEC", "LDR", "MOV"}

# Opcodes with no operand
OPCODES_NO_OPERAND = {"IN", "OUT", "END"}


@dataclass
class Instruction:
    """Parsed instruction with metadata."""
    addr: int
    opcode: str
    operand: Optional[str]  # Raw operand string
    operand_value: Optional[int]  # Resolved numeric value
    operand_type: str  # "immediate", "direct", "register", "none"
    source_line_no: int
    source_text: str


@dataclass
class ParsedProgram:
    """Result of parsing a program."""
    instructions: dict[int, Instruction]  # addr -> instruction
    labels: dict[str, int]  # label -> addr
    start_address: int
    end_address: int


def parse_program(
    text: str,
    start_address: int = 200,
    labels: Optional[dict[str, int]] = None,
) -> ParsedProgram:
    """Parse program text into instructions.
    
    Args:
        text: Program source code
        start_address: Starting address for sequential mode
        labels: Pre-defined labels (optional)
    
    Returns:
        ParsedProgram with instructions and labels
    """
    instructions: dict[int, Instruction] = {}
    resolved_labels: dict[str, int] = labels.copy() if labels else {}
    
    lines = text.split("\n")
    current_addr = start_address
    has_explicit_addresses = False
    has_sequential_addresses = False
    
    # First pass: collect labels and detect address mode
    for line_no, line in enumerate(lines, 1):
        stripped = _strip_comment(line).strip()
        if not stripped:
            continue
        
        # Check for explicit address at start
        match = re.match(r"^(\d+)\s+(.+)$", stripped)
        if match:
            has_explicit_addresses = True
        else:
            has_sequential_addresses = True
        
        # Check for label definition
        label_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", stripped)
        if label_match:
            label_name = label_match.group(1).upper()
            if label_name in resolved_labels:
                raise AddressConflict(
                    f"Duplicate label: {label_name}",
                    source_line_no=line_no,
                    source_text=line.strip(),
                )
            # Will resolve address in second pass
    
    if has_explicit_addresses and has_sequential_addresses:
        raise AddressConflict(
            "Cannot mix explicit and sequential addressing modes",
            source_line_no=1,
        )
    
    # Second pass: parse instructions
    current_addr = start_address
    
    for line_no, line in enumerate(lines, 1):
        stripped = _strip_comment(line).strip()
        if not stripped:
            continue
        
        original_text = line.strip()
        instruction_text = stripped
        addr = current_addr
        
        # Handle explicit address
        match = re.match(r"^(\d+)\s+(.+)$", stripped)
        if match:
            addr = int(match.group(1))
            instruction_text = match.group(2).strip()
        
        # Handle label definition
        label_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", instruction_text)
        if label_match:
            label_name = label_match.group(1).upper()
            resolved_labels[label_name] = addr
            instruction_text = label_match.group(2).strip()
            if not instruction_text:
                # Label only line
                if not has_explicit_addresses:
                    current_addr += 1
                continue
        
        # Parse instruction
        instruction = _parse_instruction(
            instruction_text, addr, line_no, original_text, resolved_labels
        )
        
        if addr in instructions:
            raise AddressConflict(
                f"Duplicate instruction at address {addr}",
                source_line_no=line_no,
                source_text=original_text,
            )
        
        instructions[addr] = instruction
        
        if not has_explicit_addresses:
            current_addr += 1
        else:
            current_addr = addr + 1
    
    if not instructions:
        raise ParseError("Program contains no instructions")
    
    # Third pass: resolve label references in operands
    for addr, instr in instructions.items():
        if instr.operand and instr.operand_value is None and instr.operand_type == "direct":
            label = instr.operand.upper()
            if label in resolved_labels:
                instr.operand_value = resolved_labels[label]
            else:
                raise InvalidOperand(
                    f"Unknown label: {instr.operand}",
                    source_line_no=instr.source_line_no,
                    source_text=instr.source_text,
                )
    
    addresses = sorted(instructions.keys())
    return ParsedProgram(
        instructions=instructions,
        labels=resolved_labels,
        start_address=addresses[0],
        end_address=addresses[-1],
    )


def _strip_comment(line: str) -> str:
    """Remove comment from line."""
    idx = line.find(";")
    if idx >= 0:
        return line[:idx]
    return line


def _parse_instruction(
    text: str,
    addr: int,
    line_no: int,
    original_text: str,
    labels: dict[str, int],
) -> Instruction:
    """Parse a single instruction."""
    parts = text.split(None, 1)
    if not parts:
        raise ParseError(
            "Empty instruction",
            source_line_no=line_no,
            source_text=original_text,
        )
    
    opcode = parts[0].upper()
    operand_str = parts[1].strip() if len(parts) > 1 else None
    
    if opcode not in VALID_OPCODES:
        raise UnknownOpcode(
            f"Unknown opcode: {opcode}",
            source_line_no=line_no,
            source_text=original_text,
        )
    
    # Parse operand
    operand_value = None
    operand_type = "none"
    
    if operand_str:
        operand_str_upper = operand_str.upper()
        
        # Immediate value: #n
        if operand_str.startswith("#"):
            operand_type = "immediate"
            try:
                operand_value = int(operand_str[1:])
            except ValueError:
                raise InvalidOperand(
                    f"Invalid immediate value: {operand_str}",
                    source_line_no=line_no,
                    source_text=original_text,
                )
        
        # Register operand: ACC, IX
        elif operand_str_upper in ("ACC", "IX"):
            operand_type = "register"
            operand_str = operand_str_upper
        
        # Direct address or label
        else:
            operand_type = "direct"
            # Try to parse as number
            try:
                operand_value = int(operand_str)
            except ValueError:
                # Might be a label, will resolve later
                if operand_str_upper in labels:
                    operand_value = labels[operand_str_upper]
                # else: leave as None, will be resolved in third pass
    
    # Validate operand requirements
    if opcode in OPCODES_NO_OPERAND and operand_str:
        raise InvalidOperand(
            f"{opcode} does not take an operand",
            source_line_no=line_no,
            source_text=original_text,
        )
    
    if opcode in OPCODES_WITH_OPERAND and opcode not in OPCODES_WITH_REGISTER_OPERAND:
        if not operand_str:
            raise InvalidOperand(
                f"{opcode} requires an operand",
                source_line_no=line_no,
                source_text=original_text,
            )
        
        # Check operand type validity
        if opcode in ("LDM", "LDR") and operand_type == "immediate":
            pass  # Valid: LDM #n, LDR #n
        elif opcode == "LDR" and operand_type == "register" and operand_str == "ACC":
            pass  # Valid: LDR ACC
        elif opcode in ("ADD", "SUB", "CMP") and operand_type in ("immediate", "direct"):
            pass  # Valid: ADD #n, ADD a, SUB #n, SUB a, CMP #n, CMP a
        elif opcode in ("LDD", "LDI", "LDX", "STO", "CMI", "JMP", "JPE", "JPN"):
            if operand_type != "direct":
                raise InvalidOperand(
                    f"{opcode} requires a direct address",
                    source_line_no=line_no,
                    source_text=original_text,
                )
    
    if opcode in OPCODES_WITH_REGISTER_OPERAND:
        if operand_str:
            if opcode == "MOV" and operand_str != "IX":
                raise InvalidOperand(
                    f"MOV only accepts IX as operand",
                    source_line_no=line_no,
                    source_text=original_text,
                )
            if opcode in ("INC", "DEC") and operand_str not in ("ACC", "IX"):
                raise InvalidOperand(
                    f"{opcode} only accepts ACC or IX",
                    source_line_no=line_no,
                    source_text=original_text,
                )
    
    return Instruction(
        addr=addr,
        opcode=opcode,
        operand=operand_str,
        operand_value=operand_value,
        operand_type=operand_type,
        source_line_no=line_no,
        source_text=original_text,
    )

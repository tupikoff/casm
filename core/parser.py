"""Program parser for Cambridge Assembly language."""

import re
from dataclasses import dataclass
from typing import Optional
from .errors import (
    ParseError,
    UnknownOpcode,
    InvalidOperand,
    AddressConflict,
    InvalidBinaryLiteral,
    OperandTypeError,
    InvalidShiftAmount,
)


# Valid opcodes
VALID_OPCODES = {
    "LDM",
    "LDD",
    "LDI",
    "LDX",
    "LDR",
    "MOV",
    "STO",
    "END",
    "IN",
    "OUT",
    "ADD",
    "SUB",
    "INC",
    "DEC",
    "CMP",
    "CMI",
    "JMP",
    "JPE",
    "JPN",
    "LSL",
    "LSR",
    "AND",
    "OR",
    "XOR",
}

SHIFT_OPCODES = {"LSL", "LSR"}
BITWISE_OPCODES = {"AND", "OR", "XOR"}

# Opcodes that require operand
OPCODES_WITH_OPERAND = {
    "LDM",
    "LDD",
    "LDI",
    "LDX",
    "LDR",
    "STO",
    "ADD",
    "SUB",
    "CMP",
    "CMI",
    "JMP",
    "JPE",
    "JPN",
    "LSL",
    "LSR",
    "AND",
    "OR",
    "XOR",
}

# Opcodes with optional/register operand
OPCODES_WITH_REGISTER_OPERAND = {"INC", "DEC", "LDR", "MOV"}

# Opcodes with no operand
OPCODES_NO_OPERAND = {"IN", "OUT", "END"}

_DECIMAL_LITERAL_RE = re.compile(r"^\d+$")
_BINARY_LITERAL_RE = re.compile(r"^[01]+$")


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
    clean_text: str


@dataclass
class ParsedProgram:
    """Result of parsing a program."""
    instructions: dict[int, Instruction]  # addr -> instruction
    labels: dict[str, int]  # label -> addr
    initial_memory: dict[int, int]  # addr -> value (data)
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
    initial_memory: dict[int, int] = {}
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
        
        # 1. Extract optional Address prefix
        # Supports "200 LDD 81" or "200: LDD 81" or "80 10"
        addr_match = re.match(r"^(\d+)(?:\s*:\s*|\s+)(.*)$", stripped)
        if addr_match:
            has_explicit_addresses = True
            rest = addr_match.group(2).strip()
        else:
            has_sequential_addresses = True
            rest = stripped
        
        # 2. Extract optional Label prefix from the remaining text
        # Supports "START: LDD 81" or "START: 10"
        label_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", rest)
        if label_match:
            label_name = label_match.group(1).upper()
            if label_name in resolved_labels:
                raise AddressConflict(
                    f"Duplicate label: {label_name}",
                    source_line_no=line_no,
                    source_text=line.strip(),
                )
            # Address resolution happens in Pass 2
    
    # Mixed mode is allowed: sequential addresses follow the last explicit one.
    
    # Second pass: parse instructions
    current_addr = start_address
    
    for line_no, line in enumerate(lines, 1):
        stripped = _strip_comment(line).strip()
        if not stripped:
            continue
        
        original_text = line.strip()
        # 1. Extract optional Address prefix
        addr_match = re.match(r"^(\d+)(?:\s*:\s*|\s+)(.*)$", stripped)
        if addr_match:
            addr = int(addr_match.group(1))
            instruction_text = addr_match.group(2).strip()
        else:
            addr = current_addr
            instruction_text = stripped
        
        # 2. Extract optional Label prefix from the remaining text
        label_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", instruction_text)
        if label_match:
            label_name = label_match.group(1).upper()
            resolved_labels[label_name] = addr
            instruction_text = label_match.group(2).strip()
            
        # 3. Check if the remaining text is just a number (data initialization)
        if not instruction_text:
            # Address/Label only line
            if not has_explicit_addresses:
                current_addr += 1
            else:
                current_addr = addr + 1
            continue

        data_value = _try_parse_numeric_literal(instruction_text, line_no, original_text)
        if data_value is not None:
            initial_memory[addr] = data_value
            current_addr = addr + 1
            continue
        
        # Parse instruction
        instruction = _parse_instruction(
            instruction_text, addr, line_no, original_text, instruction_text, resolved_labels
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
    if not addresses:
        # If only memory init, use 0 or something safe as start
        start_addr = 0
        end_addr = 0
    else:
        start_addr = addresses[0]
        end_addr = addresses[-1]

    return ParsedProgram(
        instructions=instructions,
        labels=resolved_labels,
        initial_memory=initial_memory,
        start_address=start_addr,
        end_address=end_addr,
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
    clean_text: str,
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
            literal_text = operand_str[1:]
            try:
                operand_value = _parse_numeric_literal(literal_text, line_no, original_text)
            except InvalidBinaryLiteral:
                raise
            except ValueError:
                if opcode in SHIFT_OPCODES:
                    raise InvalidShiftAmount(
                        f"{opcode} requires a numeric immediate shift amount",
                        source_line_no=line_no,
                        source_text=original_text,
                    )
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
                operand_value = _parse_numeric_literal(
                    operand_str,
                    line_no,
                    original_text,
                    allow_binary=False,
                )
            except InvalidBinaryLiteral:
                raise
            except ValueError:
                if operand_str_upper in labels:
                    operand_value = labels[operand_str_upper]
                # else: leave as None, will be resolved later
    
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
        elif opcode in BITWISE_OPCODES:
            if operand_type not in ("immediate", "direct"):
                raise OperandTypeError(
                    f"{opcode} requires an immediate or direct operand",
                    source_line_no=line_no,
                    source_text=original_text,
                )
        elif opcode in SHIFT_OPCODES:
            if operand_type != "immediate":
                raise OperandTypeError(
                    f"{opcode} requires an immediate shift amount",
                    source_line_no=line_no,
                    source_text=original_text,
                )
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
        clean_text=clean_text,
    )


def _try_parse_numeric_literal(
    text: str,
    line_no: int,
    source_text: str,
    *,
    allow_binary: bool = True,
) -> Optional[int]:
    """Attempt to parse numeric literal, returning None if not numeric."""
    try:
        return _parse_numeric_literal(text, line_no, source_text, allow_binary=allow_binary)
    except InvalidBinaryLiteral:
        raise
    except ValueError:
        return None


def _parse_numeric_literal(
    text: str,
    line_no: int,
    source_text: str,
    *,
    allow_binary: bool = True,
) -> int:
    """Parse decimal or binary literal, raising for invalid forms."""
    literal = text.strip()
    if not literal:
        raise ValueError("Empty literal")

    if literal.startswith("#"):
        literal = literal[1:].strip()
        if not literal:
            raise ValueError("Empty literal")

    sign = 1
    if literal[0] in "+-":
        if literal[0] == "-":
            sign = -1
        literal = literal[1:]
    if not literal:
        raise ValueError("Empty literal")

    if allow_binary and literal[0] in "Bb":
        bits = literal[1:]
        if not bits or not _BINARY_LITERAL_RE.fullmatch(bits):
            raise InvalidBinaryLiteral(
                f"Invalid binary literal: {text}",
                source_line_no=line_no,
                source_text=source_text,
            )
        value = int(bits, 2)
    else:
        if not _DECIMAL_LITERAL_RE.fullmatch(literal):
            raise ValueError("Invalid decimal literal")
        value = int(literal, 10)

    return sign * value

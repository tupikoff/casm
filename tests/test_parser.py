"""Tests for the Parser module."""

import pytest
from core.parser import parse_program, Instruction
from core.errors import (
    ParseError,
    UnknownOpcode,
    InvalidOperand,
    AddressConflict,
    InvalidBinaryLiteral,
    OperandTypeError,
    InvalidShiftAmount,
)


class TestParser:
    """Parser module tests."""

    def test_simple_instruction(self):
        """Parse single instruction."""
        result = parse_program("LDM #5")
        assert len(result.instructions) == 1
        instr = result.instructions[200]
        assert instr.opcode == "LDM"
        assert instr.operand == "#5"
        assert instr.operand_value == 5
        assert instr.operand_type == "immediate"

    def test_sequential_addressing(self):
        """Instructions get sequential addresses."""
        result = parse_program("LDM #1\nLDM #2\nLDM #3", start_address=100)
        assert 100 in result.instructions
        assert 101 in result.instructions
        assert 102 in result.instructions

    def test_empty_lines_and_comments(self):
        """Empty lines and comments are ignored."""
        program = """
        ; This is a comment
        LDM #5
        
        ; Another comment
        STO 80
        """
        result = parse_program(program)
        assert len(result.instructions) == 2

    def test_inline_comment(self):
        """Inline comments are handled."""
        result = parse_program("LDM #5  ; load 5")
        assert len(result.instructions) == 1
        assert result.instructions[200].operand_value == 5

    def test_explicit_addresses(self):
        """Explicit addresses are parsed."""
        program = "200 LDM #5\n205 STO 80"
        result = parse_program(program)
        assert 200 in result.instructions
        assert 205 in result.instructions

    def test_direct_address(self):
        """Direct address operand."""
        result = parse_program("LDD 80")
        instr = result.instructions[200]
        assert instr.operand_type == "direct"
        assert instr.operand_value == 80

    def test_register_operand(self):
        """Register operand."""
        result = parse_program("INC ACC")
        instr = result.instructions[200]
        assert instr.operand == "ACC"
        assert instr.operand_type == "register"

    def test_unknown_opcode(self):
        """Unknown opcode raises error."""
        with pytest.raises(UnknownOpcode):
            parse_program("XYZ 10")

    def test_missing_operand(self):
        """Missing required operand raises error."""
        with pytest.raises(InvalidOperand):
            parse_program("LDD")

    def test_label_definition(self):
        """Labels are defined and resolved."""
        program = """
        LOOP: LDM #5
        JMP LOOP
        """
        result = parse_program(program)
        assert "LOOP" in result.labels
        # JMP operand should be resolved to LOOP's address
        jmp_instr = result.instructions[201]
        assert jmp_instr.operand_value == 200

    def test_mixed_address_mode_allowed(self):
        """Mixing explicit and sequential addresses is now allowed."""
        program = parse_program("200 LDM #5\nLDM #10", start_address=200)
        assert 200 in program.instructions
        assert 201 in program.instructions
        assert program.instructions[200].opcode == "LDM"
        assert program.instructions[201].opcode == "LDM"

    def test_address_label_prefix(self):
        """Test line with both address and label prefixes."""
        program = parse_program("200 START: LDD 80")
        assert 200 in program.instructions
        assert program.instructions[200].opcode == "LDD"
        assert program.labels["START"] == 200

    def test_duplicate_address_error(self):
        """Duplicate addresses raise error."""
        with pytest.raises(AddressConflict):
            parse_program("200 LDM #5\n200 LDM #10")

    def test_empty_program(self):
        """Empty program raises error."""
        with pytest.raises(ParseError):
            parse_program("")
        with pytest.raises(ParseError):
            parse_program("; just a comment")

    def test_case_insensitive_opcodes(self):
        """Opcodes are case insensitive."""
        result = parse_program("ldm #5")
        assert result.instructions[200].opcode == "LDM"

    def test_mov_ix(self):
        """MOV IX is valid."""
        result = parse_program("MOV IX")
        assert result.instructions[200].opcode == "MOV"
        assert result.instructions[200].operand == "IX"

    def test_no_operand_instructions(self):
        """END, IN, OUT take no operand."""
        result = parse_program("IN\nOUT\nEND")
        assert len(result.instructions) == 3

    def test_binary_literal_parsing(self):
        """Binary literals work in data and immediates."""
        program = parse_program("81 VALUE: B00001010\nLDM #B100\nEND")
        assert program.initial_memory[81] == 10
        first_addr = min(program.instructions.keys())
        instr = program.instructions[first_addr]
        assert instr.operand_value == 4

    @pytest.mark.parametrize("literal", ["B", "B2", "#B", "#BB01"])
    def test_invalid_binary_literals(self, literal):
        """Invalid binary literal forms raise error."""
        if literal.startswith("#"):
            source = f"LDM {literal}\nEND"
        else:
            source = f"{literal}\nEND"
        with pytest.raises(InvalidBinaryLiteral):
            parse_program(source)

    def test_lsl_requires_immediate_operand(self):
        """LSL operand must be immediate."""
        with pytest.raises(OperandTypeError):
            parse_program("LSL 4\nEND")

    def test_and_rejects_register_operand(self):
        """AND only allows immediate or direct addresses."""
        with pytest.raises(OperandTypeError):
            parse_program("AND ACC\nEND")

    def test_invalid_shift_amount_literal(self):
        """Shift amount must be numeric."""
        with pytest.raises(InvalidShiftAmount):
            parse_program("LSR #foo\nEND")

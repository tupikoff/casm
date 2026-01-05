"""Ensure every opcode has a dedicated behavioral test."""

from __future__ import annotations

from dataclasses import dataclass, field
import copy
from typing import Callable

import pytest

from core import run_program, RunOptions
from core.parser import VALID_OPCODES


def expect_acc(value: int) -> Callable:
    def _check(result):
        assert result.final_state["acc"] == value

    return _check


def expect_ix(value: int) -> Callable:
    def _check(result):
        assert result.final_state["ix"] == value

    return _check


def expect_flag(value: bool) -> Callable:
    def _check(result):
        assert result.final_state["flag"] is value

    return _check


def expect_output(text: str) -> Callable:
    def _check(result):
        assert result.output_text == text

    return _check


def expect_trace_mem(addr: int, value: int) -> Callable:
    def _check(result):
        assert result.trace[-1]["mem"][str(addr)] == value

    return _check


def expect_steps(count: int) -> Callable:
    def _check(result):
        assert result.steps_executed == count

    return _check


@dataclass
class InstructionCase:
    opcode: str
    program: str
    checker: Callable
    input_text: str = ""
    options_kwargs: dict = field(default_factory=dict)


INSTRUCTION_CASES = [
    InstructionCase("LDM", "LDM #7\nEND", expect_acc(7)),
    InstructionCase(
        "LDD",
        "LDD 80\nEND",
        expect_acc(12),
        options_kwargs={"initial_memory": {80: 12}},
    ),
    InstructionCase(
        "LDI",
        "LDI 80\nEND",
        expect_acc(33),
        options_kwargs={"initial_memory": {80: 81, 81: 33}},
    ),
    InstructionCase(
        "LDX",
        "LDR #5\nLDX 80\nEND",
        expect_acc(19),
        options_kwargs={"initial_memory": {85: 19}},
    ),
    InstructionCase("LDR", "LDR #11\nEND", expect_ix(11)),
    InstructionCase("MOV", "LDM #4\nMOV IX\nEND", expect_ix(4)),
    InstructionCase(
        "STO",
        "LDM #9\nSTO 80\nEND",
        expect_trace_mem(80, 9),
        options_kwargs={"trace_watch": [80]},
    ),
    InstructionCase("END", "END", expect_steps(1)),
    InstructionCase("IN", "IN\nEND", expect_acc(65), input_text="A"),
    InstructionCase("OUT", "LDM #66\nOUT\nEND", expect_output("B")),
    InstructionCase("ADD", "LDM #1\nADD #2\nEND", expect_acc(3)),
    InstructionCase("SUB", "LDM #5\nSUB #3\nEND", expect_acc(2)),
    InstructionCase("INC", "LDM #5\nINC ACC\nEND", expect_acc(6)),
    InstructionCase("DEC", "LDM #5\nDEC ACC\nEND", expect_acc(4)),
    InstructionCase("CMP", "LDM #5\nCMP #5\nEND", expect_flag(True)),
    InstructionCase(
        "CMI",
        "LDM #7\nCMI 80\nEND",
        expect_flag(True),
        options_kwargs={"initial_memory": {80: 81, 81: 7}},
    ),
    InstructionCase(
        "JMP",
        "JMP TARGET\nLDM #0\nTARGET: LDM #8\nEND",
        expect_acc(8),
    ),
    InstructionCase(
        "JPE",
        "LDM #3\nCMP #3\nJPE DONE\nLDM #0\nDONE: END",
        expect_acc(3),
    ),
    InstructionCase(
        "JPN",
        "LDM #3\nCMP #5\nJPN ELSE\nLDM #0\nJMP DONE\nELSE: LDM #2\nDONE: END",
        expect_acc(2),
    ),
    InstructionCase("LSL", "LDM #B00000011\nLSL #2\nEND", expect_acc(12)),
    InstructionCase("LSR", "LDM #B10000000\nLSR #3\nEND", expect_acc(16)),
    InstructionCase("AND", "LDM #B1100\nAND #B0101\nEND", expect_acc(4)),
    InstructionCase("OR", "LDM #B00010000\nOR #B11\nEND", expect_acc(19)),
    InstructionCase("XOR", "LDM #B0011\nXOR #B0010\nEND", expect_acc(1)),
]


@pytest.mark.parametrize("case", INSTRUCTION_CASES, ids=lambda case: case.opcode)
def test_all_instructions_have_behavioral_tests(case: InstructionCase):
    kwargs = copy.deepcopy(case.options_kwargs)
    options = RunOptions(**kwargs) if kwargs else RunOptions()
    result = run_program(case.program, input_text=case.input_text, options=options)
    assert result.status == "ok"
    case.checker(result)


def test_instruction_case_coverage_matches_valid_opcodes():
    covered = {case.opcode for case in INSTRUCTION_CASES}
    assert covered == VALID_OPCODES

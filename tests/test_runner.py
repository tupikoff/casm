"""Tests for instructions and runner."""

import pytest
from core import run_program, RunOptions
from core.errors import StepLimitExceeded, InputUnderflow


class TestInstructions:
    """Test individual instructions via runner."""

    def test_ldm(self):
        """LDM loads immediate value into ACC."""
        result = run_program("LDM #42\nEND")
        assert result.status == "ok"
        assert result.final_state["acc"] == 42

    def test_ldd_sto(self):
        """LDD loads from memory, STO stores to memory."""
        opts = RunOptions(initial_memory={80: 100})
        result = run_program("LDD 80\nSTO 81\nEND", options=opts)
        assert result.status == "ok"
        assert result.final_state["acc"] == 100

    def test_ldi(self):
        """LDI loads indirect."""
        opts = RunOptions(initial_memory={80: 81, 81: 42})
        result = run_program("LDI 80\nEND", options=opts)
        assert result.status == "ok"
        assert result.final_state["acc"] == 42

    def test_ldx(self):
        """LDX loads indexed."""
        opts = RunOptions(initial_memory={85: 99})
        result = run_program("LDR #5\nLDX 80\nEND", options=opts)
        assert result.status == "ok"
        assert result.final_state["acc"] == 99
        assert result.final_state["ix"] == 5

    def test_ldr_immediate(self):
        """LDR #n sets IX."""
        result = run_program("LDR #10\nEND")
        assert result.status == "ok"
        assert result.final_state["ix"] == 10

    def test_ldr_acc(self):
        """LDR ACC sets IX from ACC."""
        result = run_program("LDM #25\nLDR ACC\nEND")
        assert result.status == "ok"
        assert result.final_state["ix"] == 25

    def test_mov_ix(self):
        """MOV IX sets IX from ACC."""
        result = run_program("LDM #15\nMOV IX\nEND")
        assert result.status == "ok"
        assert result.final_state["ix"] == 15

    def test_add_immediate(self):
        """ADD #n adds immediate."""
        result = run_program("LDM #10\nADD #5\nEND")
        assert result.status == "ok"
        assert result.final_state["acc"] == 15

    def test_add_memory(self):
        """ADD a adds from memory."""
        opts = RunOptions(initial_memory={80: 7})
        result = run_program("LDM #3\nADD 80\nEND", options=opts)
        assert result.status == "ok"
        assert result.final_state["acc"] == 10

    def test_sub_immediate(self):
        """SUB #n subtracts immediate."""
        result = run_program("LDM #10\nSUB #3\nEND")
        assert result.status == "ok"
        assert result.final_state["acc"] == 7

    def test_sub_memory(self):
        """SUB a subtracts from memory."""
        opts = RunOptions(initial_memory={80: 4})
        result = run_program("LDM #10\nSUB 80\nEND", options=opts)
        assert result.status == "ok"
        assert result.final_state["acc"] == 6

    def test_inc_acc(self):
        """INC ACC increments ACC."""
        result = run_program("LDM #5\nINC ACC\nEND")
        assert result.status == "ok"
        assert result.final_state["acc"] == 6

    def test_inc_ix(self):
        """INC IX increments IX."""
        result = run_program("LDR #3\nINC IX\nEND")
        assert result.status == "ok"
        assert result.final_state["ix"] == 4

    def test_dec_acc(self):
        """DEC ACC decrements ACC."""
        result = run_program("LDM #5\nDEC ACC\nEND")
        assert result.status == "ok"
        assert result.final_state["acc"] == 4

    def test_dec_ix(self):
        """DEC IX decrements IX."""
        result = run_program("LDR #3\nDEC IX\nEND")
        assert result.status == "ok"
        assert result.final_state["ix"] == 2

    def test_cmp_immediate_equal(self):
        """CMP #n sets flag True when equal."""
        opts = RunOptions(trace_include_flag=True)
        result = run_program("LDM #5\nCMP #5\nEND", options=opts)
        assert result.status == "ok"
        assert result.final_state["flag"] is True

    def test_cmp_immediate_not_equal(self):
        """CMP #n sets flag False when not equal."""
        opts = RunOptions(trace_include_flag=True)
        result = run_program("LDM #5\nCMP #10\nEND", options=opts)
        assert result.status == "ok"
        assert result.final_state["flag"] is False

    def test_cmp_memory(self):
        """CMP a compares with memory."""
        opts = RunOptions(initial_memory={80: 5}, trace_include_flag=True)
        result = run_program("LDM #5\nCMP 80\nEND", options=opts)
        assert result.status == "ok"
        assert result.final_state["flag"] is True

    def test_cmi(self):
        """CMI a compares indirect."""
        opts = RunOptions(initial_memory={80: 81, 81: 42}, trace_include_flag=True)
        result = run_program("LDM #42\nCMI 80\nEND", options=opts)
        assert result.status == "ok"
        assert result.final_state["flag"] is True

    def test_jmp(self):
        """JMP unconditional jump."""
        result = run_program("JMP 202\nLDM #99\nLDM #1\nEND")
        assert result.status == "ok"
        assert result.final_state["acc"] == 1

    def test_jpe_taken(self):
        """JPE jumps when flag True."""
        result = run_program("LDM #5\nCMP #5\nJPE 205\nLDM #99\nEND\nLDM #1\nEND")
        assert result.status == "ok"
        assert result.final_state["acc"] == 1

    def test_jpe_not_taken(self):
        """JPE falls through when flag False."""
        result = run_program("LDM #5\nCMP #10\nJPE 205\nLDM #99\nEND")
        assert result.status == "ok"
        assert result.final_state["acc"] == 99

    def test_jpn_taken(self):
        """JPN jumps when flag False."""
        result = run_program("LDM #5\nCMP #10\nJPN 205\nLDM #99\nEND\nLDM #1\nEND")
        assert result.status == "ok"
        assert result.final_state["acc"] == 1

    def test_jpn_not_taken(self):
        """JPN falls through when flag True."""
        result = run_program("LDM #5\nCMP #5\nJPN 205\nLDM #99\nEND")
        assert result.status == "ok"
        assert result.final_state["acc"] == 99


class TestIO:
    """Test I/O instructions."""

    def test_in(self):
        """IN reads character as ASCII code."""
        result = run_program("IN\nEND", input_text="A")
        assert result.status == "ok"
        assert result.final_state["acc"] == 65

    def test_in_multiple(self):
        """IN reads successive characters."""
        result = run_program("IN\nSTO 80\nIN\nSTO 81\nEND", input_text="AB")
        assert result.status == "ok"

    def test_in_underflow(self):
        """IN with empty buffer is error."""
        result = run_program("IN\nEND", input_text="")
        assert result.status == "error"
        assert result.error.type == "InputUnderflow"

    def test_out(self):
        """OUT writes character."""
        result = run_program("LDM #65\nOUT\nLDM #66\nOUT\nEND")
        assert result.status == "ok"
        assert result.output_text == "AB"

    def test_io_trace(self):
        """IO codes appear in trace."""
        opts = RunOptions(trace_include_io=True)
        result = run_program("IN\nOUT\nEND", input_text="X", options=opts)
        assert result.status == "ok"
        # IN instruction
        assert result.trace[1]["in_code"] == 88
        # OUT instruction
        assert result.trace[2]["out_code"] == 88


class TestRunner:
    """Test runner behavior."""

    def test_step_limit(self):
        """Step limit is enforced."""
        opts = RunOptions(max_steps=5)
        result = run_program("LOOP: JMP LOOP", options=opts)
        assert result.status == "error"
        assert result.error.type == "StepLimitExceeded"
        assert result.steps_executed == 5

    def test_trace_generation(self):
        """Trace is generated correctly."""
        opts = RunOptions(trace=True, trace_watch=[80])
        result = run_program("LDM #5\nSTO 80\nEND", options=opts)
        assert result.status == "ok"
        assert len(result.trace) == 4
        # After LDM
        assert result.trace[1]["acc"] == 5
        assert result.trace[1]["mem"]["80"] == 0
        # After STO
        assert result.trace[2]["acc"] == 5
        assert result.trace[2]["mem"]["80"] == 5

    def test_trace_includes_address(self):
        """Trace includes instruction address."""
        result = run_program("LDM #1\nLDM #2\nEND")
        assert result.trace[1]["addr"] == 200
        assert result.trace[2]["addr"] == 201
        assert result.trace[3]["addr"] == 202

    def test_overflow_normalization(self):
        """Overflow is normalized."""
        result = run_program("LDM #32767\nADD #1\nEND")
        assert result.status == "ok"
        assert result.final_state["acc"] == -32768

    def test_jump_without_compare(self):
        """JPE/JPN without CMP is error."""
        result = run_program("JPE 200")
        assert result.status == "error"
        assert result.error.type == "JumpWithoutCompare"

    def test_memory_out_of_bounds(self):
        """Access out of bounds is error."""
        opts = RunOptions(memory_size=100)
        result = run_program("LDD 150\nEND", options=opts)
        assert result.status == "error"
        assert result.error.type == "MemoryAccessError"

    def test_complex_loop(self):
        """Complex loop with counter."""
        program = """
        LDM #5
        STO 80
        LOOP: LDD 80
        CMP #0
        JPE DONE
        DEC ACC
        STO 80
        JMP LOOP
        DONE: END
        """
        opts = RunOptions(trace=True, trace_watch=[80])
        result = run_program(program, options=opts)
        assert result.status == "ok"
        assert result.final_state["acc"] == 0

    def test_trace_watch_list_in_result(self):
        """trace_watch is included in result."""
        opts = RunOptions(trace_watch=[80, 81, 82])
        result = run_program("END", options=opts)
        assert result.trace_watch == [80, 81, 82]


class TestAPIFormat:
    """Test result format matches API spec."""

    def test_success_result_format(self):
        """Success result has correct structure."""
        result = run_program("LDM #5\nEND")
        d = result.to_dict()
        assert "status" in d
        assert "output_text" in d
        assert "steps_executed" in d
        assert "final_state" in d
        assert "trace_watch" in d
        assert "trace" in d
        assert d["status"] == "ok"
        assert "acc" in d["final_state"]
        assert "ix" in d["final_state"]
        assert "pc" in d["final_state"]
        assert "flag" in d["final_state"]

    def test_error_result_format(self):
        """Error result has correct structure."""
        result = run_program("LDD 999")
        d = result.to_dict()
        assert d["status"] == "error"
        assert "error" in d
        assert "type" in d["error"]
        assert "message" in d["error"]
        assert "step" in d["error"]
        assert "addr" in d["error"]

"""Integration tests for all UI sample programs."""

import pytest
from core import run_program, RunOptions

def test_sample_echo():
    """Verify 'Echo Character' sample."""
    code = "; Echo one character\n\n200 IN\n201 OUT\n202 END"
    result = run_program(code, input_text="A", options=RunOptions(start_address=200))
    assert result.status == "ok"
    assert result.output_text == "A"
    assert result.steps_executed == 3

def test_sample_next_ascii():
    """Verify 'Read char and output next ASCII' sample."""
    code = "; Read char and output next ASCII\n\n200 IN\n201 ADD #1\n202 OUT\n203 END"
    result = run_program(code, input_text="A", options=RunOptions(start_address=200))
    assert result.status == "ok"
    assert result.output_text == "B"
    assert result.final_state["acc"] == 66

def test_sample_inc_mem():
    """Verify 'Increment MEM[81] by 1' sample."""
    code = "; Increment MEM[81] by 1\n81 8\n\n200 LDD 81\n201 INC ACC\n202 STO 81\n203 END"
    result = run_program(code, options=RunOptions(start_address=200))
    assert result.status == "ok"
    assert result.final_state["acc"] == 9
    assert result.trace[-1]["mem"]["81"] == 9

def test_sample_if_else():
    """Verify 'If/Else Condition' sample."""
    code = "; If X equals 10 then RESULT=0 else RESULT=1\n81 X: 10\n82 RESULT: 0\n\n200 START: LDD X\n201 CMP #10\n202 JPE THEN\n203 LDM #1\n204 STO RESULT\n205 JMP DONE\n206 THEN: LDM #0\n207 STO RESULT\n208 DONE: END"
    # Case: X is 10
    result = run_program(code, options=RunOptions(start_address=200))
    assert result.status == "ok"
    assert result.final_state["acc"] == 0
    assert result.trace[-1]["mem"]["82"] == 0
    
    # Case: X is not 10 (override initial memory)
    result_alt = run_program(code, options=RunOptions(start_address=200, initial_memory={81: 5}))
    assert result_alt.status == "ok"
    assert result_alt.final_state["acc"] == 1
    assert result_alt.trace[-1]["mem"]["82"] == 1

def test_sample_n_stars_nolabel():
    """Verify 'Output \'*\' N times (no labels)' sample."""
    code = "; Output '*' N times (no labels)\n81 5\n\n200 LDD 81\n201 CMP #0\n202 JPE 210\n203 LDM #42\n204 OUT\n205 LDD 81\n206 DEC ACC\n207 STO 81\n208 JMP 200\n210 END"
    result = run_program(code, options=RunOptions(start_address=200))
    assert result.status == "ok"
    assert result.output_text == "*****"
    assert result.final_state["acc"] == 0

def test_sample_n_stars_labels():
    """Verify 'Output \'*\' N times (labels for memory and jumps)' sample."""
    code = "; Output '*' N times (labels for memory and jumps)\n81 N: 5\n\n200 LOOP: LDD N\n201 CMP #0\n202 JPE STOP\n203 LDM #42\n204 OUT\n205 LDD N\n206 DEC ACC\n207 STO N\n208 JMP LOOP\n209 STOP: END"
    result = run_program(code, options=RunOptions(start_address=200))
    assert result.status == "ok"
    assert result.output_text == "*****"
    assert result.final_state["acc"] == 0

def test_sample_string_output():
    """Verify 'Output zero-terminated string using IX and LDX' sample."""
    code = "; Output zero-terminated string using IX and LDX\n80 STR: 72\n81 69\n82 76\n83 76\n84 79\n85 32\n86 87\n87 79\n88 82\n89 76\n90 68\n91 0\n\n200 INIT: LDR #0\n201 LOOP: LDX STR\n202 CMP #0\n203 JPE DONE\n204 OUT\n205 INC IX\n206 JMP LOOP\n207 DONE: END"
    result = run_program(code, options=RunOptions(start_address=200))
    assert result.status == "ok"
    assert result.output_text == "HELLO WORLD"
    assert result.final_state["acc"] == 0

def test_sample_sum_compare():
    """Verify 'Sum A and B, compare with TARGET, output \'Y\' or \'N\'' sample."""
    code = "; Sum A and B, compare with TARGET, output 'Y' or 'N'\n80 A: 7\n81 B: 3\n82 TARGET: 10\n\n200 START: LDD A\n201 ADD B\n202 CMP TARGET\n203 JPE YES\n204 LDM #78\n205 OUT\n206 JMP DONE\n207 YES: LDM #89\n208 OUT\n209 DONE: END"
    # Case: A + B = 10 (output 'Y')
    result = run_program(code, options=RunOptions(start_address=200))
    assert result.status == "ok"
    assert result.output_text == "Y"
    
    # Case: A + B != 10 (output 'N')
    result_alt = run_program(code, options=RunOptions(start_address=200, initial_memory={80: 5}))
    assert result_alt.status == "ok"
    assert result_alt.output_text == "N"


def test_sample_bit_mask_check():
    """Verify 'Bit mask check' sample."""
    code = "; Bit mask check: output 'Y' if (VALUE AND MASK) equals MASK, else output 'N'\n; Memory (address LABEL: value)\n80 VALUE: B00101101\n81 MASK:  #B00000101\n\n; Program (address [label:] instruction)\n200 START: LDD VALUE\n201 AND MASK\n202 CMP MASK\n203 JPE YES\n204 LDM #78\n205 OUT\n206 JMP DONE\n207 YES: LDM #89\n208 OUT\n209 DONE: END"
    result = run_program(code, options=RunOptions(start_address=200))
    assert result.status == "ok"
    assert result.output_text == "Y"

    result_alt = run_program(
        code,
        options=RunOptions(start_address=200, initial_memory={80: int("00101000", 2)}),
    )
    assert result_alt.status == "ok"
    assert result_alt.output_text == "N"


def test_sample_shift_toggle():
    """Verify 'Shift and toggle' sample."""
    code = "; Shift and toggle: ACC = (VALUE LSL 1) XOR TOGGLE, store in RESULT, output result byte\n; Memory (address LABEL: value)\n80 VALUE:  #B00001111\n81 TOGGLE: #B00110011\n82 RESULT: 0\n\n; Program (address [label:] instruction)\n200 START: LDD VALUE\n201 LSL #1\n202 XOR TOGGLE\n203 STO RESULT\n204 OUT\n205 END"
    opts = RunOptions(start_address=200, trace_watch=[82])
    result = run_program(code, options=opts)
    assert result.status == "ok"
    assert result.output_text == "-"
    assert result.trace[-1]["mem"]["82"] == 45


def test_sample_extract_high_nibble():
    """Verify 'Extract high nibble' sample."""
    code = "; Extract high nibble: ACC = (VALUE AND #B11110000) LSR 4, store in HIGH\n; Memory (address LABEL: value)\n80 VALUE: B10101100\n81 HIGH:  0\n\n; Program (address [label:] instruction)\n200 START: LDD VALUE\n201 AND #B11110000\n202 LSR #4\n203 STO HIGH\n204 END"
    opts = RunOptions(start_address=200, trace_watch=[81])
    result = run_program(code, options=opts)
    assert result.status == "ok"
    assert result.trace[-1]["mem"]["81"] == 10

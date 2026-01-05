# Cambridge Assembly Emulator

Web-based emulator for Cambridge A-Level Computer Science assembly language with instruction tracing.

## Features

- Full Cambridge AS/A-Level instruction set (data movement, arithmetic, bitwise, shifts, jumps, I/O)
- Trace table generation (exam-style)
- Configurable memory and word size
- Decimal and binary literals (`10`, `-3`, `B00001010`, `#B100`)
- Input/Output support
- Labels and comments
- Optional binary trace output for ACC & watched memory (`trace_value_format="bin"`)

## Supported Instructions

### Data Movement
- `LDM #n` — load an immediate value into ACC.
- `LDD a` — load ACC from memory address `a`.
- `LDI a` — load ACC from the address stored at `a` (double indirection).
- `LDX a` — load ACC from `a + IX`, enabling indexed addressing.
- `LDR #n` / `LDR ACC` — load IX from an immediate or from ACC.
- `MOV IX` — copy ACC into IX (shorthand for `LDR ACC`).
- `STO a` — store the value in ACC to memory address `a`.

### Arithmetic
- `ADD #n|a` — add an immediate or memory value to ACC.
- `SUB #n|a` — subtract an immediate or memory value from ACC.
- `INC ACC|IX` — increment ACC (default) or IX.
- `DEC ACC|IX` — decrement ACC (default) or IX.

### Logic / Comparison / Bitwise
- `CMP #n|a` — compare ACC against an immediate or memory value and set the compare flag.
- `CMI a` — compare ACC with the value loaded indirectly via address `a` and set the flag.
- `AND #n|a` — bitwise AND ACC with an immediate or memory operand.
- `OR #n|a` — bitwise OR ACC with an immediate or memory operand.
- `XOR #n|a` — bitwise XOR ACC with an immediate or memory operand.
- `LSL #n` — logical shift left ACC by `n` bits (zero fill).
- `LSR #n` — logical shift right ACC by `n` bits (zero fill).

### I/O
- `IN` — read the next input character (ASCII) into ACC.
- `OUT` — write the low byte of ACC to the output buffer.

### Control
- `JMP a` — unconditionally set the program counter to address `a`.
- `JPE a` — jump to `a` if the last comparison was equal.
- `JPN a` — jump to `a` if the last comparison was not equal.
- `END` — halt the program.

## Quick Start

```bash
# Install dependencies (either explicit packages or requirements file)
pip install fastapi uvicorn
# or
pip install -r requirements.txt

# Run server
python -m uvicorn web.app:app --host 0.0.0.0 --port 8080

# Open browser
open http://localhost:8080
```

## API

POST `/api/run` - Execute assembly program

```json
{
  "program": "LDM #5\nSTO 80\nEND",
  "input": "",
  "options": {
    "trace": true,
    "trace_watch": [80, 81],
    "trace_value_format": "bin",
    "initial_memory": {"80": 10}
  }
}
```

## Tests

```bash
python -m pytest tests/ -v
```

## License

MIT

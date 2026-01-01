# Cambridge Assembly Emulator

Web-based emulator for Cambridge A-Level Computer Science assembly language with instruction tracing.

## Features

- 19 assembly instructions (LDM, LDD, LDI, LDX, ADD, SUB, CMP, JMP, JPE, JPN, etc.)
- Trace table generation (exam-style)
- Configurable memory and word size
- Input/Output support
- Labels and comments

## Quick Start

```bash
# Install dependencies
pip install fastapi uvicorn

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

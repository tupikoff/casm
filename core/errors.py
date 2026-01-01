"""Custom exceptions for the Cambridge Assembly Emulator."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ErrorInfo:
    """Structured error information for API responses."""
    type: str
    message: str
    step: int
    addr: int
    source_line_no: Optional[int] = None
    source_text: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "message": self.message,
            "step": self.step,
            "addr": self.addr,
            "source_line_no": self.source_line_no,
            "source_text": self.source_text,
        }


class CASMError(Exception):
    """Base exception for all CASM errors."""

    def __init__(
        self,
        message: str,
        step: int = 0,
        addr: int = 0,
        source_line_no: Optional[int] = None,
        source_text: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.step = step
        self.addr = addr
        self.source_line_no = source_line_no
        self.source_text = source_text

    def to_error_info(self) -> ErrorInfo:
        return ErrorInfo(
            type=self.__class__.__name__,
            message=self.message,
            step=self.step,
            addr=self.addr,
            source_line_no=self.source_line_no,
            source_text=self.source_text,
        )


class ParseError(CASMError):
    """Error during program parsing."""
    pass


class CASMRuntimeError(CASMError):
    """Error during program execution."""
    pass


class MemoryAccessError(CASMRuntimeError):
    """Memory address out of bounds."""
    pass


class StepLimitExceeded(CASMRuntimeError):
    """Maximum step count exceeded."""
    pass


class JumpWithoutCompare(CASMRuntimeError):
    """Conditional jump executed without prior comparison."""
    pass


class InputUnderflow(CASMRuntimeError):
    """IN instruction with empty input buffer."""
    pass


class UnknownOpcode(ParseError):
    """Unknown instruction opcode."""
    pass


class InvalidOperand(ParseError):
    """Invalid operand for instruction."""
    pass


class AddressConflict(ParseError):
    """Conflicting address definitions."""
    pass

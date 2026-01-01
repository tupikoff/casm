"""CPU state model for the Cambridge Assembly Emulator."""

from typing import Optional


class CPU:
    """CPU state with registers and value normalization."""

    def __init__(self, word_bits: int = 16, signed: bool = True):
        self.word_bits = word_bits
        self.signed = signed

        # Pre-compute normalization bounds
        if signed:
            self._min_val = -(1 << (word_bits - 1))
            self._max_val = (1 << (word_bits - 1)) - 1
        else:
            self._min_val = 0
            self._max_val = (1 << word_bits) - 1

        self._mask = (1 << word_bits) - 1

        # Registers
        self.acc: int = 0
        self.ix: int = 0
        self.pc: int = 0
        self.flag: Optional[bool] = None
        self.ir: str = ""  # Current instruction for debugging
        self.halted: bool = False

    def normalize(self, value: int) -> int:
        """Normalize value to configured word width and signedness."""
        value = value & self._mask
        if self.signed and value > self._max_val:
            value -= 1 << self.word_bits
        return value

    def set_acc(self, value: int) -> None:
        """Set ACC with normalization."""
        self.acc = self.normalize(value)

    def set_ix(self, value: int) -> None:
        """Set IX with normalization."""
        self.ix = self.normalize(value)

    def get_state(self) -> dict:
        """Get current register state as dictionary."""
        return {
            "acc": self.acc,
            "ix": self.ix,
            "pc": self.pc,
            "flag": self.flag,
        }

    def reset(self, start_address: int = 0) -> None:
        """Reset CPU to initial state."""
        self.acc = 0
        self.ix = 0
        self.pc = start_address
        self.flag = None
        self.ir = ""
        self.halted = False

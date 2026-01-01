"""Memory model for the Cambridge Assembly Emulator."""

from typing import Optional
from .errors import MemoryAccessError


class Memory:
    """Linear memory model with configurable size and word width."""

    def __init__(
        self,
        size: int = 256,
        word_bits: int = 16,
        signed: bool = True,
        initial_values: Optional[dict[int, int]] = None,
    ):
        self.size = size
        self.word_bits = word_bits
        self.signed = signed
        self._data: list[int] = [0] * size

        # Pre-compute normalization bounds
        if signed:
            self._min_val = -(1 << (word_bits - 1))
            self._max_val = (1 << (word_bits - 1)) - 1
        else:
            self._min_val = 0
            self._max_val = (1 << word_bits) - 1

        self._mask = (1 << word_bits) - 1

        # Initialize with provided values
        if initial_values:
            for addr, val in initial_values.items():
                if 0 <= addr < size:
                    self._data[addr] = self.normalize(val)

    def normalize(self, value: int) -> int:
        """Normalize value to configured word width and signedness."""
        value = value & self._mask
        if self.signed and value > self._max_val:
            value -= 1 << self.word_bits
        return value

    def _check_bounds(self, addr: int) -> None:
        """Check if address is within valid range."""
        if addr < 0 or addr >= self.size:
            raise MemoryAccessError(f"Memory address out of range: {addr}")

    def read(self, addr: int) -> int:
        """Read value from memory address."""
        self._check_bounds(addr)
        return self._data[addr]

    def write(self, addr: int, value: int) -> None:
        """Write normalized value to memory address."""
        self._check_bounds(addr)
        self._data[addr] = self.normalize(value)

    def get_watched(self, addresses: list[int]) -> dict[str, int]:
        """Get values at watched addresses as string-keyed dict."""
        result = {}
        for addr in addresses:
            if 0 <= addr < self.size:
                result[str(addr)] = self._data[addr]
        return result

    def snapshot(self) -> list[int]:
        """Return a copy of the entire memory."""
        return self._data.copy()

"""Tests for the Memory module."""

import pytest
from core.memory import Memory
from core.errors import MemoryAccessError


class TestMemory:
    """Memory module tests."""

    def test_default_initialization(self):
        """Memory initializes with zeros."""
        mem = Memory(size=10)
        for i in range(10):
            assert mem.read(i) == 0

    def test_write_and_read(self):
        """Can write and read back values."""
        mem = Memory(size=10)
        mem.write(5, 42)
        assert mem.read(5) == 42

    def test_bounds_check_read(self):
        """Reading out of bounds raises error."""
        mem = Memory(size=10)
        with pytest.raises(MemoryAccessError):
            mem.read(10)
        with pytest.raises(MemoryAccessError):
            mem.read(-1)
        with pytest.raises(MemoryAccessError):
            mem.read(100)

    def test_bounds_check_write(self):
        """Writing out of bounds raises error."""
        mem = Memory(size=10)
        with pytest.raises(MemoryAccessError):
            mem.write(10, 0)
        with pytest.raises(MemoryAccessError):
            mem.write(-1, 0)

    def test_initial_values(self):
        """Memory can be initialized with values."""
        mem = Memory(size=100, initial_values={80: 10, 81: 8, 82: 80})
        assert mem.read(80) == 10
        assert mem.read(81) == 8
        assert mem.read(82) == 80
        assert mem.read(79) == 0

    def test_normalization_signed_16bit(self):
        """Values are normalized to 16-bit signed."""
        mem = Memory(size=10, word_bits=16, signed=True)
        mem.write(0, 32767)
        assert mem.read(0) == 32767
        mem.write(0, 32768)
        assert mem.read(0) == -32768
        mem.write(0, -1)
        assert mem.read(0) == -1
        mem.write(0, 65536)
        assert mem.read(0) == 0

    def test_normalization_unsigned_16bit(self):
        """Values are normalized to 16-bit unsigned."""
        mem = Memory(size=10, word_bits=16, signed=False)
        mem.write(0, 65535)
        assert mem.read(0) == 65535
        mem.write(0, 65536)
        assert mem.read(0) == 0
        mem.write(0, -1)
        assert mem.read(0) == 65535

    def test_get_watched(self):
        """Get watched addresses as dict."""
        mem = Memory(size=100, initial_values={80: 10, 81: 8, 82: 80})
        watched = mem.get_watched([80, 81, 82, 83])
        assert watched == {"80": 10, "81": 8, "82": 80, "83": 0}

    def test_snapshot(self):
        """Snapshot returns copy of memory."""
        mem = Memory(size=5, initial_values={0: 1, 2: 3})
        snap = mem.snapshot()
        assert snap == [1, 0, 3, 0, 0]
        snap[0] = 99
        assert mem.read(0) == 1  # Original unchanged

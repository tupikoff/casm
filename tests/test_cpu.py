"""Tests for the CPU module."""

import pytest
from core.cpu import CPU


class TestCPU:
    """CPU module tests."""

    def test_default_initialization(self):
        """CPU initializes with zeros."""
        cpu = CPU()
        assert cpu.acc == 0
        assert cpu.ix == 0
        assert cpu.pc == 0
        assert cpu.flag is None
        assert cpu.halted is False

    def test_set_acc(self):
        """ACC can be set."""
        cpu = CPU()
        cpu.set_acc(42)
        assert cpu.acc == 42

    def test_set_ix(self):
        """IX can be set."""
        cpu = CPU()
        cpu.set_ix(10)
        assert cpu.ix == 10

    def test_acc_normalization(self):
        """ACC is normalized to word width."""
        cpu = CPU(word_bits=16, signed=True)
        cpu.set_acc(32768)
        assert cpu.acc == -32768
        cpu.set_acc(-1)
        assert cpu.acc == -1

    def test_ix_normalization(self):
        """IX is normalized to word width."""
        cpu = CPU(word_bits=16, signed=True)
        cpu.set_ix(65536)
        assert cpu.ix == 0

    def test_get_state(self):
        """Get state returns correct dict."""
        cpu = CPU()
        cpu.acc = 10
        cpu.ix = 5
        cpu.pc = 200
        cpu.flag = True
        state = cpu.get_state()
        assert state == {"acc": 10, "ix": 5, "pc": 200, "flag": True}

    def test_reset(self):
        """Reset returns CPU to initial state."""
        cpu = CPU()
        cpu.acc = 100
        cpu.ix = 50
        cpu.pc = 250
        cpu.flag = True
        cpu.halted = True
        cpu.reset(start_address=300)
        assert cpu.acc == 0
        assert cpu.ix == 0
        assert cpu.pc == 300
        assert cpu.flag is None
        assert cpu.halted is False

"""Unit tests for torch device resolution."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def fake_torch_cpu(monkeypatch):
    torch = MagicMock()
    torch.cuda.is_available.return_value = False
    monkeypatch.setitem(sys.modules, "torch", torch)
    return torch


@pytest.fixture
def fake_torch_cuda(monkeypatch):
    torch = MagicMock()
    torch.cuda.is_available.return_value = True
    torch.cuda.device_count.return_value = 1
    torch.cuda.get_device_name.return_value = "Mock GPU"
    torch.cuda.get_device_capability.return_value = (8, 9)
    torch.cuda.current_device.return_value = 0
    monkeypatch.setitem(sys.modules, "torch", torch)
    return torch


def test_resolve_cpu_explicit(monkeypatch):
    fake = MagicMock()
    fake.cuda.is_available.return_value = True
    monkeypatch.setitem(sys.modules, "torch", fake)
    from app.core.device import resolve_torch_device

    assert resolve_torch_device("cpu") == "cpu"


def test_resolve_auto_uses_cuda_when_available(fake_torch_cuda):
    from app.core.device import resolve_torch_device

    assert resolve_torch_device("auto").startswith("cuda")


def test_resolve_auto_cpu_when_cuda_unavailable(fake_torch_cpu):
    from app.core.device import resolve_torch_device

    assert resolve_torch_device("auto") == "cpu"


def test_resolve_cuda_falls_back_when_unavailable(fake_torch_cpu):
    from app.core.device import resolve_torch_device

    assert resolve_torch_device("cuda") == "cpu"


def test_resolve_cuda_ok_when_available(fake_torch_cuda):
    from app.core.device import resolve_torch_device

    assert resolve_torch_device("cuda:0") == "cuda:0"

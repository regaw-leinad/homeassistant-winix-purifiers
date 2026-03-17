"""Shared test fixtures."""

from __future__ import annotations

import os

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests (requires WINIX_* env vars)",
    )


@pytest.fixture
def winix_username() -> str | None:
    return os.environ.get("WINIX_USERNAME")


@pytest.fixture
def winix_password() -> str | None:
    return os.environ.get("WINIX_PASSWORD")


@pytest.fixture
def winix_device_id() -> str | None:
    return os.environ.get("WINIX_DEVICE_ID")


@pytest.fixture
def has_credentials(winix_username: str | None, winix_password: str | None) -> bool:
    return bool(winix_username and winix_password)


@pytest.fixture
def has_device(has_credentials: bool, winix_device_id: str | None) -> bool:
    return has_credentials and bool(winix_device_id)

"""Fake implementation of multiprocessing.Pool for test purposes"""

from __future__ import annotations
from typing import Callable, NoReturn, Any, Self
from types import TracebackType

import pytest
from pytest_mock import MockFixture


@pytest.fixture(autouse=True)
def fake_pool(mocker: MockFixture) -> None:
    """Fixture to patch in FakePool as an alternative for multiprocessing.Pool"""
    mocker.patch("multiprocessing.get_context", return_value=FakeContext())


class FakePool:
    """
    This is a dummy variation on multiprocessing.Pool, which simply
    calls the function and callback immediately with no parallelism.
    It has ony the bits required for ukechords' tests to be run.

    This means the function is called in the same context it's called
    in, which is especially helpful in tests where we can register
    mocks on what would otherwise occur in forks, and monitor their
    behavior.
    """

    def apply_async(
        self,
        func: Callable[..., Any],
        args: list[Any],
        callback: Callable[..., None],
        error_callback: Callable[[BaseException], NoReturn],
    ) -> None:
        """Dummy apply_async which immediately calls its callbacks as required"""
        try:
            callback(func(*args))
        except Exception as e:  # pylint: disable=broad-exception-caught
            error_callback(e)

    def terminate(self) -> None:
        """Dummmy terminate method"""

    def close(self) -> None:
        """Dummy close method"""

    def join(self) -> None:
        """Dummy join method"""

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, _: type[BaseException], __: BaseException | None, ___: TracebackType | None
    ) -> None:
        pass


class FakeContext:
    """
    Dummy context for multiprocessing to return our FakePool
    """

    # pylint: disable=too-few-public-methods,invalid-name,missing-function-docstring
    def Pool(self) -> FakePool:
        return FakePool()

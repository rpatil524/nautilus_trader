# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2024 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

import asyncio
from collections.abc import Callable

from nautilus_trader.common.component import Logger


class RetryManager:
    """
    Provides retry state management for an HTTP request.

    Parameters
    ----------
    max_retries : int
        The maximum number of retries before failure.
    retry_delay_secs : float
        The delay (seconds) between retry attempts.
    logger : Logger
        The logger for the manager.
    exc_types : tuple[Type[BaseException], ...]
        The exception types to handle for retries.
    retry_check : Callable[[BaseException], None], optional
        A function that performs additional checks on the exception.
        If the function returns `False`, a retry will not be attempted.

    """

    def __init__(
        self,
        max_retries: int,
        retry_delay_secs: float,
        logger: Logger,
        exc_types: tuple[type[BaseException], ...],
        retry_check: Callable[[BaseException], bool] | None = None,
    ) -> None:
        self.max_retries = max_retries
        self.retry_delay_secs = retry_delay_secs
        self.retries = 0
        self.exc_types = exc_types
        self.retry_check = retry_check
        self.cancel_event = asyncio.Event()
        self.log = logger

        self.name: str | None = None
        self.details: list[object] | None = None
        self.details_str: str | None = None
        self.result: bool = False
        self.message: str | None = None

    def __repr__(self) -> str:
        return f"<{type(self).__name__}(name='{self.name}', details={self.details}) at {hex(id(self))}>"

    async def run(self, name: str, details: list[object] | None, func, *args, **kwargs):
        """
        Execute the given `func` with retry management.

        If an exception in `self.exc_types` is raised, a warning is logged, and the function is
        retried after a delay until the maximum retries are reached, at which point an error is logged.

        Parameters
        ----------
        name : str
            The name of the operation to run.
        details : list[object], optional
            The operation details such as identifiers.
        func : Awaitable
            The function to execute.
        args : Any
            Positional arguments to pass to the function `func`.
        kwargs : Any
            Keyword arguments to pass to the function `func`.

        """
        self.name = name
        self.details = details

        try:
            while True:
                if self.cancel_event.is_set():
                    self._cancel()
                    return

                try:
                    await func(*args, **kwargs)
                    self.result = True
                    return  # Successful request
                except self.exc_types as e:
                    self.log.warning(repr(e))
                    if (
                        (self.retry_check and not self.retry_check(e))
                        or not self.max_retries
                        or self.retries >= self.max_retries
                    ):
                        self._log_error()
                        self.result = False
                        self.message = str(e)
                        return  # Operation failed

                    self.retries += 1
                    self._log_retry()
                    await asyncio.sleep(self.retry_delay_secs)
        except asyncio.CancelledError:
            self._cancel()

    def cancel(self) -> None:
        """
        Cancel the retry operation.
        """
        self.log.debug(f"Canceling {self!r}")
        self.cancel_event.set()

    def clear(self) -> None:
        """
        Clear all state from this retry manager.
        """
        self.retries = 0
        self.name = None
        self.details = None
        self.details_str = None
        self.result = False
        self.message = None

    def _cancel(self) -> None:
        self.log.warning(f"Canceled retry for '{self.name}'")
        self.result = False
        self.message = "Canceled retry"

    def _log_retry(self) -> None:
        self.log.warning(
            f"Retrying {self.retries}/{self.max_retries} for '{self.name}' "
            f"in {self.retry_delay_secs}s{self._details_str()}",
        )

    def _log_error(self) -> None:
        self.log.error(
            f"Failed on '{self.name}'{self._details_str()}",
        )

    def _details_str(self) -> str:
        if not self.details:
            return ""

        if not self.details_str:
            self.details_str = ": " + ", ".join([repr(x) for x in self.details])

        return self.details_str


class RetryManagerPool:
    """
    Provides a pool of `RetryManager`s.

    Parameters
    ----------
    pool_size : int
        The size of the retry manager pool.
    max_retries : int
        The maximum number of retries before failure.
    retry_delay_secs : float
        The delay (seconds) between retry attempts.
    logger : Logger
        The logger for retry managers.
    exc_types : tuple[Type[BaseException], ...]
        The exception types to handle for retries.
    retry_check : Callable[[BaseException], None], optional
        A function that performs additional checks on the exception.
        If the function returns `False`, a retry will not be attempted.

    """

    def __init__(
        self,
        pool_size: int,
        max_retries: int,
        retry_delay_secs: float,
        logger: Logger,
        exc_types: tuple[type[BaseException], ...],
        retry_check: Callable[[BaseException], bool] | None = None,
    ) -> None:
        self.max_retries = max_retries
        self.retry_delay_secs = retry_delay_secs
        self.logger = logger
        self.exc_types = exc_types
        self.retry_check = retry_check
        self.pool_size = pool_size
        self._pool: list[RetryManager] = [self._create_manager() for _ in range(pool_size)]
        self._lock = asyncio.Lock()
        self._current_manager: RetryManager | None = None
        self._active_managers: set[RetryManager] = set()

    def _create_manager(self) -> RetryManager:
        return RetryManager(
            max_retries=self.max_retries,
            retry_delay_secs=self.retry_delay_secs,
            logger=self.logger,
            exc_types=self.exc_types,
            retry_check=self.retry_check,
        )

    async def __aenter__(self) -> RetryManager:
        """
        Asynchronous context manager entry.

        Acquires a `RetryManager` from the pool.

        """
        self._current_manager = await self.acquire()
        return self._current_manager

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """
        Asynchronous context manager exit.

        Releases the `RetryManager` back into the pool.

        """
        try:
            if self._current_manager:
                await self.release(self._current_manager)
        finally:
            # Drop reference to avoid lingering state issues
            self._current_manager = None

    def shutdown(self) -> None:
        """
        Gracefully shuts down the retry manager pool, ensuring all active retry managers
        are canceled.

        This method should be called when the component using the pool is stopped, to
        ensure that all resources are released in an orderly manner.

        """
        self.logger.info("Shutting down retry manager pool")
        for retry_manager in self._active_managers:
            retry_manager.cancel()
        self._active_managers.clear()

    async def acquire(self) -> RetryManager:
        """
        Acquire a `RetryManager` from the pool, or creates a new one if the pool is
        empty.

        Returns
        -------
        RetryManager

        """
        async with self._lock:
            retry_manager = self._pool.pop() if self._pool else self._create_manager()
            self._active_managers.add(retry_manager)
            return retry_manager

    async def release(self, retry_manager: RetryManager) -> None:
        """
        Release the given `retry_manager` back into the pool.

        If the pool is already full, the `retry_manager` will be dropped.

        Parameters
        ----------
        retry_manager : RetryManager
            The manager to be returned to the pool.

        """
        retry_manager.clear()
        self._active_managers.discard(retry_manager)

        async with self._lock:
            if len(self._pool) < self.pool_size:
                self._pool.append(retry_manager)
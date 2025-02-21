from typing import Any, Protocol


class SnapshotFunc(Protocol):
    """Callable protocol for the snapshot function."""

    def __call__(
        self,
        data: Any,
        /,
        *,
        name: str = ...,
        json: bool = ...,
    ) -> None:
        """Check snapshot."""

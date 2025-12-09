"""
An asyncio-compatible token bucket rate limiter.
"""

import asyncio
import random
import time


class TokenBucketRateLimiter:
    """A simple asyncio-compatible token bucket rate limiter.

    This rate limiter controls the rate of asynchronous operations using a
    token bucket algorithm. Tokens are added over time at a fixed rate, and
    acquiring a token may block until sufficient tokens become available.

    Attributes:
        rate: Tokens added per second.
        capacity: Maximum number of tokens the bucket can hold.
        tokens: Current number of available tokens.
        timestamp: Last update time for token refill.
        jitter_strength: Maximum absolute jitter added to wait time (± seconds).
        lock: Internal asyncio lock protecting state transitions.
    """

    __slots__ = (
        "rate",
        "capacity",
        "tokens",
        "timestamp",
        "lock",
        "jitter_strength",
    )

    def __init__(
        self,
        rate: float,
        burst: int = 10,
        jitter_strength: float = 0.3,
    ) -> None:
        """Initializes the token bucket.

        Args:
            rate: Number of tokens added per second.
            burst: Maximum bucket size (burst capacity).
            jitter_strength: Maximum jitter applied to wait time, expressed
                as an absolute additive range in seconds (± value).

        Example:
            With ``jitter_strength=0.3``, the final wait time will be adjusted
            by a random amount in the range ``[-0.3, +0.3]`` seconds.
        """
        self.rate = rate
        self.capacity = burst
        self.tokens = float(burst)
        self.timestamp = time.monotonic()
        self.lock = asyncio.Lock()
        self.jitter_strength = jitter_strength

    async def wait(self) -> None:
        """Acquires a token, blocking asynchronously if necessary.

        If a token is available, it is consumed immediately. Otherwise this
        method computes the required wait time for the next token to be
        generated, applies optional jitter, and awaits accordingly.
        """
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.timestamp

            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.timestamp = now

            if self.tokens >= 1.0:
                self.tokens = max(0.0, self.tokens - 1.0)
                return

            wait_time = (1.0 - self.tokens) / self.rate
            jitter = random.uniform(
                -self.jitter_strength,
                self.jitter_strength,
            )
            total_wait = max(0.0, wait_time + jitter)

        await asyncio.sleep(total_wait)

        async with self.lock:
            self.timestamp = time.monotonic()
            self.tokens = max(0.0, self.tokens - 1.0)

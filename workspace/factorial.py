#!/usr/bin/env python3
"""
A simple factorial utility with a reusable function and a CLI.

Usage examples:
  python factorial.py 5           # prints 120
  python factorial.py 100 --mod 1000000007  # prints 100! modulo 1e9+7

Note: Python integers have arbitrary precision, but very large n can take time.
"""
from __future__ import annotations
import argparse
from typing import Optional


def factorial(n: int) -> int:
    """Compute n! for a non-negative integer n.

    Parameters:
        n (int): non-negative integer

    Returns:
        int: n!

    Raises:
        TypeError: if n is not an int
        ValueError: if n is negative

    Examples:
        >>> factorial(5)
        120
        >>> factorial(0)
        1
    """
    if not isinstance(n, int):
        raise TypeError(f"n must be an int, got {type(n).__name__}")
    if n < 0:
        raise ValueError("n must be a non-negative integer")

    result = 1
    # Iterative approach avoids recursion overhead/limits and is clear.
    for i in range(2, n + 1):
        result *= i
    return result


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Compute factorial n! for a non-negative integer n.")
    parser.add_argument("n", type=int, help="non-negative integer")
    parser.add_argument(
        "--mod",
        type=int,
        default=None,
        help="optional modulus to compute n! modulo m (must be positive)",
    )
    args = parser.parse_args(argv)

    try:
        res = factorial(args.n)
        if args.mod is not None:
            if args.mod <= 0:
                raise ValueError("--mod must be a positive integer")
            res %= args.mod
        print(res)
    except Exception as e:
        # Use argparse's error formatting for consistent CLI behavior
        parser.error(str(e))


if __name__ == "__main__":
    main()

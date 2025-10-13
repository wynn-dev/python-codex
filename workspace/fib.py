#!/usr/bin/env python3
"""
Fibonacci utilities with CLI.

Supports:
- nth: Compute the nth Fibonacci number
- list: Produce the first N Fibonacci numbers
- upto: Produce Fibonacci numbers up to a maximum value

Conventions:
- Zero-based indexing (default): F0 = 0, F1 = 1, F2 = 1, ...
- One-based indexing (with --one-based): F1 = 1, F2 = 1, ...

Examples:
  - 10th (zero-based) Fibonacci number:
      python fib.py nth 10
  - 10th (one-based) Fibonacci number:
      python fib.py nth 10 --one-based
  - First 10 numbers (zero-based sequence starting at 0):
      python fib.py list 10
  - First 10 numbers (one-based sequence starting at 1):
      python fib.py list 10 --one-based
  - Fibonacci numbers up to 100 (inclusive by default):
      python fib.py upto 100

Implementation details:
- Uses fast doubling for efficient nth computation in O(log n) time.
- Provides generator-based listing for sequences.

"""
from __future__ import annotations

import argparse
from typing import Generator, List, Tuple


def _fib_doubling(n: int) -> Tuple[int, int]:
    """Return (F(n), F(n+1)) using fast doubling.

    Based on identities:
      F(2k)   = F(k) * [2*F(k+1) − F(k)]
      F(2k+1) = F(k+1)^2 + F(k)^2

    Runs in O(log n) time.
    """
    if n == 0:
        return (0, 1)
    else:
        a, b = _fib_doubling(n // 2)  # a = F(k), b = F(k+1)
        c = a * ((b << 1) - a)        # F(2k)
        d = a * a + b * b              # F(2k+1)
        if n % 2 == 0:
            return (c, d)
        else:
            return (d, c + d)


def fib(n: int) -> int:
    """Return the nth Fibonacci number with zero-based indexing.

    - Requires n >= 0
    - F0 = 0, F1 = 1
    - Uses fast doubling for performance on large n
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    return _fib_doubling(n)[0]


def fibonacci_sequence(one_based: bool = False) -> Generator[int, None, None]:
    """Yield an infinite Fibonacci sequence.

    - If one_based is False: yields 0, 1, 1, 2, 3, ...
    - If one_based is True:  yields 1, 1, 2, 3, 5, ...
    """
    if one_based:
        a, b = 1, 1
    else:
        a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b


def fibonacci_list(count: int, one_based: bool = False) -> List[int]:
    """Return a list containing the first `count` Fibonacci numbers.

    - count must be >= 0
    - one_based controls whether the sequence starts at 0 or 1
    """
    if count < 0:
        raise ValueError("count must be non-negative")
    seq = []
    gen = fibonacci_sequence(one_based=one_based)
    for _ in range(count):
        seq.append(next(gen))
    return seq


def fibonacci_upto(max_value: int, include_max: bool = True, one_based: bool = False) -> List[int]:
    """Return Fibonacci numbers up to a maximum value.

    - If include_max is True (default), include terms equal to max_value
    - If one_based is True, starts at 1; otherwise starts at 0
    """
    if max_value < 0:
        return []
    res = []
    for x in fibonacci_sequence(one_based=one_based):
        if include_max:
            if x > max_value:
                break
        else:
            if x >= max_value:
                break
        res.append(x)
    return res


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fibonacci utilities")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # nth command
    p_nth = subparsers.add_parser("nth", help="Compute the nth Fibonacci number")
    p_nth.add_argument("n", type=int, help="Index n (non-negative; use --one-based for F1=1)")
    p_nth.add_argument("--one-based", action="store_true", help="Use one-based indexing (F1=1)")

    # list command
    p_list = subparsers.add_parser("list", help="List the first N Fibonacci numbers")
    p_list.add_argument("count", type=int, help="Number of terms to list (non-negative)")
    p_list.add_argument("--one-based", action="store_true", help="Start sequence at 1 (1,1,2,3,...) instead of 0")
    p_list.add_argument("--sep", default=", ", help="Separator for output (default: ', ')")

    # upto command
    p_upto = subparsers.add_parser("upto", help="List Fibonacci numbers up to a maximum value")
    p_upto.add_argument("max_value", type=int, help="Maximum value")
    p_upto.add_argument("--exclude-max", action="store_true", help="Exclude terms equal to the maximum value")
    p_upto.add_argument("--one-based", action="store_true", help="Start sequence at 1 (1,1,2,3,...) instead of 0")
    p_upto.add_argument("--sep", default=", ", help="Separator for output (default: ', ')")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "nth":
        n = args.n
        if args.one_based:
            if n <= 0:
                raise SystemExit("For one-based indexing, n must be >= 1")
            # For one-based indexing, F1 = 1 equals F(1) in zero-based indexing
            result = fib(n)
        else:
            if n < 0:
                raise SystemExit("n must be >= 0")
            result = fib(n)
        print(result)

    elif args.command == "list":
        count = args.count
        if count < 0:
            raise SystemExit("count must be >= 0")
        seq = fibonacci_list(count, one_based=args.one_based)
        print(args.sep.join(str(x) for x in seq))

    elif args.command == "upto":
        max_value = args.max_value
        include_max = not args.exclude_max
        seq = fibonacci_upto(max_value, include_max=include_max, one_based=args.one_based)
        print(args.sep.join(str(x) for x in seq))

    else:
        parser.error("Unknown command")


if __name__ == "__main__":
    main()

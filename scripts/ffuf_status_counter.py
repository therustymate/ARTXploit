import json
from collections import Counter
from argparse import ArgumentParser


def status_stats(path: str) -> Counter:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return Counter(
        result["status"]
        for result in data.get("results", [])
        if "status" in result
    )


if __name__ == "__main__":
    parser = ArgumentParser(
        prog="ffuf-stat",
        description="Show HTTP status statistics from ffuf JSON output"
    )
    parser.add_argument(
        "json_file",
        help="ffuf JSON output file"
    )

    args = parser.parse_args()

    stats = status_stats(args.json_file)

    total = sum(stats.values())

    print(f"Total results: {total}")
    print("-" * 24)

    for status, count in sorted(stats.items()):
        print(f"{status}: {count}")
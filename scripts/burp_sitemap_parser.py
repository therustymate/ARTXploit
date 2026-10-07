from argparse import ArgumentParser
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


def parse_burp_sitemap(filename: str):
    root = ET.parse(filename).getroot()

    endpoints = set()

    for item in root.findall(".//item"):
        url = item.findtext("url")
        method = item.findtext("method", "GET")

        if not url:
            continue

        parsed = urlsplit(url)
        endpoint = parsed.path

        if parsed.query:
            endpoint += f"?{parsed.query}"

        endpoints.add((method, endpoint))

    return sorted(endpoints)


if __name__ == "__main__":
    parser = ArgumentParser(
        prog="burpmap",
        description="Extract endpoints from Burp Suite sitemap XML"
    )
    parser.add_argument(
        "xml",
        help="Burp Suite sitemap XML file"
    )

    args = parser.parse_args()

    for method, endpoint in parse_burp_sitemap(args.xml):
        print(f"{endpoint}")
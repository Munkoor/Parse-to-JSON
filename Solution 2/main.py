import json
from itertools import islice
from dataclasses import asdict

from realtylink_parser import RealtyLinkParser


def main() -> None:
    with open("apartments.json", "w") as f:
        parser = RealtyLinkParser()
        apartments = list(map(asdict, islice(parser.parse(), 60)))
        json.dump(apartments, f, indent=4)


if __name__ == "__main__":
    main()

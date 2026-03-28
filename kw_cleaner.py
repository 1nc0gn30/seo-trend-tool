import argparse
from pathlib import Path

import pandas as pd

from seotrendtool_core import load_keywords


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean and dedupe seed keywords from TXT/CSV into a normalized file."
    )
    parser.add_argument("--input", required=True, help="Input TXT/CSV keyword file")
    parser.add_argument("--output", default="keywords.cleaned.txt", help="Output TXT/CSV file")
    parser.add_argument("--lowercase", action="store_true", help="Lowercase all keywords")
    parser.add_argument("--min-length", type=int, default=1, help="Minimum keyword length")
    parser.add_argument("--sort", action="store_true", help="Sort alphabetically")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        keywords = load_keywords(args.input)
    except Exception as exc:
        print(f"[error] {exc}")
        return 1

    processed = []
    for kw in keywords:
        item = kw.strip()
        if args.lowercase:
            item = item.lower()
        if len(item) >= args.min_length:
            processed.append(item)

    processed = list(dict.fromkeys(processed))
    if args.sort:
        processed = sorted(processed)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.suffix.lower() == ".csv":
        pd.DataFrame({"keyword": processed}).to_csv(output_path, index=False)
    else:
        output_path.write_text("\n".join(processed) + ("\n" if processed else ""), encoding="utf-8")

    print(f"[ok] Wrote {len(processed)} cleaned keywords -> {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

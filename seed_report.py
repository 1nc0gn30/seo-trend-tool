import argparse
from pathlib import Path

import pandas as pd

from seotrendtool_core import summarize_by_seed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create seed-level summary metrics from opportunities CSV.")
    parser.add_argument("--input", default="seo_opportunities.csv", help="Input opportunities CSV")
    parser.add_argument("--output", default="seed_summary.csv", help="Output summary CSV")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    in_path = Path(args.input)
    if not in_path.exists():
        print(f"[error] File not found: {in_path}")
        return 1

    df = pd.read_csv(in_path)
    summary = summarize_by_seed(df)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out_path, index=False)
    print(f"[ok] Wrote seed summary ({len(summary)} rows) -> {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

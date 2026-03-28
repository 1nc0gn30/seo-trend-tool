import argparse
from pathlib import Path

import pandas as pd

from seotrendtool_core import rank_opportunities


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rank SEO opportunities from exported CSV and print quick wins."
    )
    parser.add_argument("--input", default="seo_opportunities.csv", help="Input opportunities CSV")
    parser.add_argument("--output", default="seo_opportunities_ranked.csv", help="Output ranked CSV")
    parser.add_argument("--top", type=int, default=20, help="Top N rows to print")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"[error] File not found: {input_path}")
        return 1

    df = pd.read_csv(input_path)
    if df.empty:
        print("[info] Input file is empty.")
        return 0

    ranked = rank_opportunities(df)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ranked.to_csv(output_path, index=False)

    cols = [c for c in ["Seed_Keyword", "Recommended_Long_Tail", "Growth_Value", "Priority_Score"] if c in ranked.columns]
    preview = ranked[cols].head(max(args.top, 1))

    print(f"[ok] Saved ranked opportunities -> {output_path.resolve()}")
    print("\nTop ranked opportunities:")
    print(preview.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

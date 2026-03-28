import argparse
from pathlib import Path

import pandas as pd

from seotrendtool_core import build_markdown_brief, rank_opportunities


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a markdown SEO brief from opportunities CSV.")
    parser.add_argument("--input", default="seo_opportunities.csv", help="Input opportunities CSV")
    parser.add_argument("--output", default="seo_brief.md", help="Output markdown file")
    parser.add_argument("--top", type=int, default=15, help="Top opportunities to include")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    in_path = Path(args.input)
    if not in_path.exists():
        print(f"[error] File not found: {in_path}")
        return 1

    df = pd.read_csv(in_path)
    ranked = rank_opportunities(df)
    brief = build_markdown_brief(ranked, top_n=args.top)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(brief, encoding="utf-8")
    print(f"[ok] Wrote brief -> {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

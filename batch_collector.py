import argparse
from math import ceil
from pathlib import Path

import pandas as pd

from seotrendtool_core import fetch_rising_keywords, load_keywords, rank_opportunities


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect trends in batches for better reliability.")
    parser.add_argument("--input", required=True, help="Seed keywords TXT/CSV")
    parser.add_argument("--output", default="seo_opportunities_batched.csv", help="Output CSV")
    parser.add_argument("--chunk-size", type=int, default=10, help="Keywords per batch")
    parser.add_argument("--timeframe", default="today 12-m", help="Google Trends timeframe")
    parser.add_argument("--geo", default="US", help="Country code or empty for global")
    parser.add_argument("--growth-threshold", type=int, default=350, help="Min growth percent")
    parser.add_argument("--min-sleep", type=float, default=1.5, help="Min sleep between keywords")
    parser.add_argument("--max-sleep", type=float, default=3.0, help="Max sleep between keywords")
    parser.add_argument("--retries", type=int, default=1, help="Retries per keyword")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        seeds = load_keywords(args.input)
    except Exception as exc:
        print(f"[error] {exc}")
        return 1

    if not seeds:
        print("[error] No keywords found.")
        return 1

    chunk_size = max(1, args.chunk_size)
    total_batches = ceil(len(seeds) / chunk_size)
    collected = []

    for i in range(total_batches):
        start = i * chunk_size
        end = start + chunk_size
        batch = seeds[start:end]
        print(f"[batch] {i + 1}/{total_batches} | keywords={len(batch)}")

        try:
            df = fetch_rising_keywords(
                keywords=batch,
                timeframe=args.timeframe,
                geo=args.geo,
                growth_threshold=args.growth_threshold,
                max_keywords=len(batch),
                min_sleep=args.min_sleep,
                max_sleep=args.max_sleep,
                retries=args.retries,
            )
        except Exception as exc:
            print(f"[warn] Batch {i + 1} failed: {exc}")
            continue

        if not df.empty:
            collected.append(df)
            print(f"[ok] Batch {i + 1} produced {len(df)} rows")
        else:
            print(f"[info] Batch {i + 1} produced no rows")

    if not collected:
        print("[info] No opportunities found across all batches.")
        return 0

    merged = pd.concat(collected, ignore_index=True)
    ranked = rank_opportunities(merged).drop_duplicates(
        subset=["Seed_Keyword", "Recommended_Long_Tail"], keep="first"
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    ranked.to_csv(out, index=False)
    print(f"[ok] Wrote {len(ranked)} total rows -> {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

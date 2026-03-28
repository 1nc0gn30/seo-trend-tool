import argparse
import sys
from pathlib import Path

from ai_clients import provider_runtime_note, run_ai_analysis
from seotrendtool_core import (
    build_markdown_brief,
    export_csv,
    fetch_rising_keywords,
    generate_title_ideas,
    load_keywords,
    rank_opportunities,
    summarize_by_seed,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SEO Trend Tool: mine breakout long-tail opportunities from Google Trends."
    )
    parser.add_argument("--input", default="keywords.txt", help="Path to TXT/CSV seed keywords")
    parser.add_argument("--output", default="seo_opportunities.csv", help="Output CSV path")
    parser.add_argument("--timeframe", default="today 12-m", help="Google Trends timeframe")
    parser.add_argument("--geo", default="US", help="Country code (e.g. US, GB) or empty for global")
    parser.add_argument("--growth-threshold", type=int, default=400, help="Minimum growth percent")
    parser.add_argument("--max-keywords", type=int, default=25, help="Cap seed terms per run")
    parser.add_argument("--min-sleep", type=float, default=4.0, help="Min seconds between keywords")
    parser.add_argument("--max-sleep", type=float, default=8.0, help="Max seconds between keywords")
    parser.add_argument("--retries", type=int, default=2, help="Retries per keyword on API error")
    parser.add_argument("--ai-provider", default="none", help="none|ollama|openai|anthropic|gemini")
    parser.add_argument("--ai-model", default="", help="Optional AI model for analysis")
    parser.add_argument("--ai-api-key", default="", help="API key for cloud providers")
    parser.add_argument("--cloud-mode", action="store_true", help="Use Streamlit Cloud-friendly defaults")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        keywords = load_keywords(args.input)
    except Exception as exc:
        print(f"[error] {exc}")
        return 1

    if not keywords:
        print("[error] No keywords found in input file.")
        return 1

    print(f"[info] Loaded {len(keywords)} unique keywords from {Path(args.input).resolve()}")
    print("[info] Running Trends collection...")

    if args.cloud_mode:
        if args.max_keywords == 25:
            args.max_keywords = 12
        if args.min_sleep == 4.0:
            args.min_sleep = 1.5
        if args.max_sleep == 8.0:
            args.max_sleep = 3.0
        if args.retries == 2:
            args.retries = 1
        print("[info] Cloud mode enabled: reduced run-time defaults applied.")

    def on_progress(idx: int, total: int, kw: str) -> None:
        print(f"[run] ({idx}/{total}) {kw}")

    def on_sleep(seconds: float) -> None:
        print(f"[wait] Sleeping {seconds:.1f}s to reduce rate-limit risk")

    try:
        result = fetch_rising_keywords(
            keywords=keywords,
            timeframe=args.timeframe,
            geo=args.geo,
            growth_threshold=args.growth_threshold,
            max_keywords=args.max_keywords,
            min_sleep=args.min_sleep,
            max_sleep=args.max_sleep,
            retries=args.retries,
            on_progress=on_progress,
            on_sleep=on_sleep,
        )
    except Exception as exc:
        print(f"[error] Collection failed: {exc}")
        return 1

    if result.empty:
        print("[info] No opportunities met the threshold.")
        return 0

    ranked = rank_opportunities(result)
    seed_summary = summarize_by_seed(ranked)
    title_ideas = generate_title_ideas(ranked, top_n=25)
    brief = build_markdown_brief(ranked, top_n=15)

    export_csv(ranked, args.output)
    print(f"[ok] Saved {len(result)} opportunities -> {Path(args.output).resolve()}")
    export_csv(seed_summary, "seed_summary.csv")
    export_csv(title_ideas, "title_ideas.csv")
    Path("seo_brief.md").write_text(brief, encoding="utf-8")
    print("[ok] Saved extras: seed_summary.csv, title_ideas.csv, seo_brief.md")

    top = ranked[["Seed_Keyword", "Recommended_Long_Tail", "Growth_%", "Priority_Score"]].head(10)
    print("\nTop opportunities:")
    print(top.to_string(index=False))

    provider = (args.ai_provider or "none").lower().strip()
    if provider != "none":
        model_defaults = {
            "ollama": "llama3",
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-haiku-latest",
            "gemini": "gemini-1.5-flash",
        }
        model_name = args.ai_model or model_defaults.get(provider, "")
        print(f"\n[ai] {provider_runtime_note(provider)}")
        print(f"[ai] Running {provider} analysis with model '{model_name}'...")
        try:
            prompt = f"""
You are an elite SEO strategist.
Analyze this Google Trends rising-keyword dataset and provide:
1) Top 5 opportunities to target now
2) Why each matters (intent + monetization angle)
3) One content title idea for each

Dataset:
{ranked.head(40).to_string(index=False)}
"""
            analysis = run_ai_analysis(
                provider=provider,
                model=model_name,
                prompt=prompt,
                api_key=args.ai_api_key,
            )
            print("\n=== AI SEO BRIEF ===")
            print(analysis)
        except Exception as exc:
            print(f"[warn] AI analysis failed: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

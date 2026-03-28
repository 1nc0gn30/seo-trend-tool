import argparse
from pathlib import Path

from seotrendtool_core import expand_keywords, load_keywords

DEFAULT_MODIFIERS = [
    "tools",
    "examples",
    "template",
    "2026",
    "guide",
    "best practices",
    "for small business",
    "for ecommerce",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate lightweight long-tail seed expansions.")
    parser.add_argument("--input", required=True, help="Input TXT/CSV seed keyword file")
    parser.add_argument("--output", default="keywords.expanded.txt", help="Output TXT file")
    parser.add_argument("--max-per-seed", type=int, default=20, help="Max variants per seed")
    parser.add_argument(
        "--modifiers",
        default=",".join(DEFAULT_MODIFIERS),
        help="Comma-separated modifier phrases",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        seeds = load_keywords(args.input)
    except Exception as exc:
        print(f"[error] {exc}")
        return 1

    modifiers = [m.strip() for m in args.modifiers.split(",") if m.strip()]
    expanded = expand_keywords(seeds, modifiers=modifiers, max_per_seed=args.max_per_seed)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(expanded) + ("\n" if expanded else ""), encoding="utf-8")

    print(f"[ok] Expanded {len(seeds)} seeds into {len(expanded)} keyword ideas -> {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

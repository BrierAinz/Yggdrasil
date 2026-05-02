#!/usr/bin/env python3
"""
Eir Analytics — Track social media metrics
============================================
Simple JSON-based metrics tracker for monitoring growth.
"""

import json
from datetime import datetime, date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
ANALYTICS_DIR = PROJECT_ROOT / "analytics"
METRICS_FILE = ANALYTICS_DIR / "metrics.json"


def load_metrics() -> dict:
    """Load existing metrics or create new."""
    if METRICS_FILE.exists():
        with open(METRICS_FILE, "r") as f:
            return json.load(f)
    return {
        "created": datetime.now().isoformat(),
        "platforms": {
            "instagram": {"followers": 0, "following": 0, "posts": 0},
            "tiktok": {"followers": 0, "following": 0, "posts": 0},
            "twitter": {"followers": 0, "following": 0, "posts": 0},
            "patreon": {"patrons": 0, "income": 0},
            "civitai": {"downloads": 0, "favorites": 0},
        },
        "daily": [],
        "content": {"generated": 0, "posted": 0, "engagement_rate": 0},
    }


def save_metrics(metrics: dict):
    """Save metrics to JSON."""
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    with open(METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)


def add_daily_snapshot(
    ig_followers: int = None,
    tiktok_followers: int = None,
    twitter_followers: int = None,
    patreon_patrons: int = None,
    patreon_income: float = None,
    posts_published: int = 0,
    engagement_rate: float = None,
):
    """Add a daily metrics snapshot."""
    metrics = load_metrics()

    today = date.today().isoformat()

    # Update platform totals
    if ig_followers is not None:
        metrics["platforms"]["instagram"]["followers"] = ig_followers
    if tiktok_followers is not None:
        metrics["platforms"]["tiktok"]["followers"] = tiktok_followers
    if twitter_followers is not None:
        metrics["platforms"]["twitter"]["followers"] = twitter_followers
    if patreon_patrons is not None:
        metrics["platforms"]["patreon"]["patrons"] = patreon_patrons
    if patreon_income is not None:
        metrics["platforms"]["patreon"]["income"] = patreon_income

    # Add daily snapshot
    snapshot = {
        "date": today,
        "ig": ig_followers,
        "tiktok": tiktok_followers,
        "twitter": twitter_followers,
        "patrons": patreon_patrons,
        "income": patreon_income,
        "posts": posts_published,
        "engagement": engagement_rate,
    }
    metrics["daily"].append(snapshot)
    metrics["content"]["posted"] += posts_published
    if engagement_rate is not None:
        metrics["content"]["engagement_rate"] = engagement_rate

    save_metrics(metrics)
    print(f"  ✓ Metrics snapshot saved for {today}")
    return metrics


def get_growth(days: int = 7) -> dict:
    """Calculate growth over the last N days."""
    metrics = load_metrics()
    daily = metrics.get("daily", [])
    if len(daily) < 2:
        return {"status": "insufficient_data", "days": len(daily)}

    recent = daily[-days:] if len(daily) >= days else daily
    first = recent[0]
    last = recent[-1]

    growth = {}
    for platform in ["ig", "tiktok", "twitter"]:
        if first.get(platform) and last.get(platform):
            diff = last[platform] - first[platform]
            pct = (diff / first[platform] * 100) if first[platform] > 0 else 0
            growth[platform] = {
                "from": first[platform],
                "to": last[platform],
                "diff": diff,
                "pct": round(pct, 1),
            }

    return growth


def print_summary():
    """Print current metrics summary."""
    metrics = load_metrics()
    daily = metrics.get("daily", [])

    print("\n◆ Eir Analytics Summary")
    print("=" * 40)

    if daily:
        latest = daily[-1]
        print(f"  Date: {latest['date']}")
        print(f"  IG Followers: {latest.get('ig', 'N/A')}")
        print(f"  TikTok Followers: {latest.get('tiktok', 'N/A')}")
        print(f"  Twitter Followers: {latest.get('twitter', 'N/A')}")
        print(f"  Patreon Patrons: {latest.get('patrons', 'N/A')}")
        print(f"  Monthly Income: ${latest.get('income', 0):.2f}")
        print(f"  Engagement Rate: {latest.get('engagement', 'N/A')}%")

    if len(daily) >= 7:
        growth = get_growth(7)
        print(f"\n  ◆ 7-Day Growth:")
        for platform, data in growth.items():
            print(f"    {platform}: {data['from']} → {data['to']} ({data['pct']:+.1f}%)")

    print(f"\n  Total Content Generated: {metrics['content']['generated']}")
    print(f"  Total Content Posted: {metrics['content']['posted']}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Eir Analytics")
    parser.add_argument("--ig", type=int, help="Instagram followers")
    parser.add_argument("--tiktok", type=int, help="TikTok followers")
    parser.add_argument("--twitter", type=int, help="Twitter/X followers")
    parser.add_argument("--patrons", type=int, help="Patreon patrons")
    parser.add_argument("--income", type=float, help="Patreon monthly income")
    parser.add_argument("--posts", type=int, default=0, help="Posts published today")
    parser.add_argument("--engagement", type=float, help="Engagement rate %")
    parser.add_argument("--summary", action="store_true", help="Print summary")
    args = parser.parse_args()

    if args.summary:
        print_summary()
    elif any([args.ig, args.tiktok, args.twitter, args.patrons]):
        add_daily_snapshot(
            ig_followers=args.ig,
            tiktok_followers=args.tiktok,
            twitter_followers=args.twitter,
            patreon_patrons=args.patrons,
            patreon_income=args.income,
            posts_published=args.posts,
            engagement_rate=args.engagement,
        )
        print_summary()
    else:
        print_summary()
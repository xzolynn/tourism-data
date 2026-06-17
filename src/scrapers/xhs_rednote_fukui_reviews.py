#!/usr/bin/env python3
"""Scrape REDNote (Xiaohongshu International) Fukui search notes with persistent login.

Reuses saved browser login session across runs, auto-scrolls to target count,
mimics human behavior with variable delays.

Requirements:
    pip install -r requirements.txt
    playwright install chromium

Usage:
    # First run (opens browser for manual login, saves session):
    python3 -m src.scrapers.xhs_rednote_fukui_reviews

    # Subsequent runs (reuses saved login):
    python3 -m src.scrapers.xhs_rednote_fukui_reviews

    # Target 1000 notes instead of default 500:
    python3 -m src.scrapers.xhs_rednote_fukui_reviews --target 1000

    # Custom search keyword:
    python3 -m src.scrapers.xhs_rednote_fukui_reviews --keyword "福井旅游"

    # Merge with existing data (default) vs replace:
    python3 -m src.scrapers.xhs_rednote_fukui_reviews --replace --allow-shrink
"""

import argparse
import time
import urllib.parse
from pathlib import Path

from src.pipeline_io import UnsafeWriteError, safe_write_csv


FIELDNAMES = ['note_id', 'title', 'note_url', 'author', 'author_url']
KEY_FIELDS = ['note_id']


def make_search_url(keyword: str) -> str:
    """Build REDNote search URL."""
    encoded = urllib.parse.quote(keyword)
    return f"https://www.rednote.com/search_result?keyword={encoded}&source=web_explore_feed"


def collect_notes(page):
    """Extract notes from current page DOM (FIXED for latest REDNote web DOM).
    
    Extracts: note_id, title, note_url, author, author_url.
    Updated selector to match new article card layout, fix 0 notes collected bug.
    """
    return page.evaluate(
        r"""
        () => {
          const normalize = (value) => value.replace(/\s+/g, ' ').trim();
          const items = [];
          const seen = new Set();

          // New selector: REDNote uses <div role="article"> for every note card
          const noteContainers = Array.from(document.querySelectorAll('div[role="article"]'));

          for (const container of noteContainers) {
            try {
              // Locate note detail link inside article card
              const noteLink = container.querySelector('a[href*="/note/"]');
              if (!noteLink) continue;

              const note_url = noteLink.href;
              const note_id = note_url.split('/note/')[1]?.split('?')[0] || '';
              
              if (!note_id || seen.has(note_id)) continue;
              seen.add(note_id);

              // Extract note title text
              let title = '';
              const textNodes = container.querySelectorAll('span, p, h3');
              for (const elem of textNodes) {
                const text = normalize(elem.innerText || '');
                if (text.length >= 4 && text.length < 300) {
                  title = text;
                  break;
                }
              }
              if (!title) continue;

              // Extract author & author homepage link
              const authorLink = container.querySelector('a[href*="/user/"]');
              const author = authorLink ? normalize(authorLink.innerText || '') : '';
              const author_url = authorLink?.href || '';

              items.push({
                note_id,
                title,
                note_url,
                author,
                author_url
              });
            } catch (err) {
              // Skip broken card elements without crash
              continue;
            }
          }
          return items;
        }
        """
    )


def scroll_to_target(page, target_count=500, max_scrolls=200, base_delay=2.5):
    """Auto-scroll page until reaching target note count or page exhausted.
    
    Args:
        page: Playwright page object
        target_count: Target number of unique notes to collect
        max_scrolls: Maximum scroll iterations before giving up
        base_delay: Base delay between scrolls in seconds (human-like variation)
    
    Returns:
        List of collected note dictionaries
    """
    previous_count = 0
    no_new_content_streak = 0
    max_streak = 8  # Stop after 8 consecutive scrolls with no new notes

    for scroll_idx in range(max_scrolls):
        import random
        delay = base_delay + random.uniform(-0.5, 1.5)

        notes = collect_notes(page)
        current_count = len(notes)

        pct = min(100, int((current_count / target_count) * 100)) if target_count else 0
        status = f"[{scroll_idx+1:3d}] {current_count:4d}/{target_count} notes"
        if current_count > 0:
            status += f" ({pct:3d}%)"
        print(status, end="", flush=True)

        if current_count >= target_count:
            print(" ✓ REACHED TARGET")
            return notes

        if current_count == previous_count:
            no_new_content_streak += 1
            print(f" (no change #{no_new_content_streak})", end="", flush=True)
            if no_new_content_streak >= max_streak:
                print(" → PAGE EXHAUSTED")
                return notes
        else:
            no_new_content_streak = 0
            new_count = current_count - previous_count
            print(f" (+{new_count})", end="", flush=True)

        print()
        previous_count = current_count

        page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        time.sleep(delay)

    print(f"\n[{max_scrolls}] Reached maximum scroll limit")
    return notes


def main():
    parser = argparse.ArgumentParser(
        description='Scrape REDNote (Xiaohongshu International) Fukui search notes.'
    )
    parser.add_argument(
        '--keyword', default='福井',
        help='Search keyword (default: 福井)'
    )
    parser.add_argument(
        '--output', default='data/raw/social/fukui_xhs_reviews.csv',
        help='CSV output file path'
    )
    parser.add_argument(
        '--target', type=int, default=500,
        help='Target number of notes to collect (default: 500)'
    )
    parser.add_argument(
        '--delay', type=float, default=2.5,
        help='Base delay between scrolls in seconds (default: 2.5, human-like with ±0.5-1.5s variation)'
    )
    parser.add_argument(
        '--max-scrolls', type=int, default=200,
        help='Max scroll iterations before stopping (default: 200)'
    )
    parser.add_argument(
        '--profile-dir', type=Path,
        default=Path.home() / '.playwright-profiles' / 'rednote',
        help='Directory for persistent browser profile with saved login'
    )
    parser.add_argument(
        '--replace', action='store_true',
        help='Replace existing CSV instead of merging by note_id'
    )
    parser.add_argument(
        '--allow-shrink', action='store_true',
        help='Allow shrinking data when using --replace (safety override)'
    )
    parser.add_argument(
        '--allow-empty', action='store_true',
        help='Allow intentionally empty output (for testing only)'
    )

    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    output_path = Path(args.output)
    search_url = make_search_url(args.keyword)

    print("=" * 70)
    print("REDNote Fukui Search Scraper (Fixed DOM Selector Version)")
    print("=" * 70)
    print(f"URL:      {search_url}")
    print(f"Target:   {args.target} notes")
    print(f"Delay:    {args.delay}s base (human-like variation ±0.5-1.5s)")
    print(f"Output:   {output_path}")
    print(f"Profile:  {args.profile_dir}")
    print()

    args.profile_dir.mkdir(parents=True, exist_ok=True)

    print("→ Starting browser with persistent login session...")
    print()

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(args.profile_dir),
            headless=False,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
            timezone_id='Asia/Tokyo',
        )

        try:
            page = context.pages[0] if context.pages else context.new_page()

            print("→ Loading search page...")
            page.goto(search_url, wait_until='domcontentloaded', timeout=60000)

            print("→ Waiting for page content to fully render...")
            time.sleep(4)

            # Force manual login wait, no auto detect to avoid timeout skip
            print("\n⚠ MANDATORY LOGIN STEP")
            print("1. Operate inside the popped browser window")
            print("2. Finish REDNote login manually via QR code")
            print("3. Confirm Fukui note cards are fully visible on page")
            print("4. Switch back to terminal, press Enter to start auto-scrape\n")
            input("Press Enter to continue after login finished: ")
            time.sleep(2)

            print("→ Starting auto-scroll collection...\n")
            notes = scroll_to_target(
                page,
                target_count=args.target,
                max_scrolls=args.max_scrolls,
                base_delay=args.delay
            )

            print()
            print("=" * 70)
            print(f"✓ Collection complete: {len(notes)} notes collected")

        finally:
            context.close()

    if not notes and not args.allow_empty:
        raise SystemExit("✗ No notes collected. Check login, page load, or website DOM changes.")

    # Deduplicate using unique note_id
    unique_notes_dict = {}
    for note in notes:
        note_id = note.get('note_id', '').strip()
        if note_id:
            unique_notes_dict[note_id] = note

    rows = list(unique_notes_dict.values())
    print(f"✓ Unique notes (dedup by note_id): {len(rows)}")
    print()

    # Safe merge write, never overwrite old data by default
    print(f"→ Writing merged data to {output_path}...")
    try:
        total_rows, backup_path = safe_write_csv(
            rows,
            output_path,
            FIELDNAMES,
            key_fields=KEY_FIELDS,
            merge_existing=not args.replace,
            allow_empty=args.allow_empty,
            allow_shrink=args.allow_shrink,
        )
    except UnsafeWriteError as exc:
        raise SystemExit(f"✗ CSV Write Error: {exc}") from exc

    if backup_path:
        print(f"✓ Backup created for old dataset: {backup_path}")

    print(f"✓ Final total unique rows in CSV: {total_rows}")
    print("=" * 70)


if __name__ == '__main__':
    main()
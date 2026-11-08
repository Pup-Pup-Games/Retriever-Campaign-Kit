#!/usr/bin/env python
"""
post_discord.py — post a session recap to a group's Discord channel via webhook.

Reads the group's incoming-webhook URL from config.json and posts a Markdown recap
file as one or more messages (chunked to Discord's 2000-character limit, split on
paragraph boundaries). Recaps only — sheets and world files live in the repo.

Set up the webhook once: in Discord, Channel → Edit → Integrations → Webhooks →
New Webhook → Copy URL, and paste it into config.json under the group's
"discord_webhook". config.json is git-ignored.

Usage:
  python post_discord.py --group seal --file groups/seal/sessions/session-01.md
  python post_discord.py --group seal --file <recap.md> --dry-run   # print, don't send

Pure stdlib (urllib); no dependencies.
"""
import argparse, json, os, re, sys, time, urllib.request, urllib.error

try:  # Windows consoles default to cp1252; recaps contain em dashes etc.
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import stonetop_lib as lib
LIMIT = 1900  # leave headroom under Discord's 2000-char hard limit


def to_discord(text):
    """Strip YAML frontmatter and flatten [[wikilinks]] for a clean Discord post."""
    text = re.sub(r"^\s*---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)
    text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", text)  # [[A|B]] -> A
    return text.strip()


def load_webhook(group, table):
    """Resolve a real webhook (multi-table groups need a table); refuse XXXX placeholders."""
    url = lib.discord_webhook(group, table)
    where = f"group '{group}'" + (f" table '{table}'" if table else "")
    if not url or "XXXX" in url:
        sys.exit(f"No real discord_webhook set for {where} in config.json.")
    return url


def chunk(text, limit=LIMIT):
    """Split on blank lines into messages under the limit, keeping paragraphs whole."""
    paras, chunks, cur = text.split("\n\n"), [], ""
    for p in paras:
        piece = (p + "\n\n")
        if len(cur) + len(piece) > limit and cur:
            chunks.append(cur.rstrip())
            cur = ""
        if len(piece) > limit:  # a single oversized paragraph: hard-split it
            for i in range(0, len(piece), limit):
                chunks.append(piece[i:i + limit].rstrip())
            continue
        cur += piece
    if cur.strip():
        chunks.append(cur.rstrip())
    return chunks


def post(url, content, thread_name=None, thread_id=None):
    """Post one chunk. Returns (status, response_json).

    `thread_name` creates a new (forum) thread carrying this message.
    `thread_id` posts into an existing thread. We request ?wait=true so the
    response includes the created message/thread, letting the caller learn the
    thread id to chain the remaining chunks into.
    """
    payload = {"content": content, "allowed_mentions": {"parse": []}}
    if thread_name:
        payload["thread_name"] = thread_name[:100]
    params = ["wait=true"]
    if thread_id:
        params.append(f"thread_id={thread_id}")
    full_url = url + ("&" if "?" in url else "?") + "&".join(params)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        full_url, data=data,
        headers={"Content-Type": "application/json",
                 # Discord sits behind Cloudflare, which blocks urllib's default
                 # Python-urllib User-Agent with a 403 (error 1010). Send a real one.
                 "User-Agent": "RetrieverCampaignKit/1.0 (+https://github.com/Pup-Pup-Games/Retriever-Campaign-Kit)"})
    with urllib.request.urlopen(req) as resp:
        raw = resp.read().decode("utf-8")
        return resp.status, (json.loads(raw) if raw else {})


def main():
    ap = argparse.ArgumentParser(description="Post a recap to Discord via webhook.")
    ap.add_argument("--group", required=True, help="group name (key in config.json)")
    ap.add_argument("--file", required=True, help="path to the recap .md to post")
    ap.add_argument("--table", help="table within a multi-table group (e.g. weeknight)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the chunked messages instead of sending")
    args = ap.parse_args()

    if not os.path.exists(args.file):
        sys.exit(f"No such recap file: {args.file}")
    with open(args.file, encoding="utf-8") as f:
        body = to_discord(f.read())
    chunks = chunk(body)

    if args.dry_run:
        for i, c in enumerate(chunks, 1):
            print(f"----- message {i}/{len(chunks)} ({len(c)} chars) -----\n{c}\n")
        return

    url = load_webhook(args.group, args.table)
    # Forum-channel webhooks require a thread name on the first post; text
    # channels don't. Try a normal post first, and if Discord asks for a thread
    # (code 220001), create one named after the recap and chain the rest into it.
    thread_name = next((ln[2:].strip() for ln in body.splitlines()
                        if ln.startswith("# ")), "Session recap")
    thread_id = None
    for i, c in enumerate(chunks, 1):
        try:
            status, resp = post(url, c, thread_id=thread_id)
        except urllib.error.HTTPError as e:
            detail = e.read().decode()
            if i == 1 and '"code": 220001' in detail:
                try:
                    status, resp = post(url, c, thread_name=thread_name)
                except urllib.error.HTTPError as e2:
                    sys.exit(f"Discord rejected message 1: HTTP {e2.code} {e2.read().decode()[:200]}")
                thread_id = resp.get("channel_id")
            else:
                sys.exit(f"Discord rejected message {i}: HTTP {e.code} {detail[:200]}")
        print(f"Posted message {i}/{len(chunks)} (HTTP {status})")
        if i < len(chunks):
            time.sleep(0.6)  # gentle on the webhook rate limit


if __name__ == "__main__":
    main()

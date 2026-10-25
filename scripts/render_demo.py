"""Render a labeled replay of captured Codex MCP answers, never a screen recording.

Run with Python plus Pillow, ffmpeg and ffprobe installed. No network access is used.
Review JSON has question_id, quote, root_cause and evidence string fields. The quote
must occur verbatim in that question's recorded answer. Optional source_transcript
selects an earlier captured attempt for the review quote.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class Card:
    title: str
    context: str
    text: str
    source: str


def wrap(text: str, width: int = 99) -> list[str]:
    return [line for paragraph in text.splitlines() for line in (
        textwrap.wrap(paragraph, width=width, replace_whitespace=False) or [""]
    )]


def render(card: Card, path: Path, font_path: Path, index: int, count: int) -> bool:
    image = Image.new("RGB", (1920, 1080), "#101b2b")
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.truetype(str(font_path), 48)
    body_font = ImageFont.truetype(str(font_path), 32)
    label_font = ImageFont.truetype(str(font_path), 25)
    draw.text((70, 40), "HOUSE ACCOUNT / CAPTURED CODEX MCP REPLAY", font=label_font, fill="#85d6d0")
    draw.text((70, 95), card.title, font=title_font, fill="white")
    context = wrap(card.context, 105)
    y = 170
    for line in context[:3]:
        draw.text((70, y), line, font=body_font, fill="#aebed2")
        y += 39
    y += 22
    lines = wrap(card.text)
    capacity = (940 - y) // 39
    excerpt = len(lines) > capacity
    for line in lines[:capacity - 1 if excerpt else capacity]:
        draw.text((70, y), line, font=body_font, fill="#f1f5fa")
        y += 39
    if excerpt:
        draw.text((70, y), "[Excerpt ends. Full verbatim answer in review.html.]", font=body_font, fill="#f6cd7c")
    draw.line((70, 970, 1850, 970), fill="#435771", width=2)
    draw.text((70, 995), card.source, font=label_font, fill="#aebed2")
    draw.text((1710, 995), f"{index} / {count}", font=label_font, fill="#aebed2")
    image.save(path)
    return excerpt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transcript", type=Path, required=True)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="New directory for private review artifacts")
    parser.add_argument("--font", type=Path, default=Path("/System/Library/Fonts/Supplemental/Arial.ttf"))
    parser.add_argument("--seconds-per-card", type=int, default=30)
    args = parser.parse_args()
    transcript = json.loads(args.transcript.read_text())
    questions = transcript.get("questions", [])
    if not questions or any(not q.get("answer") for q in questions):
        parser.error("Transcript must contain recorded questions and nonempty answers")
    if len({q["id"] for q in questions}) != len(questions):
        parser.error("Question identifiers must be unique")
    complete = {q["id"] for q in questions} == {f"Q{i}" for i in range(1, 7)}
    title = "P4 demo review" if complete else "Partial capture review"
    cards = [Card(title, "Replay of captured Codex CLI interaction over local stdio MCP.",
        "These cards reproduce recorded prompts, selected tools and answers. Long answers are "
        "explicitly excerpted. The accompanying HTML contains the full replies.\n\n"
        "This is a transcript replay, not a live screen recording. There is no audio.\n\n"
        f"Recorded client: {transcript.get('client', 'unspecified')}\n"
        f"Reference date: {transcript.get('as_of', 'unspecified')}\n"
        f"Capture status: {transcript.get('status', 'unspecified')}\n"
        f"Semantic review: {transcript.get('semantic_review', 'unspecified')}",
        "Source: agent-transcript.json. Private review artifact.")]
    for question in questions:
        tools = ", ".join(question.get("selected_tools", [])) or "No tools recorded"
        cards.append(Card(question["id"], question["question"], question["answer"], f"Recorded tools: {tools}"))
    review = None
    if args.review:
        review = json.loads(args.review.read_text())
        if any(not isinstance(review.get(key), str) or not review[key].strip()
               for key in ("question_id", "quote", "root_cause", "evidence")):
            parser.error("Review must supply question_id, quote, root_cause and evidence strings")
        review_questions = questions
        if review.get("source_transcript"):
            review_source = Path(review["source_transcript"])
            if not review_source.is_absolute():
                review_source = args.review.resolve().parent / review_source
            review_questions = json.loads(review_source.read_text())["questions"]
        matching = next((q for q in review_questions if q["id"] == review["question_id"]), None)
        if matching is None or review["quote"] not in matching["answer"]:
            parser.error("Review quote must occur verbatim in the referenced answer")
        cards.append(Card("Weak answer and root cause", f"Independent review of {review['question_id']}" + (". Earlier captured attempt." if review.get("source_transcript") else ""),
            f"Recorded quote\n{review['quote']}\n\nReviewer diagnosis\n{review['root_cause']}\n\n"
            f"Evidence\n{review['evidence']}", "Diagnosis supplied by reviewer. Quote checked against transcript."))
    if not 1 <= args.seconds_per_card or len(cards) * args.seconds_per_card > 300:
        parser.error("Total video duration must be positive and at most 300 seconds")
    if not args.font.is_file() or not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        parser.error("A TrueType font, ffmpeg and ffprobe must be installed")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    (output / "agent-transcript.json").write_bytes(args.transcript.read_bytes())
    if args.review:
        (output / "review.json").write_bytes(args.review.read_bytes())
        if review and review.get("source_transcript"):
            (output / "review-source-transcript.json").write_bytes(review_source.read_bytes())
    excerpts = []
    for index, card in enumerate(cards, 1):
        excerpts.append(render(card, output / f"card-{index:02}.png", args.font, index, len(cards)))
    escape = html.escape
    sections = "\n".join(
        f"<section><h2>{escape(c.title)}</h2><p>{escape(c.context)}</p>"
        f"<pre>{escape(c.text)}</pre><small>{escape(c.source)}</small></section>" for c in cards
    )
    (output / "review.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>' + title + '</title>'
        '<style>body{background:#101b2b;color:#f1f5fa;font:18px system-ui;max-width:1100px;'
        'margin:40px auto;padding:20px}section{margin:50px 0;padding:25px;border:1px solid #435771}'
        'pre{white-space:pre-wrap;overflow-wrap:anywhere;font:16px/1.6 ui-monospace}'
        'a,small{color:#85d6d0}video{width:100%}</style><h1>' + title + '</h1>'
        '<p>Private transcript replay. Answers are verbatim. No live screen recording or audio.</p>'
        '<p><a href="agent-transcript.json">Full source transcript</a></p>' +
        ('<p><a href="review-source-transcript.json">Earlier captured attempt for weak-answer review</a></p>'
         if review and review.get("source_transcript") else '') +
        '<video controls src="demo-replay.mp4"></video>' + sections + '</html>'
    )
    subprocess.run([
        "ffmpeg", "-v", "error", "-framerate", f"1/{args.seconds_per_card}",
        "-i", str(output / "card-%02d.png"), "-c:v", "libx264", "-preset", "veryfast",
        "-tune", "stillimage", "-r", "10", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(output / "demo-replay.mp4"),
    ], check=True, timeout=240)
    probe = json.loads(subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height,codec_name",
        "-of", "json", str(output / "demo-replay.mp4"),
    ], check=True, capture_output=True, text=True, timeout=10).stdout)
    if float(probe["format"]["duration"]) > 300:
        raise ValueError("Encoded video exceeds five minutes")
    manifest = {
        "format": "labeled transcript replay", "complete_six_questions": complete,
        "weak_answer_review_included": review is not None, "card_count": len(cards),
        "review_source_sha256": hashlib.sha256(review_source.read_bytes()).hexdigest()
        if review and review.get("source_transcript") else None,
        "excerpted_cards": [i + 1 for i, excerpt in enumerate(excerpts) if excerpt],
        "transcript_sha256": hashlib.sha256(args.transcript.read_bytes()).hexdigest(),
        "video": probe,
    }
    (output / "render-receipt.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()

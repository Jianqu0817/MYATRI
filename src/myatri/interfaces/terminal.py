"""Readable plain-text blocks, including in Windows terminals without ANSI."""
from datetime import datetime


def display_time(value):
    return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M:%S")


def chat_block(speaker, body, sent_at):
    lines = body.strip().splitlines() or [""]
    return (f"\n{'─' * 48}\n[{speaker}]  {display_time(sent_at)}\n" +
            "\n".join("  " + line if line else "" for line in lines) + "\n")


def input_prompt():
    return f"\n{'─' * 48}\n[你]\n  > "

#!/usr/bin/env python3
"""
Session Merger Tool
-------------------
Merge similar or duplicate AI conversation sessions into a single consolidated session.

Similarity is computed using TF-IDF + cosine similarity on the combined text of each session.
Sessions whose similarity score exceeds the threshold are grouped and merged.

Usage:
    python session_merger.py --input sessions.json --output merged.json --threshold 0.6
    python session_merger.py --input sessions.json --output merged.json --list-groups

Input JSON format (list of sessions):
    [
      {
        "id": "session-1",
        "title": "How to use Python",
        "messages": [
          {"role": "user", "content": "How do I read a file in Python?"},
          {"role": "assistant", "content": "You can use open()..."}
        ]
      },
      ...
    ]
"""

import json
import math
import re
import argparse
import sys
from collections import defaultdict
from typing import Any


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    """Lowercase, remove punctuation, split into tokens."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return [t for t in text.split() if len(t) > 1]


def session_text(session: dict) -> str:
    """Concatenate all message contents in a session into a single string."""
    parts = []
    if session.get("title"):
        parts.append(session["title"])
    for msg in session.get("messages", []):
        content = msg.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            # Some formats use a list of content blocks
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
    return " ".join(parts)


# ---------------------------------------------------------------------------
# TF-IDF cosine similarity
# ---------------------------------------------------------------------------

def compute_tf(tokens: list[str]) -> dict[str, float]:
    tf: dict[str, float] = defaultdict(float)
    for t in tokens:
        tf[t] += 1.0
    n = len(tokens) or 1
    return {t: c / n for t, c in tf.items()}


def compute_tfidf_vectors(
    corpus: list[list[str]],
) -> list[dict[str, float]]:
    """Return TF-IDF vectors for each document in *corpus*."""
    n_docs = len(corpus)
    df: dict[str, int] = defaultdict(int)
    for tokens in corpus:
        for t in set(tokens):
            df[t] += 1

    vectors = []
    for tokens in corpus:
        tf = compute_tf(tokens)
        vec = {}
        for t, tf_val in tf.items():
            idf = math.log((n_docs + 1) / (df[t] + 1)) + 1.0
            vec[t] = tf_val * idf
        vectors.append(vec)
    return vectors


def cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    common = set(a) & set(b)
    if not common:
        return 0.0
    dot = sum(a[t] * b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def build_similarity_matrix(
    vectors: list[dict[str, float]],
) -> list[list[float]]:
    n = len(vectors)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        matrix[i][i] = 1.0
        for j in range(i + 1, n):
            sim = cosine_similarity(vectors[i], vectors[j])
            matrix[i][j] = sim
            matrix[j][i] = sim
    return matrix


# ---------------------------------------------------------------------------
# Grouping (union-find)
# ---------------------------------------------------------------------------

class UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x: int, y: int) -> None:
        self.parent[self.find(x)] = self.find(y)

    def groups(self) -> dict[int, list[int]]:
        result: dict[int, list[int]] = defaultdict(list)
        for i in range(len(self.parent)):
            result[self.find(i)].append(i)
        return dict(result)


def group_sessions(
    similarity_matrix: list[list[float]], threshold: float
) -> list[list[int]]:
    n = len(similarity_matrix)
    uf = UnionFind(n)
    for i in range(n):
        for j in range(i + 1, n):
            if similarity_matrix[i][j] >= threshold:
                uf.union(i, j)
    return list(uf.groups().values())


# ---------------------------------------------------------------------------
# Merging
# ---------------------------------------------------------------------------

def merge_group(sessions: list[dict]) -> dict:
    """Merge a list of sessions into one consolidated session."""
    if len(sessions) == 1:
        return sessions[0]

    # Build title from most common words across session titles
    titles = [s.get("title", "") for s in sessions if s.get("title")]
    merged_title = (
        " | ".join(dict.fromkeys(titles))  # deduplicate while preserving order
        if titles
        else "Merged Session"
    )

    # Collect all messages, deduplicate by normalised content
    seen: set[str] = set()
    merged_messages: list[dict] = []
    for session in sessions:
        for msg in session.get("messages", []):
            content = msg.get("content", "")
            if isinstance(content, list):
                key = json.dumps(content, ensure_ascii=False, sort_keys=True)
            else:
                key = re.sub(r"\s+", " ", str(content).strip().lower())
            if key not in seen:
                seen.add(key)
                merged_messages.append(msg)

    # Collect source session ids for reference
    source_ids = [s.get("id", str(i)) for i, s in enumerate(sessions)]

    merged: dict[str, Any] = {
        "id": f"merged-{'_'.join(str(s.get('id', i)) for i, s in enumerate(sessions))}",
        "title": merged_title,
        "source_session_ids": source_ids,
        "messages": merged_messages,
    }
    return merged


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def load_sessions(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Some exports wrap sessions under a key
        for key in ("sessions", "conversations", "chats"):
            if key in data:
                return data[key]
        return [data]
    raise ValueError(f"Unexpected JSON structure in {path}")


def run_merger(
    sessions: list[dict],
    threshold: float = 0.5,
) -> tuple[list[dict], list[list[int]]]:
    """Return (merged_sessions, groups_of_indices)."""
    if not sessions:
        return [], []

    corpus = [tokenize(session_text(s)) for s in sessions]
    vectors = compute_tfidf_vectors(corpus)
    matrix = build_similarity_matrix(vectors)
    groups = group_sessions(matrix, threshold)

    merged = []
    for group in groups:
        group_sessions_list = [sessions[i] for i in group]
        merged.append(merge_group(group_sessions_list))

    return merged, groups


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_groups(sessions: list[dict], groups: list[list[int]], matrix: list[list[float]]) -> None:
    print(f"\nFound {len(groups)} group(s) from {len(sessions)} session(s):\n")
    for g_idx, group in enumerate(groups, 1):
        label = "UNIQUE" if len(group) == 1 else f"MERGED ({len(group)} sessions)"
        print(f"  Group {g_idx} [{label}]")
        for idx in group:
            title = sessions[idx].get("title") or sessions[idx].get("id", f"session-{idx}")
            print(f"    [{idx}] {title}")
        if len(group) > 1:
            pairs = [
                (i, j, matrix[i][j])
                for i in group
                for j in group
                if i < j
            ]
            for i, j, sim in pairs:
                print(f"         similarity [{i}]↔[{j}]: {sim:.3f}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge similar or duplicate AI conversation sessions."
    )
    parser.add_argument("--input", required=True, help="Path to input JSON file with sessions")
    parser.add_argument("--output", default="merged_sessions.json", help="Path to output JSON file")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Cosine similarity threshold (0.0–1.0). Higher = stricter matching. Default: 0.5",
    )
    parser.add_argument(
        "--list-groups",
        action="store_true",
        help="Print similarity groups without writing output file",
    )
    args = parser.parse_args()

    print(f"Loading sessions from: {args.input}")
    sessions = load_sessions(args.input)
    print(f"Loaded {len(sessions)} session(s).")

    if not sessions:
        print("No sessions found. Exiting.")
        sys.exit(0)

    corpus = [tokenize(session_text(s)) for s in sessions]
    vectors = compute_tfidf_vectors(corpus)
    matrix = build_similarity_matrix(vectors)
    groups = group_sessions(matrix, args.threshold)

    if args.list_groups:
        print_groups(sessions, groups, matrix)
        return

    merged_sessions = []
    for group in groups:
        group_sessions_list = [sessions[i] for i in group]
        merged_sessions.append(merge_group(group_sessions_list))

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(merged_sessions, f, ensure_ascii=False, indent=2)

    reduced = len(sessions) - len(merged_sessions)
    print(f"\nResult: {len(sessions)} sessions → {len(merged_sessions)} sessions ({reduced} merged/removed)")
    print(f"Output written to: {args.output}")

    if args.list_groups or True:
        print_groups(sessions, groups, matrix)


if __name__ == "__main__":
    main()

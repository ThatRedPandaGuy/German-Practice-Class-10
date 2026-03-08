"""
utils.py — Helper functions for the German Lesen Practice App.

Covers:
  - Stop word loading
  - Text tokenisation
  - OpenThesaurus API calls
  - Candidate word selection with synonym validation
  - Blank construction for the exercise
"""

import re
import json
import random
import requests
from pathlib import Path


# ── Constants ────────────────────────────────────────────────────────────────

OPENTHESAURUS_URL = "https://www.openthesaurus.de/synonyme/search"
API_TIMEOUT = 6          # seconds before we give up on a single API call
MIN_SYNONYMS = 3         # minimum synonyms required to keep a candidate word
TARGET_BLANKS = 5        # how many blanks we aim to create per round
MIN_WORD_LENGTH = 3      # ignore very short tokens even after stop-word removal


# ── Data loaders ─────────────────────────────────────────────────────────────

def load_stopwords(path: str = "stopwords.txt") -> set[str]:
    """
    Load stop words from a plain-text file (one word per line).

    Matching is case-insensitive: all words are stored in lowercase so that
    comparison with lowercased tokens works correctly.

    Args:
        path: Relative or absolute path to the stop-word file.

    Returns:
        A set of lowercase stop words.
    """
    stopwords: set[str] = set()
    filepath = Path(path)
    if not filepath.exists():
        return stopwords
    with filepath.open(encoding="utf-8") as fh:
        for line in fh:
            word = line.strip().lower()
            if word:
                stopwords.add(word)
    return stopwords


def load_texts(path: str = "texts.json") -> list[dict]:
    """
    Load the texts dataset from a local JSON file.

    Args:
        path: Relative or absolute path to the JSON file.

    Returns:
        A list of text dictionaries, each with keys:
        id, title, level, text.
    """
    filepath = Path(path)
    if not filepath.exists():
        return []
    with filepath.open(encoding="utf-8") as fh:
        return json.load(fh)


# ── Text processing ───────────────────────────────────────────────────────────

def tokenise(text: str) -> list[str]:
    """
    Split a German text into word tokens, preserving original casing.

    We use a simple word-boundary regex that handles German umlauts (ä, ö, ü, ß).
    Punctuation and whitespace are excluded from tokens.

    Args:
        text: Raw German text string.

    Returns:
        Ordered list of word tokens as they appear in the text.
    """
    # Match sequences of Unicode word characters (covers ä ö ü ß etc.)
    return re.findall(r"[^\W\d_]+", text, re.UNICODE)


def filter_candidates(tokens: list[str], stopwords: set[str]) -> list[str]:
    """
    Remove stop words and very short words from the token list.

    Comparison is case-insensitive (token lowercased before checking).
    Duplicate surface forms are preserved — the same word at different
    positions is a valid independent candidate.

    Args:
        tokens:    Full list of tokens from tokenise().
        stopwords: Set of lowercase stop words.

    Returns:
        Filtered list of tokens (original casing retained).
    """
    result = []
    for tok in tokens:
        if len(tok) < MIN_WORD_LENGTH:
            continue
        if tok.lower() in stopwords:
            continue
        result.append(tok)
    return result


# ── OpenThesaurus API ─────────────────────────────────────────────────────────

def fetch_synonyms(word: str) -> list[str]:
    """
    Query the OpenThesaurus REST API for German synonyms of *word*.

    The API is called with the lowercase form of the word (German nouns are
    capitalised but the API handles both; lowercasing improves recall).

    Args:
        word: The German word to look up (any casing).

    Returns:
        A deduplicated list of synonym strings, excluding the query word itself.
        Returns an empty list on timeout, network error, or no results.

    Raises:
        Nothing — all exceptions are caught and an empty list is returned so
        that the caller can simply skip the word.
    """
    try:
        resp = requests.get(
            OPENTHESAURUS_URL,
            params={"q": word.lower(), "format": "application/json"},
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    synonyms: set[str] = set()
    for synset in data.get("synsets", []):
        for term in synset.get("terms", []):
            term_word = term.get("term", "").strip()
            if not term_word:
                continue
            # Skip if it matches the query word (any casing)
            if term_word.lower() == word.lower():
                continue
            # Skip multi-word phrases, bracketed annotations, and anything
            # containing punctuation that makes it unsuitable as a gap option
            # (slashes, parentheses, commas, digits mixed with letters, etc.)
            if not re.match(r"^[^\W\d_]+$", term_word, re.UNICODE):
                continue
            synonyms.add(term_word)

    return list(synonyms)


# ── Blank construction ────────────────────────────────────────────────────────

def build_blanks(
    text: str,
    stopwords: set[str],
    max_attempts: int = 60,
) -> list[dict] | None:
    """
    Select TARGET_BLANKS words from *text* that each have ≥ MIN_SYNONYMS
    synonyms on OpenThesaurus, then build blank descriptors for the exercise.

    Algorithm:
      1. Tokenise and filter stop words → candidate pool.
      2. Shuffle the pool and iterate through candidates.
      3. For each candidate fetch synonyms; skip if fewer than MIN_SYNONYMS.
      4. Once TARGET_BLANKS valid words are found, return their descriptors.
      5. If the pool is exhausted before TARGET_BLANKS are found → return None.

    Each blank descriptor is a dict:
      {
        "word":       str,   # original surface form in the text
        "synonym_1":  str,   # first distractor
        "synonym_2":  str,   # second distractor
        "options":    list,  # [word, syn1, syn2] shuffled
        "position":   int,   # 0-based index in the token list
      }

    Args:
        text:         The German text string for this round.
        stopwords:    Set of lowercase stop words.
        max_attempts: Guard against infinite loops when the text is short.

    Returns:
        List of blank dicts (length == TARGET_BLANKS), or None if impossible.
    """
    tokens = tokenise(text)
    candidates = filter_candidates(tokens, stopwords)

    if len(candidates) < TARGET_BLANKS:
        return None  # caller should skip this text

    # Build pool as (word, token_index) for every candidate token,
    # preserving each occurrence independently — duplicate words each
    # get their own position so both can become separate gaps.
    candidate_set = set(candidates)
    pool = [
        (tok, idx)
        for idx, tok in enumerate(tokens)
        if tok in candidate_set
    ]
    random.shuffle(pool)

    blanks: list[dict] = []
    attempts = 0

    for word, position in pool:
        if attempts >= max_attempts:
            break
        attempts += 1

        synonyms = fetch_synonyms(word)
        if len(synonyms) < MIN_SYNONYMS:
            continue  # not enough synonyms — skip this word

        # Pick exactly 3 distractors at random
        chosen = random.sample(synonyms, 3)
        options = [word] + chosen
        random.shuffle(options)

        blanks.append({
            "word": word,
            "synonym_1": chosen[0],
            "synonym_2": chosen[1],
            "synonym_3": chosen[2],
            "options": options,
            "position": position,
        })

        if len(blanks) == TARGET_BLANKS:
            break

    if len(blanks) < TARGET_BLANKS:
        return None  # could not find enough valid words

    # Sort by position so gap [1] is the first word in the text,
    # gap [2] is the second, etc. — matching reading order.
    blanks.sort(key=lambda b: b["position"])

    return blanks


# ── Text rendering helper ─────────────────────────────────────────────────────

def render_text_with_blanks(text: str, blanks: list[dict]) -> list:
    """
    Split the text into segments so the UI can interleave plain text
    with interactive dropdown widgets.

    Returns a list of segments, each being either:
      {"type": "text",  "content": str}           — plain text chunk
      {"type": "blank", "blank_index": int}        — placeholder for dropdown i

    Matching is done by TOKEN POSITION (the blank's recorded index in the token
    list), not by word string. This means two gaps with the same surface form
    (e.g. both "mal") are each correctly marked at their own position.

    Args:
        text:   Original German text.
        blanks: List of blank dicts from build_blanks(), sorted by position.

    Returns:
        Ordered list of segment dicts.
    """
    # Build a lookup: token_index → blank_index (i.e. gap number 0-based)
    position_to_blank: dict[int, int] = {
        b["position"]: i for i, b in enumerate(blanks)
    }

    segments: list[dict] = []
    pattern = re.compile(r"[^\W\d_]+", re.UNICODE)
    last_end = 0
    token_index = 0  # counts every word token we encounter in the text

    for match in pattern.finditer(text):
        start, end = match.span()

        # Emit any leading whitespace / punctuation as plain text
        if start > last_end:
            segments.append({"type": "text", "content": text[last_end:start]})

        if token_index in position_to_blank:
            blank_idx = position_to_blank[token_index]
            segments.append({"type": "blank", "blank_index": blank_idx})
        else:
            segments.append({"type": "text", "content": match.group()})

        token_index += 1
        last_end = end

    # Trailing punctuation / whitespace
    if last_end < len(text):
        segments.append({"type": "text", "content": text[last_end:]})

    return segments

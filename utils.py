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
MIN_SYNONYMS = 2         # minimum synonyms required to keep a candidate word
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
            # Exclude the query word itself (case-insensitive) and empty strings
            if term_word and term_word.lower() != word.lower():
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

    # Unique candidates by position (word + index in token list)
    # We use the position of the first occurrence in *tokens* for each candidate.
    token_positions: dict[str, int] = {}
    for idx, tok in enumerate(tokens):
        if tok in candidates and tok not in token_positions:
            token_positions[tok] = idx

    # Build a pool of (word, position) tuples and shuffle
    pool = [(w, token_positions[w]) for w in candidates if w in token_positions]
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

        # Pick exactly 2 distractors at random
        chosen = random.sample(synonyms, 2)
        options = [word] + chosen
        random.shuffle(options)

        blanks.append({
            "word": word,
            "synonym_1": chosen[0],
            "synonym_2": chosen[1],
            "options": options,
            "position": position,
        })

        if len(blanks) == TARGET_BLANKS:
            break

    if len(blanks) < TARGET_BLANKS:
        return None  # could not find enough valid words

    return blanks


# ── Text rendering helper ─────────────────────────────────────────────────────

def render_text_with_blanks(text: str, blanks: list[dict]) -> list:
    """
    Split the text into segments so the UI can interleave plain text
    with interactive dropdown widgets.

    Returns a list of segments, each being either:
      {"type": "text",  "content": str}           — plain text chunk
      {"type": "blank", "blank_index": int}        — placeholder for dropdown i

    The segments are ordered as they appear in the original text.

    Args:
        text:   Original German text.
        blanks: List of blank dicts from build_blanks().

    Returns:
        Ordered list of segment dicts.
    """
    tokens = tokenise(text)

    # Map each blank to its word (we'll replace first occurrence in token order)
    blank_by_word: dict[str, int] = {}
    for i, b in enumerate(blanks):
        if b["word"] not in blank_by_word:
            blank_by_word[b["word"]] = i

    segments: list[dict] = []
    used_blank_indices: set[int] = set()

    # We rebuild the text character-by-character using regex spans
    pattern = re.compile(r"[^\W\d_]+", re.UNICODE)
    last_end = 0

    for match in pattern.finditer(text):
        token = match.group()
        start, end = match.span()

        # Add any leading punctuation / whitespace as plain text
        if start > last_end:
            segments.append({"type": "text", "content": text[last_end:start]})

        blank_idx = blank_by_word.get(token)
        if blank_idx is not None and blank_idx not in used_blank_indices:
            # Replace with a blank widget
            segments.append({"type": "blank", "blank_index": blank_idx})
            used_blank_indices.add(blank_idx)
        else:
            segments.append({"type": "text", "content": token})

        last_end = end

    # Append any trailing punctuation
    if last_end < len(text):
        segments.append({"type": "text", "content": text[last_end:]})

    return segments

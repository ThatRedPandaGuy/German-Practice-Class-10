"""
app.py — German Lesen Practice App (main entry point).

Run locally:  streamlit run app.py
Deploy:       Push to GitHub → connect to Streamlit Community Cloud.

Session state keys
──────────────────
  stopwords          set[str]          loaded once at startup
  texts              list[dict]        full texts.json contents
  seen_ids           dict[str,set]     level → set of already-seen text IDs
  current_text       dict | None       active text entry
  blanks             list[dict] | None active blank descriptors
  submitted          bool              whether the user has checked answers
  score_correct      int               cumulative correct answers this session
  score_total        int               cumulative blanks attempted this session
  error_msg          str               user-facing error to display (cleared each round)
  hints_revealed     set[int]          blank indices where hint was clicked
"""

import random
import streamlit as st

from utils import (
    load_stopwords,
    load_texts,
    build_blanks,
    render_text_with_blanks,
    TARGET_BLANKS,
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Deutsch Lesen — Lückentext",
    page_icon="🇩🇪",
    layout="centered",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    /* ── Google Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,400&family=Source+Sans+3:wght@300;400;600&display=swap');

    /* ── Root tokens ── */
    :root {
        --navy:   #0d1b2a;
        --navy2:  #1a2d42;
        --amber:  #e8a838;
        --amber2: #f0c060;
        --cream:  #f5f0e8;
        --green:  #3aaf7a;
        --red:    #e05c5c;
        --muted:  #8a9bb0;
    }

    /* ── Base ── */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: var(--navy) !important;
        color: var(--cream) !important;
        font-family: 'Source Sans 3', sans-serif !important;
        font-weight: 300;
    }

    [data-testid="stSidebar"] { display: none; }

    /* ── Header ── */
    .lesen-header {
        text-align: center;
        padding: 2.2rem 0 1rem;
    }
    .lesen-header h1 {
        font-family: 'Playfair Display', serif;
        font-size: 2.6rem;
        font-weight: 700;
        color: var(--amber);
        letter-spacing: 0.02em;
        margin-bottom: 0.15rem;
    }
    .lesen-header p {
        color: var(--muted);
        font-size: 0.95rem;
        margin: 0;
        font-style: italic;
    }

    /* ── Score pill ── */
    .score-pill {
        display: inline-block;
        background: var(--navy2);
        border: 1px solid var(--amber);
        border-radius: 999px;
        padding: 0.35rem 1.1rem;
        font-size: 0.88rem;
        color: var(--amber2);
        font-weight: 600;
        letter-spacing: 0.04em;
    }

    /* ── Text card ── */
    .text-card {
        background: var(--navy2);
        border-radius: 12px;
        border: 1px solid rgba(232,168,56,0.18);
        padding: 1.6rem 2rem;
        margin: 1.2rem 0;
        font-family: 'Playfair Display', serif;
        font-style: italic;
        font-size: 1.08rem;
        line-height: 1.85;
        color: var(--cream);
    }
    .text-card .text-title {
        font-style: normal;
        font-weight: 700;
        font-size: 1.15rem;
        color: var(--amber);
        margin-bottom: 0.7rem;
        display: block;
    }

    /* ── Blank word inline ── */
    .blank-correct {
        color: var(--green);
        font-weight: 600;
        font-style: normal;
        border-bottom: 2px solid var(--green);
        padding-bottom: 1px;
    }
    .blank-wrong {
        color: var(--red);
        font-weight: 600;
        font-style: normal;
        border-bottom: 2px solid var(--red);
        padding-bottom: 1px;
    }
    .blank-answer {
        color: var(--muted);
        font-style: normal;
        font-size: 0.88rem;
    }

    /* ── Selectbox & button tweaks ── */
    div[data-testid="stSelectbox"] > div {
        background: #0d1b2a !important;
        border: 1px solid rgba(232,168,56,0.35) !important;
        border-radius: 8px !important;
        color: var(--cream) !important;
    }
    div[data-testid="stSelectbox"] label {
        color: var(--muted) !important;
        font-size: 0.8rem;
    }

    .stButton > button {
        background: var(--amber) !important;
        color: var(--navy) !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.4rem !important;
        font-family: 'Source Sans 3', sans-serif !important;
        font-size: 0.95rem !important;
        transition: background 0.2s;
    }
    .stButton > button:hover {
        background: var(--amber2) !important;
    }

    /* Secondary / ghost button style — applied via a wrapper class */
    .btn-ghost .stButton > button {
        background: transparent !important;
        color: var(--muted) !important;
        border: 1px solid var(--muted) !important;
    }
    .btn-ghost .stButton > button:hover {
        border-color: var(--amber) !important;
        color: var(--amber) !important;
    }

    /* ── Hint badge ── */
    .hint-badge {
        display: inline-block;
        background: rgba(232,168,56,0.12);
        border: 1px solid rgba(232,168,56,0.35);
        border-radius: 6px;
        padding: 0.15rem 0.55rem;
        font-size: 0.8rem;
        color: var(--amber2);
        margin-left: 0.4rem;
    }

    /* ── Level badge ── */
    .level-badge {
        display: inline-block;
        border-radius: 4px;
        padding: 0.1rem 0.5rem;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        margin-left: 0.5rem;
        vertical-align: middle;
    }
    .level-a { background:#1e4d30; color:#5fe09a; }
    .level-b { background:#1a3a5c; color:#6ab4f5; }
    .level-c { background:#4d1a4d; color:#d98aff; }

    /* ── Divider ── */
    hr { border-color: rgba(255,255,255,0.07) !important; }

    /* ── Info / warning boxes ── */
    .info-box {
        background: rgba(232,168,56,0.08);
        border-left: 3px solid var(--amber);
        border-radius: 0 8px 8px 0;
        padding: 0.75rem 1rem;
        margin: 0.8rem 0;
        font-size: 0.9rem;
        color: var(--cream);
    }
    .error-box {
        background: rgba(224,92,92,0.1);
        border-left: 3px solid var(--red);
        border-radius: 0 8px 8px 0;
        padding: 0.75rem 1rem;
        margin: 0.8rem 0;
        font-size: 0.9rem;
        color: var(--cream);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state initialisation ──────────────────────────────────────────────

def _init_state() -> None:
    """Initialise all session-state keys on the first run."""
    defaults = {
        "stopwords": None,          # loaded lazily below
        "texts": None,              # loaded lazily below
        "seen_ids": {},             # { level_key: set() }
        "current_text": None,
        "blanks": None,
        "submitted": False,
        "score_correct": 0,
        "score_total": 0,
        "error_msg": "",
        "hints_revealed": set(),
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_state()

# ── Load data (cached across reruns) ─────────────────────────────────────────

@st.cache_resource
def _load_stopwords():
    return load_stopwords("stopwords.txt")


@st.cache_resource
def _load_texts():
    return load_texts("texts.json")


if st.session_state.stopwords is None:
    st.session_state.stopwords = _load_stopwords()

if st.session_state.texts is None:
    st.session_state.texts = _load_texts()


# ── Helper utilities ──────────────────────────────────────────────────────────

LEVEL_GROUPS = {
    "Alle Niveaus": None,
    "A1 / A2 — Anfänger": ["A1", "A2"],
    "B1 / B2 — Mittelstufe": ["B1", "B2"],
    "C1 / C2 — Fortgeschrittene": ["C1", "C2"],
}


def _level_class(level: str) -> str:
    prefix = level[0].upper() if level else "A"
    return {"A": "level-a", "B": "level-b", "C": "level-c"}.get(prefix, "level-a")


def _pick_text(allowed_levels: list[str] | None, level_key: str) -> dict | None:
    """
    Pick a random unseen text matching *allowed_levels*.

    If all matching texts have been seen, resets the seen-set for that level
    and picks from the full pool (avoids getting stuck).

    Args:
        allowed_levels: List of CEFR level strings (e.g. ["A1","A2"]) or None = any.
        level_key:      Hashable key for the seen-IDs dict.

    Returns:
        A text dict or None if no texts match the level filter at all.
    """
    all_texts: list[dict] = st.session_state.texts
    pool = [t for t in all_texts if allowed_levels is None or t["level"] in allowed_levels]
    if not pool:
        return None

    seen: set[int] = st.session_state.seen_ids.get(level_key, set())
    unseen = [t for t in pool if t["id"] not in seen]

    if not unseen:
        # All texts at this level exhausted — reset and start over
        st.session_state.seen_ids[level_key] = set()
        unseen = pool

    chosen = random.choice(unseen)
    st.session_state.seen_ids.setdefault(level_key, set()).add(chosen["id"])
    return chosen


def _start_new_round(allowed_levels: list[str] | None, level_key: str) -> None:
    """
    Pick a new text, build its blanks, and update session state.

    Shows a spinner while the API calls are in flight.

    Args:
        allowed_levels: See _pick_text().
        level_key:      See _pick_text().
    """
    st.session_state.error_msg = ""
    st.session_state.submitted = False
    st.session_state.blanks = None
    st.session_state.current_text = None
    st.session_state.hints_revealed = set()

    text_entry = _pick_text(allowed_levels, level_key)
    if text_entry is None:
        st.session_state.error_msg = (
            "Keine Texte für dieses Niveau gefunden. "
            "Bitte wähle ein anderes Niveau oder füge Texte zur texts.json hinzu."
        )
        return

    with st.spinner("Synonyme werden geladen …"):
        blanks = build_blanks(text_entry["text"], st.session_state.stopwords)

    if blanks is None:
        # Auto-skip: mark as seen and try again (recursive, but bounded by pool size)
        st.session_state.seen_ids.setdefault(level_key, set()).add(text_entry["id"])
        st.session_state.error_msg = (
            f"Text „{text_entry['title']}" hat zu wenige auswählbare Wörter"
            "automatisch übersprungen."
        )
        # Attempt once more with a fresh pick (don't recurse endlessly)
        text_entry2 = _pick_text(allowed_levels, level_key)
        if text_entry2 and text_entry2["id"] != text_entry["id"]:
            with st.spinner("Synonyme werden geladen …"):
                blanks = build_blanks(text_entry2["text"], st.session_state.stopwords)
            if blanks:
                st.session_state.current_text = text_entry2
                st.session_state.blanks = blanks
                st.session_state.error_msg = ""
        return

    st.session_state.current_text = text_entry
    st.session_state.blanks = blanks


# ── UI — Header ───────────────────────────────────────────────────────────────

st.markdown(
    """
    <div class="lesen-header">
      <h1>🇩🇪 Deutsches Lesen</h1>
      <p>Lückentext-Training • Wähle das richtige Wort aus dem Dropdown</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── UI — Controls row ─────────────────────────────────────────────────────────

ctrl_left, ctrl_mid, ctrl_right = st.columns([3, 2, 2])

with ctrl_left:
    level_label = st.selectbox(
        "Niveau",
        options=list(LEVEL_GROUPS.keys()),
        index=0,
        label_visibility="collapsed",
    )

allowed_levels = LEVEL_GROUPS[level_label]
level_key = level_label  # use the human label as dict key

with ctrl_mid:
    if st.button("▶ Neue Runde", use_container_width=True):
        _start_new_round(allowed_levels, level_key)
        st.rerun()

with ctrl_right:
    correct = st.session_state.score_correct
    total = st.session_state.score_total
    st.markdown(
        f'<div style="padding-top:0.45rem; text-align:center;">'
        f'<span class="score-pill">✓ {correct} / {total}</span></div>',
        unsafe_allow_html=True,
    )

st.divider()

# ── UI — Error / info messages ────────────────────────────────────────────────

if st.session_state.error_msg:
    st.markdown(
        f'<div class="error-box">⚠️ {st.session_state.error_msg}</div>',
        unsafe_allow_html=True,
    )

# ── UI — No active round ──────────────────────────────────────────────────────

if st.session_state.current_text is None or st.session_state.blanks is None:
    st.markdown(
        '<div class="info-box">Klicke auf <strong>▶ Neue Runde</strong>, '
        "um mit dem Üben zu beginnen.</div>",
        unsafe_allow_html=True,
    )
    st.stop()

# ── UI — Active round ─────────────────────────────────────────────────────────

text_entry: dict = st.session_state.current_text
blanks: list[dict] = st.session_state.blanks
submitted: bool = st.session_state.submitted

# Title + level badge
level_cls = _level_class(text_entry.get("level", "A"))
st.markdown(
    f'<div style="margin-bottom:0.3rem;">'
    f'<span style="font-family:\'Playfair Display\',serif;font-size:1.15rem;'
    f'font-weight:700;color:var(--amber);">{text_entry["title"]}</span>'
    f'<span class="level-badge {level_cls}">{text_entry.get("level","")}</span>'
    f"</div>",
    unsafe_allow_html=True,
)

# ── Render text + dropdowns ───────────────────────────────────────────────────

segments = render_text_with_blanks(text_entry["text"], blanks)

# We'll collect user answers keyed by blank index
user_answers: dict[int, str] = {}

# Render in a streaming fashion:
# Collect consecutive "text" segments and flush before each blank widget.

pending_text: list[str] = []

def _flush_text(parts: list[str]) -> None:
    """Emit accumulated plain-text as a single styled span."""
    if parts:
        joined = "".join(parts)
        # Render inline with the surrounding italic/serif style
        st.markdown(
            f'<span style="font-family:\'Playfair Display\',serif;'
            f'font-style:italic;font-size:1.05rem;line-height:1.85;'
            f'color:var(--cream);">{joined}</span>',
            unsafe_allow_html=True,
        )
        parts.clear()


# We use st.container with columns to inline text + widgets.
# Streamlit doesn't truly support inline mixed text+widgets, so we
# render each blank on its own labelled row instead, and show the
# full text in the card above for reading context.

# ① Show the full text in a reading card
card_html = '<div class="text-card">'
for seg in segments:
    if seg["type"] == "text":
        card_html += seg["content"]
    else:
        b = blanks[seg["blank_index"]]
        card_html += (
            f'<span style="border-bottom:2px dashed var(--amber);'
            f'color:var(--amber2);font-style:normal;font-weight:600;">'
            f"[{seg['blank_index']+1}]</span>"
        )
card_html += "</div>"
st.markdown(card_html, unsafe_allow_html=True)

# ② Per-blank widgets
st.markdown(
    '<p style="color:var(--muted);font-size:0.85rem;margin:0.3rem 0 0.8rem;">'
    "Wähle das passende Wort für jede Lücke:</p>",
    unsafe_allow_html=True,
)

for i, blank in enumerate(blanks):
    hint_revealed = i in st.session_state.hints_revealed
    hint_text = f"Tipp: {blank['word'][0].upper()}…" if hint_revealed else ""

    col_num, col_sel, col_hint = st.columns([0.5, 4, 1.5])

    with col_num:
        st.markdown(
            f'<div style="padding-top:0.6rem;text-align:center;'
            f'font-weight:700;color:var(--amber);">[{i+1}]</div>',
            unsafe_allow_html=True,
        )

    with col_sel:
        if submitted:
            # Show result inline instead of a dropdown
            correct_word = blank["word"]
            answer = st.session_state.get(f"answer_{i}", blank["options"][0])
            is_correct = answer.lower() == correct_word.lower()
            icon = "✅" if is_correct else "❌"
            cls = "blank-correct" if is_correct else "blank-wrong"
            st.markdown(
                f'{icon} <span class="{cls}">{answer}</span>'
                + (
                    f'  <span class="blank-answer">(richtig: {correct_word})</span>'
                    if not is_correct
                    else ""
                ),
                unsafe_allow_html=True,
            )
            user_answers[i] = answer
        else:
            answer = st.selectbox(
                f"Lücke {i+1}",
                options=blank["options"],
                key=f"answer_{i}",
                label_visibility="collapsed",
            )
            user_answers[i] = answer

    with col_hint:
        if not submitted:
            if hint_revealed:
                st.markdown(
                    f'<span class="hint-badge">💡 {hint_text}</span>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button("💡 Tipp", key=f"hint_{i}", use_container_width=True):
                    st.session_state.hints_revealed.add(i)
                    st.rerun()

# ── UI — Submit / Next / Quit ─────────────────────────────────────────────────

st.divider()
btn1, btn2, btn3 = st.columns([2, 2, 2])

with btn1:
    if not submitted:
        if st.button("✔ Antworten prüfen", use_container_width=True):
            # Score this round
            round_correct = 0
            for i, blank in enumerate(blanks):
                chosen = user_answers.get(i, "")
                if chosen.lower() == blank["word"].lower():
                    round_correct += 1
            st.session_state.score_correct += round_correct
            st.session_state.score_total += TARGET_BLANKS
            st.session_state.submitted = True
            st.rerun()

with btn2:
    if submitted:
        if st.button("▶ Nächste Runde", use_container_width=True):
            _start_new_round(allowed_levels, level_key)
            st.rerun()

with btn3:
    with st.container():
        st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
        if st.button("✕ Beenden", use_container_width=True):
            # Reset everything except cumulative score display
            st.session_state.current_text = None
            st.session_state.blanks = None
            st.session_state.submitted = False
            st.session_state.hints_revealed = set()
            st.session_state.error_msg = ""
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ── UI — Round result summary (after submission) ──────────────────────────────

if submitted:
    round_correct = sum(
        1
        for i, b in enumerate(blanks)
        if st.session_state.get(f"answer_{i}", "").lower() == b["word"].lower()
    )
    pct = int(round_correct / TARGET_BLANKS * 100)
    emoji = "🎉" if pct == 100 else "👍" if pct >= 60 else "📚"
    st.markdown(
        f'<div class="info-box" style="margin-top:1rem;">'
        f"{emoji} Diese Runde: <strong>{round_correct} / {TARGET_BLANKS}</strong> "
        f"({pct} %) — Gesamt: <strong>{st.session_state.score_correct} / "
        f"{st.session_state.score_total}</strong></div>",
        unsafe_allow_html=True,
    )

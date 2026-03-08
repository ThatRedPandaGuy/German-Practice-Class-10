"""
app.py — German Lesen Practice App (main entry point).

Run locally:  streamlit run app.py
Deploy:       Push to GitHub → connect to Streamlit Community Cloud.

Session state keys
──────────────────
  stopwords      set[str]          loaded once at startup
  texts          list[dict]        full texts.json contents
  seen_ids       set[int]          IDs of texts already seen this session
  current_text   dict | None       active text entry
  blanks         list[dict] | None active blank descriptors
  submitted      bool              whether the user has checked answers
  score_correct  int               cumulative correct answers this session
  score_total    int               cumulative blanks attempted this session
  error_msg      str               user-facing error (cleared each new round)
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
    page_title="Deutsch Lesen — Gap Fill",
    page_icon="🇩🇪",
    layout="centered",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    /* Times New Roman is a system font — no import needed */

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

    html, body, [data-testid="stAppViewContainer"] {
        background-color: var(--navy) !important;
        color: var(--cream) !important;
        font-family: 'Times New Roman', Times, serif !important;
        font-weight: 300;
    }

    [data-testid="stSidebar"] { display: none; }

    /* ── Header ── */
    .lesen-header {
        text-align: center;
        padding: 2.4rem 0 1.2rem;
    }
    .lesen-header h1 {
        font-family: 'Times New Roman', Times, serif;
        font-size: 2.8rem;
        font-weight: 700;
        color: var(--amber);
        letter-spacing: 0.02em;
        margin-bottom: 0.2rem;
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
        padding: 0.35rem 1.2rem;
        font-size: 0.88rem;
        color: var(--amber2);
        font-weight: 600;
        letter-spacing: 0.04em;
    }

    /* ── Chapter badge ── */
    .chapter-badge {
        display: inline-block;
        background: var(--navy2);
        border: 1px solid rgba(232,168,56,0.4);
        border-radius: 4px;
        padding: 0.1rem 0.6rem;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        color: var(--amber2);
        margin-left: 0.6rem;
        vertical-align: middle;
    }

    /* ── Text reading card ── */
    .text-card {
        background: var(--navy2);
        border-radius: 12px;
        border: 1px solid rgba(232,168,56,0.18);
        padding: 1.8rem 2.2rem;
        margin: 1.2rem 0;
        font-family: 'Times New Roman', Times, serif;
        font-style: italic;
        font-size: 1.08rem;
        line-height: 1.9;
        color: var(--cream);
    }

    /* ── Answer feedback ── */
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
        font-size: 0.85rem;
    }

    /* ── Selectbox ── */
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

    /* ── Primary button ── */
    .stButton > button {
        background: var(--amber) !important;
        color: var(--navy) !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.4rem !important;
        font-family: 'Times New Roman', Times, serif !important;
        font-size: 0.95rem !important;
        transition: background 0.2s;
    }
    .stButton > button:hover {
        background: var(--amber2) !important;
    }

    /* ── Divider ── */
    hr { border-color: rgba(255,255,255,0.07) !important; }

    /* ── Info / error boxes ── */
    .info-box {
        background: rgba(232,168,56,0.08);
        border-left: 3px solid var(--amber);
        border-radius: 0 8px 8px 0;
        padding: 0.75rem 1rem;
        margin: 0.8rem 0;
        font-size: 0.9rem;
        color: var(--cream);
        text-align: center;
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

    /* ── Gap number ── */
    .gap-num {
        font-weight: 700;
        color: var(--amber);
        padding-top: 0.6rem;
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state ─────────────────────────────────────────────────────────────

def _init_state() -> None:
    """Initialise all session-state keys on first run."""
    defaults = {
        "stopwords":     None,
        "texts":         None,
        "seen_ids":      set(),
        "current_text":  None,
        "blanks":        None,
        "submitted":     False,
        "score_correct": 0,
        "score_total":   0,
        "error_msg":     "",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_state()

# ── Data loading ──────────────────────────────────────────────────────────────

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


# ── Round logic ───────────────────────────────────────────────────────────────

def _pick_text() -> dict | None:
    """
    Pick a random unseen text from the full pool.

    When every text has been seen, the seen-set resets so the cycle repeats.

    Returns:
        A text dict, or None if texts.json is empty.
    """
    all_texts: list[dict] = st.session_state.texts
    if not all_texts:
        return None

    seen: set[int] = st.session_state.seen_ids
    unseen = [t for t in all_texts if t["id"] not in seen]

    if not unseen:
        # Full cycle complete — reset and start over
        st.session_state.seen_ids = set()
        unseen = all_texts

    chosen = random.choice(unseen)
    st.session_state.seen_ids.add(chosen["id"])
    return chosen


def _start_new_round() -> None:
    """
    Select a new text, fetch synonyms via OpenThesaurus, build blanks,
    and store everything in session state.

    Handles auto-skip if a text has too few usable content words.
    """
    st.session_state.error_msg = ""
    st.session_state.submitted = False
    st.session_state.blanks = None
    st.session_state.current_text = None

    text_entry = _pick_text()
    if text_entry is None:
        st.session_state.error_msg = (
            "No texts found. Please add entries to texts.json and restart."
        )
        return

    with st.spinner("Loading synonyms from OpenThesaurus…"):
        blanks = build_blanks(text_entry["text"], st.session_state.stopwords)

    if blanks is None:
        # Text has too few usable words — mark as seen and try once more
        st.session_state.seen_ids.add(text_entry["id"])
        st.session_state.error_msg = (
            f"Text '{text_entry['title']}' had too few usable words "
            "and was skipped automatically."
        )
        text_entry2 = _pick_text()
        if text_entry2 and text_entry2["id"] != text_entry["id"]:
            with st.spinner("Loading synonyms from OpenThesaurus…"):
                blanks = build_blanks(text_entry2["text"], st.session_state.stopwords)
            if blanks:
                st.session_state.current_text = text_entry2
                st.session_state.blanks = blanks
                st.session_state.error_msg = ""
        return

    st.session_state.current_text = text_entry
    st.session_state.blanks = blanks


# ── Header ────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div class="lesen-header">
      <h1>🇩🇪 Deutsches Lesen</h1>
      <p>German reading practice — choose the correct word for each numbered gap</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Top bar — three equal columns ────────────────────────────────────────────
#
#   [ Score: x / y ]   [ ▶ New Round ]   [ ✕ Quit ]
#

col_score, col_new, col_quit = st.columns([2, 2, 2])

# Style the Quit button via its key so it doesn't need a broken div wrapper
st.markdown(
    """
    <style>
    div[data-testid="stButton"]:has(button[kind="secondary"]) button,
    button[data-testid="baseButton-secondary"] {
        background: transparent !important;
        color: var(--muted) !important;
        border: 1px solid var(--muted) !important;
    }
    button[data-testid="baseButton-secondary"]:hover {
        border-color: var(--amber) !important;
        color: var(--amber) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with col_score:
    correct = st.session_state.score_correct
    total = st.session_state.score_total
    st.markdown(
        f'<div style="padding-top:0.45rem;text-align:center;">'
        f'<span class="score-pill">Score: {correct} / {total}</span></div>',
        unsafe_allow_html=True,
    )

with col_new:
    if st.button("▶ New Round", use_container_width=True, type="primary"):
        _start_new_round()
        st.rerun()

with col_quit:
    if st.button("✕ Quit", use_container_width=True, type="secondary"):
        st.session_state.current_text = None
        st.session_state.blanks = None
        st.session_state.submitted = False
        st.session_state.error_msg = ""
        st.rerun()

st.divider()

# ── Error messages ────────────────────────────────────────────────────────────

if st.session_state.error_msg:
    st.markdown(
        f'<div class="error-box">⚠️ {st.session_state.error_msg}</div>',
        unsafe_allow_html=True,
    )

# ── No active round ───────────────────────────────────────────────────────────

if st.session_state.current_text is None or st.session_state.blanks is None:
    st.markdown(
        '<div class="info-box">'
        "Press <strong>▶ New Round</strong> to begin a reading exercise."
        "</div>",
        unsafe_allow_html=True,
    )
    st.stop()

# ── Active round ──────────────────────────────────────────────────────────────

text_entry: dict = st.session_state.current_text
blanks: list[dict] = st.session_state.blanks
submitted: bool = st.session_state.submitted

# Text title + chapter badge (uses "chapter" field if set, falls back to "id")
chapter_num = text_entry.get("chapter", text_entry.get("id", "—"))
st.markdown(
    f'<div style="margin-bottom:0.4rem;">'
    f'<span style="font-family:\'Times New Roman\',Times,serif;font-size:1.2rem;'
    f'font-weight:700;color:var(--amber);">{text_entry["title"]}</span>'
    f'<span class="chapter-badge">Chapter {chapter_num}</span>'
    f"</div>",
    unsafe_allow_html=True,
)

# ── Reading card: full German text with [n] gap markers ──────────────────────

segments = render_text_with_blanks(text_entry["text"], blanks)

card_html = '<div class="text-card">'
for seg in segments:
    if seg["type"] == "text":
        card_html += seg["content"]
    else:
        n = seg["blank_index"] + 1
        card_html += (
            f'<span style="border-bottom:2px dashed var(--amber);'
            f'color:var(--amber2);font-style:normal;font-weight:700;">'
            f"[{n}]</span>"
        )
card_html += "</div>"
st.markdown(card_html, unsafe_allow_html=True)

# ── Gap dropdowns ─────────────────────────────────────────────────────────────

st.markdown(
    '<p style="color:var(--muted);font-size:0.85rem;margin:0.2rem 0 0.9rem;">'
    "Select the correct word for each numbered gap:</p>",
    unsafe_allow_html=True,
)

user_answers: dict[int, str] = {}

for i, blank in enumerate(blanks):
    col_num, col_sel = st.columns([0.5, 5.5])

    with col_num:
        st.markdown(
            f'<div class="gap-num">[{i + 1}]</div>',
            unsafe_allow_html=True,
        )

    with col_sel:
        if submitted:
            correct_word = blank["word"]
            answer = st.session_state.get(f"answer_{i}", blank["options"][0])
            is_correct = answer.lower() == correct_word.lower()
            icon = "✅" if is_correct else "❌"
            cls = "blank-correct" if is_correct else "blank-wrong"
            correction = (
                f'&nbsp;<span class="blank-answer">(correct: {correct_word})</span>'
                if not is_correct
                else ""
            )
            st.markdown(
                f'{icon} <span class="{cls}">{answer}</span>{correction}',
                unsafe_allow_html=True,
            )
            user_answers[i] = answer
        else:
            answer = st.selectbox(
                f"Gap {i + 1}",
                options=blank["options"],
                key=f"answer_{i}",
                label_visibility="collapsed",
            )
            user_answers[i] = answer

# ── Action buttons — two equal centred columns ────────────────────────────────
#
#   [spacer]   [ ✔ Check Answers ]   [ ▶ Next Round ]   [spacer]
#

st.divider()
_, col_check, col_next, _ = st.columns([1, 2, 2, 1])

with col_check:
    if not submitted:
        if st.button("✔ Check Answers", use_container_width=True):
            round_correct = sum(
                1
                for i, b in enumerate(blanks)
                if user_answers.get(i, "").lower() == b["word"].lower()
            )
            st.session_state.score_correct += round_correct
            st.session_state.score_total += TARGET_BLANKS
            st.session_state.submitted = True
            st.rerun()

with col_next:
    if submitted:
        if st.button("▶ Next Round", use_container_width=True):
            _start_new_round()
            st.rerun()

# ── Round result summary ──────────────────────────────────────────────────────

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
        f"{emoji}&nbsp; This round: <strong>{round_correct} / {TARGET_BLANKS}</strong>"
        f" ({pct}%)&nbsp;&nbsp;|&nbsp;&nbsp;"
        f"Session total: <strong>{st.session_state.score_correct} / "
        f"{st.session_state.score_total}</strong>"
        f"</div>",
        unsafe_allow_html=True,
    )

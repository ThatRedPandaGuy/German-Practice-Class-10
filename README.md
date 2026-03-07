# 🇩🇪 Deutsches Lesen — German Reading Comprehension Practice App

> **⚠️ AI-Generated Project**: This entire application — including all code, data files, and this README — was designed and written by [Claude](https://claude.ai), an AI assistant made by Anthropic. No human wrote any of the source code. It is shared openly for learning, experimentation, and further development.

---

## What is this?

A lightweight, free-to-deploy **German reading comprehension (Lesen) trainer** built with [Streamlit](https://streamlit.io). It presents authentic German texts, blanks out key vocabulary words, and challenges you to fill each gap by choosing the correct word from a dropdown of near-synonyms — a classic cloze-test format used in CEFR language exams.

Synonyms are fetched live from [OpenThesaurus](https://www.openthesaurus.de), a free and open German synonym dictionary. No API key is required.

---

## Features

| Feature | Details |
|---|---|
| 📖 Cloze-test exercise | 5 blanks per round, each filled from a shuffled dropdown of the correct word + 2 real synonyms |
| 🎚️ CEFR difficulty filter | Filter texts by A1/A2, B1/B2, or C1/C2 before each round |
| ✅ Instant feedback | Per-blank ✅ / ❌ with the correct answer revealed on submission |
| 💡 Hint system | Reveal the first letter of any word without giving it away entirely |
| 📊 Score tracker | Running correct/total tally across your whole session |
| 🔁 Progress tracking | Already-seen texts are avoided until the full level pool is exhausted, then it resets |
| ⚡ Live synonym API | Words with fewer than 2 synonyms are automatically skipped and replaced |
| 🛡️ Graceful error handling | API timeouts and texts that are too short are handled without crashing |

---

## Project Structure

```
/
├── app.py            # Streamlit UI — all pages, widgets, and session logic
├── utils.py          # Text processing, OpenThesaurus API calls, blank builder
├── texts.json        # Text dataset (6 placeholder texts, A1–C1)
├── stopwords.txt     # ~200 German function/stop words
└── requirements.txt  # streamlit, requests
```

---

## Getting Started

### Run locally

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the app
streamlit run app.py
```

Your browser will open at `http://localhost:8501`.

### Deploy for free (Streamlit Community Cloud)

1. Push this repository to GitHub (all files in the root directory).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app** → select your repo → set the main file to `app.py`.
4. Click **Deploy**. No secrets or environment variables needed.

---

## Adding Your Own Texts

Edit `texts.json` and add entries following this schema:

```json
{
  "id": 7,
  "title": "Mein Titel",
  "level": "B1",
  "text": "Ihr deutscher Text hier..."
}
```

Supported CEFR levels: `A1`, `A2`, `B1`, `B2`, `C1`, `C2`.

The app will automatically include new texts in the rotation on next launch. No other changes are required.

---

## How It Works

1. A random text is selected from the pool matching your chosen CEFR level.
2. The text is tokenised and German stop words (articles, conjunctions, pronouns, etc.) are stripped out.
3. From the remaining content words, candidates are drawn one at a time and queried against the OpenThesaurus API.
4. Any word returning fewer than 2 synonyms is skipped; the process repeats until exactly 5 valid words are found.
5. Each blank is rendered as a dropdown containing the correct word shuffled with 2 synonym distractors.
6. On submission, answers are validated and the score is updated.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | [Streamlit](https://streamlit.io) |
| Synonym API | [OpenThesaurus](https://www.openthesaurus.de) (free, no key) |
| Language | Python 3.11+ |
| Hosting | Streamlit Community Cloud (free tier) |
| Data | Local JSON + plain-text files |

---

## Limitations & Notes

- The synonym API requires an internet connection at runtime — offline use is not supported.
- Synonym quality depends on OpenThesaurus coverage. Less common words may occasionally be skipped.
- The placeholder texts are designed for demonstration only. For serious study, replace them with graded authentic texts.

---

## License

This project is released into the public domain. Do whatever you like with it.

---

## About the AI Author

This project was generated in a single session by **Claude Sonnet** (claude.ai), an AI assistant built by [Anthropic](https://www.anthropic.com). The prompt specified the full feature set, file structure, edge-case handling, and deployment target. Claude wrote every line of code, data, and documentation without human edits.

If you find bugs or want to extend the app, feel free to open a PR — human contributions welcome.

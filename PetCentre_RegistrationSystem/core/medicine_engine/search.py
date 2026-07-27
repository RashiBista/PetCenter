"""
Typo-tolerant medicine search, backed by a TF-IDF model trained offline
on a curated veterinary-medicine dataset (see the top-level search/
notebook this was built from — the trained artifacts here are a copy of
search/models/*.pkl, bundled inside the Django project so they ship with
the Docker build instead of living outside it).

Loaded lazily (on first search) rather than at import time, so a
missing/corrupt pickle only breaks the specific request that needs it,
not the whole app on startup.
"""
import os
import pickle
import re
from difflib import get_close_matches

from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

_state = {}

# Maps common pet-owner phrasing (lay terms, plus a handful of the most
# likely single-word typos of them) to the clinical vocabulary this
# dataset actually uses — TF-IDF only ever matches on literal shared
# tokens, so "poop" and "diarrhea" have zero overlap no matter how
# semantically close they are to a person. Checked phrase keys (multi-
# word) before word-level correction; word keys are also fed through
# get_close_matches so close misspellings of these terms resolve too
# (see _expand_query).
SYMPTOM_SYNONYMS = {
    "worm": "worms deworming anthelmintic parasite",
    "worms": "deworming anthelmintic parasite",
    "deworming": "worms anthelmintic parasite",
    "poop": "diarrhea stool faecal",
    "poo": "diarrhea stool faecal",
    "diarrhea": "diarrhoea loose stool",
    "diarrhoea": "diarrhea loose stool",
    "throw up": "vomit vomiting",
    "throwing up": "vomit vomiting",
    "puke": "vomit vomiting",
    "puking": "vomit vomiting",
    "pee": "urinary urine",
    "peeing": "urinary urine",
    "itchy": "itching pruritus allergy skin",
    "itch": "itching pruritus allergy skin",
    "scratching": "itching pruritus allergy skin",
    "fever": "pyrexia temperature",
    "cough": "coughing respiratory bronchodilator expectorant",
    "coughing": "respiratory bronchodilator expectorant",
    "wound": "injury antiseptic",
    "cut": "injury antiseptic wound",
    "flea": "flea tick ectoparasite",
    "fleas": "flea tick ectoparasite",
    "ticks": "flea tick ectoparasite",
    "not eating": "appetite anorexia",
    "wont eat": "appetite anorexia",
    "won't eat": "appetite anorexia",
    "pain": "analgesic pain relief",
    "swelling": "inflammation antiinflammatory",
    "ear infection": "otitis ear",
    "eye infection": "conjunctivitis eye ophthalmic",
}


def _load(name):
    with open(os.path.join(DATA_DIR, name), "rb") as f:
        return pickle.load(f)


def _ensure_loaded():
    if _state:
        return
    _state["tfidf"] = _load("tfidf_vectorizer.pkl")
    _state["tfidf_matrix"] = _load("tfidf_matrix.pkl")
    _state["cosine_sim"] = _load("cosine_sim.pkl")
    _state["df"] = _load("medicine_dataset.pkl")
    _state["medicine_list"] = _state["df"]["generic_name"].str.lower().unique().tolist()
    # Word-level vocabulary drawn from what the dataset actually says
    # (category + indications), used to typo-correct clinical/symptom
    # words the way correct_query() already typo-corrects drug names —
    # e.g. "dirrhea"/"dirrohea" -> "diarrhea". Short words are dropped;
    # they produce too many spurious close matches to be useful.
    text = " ".join(_state["df"]["category"].astype(str)) + " " + " ".join(_state["df"]["indications"].astype(str))
    _state["clinical_vocab"] = sorted({w for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 4})
    # Single-word synonym keys, checked separately from clinical_vocab —
    # a typo of the LAY term itself (e.g. "scrathing" for "scratching")
    # won't be close to anything in the dataset's own vocabulary, since
    # "scratching" isn't a word the dataset uses; it only exists here.
    _state["synonym_keys"] = [k for k in SYMPTOM_SYNONYMS if " " not in k]


def _serialize_row(idx, row, similarity=None):
    entry = {
        "id": int(idx),
        "name": row["generic_name"].title(),
        "category": row["category"].title(),
        "dosage_form": row["dosage_form"].title(),
        "strength": row["strength"],
        "indications": row["indications"],
    }
    if similarity is not None:
        entry["similarity"] = round(float(similarity) * 100, 2)
    return entry


def correct_query(query):
    """Whole-query typo correction against known drug names (e.g. 'amocxilin' -> 'amoxicillin')."""
    _ensure_loaded()
    match = get_close_matches(query.lower().strip(), _state["medicine_list"], n=1, cutoff=0.7)
    return match[0] if match else query.lower().strip()


def _expand_query(query):
    """
    Symptom/lay-term handling for whatever correct_query() didn't already
    resolve as a drug name: phrase-level synonym swaps first (multi-word
    keys like "throw up"), then per-word — an exact synonym-dict hit, or
    else a fuzzy correction against the dataset's own clinical vocabulary
    — so "poop" pulls in diarrhea-related terms and "dirrohea" resolves
    to "diarrhea" the same way a misspelled drug name would.
    """
    q = query.lower().strip()
    expansions = [exp for phrase, exp in SYMPTOM_SYNONYMS.items() if " " in phrase and phrase in q]

    corrected_words = []
    for word in re.findall(r"[a-z]+", q):
        if word in SYMPTOM_SYNONYMS:
            expansions.append(SYMPTOM_SYNONYMS[word])
            corrected_words.append(word)
            continue
        syn_match = get_close_matches(word, _state["synonym_keys"], n=1, cutoff=0.75)
        if syn_match:
            expansions.append(SYMPTOM_SYNONYMS[syn_match[0]])
            corrected_words.append(syn_match[0])
            continue
        vocab_match = get_close_matches(word, _state["clinical_vocab"], n=1, cutoff=0.75)
        corrected_words.append(vocab_match[0] if vocab_match else word)

    return " ".join(corrected_words + expansions)


def smart_search(query, top_n=20):
    _ensure_loaded()
    df = _state["df"]
    stripped = query.lower().strip()
    drug_corrected = correct_query(query)
    # Only trust the drug-name correction if it actually changed
    # something — otherwise it's just the original query echoed back,
    # and symptom/lay-term expansion should get a turn instead.
    search_text = drug_corrected if drug_corrected != stripped else _expand_query(query)

    scores = cosine_similarity(_state["tfidf"].transform([search_text]), _state["tfidf_matrix"]).flatten()
    top_indices = scores.argsort()[::-1]

    results = []
    for idx in top_indices:
        if scores[idx] <= 0:
            continue
        results.append(_serialize_row(idx, df.iloc[idx], similarity=scores[idx]))
        if len(results) == top_n:
            break
    return results  # empty list if nothing found — the view decides the message


def list_all():
    """Full catalog, alphabetical — used for the default (no query) browse state."""
    _ensure_loaded()
    df = _state["df"].sort_values("generic_name")
    return [_serialize_row(idx, row) for idx, row in df.iterrows()]


def get_by_id(medicine_id):
    """A single medicine by its dataframe row index (the 'id' smart_search/list_all hand back)."""
    _ensure_loaded()
    df = _state["df"]
    try:
        row = df.loc[medicine_id]
    except KeyError:
        return None
    return _serialize_row(medicine_id, row)


def recommend_medicine(medicine_name, top_n=5):
    """Given a known medicine, other medicines with similar clinical profiles."""
    _ensure_loaded()
    df = _state["df"]
    matches = df.index[df["generic_name"] == medicine_name.lower().strip()].tolist()
    if not matches:
        return []
    idx = matches[0]
    sim = sorted(enumerate(_state["cosine_sim"][idx]), key=lambda x: x[1], reverse=True)
    sim = [s for s in sim if s[0] != idx][:top_n]
    return [_serialize_row(i, df.iloc[i], similarity=score) for i, score in sim]

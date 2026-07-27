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
from difflib import get_close_matches

from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

_state = {}


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
    _ensure_loaded()
    match = get_close_matches(query.lower().strip(), _state["medicine_list"], n=1, cutoff=0.7)
    return match[0] if match else query.lower().strip()


def smart_search(query, top_n=20):
    _ensure_loaded()
    df = _state["df"]
    corrected = correct_query(query)
    scores = cosine_similarity(_state["tfidf"].transform([corrected]), _state["tfidf_matrix"]).flatten()
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

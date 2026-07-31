#The train code iincase any thing changes in the future, only run this once to build the model and save the artifacts, then comment it out to avoid overwriting the saved models.
#and run it in collab
# import os, pickle
# import pandas as pd
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DATA_PATH = os.path.join(BASE_DIR, "data", "cleaned_veterinary_medicine.csv")
# MODEL_DIR = os.path.join(BASE_DIR, "models")
# os.makedirs(MODEL_DIR, exist_ok=True)

# CATEGORY_KEYWORDS = { ... }  # paste your full 54-entry dict from notebook cell 78

# def enrich_document(row):
#     text = str(row["combined_features"])
#     category = str(row["category"]).lower().strip()
#     if category in CATEGORY_KEYWORDS:
#         text += " " + CATEGORY_KEYWORDS[category]
#     return text

# def build():
#     df = pd.read_csv(DATA_PATH)
#     cols = ["generic_name", "category", "dosage_form", "strength", "indications"]
#     df[cols] = df[cols].fillna("")
#     for c in cols:
#         df[c] = df[c].str.lower().str.strip()

#     df["combined_features"] = (
#         df["generic_name"] + " " + df["category"] + " " + df["category"] + " " +
#         df["dosage_form"] + " " + df["strength"] + " " + df["indications"] + " " + df["indications"]
#     )
#     df["enriched_features"] = df.apply(enrich_document, axis=1)

#     tfidf = TfidfVectorizer(stop_words="english", lowercase=True)
#     tfidf_matrix = tfidf.fit_transform(df["enriched_features"])
#     cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

#     pickle.dump(tfidf, open(os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"), "wb"))
#     pickle.dump(tfidf_matrix, open(os.path.join(MODEL_DIR, "tfidf_matrix.pkl"), "wb"))
#     pickle.dump(cosine_sim, open(os.path.join(MODEL_DIR, "cosine_sim.pkl"), "wb"))
#     pickle.dump(df, open(os.path.join(MODEL_DIR, "medicine_dataset.pkl"), "wb"))
#     print(f"Saved artifacts to {MODEL_DIR}")

# if __name__ == "__main__":
#     build()

## Actual search enginee
import os, pickle
from difflib import get_close_matches
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")

# Loaded lazily (on first search) rather than at import time this file
# gets imported into a running Django process eventually, and a missing
# or stale pickle shouldn't crash the whole app on startup; it should
# only fail the specific request that actually needs a search.
_state = {}

def _load(name):
    with open(os.path.join(MODEL_DIR, name), "rb") as f:
        return pickle.load(f)

def _ensure_loaded():
    if _state:
        return
    _state["tfidf"] = _load("tfidf_vectorizer.pkl")
    _state["tfidf_matrix"] = _load("tfidf_matrix.pkl")
    _state["cosine_sim"] = _load("cosine_sim.pkl")
    _state["df"] = _load("medicine_dataset.pkl")
    _state["medicine_list"] = _state["df"]["generic_name"].str.lower().unique().tolist()

def correct_query(query):
    _ensure_loaded()
    match = get_close_matches(query.lower().strip(), _state["medicine_list"], n=1, cutoff=0.7)
    return match[0] if match else query.lower().strip()

def smart_search(query, top_n=5):
    _ensure_loaded()
    df = _state["df"]
    query = correct_query(query)
    scores = cosine_similarity(_state["tfidf"].transform([query]), _state["tfidf_matrix"]).flatten()
    top_indices = scores.argsort()[::-1]

    results = []
    for idx in top_indices:
        if scores[idx] <= 0:
            continue
        row = df.iloc[idx]
        results.append({
            "medicine": row["generic_name"].title(),
            "category": row["category"].title(),
            "dosage_form": row["dosage_form"].title(),
            "strength": row["strength"],
            "indications": row["indications"],
            "similarity": round(float(scores[idx]) * 100, 2),
        })
        if len(results) == top_n:
            break
    return results  # empty list if nothing found  view decides the message

def recommend_medicine(medicine_name, top_n=5):
    _ensure_loaded()
    df = _state["df"]
    matches = df.index[df["generic_name"] == medicine_name.lower().strip()].tolist()
    if not matches:
        return []
    idx = matches[0]
    sim = sorted(enumerate(_state["cosine_sim"][idx]), key=lambda x: x[1], reverse=True)
    sim = [s for s in sim if s[0] != idx][:top_n]
    return [{
        "medicine": df.iloc[i]["generic_name"].title(),
        "category": df.iloc[i]["category"].title(),
        "similarity": round(float(score) * 100, 2),
    } for i, score in sim]

if __name__ == "__main__":
    # Manual smoke test —> only runs when this file is executed directly
    
    print(smart_search("worms"))
    print(smart_search("rabies"))
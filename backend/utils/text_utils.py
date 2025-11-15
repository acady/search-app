import re

STOPWORDS = set([
    "und","oder","der","die","das","ein","eine","ist","sind",
    "the","and","of","in","to","for","a","an","on","at","mit"
])

def extract_keywords(text: str, max_keywords: int = 10):
    words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]{3,}", text.lower())
    freq = {}
    for w in words:
        if w in STOPWORDS:
            continue
        freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:max_keywords]]

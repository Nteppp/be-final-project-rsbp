from sentence_transformers import SentenceTransformer

model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

def embed_texts(texts: list[str]) -> list[list[float]]:
    return model.encode(texts).tolist()

    
    
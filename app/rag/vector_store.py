import faiss
import numpy as np
import os

VECTOR_PATH = "vector_store/resume_index.faiss"

dimension = 384

if os.path.exists(VECTOR_PATH):
    index = faiss.read_index(VECTOR_PATH)
else:
    index = faiss.IndexFlatL2(dimension)


def store_vector(vector):
    vector = np.array([vector]).astype("float32")
    index.add(vector)
    faiss.write_index(index, VECTOR_PATH)


def search_vectors(query_vector, k=5):
    query_vector = np.array([query_vector]).astype("float32")
    distances, indices = index.search(query_vector, k)
    return distances, indices
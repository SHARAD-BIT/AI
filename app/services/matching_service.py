from app.rag.embeddings import create_embedding
from app.rag.vector_store import search_vectors
from app.models.vector_metadata import get_metadata


def match_candidates(query):

    query_vector = create_embedding(query)

    distances, indices = search_vectors(query_vector, k=10)

    metadata = get_metadata()

    results = []

    for idx in indices[0]:

        if idx < len(metadata):

            results.append(metadata[idx])

    return results
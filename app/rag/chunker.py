def split_text(text, chunk_size=800, overlap=150):
    words = text.split()
    chunks = []

    if not words:
        return chunks

    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end]).strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks
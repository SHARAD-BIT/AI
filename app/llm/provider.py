import os
from ollama import chat


OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


def llm_json_extract(prompt: str, schema: dict) -> str:
    """
    Call Ollama with structured JSON output.
    Returns raw JSON string.
    """
    response = chat(
        model=OLLAMA_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        format=schema,
        options={
            "temperature": 0
        },
    )

    return response.message.content
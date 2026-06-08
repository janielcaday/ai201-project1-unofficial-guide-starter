from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL

_client = Groq(api_key=GROQ_API_KEY)

DISTANCE_THRESHOLD = 0.7

_SYSTEM_PROMPT = """\
You are a landlord/tenant assistant for Georgia property owners.
Answer ONLY using the provided document excerpts below.
Do NOT use your general knowledge or training data.
If the excerpts do not contain enough information to answer the question, respond with exactly:
"I don't have enough information in the loaded guides to answer that."
Never speculate or infer beyond what the documents explicitly state.\
"""


def generate_response(query, retrieved_chunks):
    """
    Generate a grounded answer from retrieved landlord/tenant guide chunks.

    `retrieved_chunks` is the list returned by retrieve(). Each item is a dict:
      - "text"     : the chunk text
      - "source"   : the source document filename
      - "distance" : cosine distance score (lower = more similar)

    Returns a plain string containing the LLM answer followed by a
    programmatically-built source list — attribution is never left to the model.
    """
    if not retrieved_chunks:
        return (
            "I couldn't find anything relevant in the loaded guides. "
            "Try rephrasing your question — or check that your ingestion pipeline is working."
        )

    passing = [c for c in retrieved_chunks if c["distance"] <= DISTANCE_THRESHOLD]

    if not passing:
        return (
            "I don't have enough information in the loaded guides to answer that."
        )

    context_block = "\n---\n".join(
        f"[Source: {c['source']}]\n{c['text']}" for c in passing
    )

    user_message = f"Document excerpts:\n{context_block}\n\nQuestion: {query}"

    response = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.0,
    )

    answer = response.choices[0].message.content.strip()

    unique_sources = sorted({c["source"] for c in passing})
    sources_block = "\n".join(f"• {s}" for s in unique_sources)

    return f"{answer}\n\nSources:\n{sources_block}"

import gradio as gr
from pathlib import Path

from ingest import load_all_documents
from retriever import embed_and_store, retrieve, get_collection
from generator import generate_response
from config import DOCS_PATH


# ---------------------------------------------------------------------------
# Ingestion — runs once on startup
# ---------------------------------------------------------------------------

def run_ingestion():
    """
    Load documents, chunk them, and store in ChromaDB.

    If the vector store is already populated, ingestion is skipped.
    To re-ingest (e.g. after adding documents), delete the
    ./chroma_db folder and restart the app.
    """
    collection = get_collection()

    if collection.count() > 0:
        print(f"Vector store already populated ({collection.count()} chunks). Skipping ingestion.")
        print("To re-ingest, delete the ./chroma_db folder and restart.")
        return

    print("Ingesting documents...")
    all_chunks = load_all_documents(Path(DOCS_PATH))

    if all_chunks:
        embed_and_store(all_chunks)
        print(f"Ingestion complete. {len(all_chunks)} chunks stored.")
    else:
        print(
            "\n⚠️  No chunks produced. Make sure documents/ contains .md files.\n"
            "    The app will start, but won't be able to answer questions yet.\n"
        )


# ---------------------------------------------------------------------------
# Chat handler
# ---------------------------------------------------------------------------

def chat(message, history):
    if not message.strip():
        return ""
    retrieved = retrieve(message)
    return generate_response(message, retrieved)


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

with gr.Blocks(
    theme=gr.themes.Soft(primary_hue="indigo"),
    title="Georgia Landlord/Tenant Guide",
) as demo:

    gr.HTML("""
        <div style="text-align:center; padding:1.25rem 0 0.5rem;">
            <h1 style="font-size:2rem; font-weight:700; color:#312e81; margin:0;">
                🏠 Georgia Landlord/Tenant Guide
            </h1>
            <p style="color:#6b7280; font-size:1rem; margin:0.4rem 0 0;">
                Ask anything about renting, leases, and property management in Georgia — answers straight from the guides.
            </p>
        </div>
    """)

    with gr.Row():
        with gr.Column(scale=3):
            gr.ChatInterface(
                fn=chat,
                type="messages",
                chatbot=gr.Chatbot(
                    height=440,
                    type="messages",
                    placeholder=(
                        "<div style='text-align:center; color:#9ca3af; margin-top:3rem;'>"
                        "Ask a landlord/tenant question to get started 🏡"
                        "</div>"
                    ),
                ),
                textbox=gr.Textbox(
                    placeholder='e.g. "How long does a landlord have to return a security deposit?"',
                    container=False,
                    scale=7,
                ),
                examples=[
                    "How long does a landlord have to return a security deposit in Georgia?",
                    "What can a landlord legally deduct from a security deposit?",
                    "What are valid grounds for evicting a tenant in Georgia?",
                    "What steps must a landlord follow to begin the eviction process?",
                    "What counts as an emergency repair that a tenant can demand immediately?",
                    "What should I include in a tenant screening checklist?",
                    "What are a landlord's required disclosures under Georgia law?",
                    "How should I handle a contractor who does poor work on my rental?",
                    "What records should I keep for rental property finances?",
                    "What must a landlord do before a move-out inspection?",
                ],
                cache_examples=False,
            )

        with gr.Column(scale=1, min_width=260):
            gr.HTML("""
                <div style="background:#f5f3ff; border:1px solid #ddd6fe;
                            border-radius:10px; padding:1rem; margin-top:0.5rem;">
                    <p style="font-size:0.8rem; font-weight:700; color:#4c1d95;
                               margin:0 0 0.5rem; letter-spacing:0.05em;">
                        📚 LOADED GUIDES
                    </p>
                    <ul style="font-size:0.82rem; list-style:none;
                                padding:0; margin:0; line-height:1.9;">
                        <li style="color:#5b21b6 !important;">🔨 Contractor Management</li>
                        <li style="color:#5b21b6 !important;">🚨 Emergency Repairs</li>
                        <li style="color:#5b21b6 !important;">⚖️ Eviction Process</li>
                        <li style="color:#5b21b6 !important;">📜 GA Landlord-Tenant Laws</li>
                        <li style="color:#5b21b6 !important;">📄 Lease Agreements</li>
                        <li style="color:#5b21b6 !important;">🛠️ Maintenance Requests</li>
                        <li style="color:#5b21b6 !important;">🔍 Property Inspections</li>
                        <li style="color:#5b21b6 !important;">💰 Rental Property Finances</li>
                        <li style="color:#5b21b6 !important;">🔐 Security Deposits</li>
                        <li style="color:#5b21b6 !important;">👤 Tenant Screening</li>
                    </ul>
                    <hr style="border:none; border-top:1px solid #ddd6fe; margin:0.75rem 0;">
                    <p style="font-size:0.75rem; color:#7c3aed; margin:0; line-height:1.5;">
                        Answers are grounded in the loaded guides only. If a topic
                        isn't covered, the assistant will say so.
                    </p>
                </div>
            """)


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  Georgia Landlord/Tenant Guide — starting up")
    print("=" * 50 + "\n")
    run_ingestion()
    demo.launch()

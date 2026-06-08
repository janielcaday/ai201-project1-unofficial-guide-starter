# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain
Homeowner / Landlord Assistant

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->

---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Georgia DCA | `.md` file | `documents/georgia_landlord_tenant_laws.md` |
| 2 | Federal Trade Commission | `.md` file | `documents/tenant_screening.md` |
| 3 | Fulton County Magistrate Court | `.md` file | `documents/eviction_process.md` |
| 4 | HUD | `.md` file | `documents/property_inspections.md` |
| 5 | ManageCasa | `.md` file | `documents/maintenance_requests.md` |
| 6 | Georgia Code Title 44 Ch. 7 | `.md` file | `documents/security_deposits.md` |
| 7 | Landlord resource article | `.md` file | `documents/contractor_management.md` |
| 8 | Property management resource | `.md` file | `documents/rental_property_finances.md` |
| 9 | Landlord resource guide | `.md` file | `documents/emergency_repairs.md` |
| 10 | Georgia lease template | `.md` file | `documents/lease_agreements.md` |
---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:** 1000 chars

**Overlap:** 200 chars

**Why these choices fit your documents:** Legal and property-management documents are structured around dense paragraphs and numbered clauses — 1000 chars captures a complete rule or obligation without over-packing multiple distinct concepts into one chunk, which would dilute retrieval precision. 200-char overlap ensures that facts split across a paragraph boundary (e.g., a condition on one side, its consequence on the other) still appear together in at least one chunk.

**Final chunk count:** 162

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers` (local, no API cost)

**Production tradeoff reflection:** If cost were not a constraint, I would evaluate larger models like `text-embedding-3-large` (OpenAI) or a domain-specific legal embedding model. The main tradeoffs are: `all-MiniLM-L6-v2` has a 256-token context limit, which can truncate longer chunks and lose information; larger models handle longer passages and domain-specific terminology more accurately. For a Georgia landlord/tenant system, legal terminology and statute citations need precise vector representations — a model trained on legal corpora would likely outperform a general-purpose model. The tradeoff is latency and hosting complexity: a local model is fast and private, while an API-hosted model introduces network round trips but requires no local GPU.

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**

```
You are a landlord/tenant assistant for Georgia property owners.
Answer ONLY using the provided document excerpts below.
Do NOT use your general knowledge or training data.
If the excerpts do not contain enough information to answer the question, respond with exactly:
"I don't have enough information in the loaded guides to answer that."
Never speculate or infer beyond what the documents explicitly state.
```

Before the chunks even reach the model, a distance filter (`distance <= 0.7`) drops any chunk that scored below relevance threshold — so the model never sees off-topic context. Only chunks that pass the filter are assembled into the prompt.

**How source attribution is surfaced in the response:** Source filenames are extracted programmatically from the passing chunks (not by the model) and appended to every response as a `Sources:` block. This prevents the LLM from fabricating or omitting citations — attribution is always constructed from the actual retrieval metadata.

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | **How long does a landlord have to return a security deposit in Georgia?** | *30 days after the lease ends* | *A landlord must return the security deposit within thirty (30) days after the termination of the Lease or in accordance with the applicable law on Security Deposit, whichever is applicable, however, another source also mentions "within thirty (30) days" after termination.* | Relevant | Accurate |
| 2 | **What should I check before approving a rental applicant?** | *income, review credit history, perform a background check, and contact previous landlords* | *I don't have enough information in the loaded guides to answer that.* | Off-target | Inaccurate |
| 3 | **What qualifies as an emergency repair in a rental property?** | *issues that threaten health, safety, or property, such as burst pipes, major water leaks, loss of heat during winter, electrical hazards, or sewage backups* | *Conditions that typically trigger immediate habitability obligations include roof leaks causing interior water damage, non-functioning heating systems in cold climates, sewage backups, confirmed mold growth affecting air quality, structural defects that pose safety risks, and infestations of rodents, cockroaches, or bedbugs. Minor aesthetic issues, such as scuffed paint or worn carpet, generally do not rise to a habitability violation.* | Relevant | Accurate |
| 4 | **What should be included in a move-out inspection?** | *document the property's condition, identify damages beyond normal wear and tear, take photographs when appropriate, and record any issues that may justify deductions from the security deposit.* | *A move-out inspection should include recording the condition and cost to correct (if applicable) for each item, using the inspection checklist. The checklist includes items such as entrance / halls, living room, dining room, kitchen* | Relevant | Accurate |
| 5 | **How can I avoid hiring a bad contractor?** | *obtain multiple estimates, verify licenses and insurance, check references, and avoid contractors who demand full payment upfront, accept only cash, or ask the property owner to obtain permits on their behalf.* | *To avoid hiring a bad contractor, you should be skeptical of contractors who solicit business door-to-door or send flyers in the mail. Steer clear of contractors who aren't listed anywhere. Avoid contractors who ask you to pay for an entire project up-front. Be wary of contractors who accept cash only. Don't hire contractors who ask you to obtain any needed permits for the work. You can find a good contractor by asking for recommendations from family, friends, colleagues, and other service professionals you like and trust, or by looking online at Google reviews, Yelp reviews, and other website comments.* | Relevant | Accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:** *What should I check before approving a rental applicant?*

**What the system returned:** *I don't have enough information in the loaded guides to answer that.*

**Root cause (tied to a specific pipeline stage):** Retrieval + distance filtering. The question "What should I check before approving a rental applicant?" is phrased around a landlord's decision-making process, but `tenant_screening.md` is framed around FCRA compliance and consumer reports — the semantic distance between those two framings pushed the relevant chunks past the 0.7 cosine distance threshold, so they were dropped before the model ever saw them. The model then had no grounded context and correctly refused to answer.

**What you would change to fix it:** Two options: (1) lower or remove the distance threshold and instead pass all top-k chunks to the model, relying on the system prompt to say "I don't know" when context is weak; (2) rephrase the tenant screening document to include more direct landlord-action language (e.g., "steps to approve an applicant") so its embeddings align more closely with the kinds of queries a landlord would ask.

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:** One way the spec helped me is that it helped me prompt AI much better. Because I had already written out the chunking strategy, retrieval approach, and architecture in planning.md before touching any code, I could paste specific sections directly into prompts and get accurate implementations on the first or second try. Without that spec, I would have been describing things vaguely and getting generic results.

**One way your implementation diverged from the spec, and why:** The planning.md verification target for Milestone 4 stated "confirm distance scores below 0.5." During testing, a threshold of 0.5 proved too strict — it filtered out chunks that were genuinely relevant but semantically phrased differently from the query (e.g., the tenant screening documents used FCRA compliance language while queries used landlord-action language). I raised the threshold to 0.7, which kept more potentially useful context and let the system prompt's grounding instruction handle cases where the context was still insufficient. The Q2 failure case shows the limit of even the relaxed threshold: 0.7 still wasn't wide enough to catch the screening chunks for that particular query framing.

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:* The Chunking Strategy section and Documents section from planning.md, plus the architecture diagram, and asked Claude to implement `ingest.py` with 1000-char chunks, 200-char overlap, and recursive splitting on headings and paragraphs.
- *What it produced:* A working `ingest.py` with `split_text()` using a separator hierarchy (`\n\n`, `\n`, `. `, ` `, `""`), a `clean_markdown()` function that strips formatting, and an `add_overlap()` function that prepends the tail of the previous chunk.
- *What I changed or overrode:* Added a `MIN_CHUNK_SIZE = 100` guard to drop fragments shorter than 100 chars, which wasn't in the original spec but turned out to be necessary after inspecting the output and finding several very small residual chunks.

**Instance 2**

- *What I gave the AI:* The Grounded Generation requirements from the milestone description (context-only answers, source attribution, Groq integration, Gradio UI) along with `retriever.py` and `ingest.py` as context.
- *What it produced:* `generator.py` with a system prompt enforcing context-only answers, a distance filter to drop low-relevance chunks, and a programmatic `Sources:` block appended after the model response. Also produced `app.py` with a `gr.ChatInterface` Gradio UI.
- *What I changed or overrode:* Set `temperature=0.0` on the Groq call (the initial output used `temperature=0.7`), to reduce the chance of the model embellishing beyond what the documents state.

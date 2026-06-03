🤖 LangGraph Business Agent
A practice project demonstrating LangGraph concepts by building a business assistant that answers accounting and inventory questions using CSV data and a local/cloud LLM (Groq).
Now includes human‑in‑the‑loop email approval and checkpointing.

🎯 What this project demonstrates
LangGraph Concept Implementation in this project
StateGraph & MessageGraph Custom AgentState with typed fields
Nodes Functions for classification, lookups, assessment, formatting, email sending
Conditional edges Routing by classification (accounting/inventory) and llm_assessment (low/acceptable)
Tool binding get_account_balance, get_overdue_customer_debt with bind_tools
Checkpointing MemorySaver for state persistence (ready for SqliteSaver/PostgresSaver)
Human‑in‑the‑loop interrupt_before + update_state with as_node for debt collection approval
Streaming stream_mode="updates" to show intermediate results
Subgraphs & parallel exec (Extendable – planned)
Testing & error handling Unit tests, fallback logic
🧩 Business Use Case
A small business owner asks questions like:

"What is the status of our cash balance?"

"Do we need to restock monitors?"

"Check our payroll balance for a small shop"

The agent:

Classifies the query (accounting or inventory)

Looks up data from CSV files (accounts, customers debt, inventory)

Calls an LLM (Groq) to assess the balance or recommend restocking

If the balance is low, it:

Fetches the most overdue customer debt

Drafts a polite collection email

Pauses execution and waits for human approval before sending

Returns a human‑friendly answer (with email status)

🛠️ Tech Stack
LangGraph – graph orchestration

LangChain – tools, LLM integration

Groq (or Ollama locally) – LLM for classification, assessment, email drafting

CSV – data storage (accounts, customers debt, inventory)

Python – 3.10+

uv / pip – package management

🧠 Understanding the Graph Flow

````mermaid
graph TD
    START --> classify[classify_question]
    classify --> |accounting| lookup[accounting_lookup]
    classify --> |inventory| inv_lookup[inventory_lookup]
    lookup --> assess[accounting_assessment]
    assess --> |low| collect[collect_debt]
    assess --> |acceptable| good[accounting_assessment_good]
    collect --> send_email[send_email <br/><i>interrupt before</i>]
    send_email --> format[format_response]
    good --> format
    inv_lookup --> inv_assess[inventory_assessment]
    inv_assess --> format
    format --> END
    ```
Node descriptions
classify_question – LLM classifies query as accounting or inventory.

accounting_lookup – Uses bind_tools to call get_account_balance (CSV lookup).

accounting_assessment – LLM labels balance as low or acceptable.

collect_debt – Fetches most overdue customer, drafts an email (LLM).

send_email – Simulates email sending. Execution pauses here (interrupt) until human approves.

accounting_assessment_good – Narrative assessment for acceptable balances.

inventory_lookup – Searches inventory CSV for the item.

inventory_assessment – LLM advises on restocking based on min/current quantities.

format_response – Formats final answer for display.

👤 Human‑in‑the‑Loop Approval
When a low cash balance triggers debt collection:

The graph runs until just before send_email.

The user sees the drafted email.

The user approves (y) or rejects (n) via input.

The graph resumes using update_state(..., as_node="node_send_email").

The email is marked as sent or rejected, and the final answer is displayed.
````

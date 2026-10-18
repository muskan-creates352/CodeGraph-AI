# CodeGraph AI — WeMakeDevs Graph Hacks Submission Guide 🚀

## 1. Track-Fit Pitch ("Agents That Act on Connected Data")

### One-Sentence Value Proposition:
> **CodeGraph AI is a zero-execution codebase investigation agent that acts on connected code topologies in FalkorDB to provide sub-20ms, verifiable graph evidence for refactoring impacts, execution paths, and dead code.**

### 120-Word Project Pitch:
> When software engineers refactor code or investigate incidents, traditional text grep tools produce overwhelming noise, while LLM chatbots hallucinate dependencies that do not exist. CodeGraph AI bridges this gap by transforming source code into a connected property graph stored in FalkorDB. 
> 
> Rather than relying on guesswork, our Investigation Agent acts directly on connected GraphBLAS matrices, executing declarative Cypher traversals in under 15 milliseconds. It uncovers multi-hop blast radiuses, isolates critical call execution chains, and identifies unreferenced dead code—backing every finding with transparent Cypher queries and exact source line references. By pairing static AST analysis with FalkorDB’s sub-millisecond graph engine, CodeGraph AI delivers codebase intelligence developers can actually trust.

### Why This Is the Premier Fit for "Agents That Act on Connected Data":
1. **The Graph Is Not an Optional Database:** In CodeGraph AI, the graph is the **reasoning engine**. Answering *"What breaks if function X changes?"* is fundamentally a graph reachability problem (`MATCH (caller)-[:CALLS*]->(target)`). Without FalkorDB, the agent cannot function.
2. **Decisions You Can Trace:** Unlike black-box generative models that produce unsupported text, CodeGraph AI returns the **exact graph traversal proof** (nodes, relationships, file paths, and line numbers) behind every decision.
3. **GraphBLAS Efficiency:** FalkorDB's linear algebraic sparse-matrix engine processes deep call chains in **1.3 ms to 17 ms**, proving the power of graph databases over recursive relational joins.

---

## 2. Compelling 2-Minute Demo Script (For Video Recording)

| Timestamp | Section | Visual on Screen | Spoken Script / Actions |
| :---: | :--- | :--- | :--- |
| **0:00 - 0:20** | **The Problem** | Slide or Terminal | *"Hi, I'm Muskan Kumari, and this is CodeGraph AI for WeMakeDevs Graph Hacks. When developers refactor code or investigate bugs, text grep gives noisy results, and AI chatbots hallucinate relationships. We built an agent that doesn't guess—it acts on connected graph data in FalkorDB."* |
| **0:20 - 0:45** | **1-Click Ingestion & Topology** | CodeGraph AI Dashboard | *Click **"Load Demo Repository"**.*<br/>*"In just 113 milliseconds, CodeGraph AI safely parses our e-commerce codebase with zero execution and ingests 25 nodes and 39 relationships into FalkorDB. On the canvas, you can see our Files in blue, Classes in purple, and Functions in amber, connected by CALLS, IMPORTS, and INHERITANCE edges."* |
| **0:45 - 1:15** | **Blast Radius Impact Analysis** | Investigation Console | *Select **"calculate_discount"** and click **"Investigate"**.*<br/>*"Let's test our agent: What happens if I change `calculate_discount`? Instantly—in 17 milliseconds—FalkorDB traces incoming CALLS edges. The agent highlights the affected nodes in red: `calculate_order_total` is directly affected at depth 1, and `checkout_order` is indirectly affected at depth 2."* |
| **1:15 - 1:40** | **Call Path Tracing & Dead Code** | Investigation Console | *Click **"Call Path Tracing"** (`post_checkout_endpoint` ➔ `format_log_entry`).*<br/>*"Next, how does our API endpoint reach our log formatter? The agent queries FalkorDB for the shortest path and reveals the exact 2-hop execution chain: `post_checkout_endpoint` invokes `log_info`, which calls `format_log_entry`."*<br/>*Switch to **"Dead Code"** tab:* *"Running dead-code detection finds two orphan helpers in `unused_helpers.py` with High Confidence, while correctly labeling public endpoints as low confidence."* |
| **1:40 - 2:00** | **Cypher Proof & Conclusion** | Cypher Inspector Drawer | *Expand **"Cypher Query Inspector"**.*<br/>*"Here is the best part: the agent shows the exact raw Cypher query and execution latency. Every decision is 100% verified ground truth from FalkorDB. CodeGraph AI gives developers real context they can trust. Thank you!"* |

### Recording Backup Plan:
* If Docker or the live database encounters local latency during screen capture:
  * Use the pre-warmed default graph (`codegraph`).
  * All 35 backend tests run in 2.3 seconds with `pytest backend/tests -v` as proof of working code.

---

## 3. Truthful AI Assistance Disclosure

In accordance with official WeMakeDevs hackathon rules:
* **Tool Utilization:** AI coding assistants were used during development as an interactive pair-programming partner and mentor.
* **Categories of AI Assistance:**
  1. Brainstorming and architecture outlining for the solo hackathon timeline.
  2. Synthesizing initial boilerplate for FastAPI endpoints and Pydantic request models.
  3. Generating comprehensive test scenarios for Pytest.
  4. Styling assistance with Tailwind CSS utility classes.
* **Human Direct Authorship:** All engineering logic, AST static visitor rules, Cypher traversal designs, FalkorDB schema design, and environment problem-solving (such as resolving WSL2 port-forwarding collisions) were directed, verified, tested, and implemented by Muskan Kumari.

---

## 4. Production Cloud Deployment Architecture (Plan)

*Currently, CodeGraph AI is configured for fast, zero-cost, offline local development on Windows via Docker Desktop.*

If deploying live for public web access:
1. **Frontend Hosting:** [Vercel](https://vercel.com/) or [Cloudflare Pages](https://pages.cloudflare.com/) (Deploying the static `dist/` directory produced by `npm run build`).
2. **Backend Hosting:** [Render](https://render.com/) or [Railway](https://railway.app/) (Running `uvicorn app.main:app` in a Python 3.11 container).
3. **Database Hosting:** [FalkorDB Cloud](https://app.falkordb.cloud/) (Managed cloud database instance with global endpoint and password protection).

### Required Environment Variables (By Name Only):
* `FALKORDB_HOST`: Hostname of the remote FalkorDB instance (e.g., `cloud.falkordb.com`).
* `FALKORDB_PORT`: Database port (e.g., `6379`).
* `FALKORDB_PASSWORD`: Authentication token for FalkorDB Cloud.
* `FALKORDB_GRAPH_NAME`: Target graph name (default: `codegraph`).
* `VITE_API_BASE_URL`: Base URL of the deployed FastAPI backend for frontend requests.

*(No secrets or credentials are hardcoded anywhere in the codebase).*

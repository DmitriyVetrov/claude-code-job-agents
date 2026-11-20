# AI market taxonomy

Controlled vocabulary for `data/ai-market/postings.jsonl`. Counts in the digest only add
up if every posting uses these exact tags. A new tag goes to **Proposed tags** first; the
user accepts it, then it moves to its group (and old postings may be re-tagged).

## Posting schema (one JSON object per line)

| Key | Type | Values |
|---|---|---|
| `id` | string | `<platform>:<platform job id>`, for example `linkedin:4431234567` |
| `seen` | date | the collect date, `YYYY-MM-DD` |
| `posted` | date or null | |
| `platform`, `url`, `title`, `company`, `location` | string | as on the posting |
| `region` | enum | `ES`, `EU-remote`, `NL`, `UK`, `IE`, `US`, `global-remote`, `other-EU`, `other` |
| `work_mode` | enum | `remote`, `hybrid`, `onsite`, `unclear` |
| `eligible_from_spain` | enum | `yes`, `no`, `unclear`: can a Spanish permanent resident (non-EU citizen) be hired as written, with no visa? |
| `seniority` | enum | `junior`, `mid`, `senior`, `staff+`, `unclear` |
| `years_required` | int or null | the minimum years stated |
| `archetype` | enum | see Archetypes |
| `languages` | tags | programming languages required or clearly used |
| `must_have` | tags | required |
| `nice_to_have` | tags | "bonus", "plus", "ideally" |
| `domain` | string | business domain in one or two words (`fintech`, `legal`, `customer support`, ...) |
| `salary` | string or null | as stated, with currency and period |
| `english` | enum | `B2-ok`, `C1+`, `native`, `unstated` |
| `responsibilities` | string | 1-2 sentences: what the person actually does |
| `signals` | list of strings | short free-text phrases that recur and matter (`evals in production`, `talks to customers weekly`, `own the agent end to end`) |
| `gap` | tags | `must_have` tags the candidate has no evidence for in the CV or portfolio.md |
| `readiness` | enum | `now` (could apply today), `stretch` (1-2 gaps closable in weeks), `far` (core skill missing: ML research, PhD, years of Python ML) |
| `hunt_candidate` | bool | a real .NET/C# backend role with an AI part that `/hunt` could apply to today |
| `notes` | string | anything else, short |

## Archetypes

| Tag | The job |
|---|---|
| `ai-app-engineer` | builds LLM features into a product: backend + model APIs + RAG/tools |
| `agent-engineer` | builds agentic systems: orchestration, tool use, multi-agent, memory |
| `ai-automation` | business-process automation with LLMs: n8n / Make / Zapier / Power Automate / scripts |
| `ai-solutions` | customer-facing: solutions / forward-deployed engineer, implementation, pre-sales |
| `ai-platform` | LLMOps / AI infra: gateways, serving, observability, evaluation platforms |
| `ai-integration-dotnet` | .NET / C# role integrating Azure OpenAI, Semantic Kernel, Agent Framework |
| `ai-quality` | evaluation, AI QA, red teaming, prompt engineering as the main job |
| `ml-engineer` | trains / fine-tunes models, classical ML, MLOps |
| `research` | research scientist / engineer, PhD-level |
| `ai-product` | AI product manager or owner |
| `freelance-gig` | an Upwork-style project, not a position |

## Skill tags

| Group | Tags |
|---|---|
| languages | `python`, `typescript`, `javascript`, `csharp`, `java`, `go`, `rust`, `sql` |
| model APIs | `openai-api`, `anthropic-api`, `azure-openai`, `bedrock`, `vertex-gemini`, `open-weight-llm`, `huggingface` |
| frameworks | `langchain`, `langgraph`, `llamaindex`, `semantic-kernel`, `ms-agent-framework`, `autogen`, `crewai`, `openai-agents-sdk`, `claude-agent-sdk`, `pydantic-ai`, `dspy`, `vercel-ai-sdk`, `haystack` |
| LLM concepts | `rag`, `embeddings`, `vector-db`, `hybrid-search`, `reranking`, `agents`, `tool-calling`, `multi-agent`, `mcp`, `prompt-engineering`, `structured-output`, `context-engineering`, `memory`, `guardrails`, `human-in-the-loop`, `streaming`, `document-processing`, `voice`, `computer-use`, `fine-tuning`, `cost-latency-optimization` |
| evaluation and observability | `evals`, `llm-observability`, `langsmith`, `langfuse`, `promptfoo`, `ragas`, `deepeval`, `arize-phoenix`, `ab-testing` |
| vector stores and search | `pgvector`, `pinecone`, `qdrant`, `weaviate`, `chroma`, `azure-ai-search`, `elasticsearch`, `opensearch` |
| automation | `n8n`, `make`, `zapier`, `power-automate`, `uipath`, `rpa` |
| engineering | `fastapi`, `django`, `nodejs`, `dotnet`, `aspnet`, `rest-api`, `microservices`, `event-driven`, `docker`, `kubernetes`, `ci-cd`, `testing`, `postgres`, `redis`, `react`, `nextjs` |
| cloud | `aws`, `azure`, `gcp` |
| ML | `pytorch`, `ml-fundamentals`, `transformers`, `mlops`, `statistics`, `nlp` |
| other | `customer-facing`, `product-sense`, `startup-experience`, `degree-cs`, `phd`, `security`, `data-pipelines`, `other` |

## Proposed tags

From the 2026-10-23 collect (recorded as `other` until accepted). Counts are postings.

| Proposed tag | Meaning | Seen |
|---|---|---|
| `ai-assisted-coding` | daily Claude Code / Cursor / Codex / Copilot use is a requirement | djinni ~23, linkedin 6, remote-boards 4 |
| archetype `ai-native-swe` | a regular SWE role where daily coding-agent use is required (now filed under ai-integration-dotnet / ai-app-engineer) | djinni 7 |
| `copilot-studio` | Microsoft low-code AI: Power Platform, Dataverse, Copilot Studio | linkedin 5, djinni 1 |
| `iac-terraform` | Terraform / Bicep / OpenTofu / CDK | linkedin 4, djinni 3 |
| `llm-general` | "experience with LLMs" with no named API or framework | linkedin 2, remote-boards 3 |
| `language-requirement` | a non-English language at C1/fluent (Spanish, Dutch, German, Italian): a hard filter for the candidate | linkedin 5 |
| `opentelemetry` | | linkedin 2 |
| `google-adk` | Google Agent Development Kit | linkedin 2 |
| `ml-libraries` | TensorFlow, scikit-learn | linkedin 3 |
| `graphql` | | djinni 1, remote-boards 1 |
| `angular` | | djinni 2 |
| `computer-vision` | YOLO / OpenCV | djinni 2 |
| `no-code-agent-platform` | Sierra, Decagon, Ada | remote-boards 1 |
| `knowledge-graphs` | Neo4j, ontologies | djinni 1 |
| `azure-data-platform` | Cosmos DB, Synapse | djinni 1 |
| `ai-governance` | governance for AI agents | djinni 1 |
| `gpu-llm-serving` | air-gapped GPU LLM serving | remote-boards 1 |
| `people-management` | hire and grow engineers | remote-boards 1 |
| `ruby`, `perl`, `jax-tpu`, `palantir-foundry`, `camunda`, `device-automation` | one-offs | 1-2 each |

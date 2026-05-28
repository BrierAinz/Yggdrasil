# Yggdrasil Architecture

High-level system design and data flow diagrams.

---

## System Overview

```mermaid
graph TB
    User[User / Developer]
    TG[Telegram Bot]
    CLI[Lilith CLI]
    API[Lilith API]
    Core[Lilith Core Engine]
    LLM[LM Studio<br/>Local LLM]
    Mem[Vector Memory<br/>SQLite + Embeddings]
    Tools[Tool Registry<br/>30+ Tools]
    Agents[Sub-Agent Pool]
    FS[File System]
    GH[GitHub API]
    Notify[Notification System]

    User -->|Chat| TG
    User -->|Commands| CLI
    User -->|HTTP| API

    TG -->|IPC / HTTP| Core
    CLI -->|Direct| Core
    API -->|FastAPI| Core

    Core -->|Prompt + Context| LLM
    Core -->|Store / Recall| Mem
    Core -->|Execute| Tools
    Core -->|Delegate| Agents

    Tools -->|Read / Write| FS
    Tools -->|API Calls| GH
    Tools -->|Push| Notify

    Agents -->|Spawn tasks| Core
```

---

## Message Flow

```mermaid
sequenceDiagram
    participant U as User
    participant I as Input Interface
    participant C as Core Orchestrator
    participant M as Memory
    participant L as LM Studio
    participant T as Tool Registry
    participant A as Sub-Agent

    U->>I: Send message
    I->>C: Forward message

    C->>M: Recall relevant context
    M-->>C: Return top-k memories

    C->>C: Build system prompt<br/>+ injected context
    C->>L: Send prompt
    L-->>C: Return LLM response<br/>(may include tool calls)

    alt Tool Call Detected
        C->>T: Execute tool
        T-->>C: Return result
        C->>L: Send result for final answer
        L-->>C: Return formatted response
    end

    alt Sub-Agent Required
        C->>A: Spawn agent with task
        A->>C: Return sub-result
        C->>L: Integrate sub-result
        L-->>C: Return final answer
    end

    C->>M: Store conversation
    C-->>I: Return response
    I-->>U: Display answer
```

---

## Memory Pipeline

```mermaid
graph LR
    Input[User Input / Tool Result]
    Extract[Entity Extraction]
    Embed[Sentence-Transformers<br/>Embedding]
    Store[(SQLite Vector Store)]
    Search[Cosine Similarity Search]
    Compress[Auto-Compression<br/>Old Conversations]
    Inject[Context Injection]

    Input --> Extract
    Extract --> Embed
    Embed --> Store
    Store --> Search
    Search --> Inject
    Store --> Compress
    Compress --> Store
```

---

## Tool Execution Flow

```mermaid
graph TD
    A[Tool Call Detected] --> B{Permission Required?}
    B -->|Yes| C[Ask User Confirmation]
    C -->|Approved| D[Execute Tool]
    C -->|Denied| E[Return Denied Message]
    B -->|No| D
    D --> F{Success?}
    F -->|Yes| G[Return Result]
    F -->|No| H[Retry / Fallback]
    H --> D
    G --> I[Store in Memory]
```

---

## Nine Realms Data Flow

```mermaid
graph LR
    Muspel[Muspelheim<br/>Active Dev]
    Asgard[Asgard<br/>Core Tech]
    Vanaheim[Vanaheim<br/>AI Agents]
    Alfheim[Alfheim<br/>UI / Frontend]
    Midgard[Midgard<br/>Personal Apps]
    Svartalf[Svartalfheim<br/>Docs / Knowledge]
    Niflheim[Niflheim<br/>Resources / Assets]
    Jotunheim[Jotunheim<br/>Massive Projects]
    Helheim[Helheim<br/>Archive]

    Muspel -->|Promote| Asgard
    Asgard -->|Consume| Vanaheim
    Vanaheim -->|Consume| Alfheim
    Asgard -->|Feed| Svartalf
    Muspel -->|Archive| Helheim
    Niflheim -->|Supply| Muspel
    Jotunheim -->|Merge| Asgard
```

---

## Sub-Agent Delegation

```mermaid
graph TB
    Orchestrator[Main Orchestrator]
    Agent1[Code Agent]
    Agent2[Research Agent]
    Agent3[Debug Agent]
    Agent4[Creative Agent]

    Orchestrator -->|"task: refactor"| Agent1
    Orchestrator -->|"task: investigate"| Agent2
    Orchestrator -->|"task: fix bug"| Agent3
    Orchestrator -->|"task: generate content"| Agent4

    Agent1 -->|result| Orchestrator
    Agent2 -->|result| Orchestrator
    Agent3 -->|result| Orchestrator
    Agent4 -->|result| Orchestrator

    Orchestrator -->|"synthesize & respond"| User
```

---

## Deployment Architecture

```mermaid
graph TB
    Dev[Developer Machine]
    LM[LM Studio<br/>localhost:1234]
    Lilith[Lilith Core<br/>localhost:8000]
    TG_Bot[Telegram Bot<br/>Polling]
    CLI[CLI Terminal]
    Browser[Web Browser]

    Dev -->|Runs| LM
    Dev -->|Runs| Lilith
    Dev -->|Runs| TG_Bot
    Dev -->|Uses| CLI
    Dev -->|Opens| Browser

    Lilith <-->|OpenAI API| LM
    TG_Bot <-->|HTTP| Lilith
    CLI <-->|Direct| Lilith
    Browser <-->|HTTP / WS| Lilith
```

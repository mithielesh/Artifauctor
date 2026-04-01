# Artifauctor - Autonomous Content Pipeline

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-8E75B2?style=flat-square&logo=googlebard&logoColor=white)](https://aistudio.google.com/)
[![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-F7DF1E?style=flat-square&logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.0-38B2AC?style=flat-square&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![GraphQL](https://img.shields.io/badge/GraphQL-E10098?style=flat-square&logo=graphql&logoColor=white)](https://graphql.org/)

An enterprise-grade, multi-agent AI SEO engine that researches, drafts, validates, and autonomously deploys high-ranking content using a Human-in-the-Loop (HITL) architecture.

## System Architecture

```mermaid
flowchart LR
    %% Styling
    classDef input fill:#f3f0ff,stroke:#1f2937,stroke-width:2px,color:#111827
    classDef agent fill:#818cf8,stroke:#1f2937,stroke-width:2px,color:#fff
    classDef external fill:#1f2937,stroke:#fff,stroke-width:2px,color:#fff
    classDef deploy fill:#10b981,stroke:#1f2937,stroke-width:2px,color:#fff

    %% Flow
    User([User Input]) --> API{FastAPI Engine}
    
    %% Research Phase
    API -->|1. Keyword| Scraper[Tavily Scraper]
    Scraper -.->|Live SERP Data| API
    
    %% Multi-Agent Pipeline
    API -->|2. Context| Strat[Agent 1: Strategist]
    Strat -->|Outline| Writer[Agent 2: Writer]
    Writer -->|Draft| Val[Agent 3: Validator]
    
    %% HITL Deployment
    Val --> UI[Neo-Brutalist UI & Metrics]
    UI --> App{HITL Approval}
    
    %% Publishing
    App -->|Approve| DevTo[Dev.to REST API]
    App -->|Approve| Hash[Hashnode GQL API]
    App -->|Reject| Drop((Discard))

    %% Apply Classes
    class User,UI,Drop input;
    class Strat,Writer,Val agent;
    class Scraper external;
    class DevTo,Hash deploy;
```

## Core Features

### Multi-Agent AI Pipeline
- **Strategist Agent:** Analyzes live SERP gaps to create hyper-targeted, domain-specific outlines.
- **Master Writer Agent:** Drafts 1,000+ word deep-dives using the PAS framework (Problem-Agitate-Solution) with code snippets and Markdown tables.
- **Validator Agent:** Runs local heuristic scoring for SEO performance, naturalness, keyword density, and snippet readiness.

### Real-Time Intelligence & Reliability
- **Zero-Hallucination Grounding:** Uses Tavily to inject live Google Search data directly into the LLM context window.
- **Enterprise Retry Logic:** Built-in exponential backoff to seamlessly handle API rate limits (HTTP 429) without crashing.

### Human-in-the-Loop (HITL) Deployment
- **Staging Dashboard:** Holds generated content in a pending state for editorial review.
- **One-Click Publishing:** Transforms approved drafts into live articles on Dev.to and Hashnode instantly.
- **BYOK Architecture:** Designed to support "Bring Your Own Key" for stateless, zero-liability public hosting.

### Neo-Brutalist UX
- **Custom CSS Engine:** Pastel Space Grotesk aesthetics with sharp borders, heavy shadows, and interactive input pills.
- **Agent Visualizer:** Custom CSS keyframe animations representing the 3 backend agents working in tandem.

## Technology Stack

**Backend**
- Python 3.9+ / FastAPI
- Uvicorn (ASGI Server)

**AI & External APIs**
- Google Gemini API (gemini-2.5-flash-lite)
- Tavily Search API
- Hashnode GraphQL 2.0 API
- Dev.to REST API

**Frontend**
- HTML5 / Vanilla JavaScript (ES6)
- Tailwind CSS (Utility styling)
- Marked.js (Markdown to HTML parsing)

## API Overview

### AI Generation (/api/v1)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/generate` | POST | Triggers SERP scraper and full multi-agent generation pipeline. Returns content & SEO metrics. |

### HITL Deployment (/api/v1/publish)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/publish/devto` | POST | Pushes approved Markdown payload to Dev.to via REST API. Returns live URL. |
| `/publish/hashnode` | POST | Pushes approved Markdown payload to Hashnode via GraphQL. Returns live URL. |

## License

![MIT License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)

# SAIKO: Local-First AI Orchestrator

> **Status:** Alpha (v10)
> **Architecture:** Decoupled Client-Server (REST API)
> **Latency:** ~1.2s End-to-End (Voice-to-Voice)
> **Privacy:** 100% Offline / Zero-Egress

## Executive Summary
Saiko is a fully **containerized, private AI agent** designed for high-performance voice interaction on consumer hardware.

Unlike standard chatbots that rely on cloud APIs (OpenAI/Anthropic), Saiko runs a custom **ExLlamaV2 inference engine** locally, orchestrated by a stateless FastAPI backend. It features a custom "NeuroCortex" RAG system for instant policy retrieval and a self-healing SQLite database for transactional logic, achieving 3 to 1.2s latency without sending data to the cloud.

## System Architecture


```mermaid
---
config:
  layout: fixed
  theme: neo
  look: classic
---
flowchart TB
 subgraph HOST["WINDOWS HOST "]
    direction TB
    Mic["Microphone"]
    Spk["Speakers"]
    
    subgraph CLIENT["client.py"]
        AsyncLoop["AsyncIO Event Loop"]
        Ears["Faster-Whisper (Multiprocess)"]
        Mouth["PyTTSx3 (Threaded)"]
    end
 end
 
 subgraph DOCKER["DOCKER CONTAINER"]
    direction TB
    API["FastAPI (server.py)"]
    
    subgraph CORE["Neural Engine"]
        Bridge["Queue Bridge"]
        Cortex["NeuroCortex (RAG)"]
        Controller["Stateless Logic"]
        ExLlama["Mistral-Nemo (GPU)"]
        DB[("SQLite (Orders)")]
    end
 end

    %% DATA FLOW
    Mic --> Ears
    Ears -- "Text Packet" --> AsyncLoop
    AsyncLoop -- "POST /chat (JSON)" --> API
    
    API --> Bridge
    Bridge --> Cortex
    Cortex -- "RAG Context" --> Controller
    Cortex -- "Call Flow" --> Controller
    Controller -- "Query" --> DB
    Controller -- "Inference Request" --> ExLlama
    ExLlama -- "Stream Tokens" --> Controller
    Controller --> Bridge
    Bridge --> API
    
    API -- "200 OK (JSON)" --> AsyncLoop
    AsyncLoop -- "TTS Stream" --> Mouth
    Mouth --> Spk

    %% STYLING
    style DOCKER fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000000
    style HOST fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#000000
    style CORE fill:#b3e5fc,stroke:#0277bd,stroke-dasharray: 5 5,color:#000000
    style CLIENT fill:#ffe0b2,stroke:#ef6c00,stroke-dasharray: 5 5,color:#000000
    style ExLlama fill:#ccff90,stroke:#33691e,stroke-width:2px,color:#000000
    linkStyle default stroke:#000000,stroke-width:2px;
```

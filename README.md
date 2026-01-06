graph TD
    %% HARDWARE LAYER
    subgraph HARDWARE [Consumer Hardware (RTX 3060)]
        Mic[🎙️ Microphone]
        GPU[🔥 GPU (CUDA)]
        RAM[🧠 RAM (12GB VRAM + Sys)]
    end

    %% PROCESS 1: EARS
    subgraph PROCESS_EARS [Process: The Ears (faster_ears.py)]
        direction TB
        PyAudio[PyAudio Stream]
        VAD{Silero VAD}
        Whisper[Distil-Whisper Large]
        
        Mic --> PyAudio
        PyAudio --> VAD
        VAD -- Voice Detected --> Whisper
        Whisper -- "GPU Compute" --> GPU
    end

    %% IPC BRIDGE
    Queue((IPC Queue))
    PROCESS_EARS -- "Text Packet" --> Queue

    %% PROCESS 2: BRAIN
    subgraph PROCESS_BRAIN [Process: The Brain (brain.py)]
        direction TB
        Bridge[BrainBridge Listener]
        
        %% LAYERS
        Regex{Regex 'Reflex' Layer}
        Router{Semantic Router}
        LLM[Mistral-Nemo LLM]
        
        Queue --> Bridge
        Bridge --> Regex
        
        %% LOGIC FLOW
        Regex -- "Simple Query (Greeting/Wait)" --> Response_Fast[Cached Response]
        Regex -- "Complex Query" --> Router
        
        Router -- "Intent Check" --> RAM
        Router -- "RAG/Context" --> LLM
        
        LLM -- "Inference" --> GPU
        LLM --> Response_Slow[Generated Response]
    end

    %% UI LAYER
    subgraph PROCESS_UI [Main Thread: GUI (main.py)]
        DPG[DearPyGui Renderer]
        Stream[Async Token Streamer]
    end

    Response_Fast --> DPG
    Response_Slow --> Stream --> DPG
    
    %% STYLING
    style PROCESS_EARS fill:#f9f,stroke:#333,stroke-width:2px
    style PROCESS_BRAIN fill:#bbf,stroke:#333,stroke-width:2px
    style GPU fill:#ff9,stroke:#f00

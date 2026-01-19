# syntax=docker/dockerfile:1
# ^ KEEP THIS TOP LINE. It enables the advanced BuildKit features.

# 1. THE MILITARY BASE
FROM nvidia/cuda:12.1.1-devel-ubuntu22.04

# 2. PREVENT HANGS
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Mexico_City

# 3. ENV VARS
ENV PYTHONUNBUFFERED=1
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}

# 4. SYSTEM DEPS (Cached)
# We combine these into one RUN to reduce image layers
RUN apt-get update && apt-get install -y software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3-pip \
    git \
    build-essential \
    ninja-build \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# 5. PYTHON ALIAS
RUN ln -sf /usr/bin/python3.11 /usr/bin/python3 \
    && ln -sf /usr/bin/python3.11 /usr/bin/python

# 6. UPGRADE PIP (With Cache!)
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m ensurepip --upgrade \
    && python -m pip install --upgrade pip

# 7. WORKDIR
WORKDIR /app

# 8. INSTALL TORCH (The Heavy Hitter)
# This mount saves the 2GB+ download so you never download it twice.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 9. INSTALL REQUIREMENTS
COPY requirements.txt .
# Using cache mount here too
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefer-binary -r requirements.txt

# 10. COPY THE BRAIN
COPY . .

# 11. LAUNCH
EXPOSE 8000
# Added --reload for dev mode (optional, see below)
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
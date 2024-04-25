#FROM nvidia/cuda:12.3.1-runtime-ubuntu20.04
#FROM nvidia/cuda:12.3.1-devel-ubuntu22.04
FROM nvidia/cuda:12.2.0-devel-ubuntu22.04
#FROM python:3.10-slim-bullseye

RUN apt-get update \
    && DEBIAN_FRONTEND="noninteractive" apt-get install -y --no-install-recommends \
        git \
        locales \
        sudo \
        build-essential \
        dpkg-dev \
        wget \
        openssh-server \
        nano \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ADD ./src/ /app
RUN pip install --no-cache-dir -r requirements.txt
#ENV CMAKE_ARGS="-DLLAMA_CUBLAS=ON"
#ENV FORCE_CMAKE=1 
#RUN CMAKE_ARGS="-DLLAMA_CUBLAS=ON" FORCE_CMAKE=1 pip install --upgrade --force-reinstall llama-cpp-python --no-cache-dir
RUN CUDACXX=/usr/local/cuda-12/bin/nvcc CMAKE_ARGS="-DLLAMA_CUBLAS=on -DCMAKE_CUDA_ARCHITECTURES=all-major" FORCE_CMAKE=1 \
    pip install "llama-cpp-python==0.2.57" --no-cache-dir --force-reinstall --upgrade
EXPOSE 80

ENV PYTHONDONTWRITEBYTECODE=1

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"] 
FROM python:3.10-slim-bullseye as builder
#FROM tensorflow/tensorflow:2.15.0.post1 as builder

WORKDIR /app
ADD ./src/ /app

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
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
#RUN pip install transformers[tf-cpu]

RUN CMAKE_ARGS="-DLLAVA_BUILD=off" pip install --no-cache-dir -r requirements.txt
#RUN CMAKE_ARGS="-DLLAMA_CUBLAS=on" FORCE_CMAKE=1 pip install llama-cpp-python

FROM python:3.10-slim-bullseye

COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
#RUN rm -rf /usr/local/lib/python3.10/site-packages/nvidia*
WORKDIR /app
ADD ./src /app

EXPOSE 80

ENV PYTHONDONTWRITEBYTECODE=1

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"] 
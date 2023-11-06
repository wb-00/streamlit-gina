# app/Dockerfile

FROM python:3.11.6-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/wb-00/streamlit-gina.git .

RUN pip3 install --upgrade pip

RUN pip3 install -r requirements.txt

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "Basic_Info.py", "--server.port=8501", "--server.address=0.0.0.0"]

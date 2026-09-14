FROM python:3.10-slim

WORKDIR /app

COPY indexer/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY indexer/indexer.py ./
COPY indexer/memory_indexer.py ./

ENTRYPOINT ["python", "indexer.py"]
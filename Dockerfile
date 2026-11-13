FROM python:3.12.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0

WORKDIR /workspace
COPY . /workspace

ENTRYPOINT ["python", "main.py"]
CMD ["--help"]


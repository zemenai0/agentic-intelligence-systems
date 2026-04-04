FROM python:3.12.3-slim

WORKDIR /app

COPY pyproject.toml setup.py README.md ./
COPY requirements ./requirements
COPY src ./src

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "agentic_intelligence_systems.api:app", "--host", "0.0.0.0", "--port", "8000"]

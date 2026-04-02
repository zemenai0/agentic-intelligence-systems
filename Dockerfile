FROM python:3.12.3-slim

WORKDIR /app

COPY pyproject.toml setup.py README.md ./
COPY requirements ./requirements
COPY src ./src

RUN pip install --no-cache-dir -e .

CMD ["python", "--version"]

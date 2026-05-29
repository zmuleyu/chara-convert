FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir pip==24.0
COPY chara-convert /chara-convert
COPY apps/api /app
# Install both LLM backend SDKs so a single image works for either
# ANTHROPIC_API_KEY or DEEPSEEK_API_KEY (factory picks at runtime).
RUN pip install --no-cache-dir -e '/chara-convert[ai,deepseek]' -e /app
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir pip==24.0
COPY chara-convert /chara-convert
COPY apps/api /app
RUN pip install --no-cache-dir -e /chara-convert -e /app
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

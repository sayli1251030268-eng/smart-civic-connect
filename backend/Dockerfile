FROM python:3.11-slim
# Build with --build-arg WITH_AI=true to include PyTorch (CPU) + CLIP. Needs roughly 2 GB RAM at runtime.
ARG WITH_AI=false
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HOME=/app/.cache
WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt
RUN if [ "$WITH_AI" = "true" ]; then \
      pip install torch --index-url https://download.pytorch.org/whl/cpu && \
      pip install "transformers==4.44.2" "numpy<2"; fi
COPY app ./app
RUN useradd -m app && mkdir -p uploads .cache && chown -R app /app
USER app
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]

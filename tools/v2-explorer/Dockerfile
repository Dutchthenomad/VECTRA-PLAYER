FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    duckdb \
    numpy \
    pandas \
    pydantic \
    scipy \
    matplotlib \
    seaborn

# Copy application code
COPY . /app/

# Notebooks are mounted as a volume at runtime (/app/notebooks)
# The sidebet module adds this to sys.path to import analysis code

EXPOSE 9040

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9040"]

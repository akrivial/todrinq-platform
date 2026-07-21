FROM python:3.11

WORKDIR /app

ENV TODRINQ_SCHEDULER_ENABLED=true
ENV PYTHONUNBUFFERED=1

COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

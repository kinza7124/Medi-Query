<<<<<<< HEAD
FROM python:3.10-slim-buster

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt

CMD ["python3", "app.py"]
=======
FROM python:3.10-slim-buster

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
COPY setup.py /app/setup.py
COPY src /app/src
COPY app.py /app/app.py
COPY improved_retrieval.py /app/improved_retrieval.py
COPY rag_evaluation_comprehensive.py /app/rag_evaluation_comprehensive.py
COPY run_comprehensive_evaluation.py /app/run_comprehensive_evaluation.py
COPY store_index.py /app/store_index.py
COPY templates /app/templates
COPY static /app/static
COPY data /app/data
COPY docs /app/docs

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY wsgi.py /app/wsgi.py

EXPOSE 5000

CMD ["gunicorn", "--workers", "2", "--worker-class", "gthread", "--threads", "8", "--timeout", "120", "--bind", "0.0.0.0:5000", "wsgi:app"]
>>>>>>> 0f3dabdf0489b2ce5e7d2ba60cbccf4a3d92b1ce

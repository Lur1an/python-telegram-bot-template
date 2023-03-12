FROM python:3.11
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
ENV PYTHONPATH "${PYTHONPATH}:/src"
RUN pwd
RUN ls
CMD ["python", "./src/main.py"]


FROM python:3.12-alpine

RUN apk add --no-cache openssh-client

RUN pip install flask

COPY app.py .

CMD ["python","app.py"]
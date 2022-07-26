FROM python:3.9-slim
# FROM python:3.9-alpine

ADD . /code
WORKDIR /code

# RUN apk add build-base

RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt
CMD ["/bin/sh", "-c", "python run.py"]


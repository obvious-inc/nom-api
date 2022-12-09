ARG PYTHON_FULL_VERSION=3.9.13
ARG POETRY_VERSION=1.2.2
ARG PIP_MIN_VERSION=22.3.1

FROM python:$PYTHON_FULL_VERSION

ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade 'pip>=$PIP_MIN_VERSION'

ARG POETRY_VERSION
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/usr/local POETRY_VERSION=$POETRY_VERSION python -
RUN poetry config virtualenvs.create false && poetry config virtualenvs.in-project false

WORKDIR /code

COPY tox.ini pyproject.toml poetry.lock scripts ./
RUN poetry install

COPY app ./app

CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "5001"]

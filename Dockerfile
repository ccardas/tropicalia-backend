FROM python:3.7-buster

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python

ENV PATH="${PATH}:/root/.poetry/bin"

RUN mkdir -p $HOME/.tropicalia/

WORKDIR /tropicalia
COPY poetry.lock pyproject.toml /tropicalia/

RUN poetry config virtualenvs.create false \
  && poetry install --no-dev --no-interaction --no-ansi

COPY . /tropicalia

CMD ["poetry", "run", "tropicalia"]
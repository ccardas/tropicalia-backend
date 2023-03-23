FROM python:3.7-buster

#RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
ENV GET_POETRY_IGNORE_DEPRECATION=1

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/1.3/get-poetry.py | python 

ENV PATH="${PATH}:/root/.poetry/bin"

COPY db.sqlite3 /.tropicalia/

WORKDIR /tropicalia
COPY poetry.lock pyproject.toml /tropicalia/

RUN poetry config virtualenvs.create false \
  && poetry install --no-dev --no-interaction --no-ansi

COPY . /tropicalia

EXPOSE 8001

CMD ["poetry", "run", "tropicalia"]

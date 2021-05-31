## [TROPICAL-IA](https://github.com/ccardas/tropicalia-backend) 

---

<a href="https://github.com/ccardas/tropicalia-backend"><img alt="Version: 0.5.5" src="https://img.shields.io/badge/version-2.0-success?color=0080FF&style=flat-square"></a> <a href="https://github.com/ccardas/tropicalia-backend"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square"></a>

*TROPICAL-IA is an asynchronous algorithm training and forecasting platform supported by a RESTful API*

This project requires the following to work:

* SQLite3
* MinIO

You can setup a minimal development environment using Docker Compose.

```commandline
docker-compose up -d
```

### 🚀 Setup 

#### Installation

Via source code using [Poetry](https://github.com/python-poetry/poetry):

```commandline
git clone https://github.com/ccardas/tropicalia-backend.git
cd tropicalia-backend
poetry install
```

Before running `tropicalia`, save a copy of [`.env.template`](.env.template) as `.env` and insert your own values. 
`tropicalia` will then look for a valid `.env` file in the **current working directory**. In its absence, it will use the default values from the config file.

#### Deploy server 

Server can be [deployed](https://fastapi.tiangolo.com/deployment/) with *uvicorn*, a lightning-fast ASGI server, using the command-line client.

```commandline
poetry run tropicalia
```

Alternatively, use the provided [`Dockerfile`](Dockerfile):

```commandline
sudo docker build . -t tropicalia-backend
sudo docker run -p 8001:8001 tropicalia-backend
```

Online documentation is available at `/api/docs`.
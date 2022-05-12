# NewShades API

This is the API used by NewShades DAO.

## Getting started

Check what's the tech stack being used for the API and how to start it locally.

### Built With

Major tech being used:

* Python
* MongoDB
* Docker
* [FastAPI](https://fastapi.tiangolo.com/)

### Prerequisites

We're using Python 3.9.9. Make sure you're using the same version, or use Docker to run this.

### Installation

If you prefer using Docker for development, clone the repo and simply run:

```sh
docker compose up --build
```

Otherwise, you can follow these steps:

1. Clone the repo
   ```sh
   git clone git@github.com:NewShadesDAO/api.git
   ```
2. Install `poetry` – dependency management tooling for Python ([see full installation documentation for additional options](<https://github.com/python-poetry/poetry#installation>))
   ```sh
   curl -sSL https://install.python-poetry.org | python3 -

   # Note: add `export PATH="~/Library/Python/3.9/bin:$PATH"` to your shell configuration file.
   ```
3. Install packages
   ```sh
   poetry install
   ```
4. Setup local .env file
   ```sh
   cp .env.template .env
   ```
5. Run the server
   ```sh
   poetry run uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload
   ```

### Testing

You can run all tests by running `poetry run pytest` on the shell or via docker:

```sh
docker exec -it <container_id> pytest
```

Make sure you replace `<container_id>` with the container running the API.

## Usage

Go to `/docs` to find the API documentation. Locally: `http://localhost:5001/docs`

- [ ] Add Insomnia shared workspace

## Contributing

Pull requests are welcome. For major changes, please open an issue first or ping a core member in discord (#development) to discuss what you would like to change.

Please make sure to update tests as appropriate.

To run both linters and tests locally you can do:

```
docker compose exec web mypy . && flake8 && black . && isort .
docker compose exec web pytest -rf
```

If you're not using docker, remove the `docker compose exec web` part.

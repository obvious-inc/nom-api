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
2. Install packages
   ```sh
   pip install -r requirements.txt
   ```
3. Setup local .env file
   ```sh
   copy .env.template .env
   ```
4. Run the server
   ```sh
   uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload
   ```

### Testing

You can run all tests by running `pytest` on the shell or via docker:

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

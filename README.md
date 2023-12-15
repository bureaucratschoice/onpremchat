# What it does? 
* With this repo you get a container which offers a rest api to a local hosted llama based llm. No GPU required.
* Models are downloaded on first time of usage and stored in an external mount.

# How to configure it?

* LLM specific configuration is done via config/config.yml. Default config loads a german fine tuned llm. 
* Container specific configuration is done via docker-compose.yml.

# How to use it?

* docker-compose up
* By default, service is available under localhost:8000.
* To learn about the api and try things out, connect to localhost:8000/docs

# How to use it secure?
* Service provides basic security suitable for usage inside perimeter. It's not recommende to directly expose the service to the internet.


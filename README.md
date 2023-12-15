# What it does? 
* With this repo you get a container which offers a rest api to a local hosted llama based llm. No GPU required.
* Models are downloaded on first time of usage and stored in an external mount.
* Chat history is held in memory only.

# What ressources do you need?
* The system uses as much CPU cores as you can provide. For acceptable performance 4 cores are recommended.
* Maximum RAM required is about 8 GB. In general less than 1 GB is used.

# How to configure it?

* Configuration is done via environment variable. Default config loads a german fine tuned llm. 

# How to use it?

* docker-compose up
* By default, service is available under localhost:8000.
* A frontend to chat with the llm is available under localhost:8000/chat
* To learn about the api and try things out, connect to localhost:8000/docs

# How to use it secure?
* Service provides basic security suitable for usage inside perimeter. It's not recommende to directly expose the service to the internet.


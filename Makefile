build:
	docker-compose build

shell:
	docker-compose run --rm shell /bin/bash

clean:
	docker-compose down --volumes --remove-orphans --rmi local
	docker image prune -f

lint:
	ruff format .
	ruff check --fix  .

admin:
	echo "👉 You need to 'cd /app' to be able to use the code!!"
	docker-compose run --rm -v $$(pwd):/app --entrypoint bash temporal-admin-tools

up:
	docker-compose up temporal temporal-admin-tools temporal-ui worker service

client:
	docker-compose run --rm -it shell python3 -m client

m main:
	uv run uvicorn main:app --host 0.0.0.0 --port 8900

p postgres:
	podman run --replace --name pg18 -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=postgres -p 5432:5432 -v pg18data:/var/lib/postgresql -d docker.io/library/postgres:18
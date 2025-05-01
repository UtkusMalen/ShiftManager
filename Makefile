
# Define the docker compose file
COMPOSE_FILE = docker-compose.yml

# Use the modern docker compose command
COMPOSE_COMMAND = docker compose

# --- General Commands ---

.PHONY: help
help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "General:"
	@echo "  help         - Display this help message."
	@echo "  build        - Build the bot container image."
	@echo "  up           - Build (if necessary) and start all services in detached mode."
	@echo "  down         - Stop and remove containers, networks."
	@echo "  clean        - Stop and remove containers, networks, volumes, and images."
	@echo ""
	@echo "Database:"
	@echo "  db-init      - Initialize the database from scratch (WARNING: THIS WILL DELETE ALL DATA!)."
	@echo "                 Stops DB, removes volume, starts DB, waits for healthy, creates tables."
	@echo "  db-start     - Start only the database service."
	@echo "  db-stop      - Stop only the database service."
	@echo ""
	@echo "Migrations (Alembic):"
	@echo "  migrate-init - Initialize Alembic environment inside the bot container."
	@echo "  migrate <message> - Generate a new migration script with an optional message."
	@echo "  migrate-upgrade - Apply all pending migrations."
	@echo "  migrate-downgrade <revision> - Revert to a specific revision (use HEAD~1 for previous)."
	@echo ""
	@echo "Development (requires local Python/pip):"
	@echo "  install-deps - Install Python dependencies locally."
	@echo "  run-local    - Run the bot script locally (requires .env, local deps, and DB accessible)."
	@echo ""
	@echo "Note: The 'version' key in docker-compose.yml is deprecated but doesn't cause errors."


.PHONY: build
build:
	@echo "Building bot container image..."
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) build bot
	@echo "Build complete."

.PHONY: up
up: build
	@echo "Starting services..."
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) up -d
	@echo "Services started."

.PHONY: down
down:
	@echo "Stopping services..."
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) down
	@echo "Services stopped."

.PHONY: clean
clean:
	@echo "Stopping and removing all services, networks, volumes, and images..."
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) down -v --rmi all
	@echo "Cleanup complete."

# --- Database Commands ---

.PHONY: db-init
db-init:
	@echo "Initializing database from scratch (WARNING: THIS WILL DELETE ALL DATA!)"
	# Stop and remove *only* the DB service and its volume
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) down -v db
	@echo "Starting database service for initialization..."
	# Start ONLY the DB service. It will perform initdb on first run due to volume removal.
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) up -d db
	@echo "Waiting for database service to become healthy..."
	# Use docker inspect to wait for the healthy status
	@while [ "$$($(COMPOSE_COMMAND) -f $(COMPOSE_FILE) inspect --format='{{.State.Health.Status}}' "$(shell $(COMPOSE_COMMAND) -f $(COMPOSE_FILE) ps -q db)" 2>/dev/null)" != "healthy" ]; do \
	  echo -n "."; sleep 1; \
	done; echo ""
	@echo "Database service is healthy."
	# Run the command to create tables using the application code inside the *bot* container
	# Need to ensure the bot container exists and is ready to run commands.
	# The 'up' command below will wait for DB health check before starting bot.
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) up -d bot # Ensure bot container is also up and healthy
	@echo "Waiting for bot service to be running to create tables..."
	@while [ "$$($(COMPOSE_COMMAND) -f $(COMPOSE_FILE) inspect --format='{{.State.Health.Running}}' "$(shell $(COMPOSE_COMMAND) -f $(COMPOSE_FILE) ps -q bot)" 2>/dev/null)" != "true" ]; do \
	  echo -n "."; sleep 1; \
	done; echo ""
	@echo "Bot service is running. Creating tables..."
	# Execute the table creation script/function inside the bot container
	# This assumes you have a way to trigger create_db_and_tables() from an executable script/module in your bot container.
	# A simple way is to add a dedicated script or run it directly via python -c
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) exec bot python -c 'import asyncio; from src.db.engine import create_db_and_tables; asyncio.run(create_db_and_tables())'
	@echo "Database and tables created."
	@echo "Database initialization complete."


.PHONY: db-start
db-start:
	@echo "Starting database service..."
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) up -d db
	@echo "Database service started."

.PHONY: db-stop
db-stop:
	@echo "Stopping database service..."
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) stop db
	@echo "Database service stopped."


# --- Alembic Migration Commands ---
# These commands run inside the 'bot' container

# Make sure the services are up before running migrations
MIGRATE_DEPS = up

.PHONY: migrate-init
migrate-init: $(MIGRATE_DEPS)
	@echo "Initializing Alembic environment inside bot container..."
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) exec bot alembic init -t async alembic
	@echo "Alembic initialization command sent to bot container. Check container logs for output."

.PHONY: migrate
migrate: $(MIGRATE_DEPS)
	@if [ -z "$(message)" ]; then \
		echo "Error: Migration message is required."; \
		echo "Usage: make migrate message='your migration message'"; \
		exit 1; \
	fi
	@echo "Generating new migration script inside bot container..."
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) exec bot alembic revision -autogenerate -m "$(message)"
	@echo "Migration generation command sent to bot container. Check container logs for output and review the generated script."

.PHONY: migrate-upgrade
migrate-upgrade: $(MIGRATE_DEPS)
	@echo "Applying pending migrations inside bot container..."
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) exec bot alembic upgrade head
	@echo "Upgrade command sent to bot container. Check container logs for output."

.PHONY: migrate-downgrade
migrate-downgrade: $(MIGRATE_DEPS)
	@if [ -z "$(revision)" ]; then \
		echo "Error: Target revision is required."; \
		echo "Usage: make migrate-downgrade revision=HEAD~1"; \
		exit 1; \
	fi
	@echo "Reverting migration inside bot container to revision $(revision)..."
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) exec bot alembic downgrade $(revision)
	@echo "Downgrade command sent to bot container. Check container logs for output."

# --- Local Development Commands ---

.PHONY: install-deps
install-deps:
	@echo "Installing Python dependencies locally..."
	pip install -r requirements.txt
	@echo "Dependencies installed."

.PHONY: run-local
run-local: install-deps
	@echo "Running bot script locally..."
	@echo "Ensure your .env is configured for local DB access or Docker DB is running and accessible."
	python bot.py
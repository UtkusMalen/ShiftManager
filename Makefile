# Define the docker compose file
COMPOSE_FILE = docker-compose.yml

# Use the modern docker compose command (or fallback to older docker-compose)
COMPOSE_COMMAND = docker compose

# Docker command
DOCKER_COMMAND = docker

# Define service names
BOT_SERVICE = bot
DB_SERVICE = db

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
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) build $(BOT_SERVICE)
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
	@echo "1. Initializing database from scratch (removing volume)..."
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) down -v $(DB_SERVICE)
	@echo "2. Starting database service ($(DB_SERVICE))..."
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) up -d $(DB_SERVICE)
	@echo "3. Waiting for database service ($(DB_SERVICE)) to become healthy..."
	@status="starting"; \
	while [ "$$status" != "healthy" ]; do \
	    container_id=$$($(COMPOSE_COMMAND) -f $(COMPOSE_FILE) ps -q $(DB_SERVICE)); \
	    if [ -n "$$container_id" ]; then \
	        inspect_output=$$($(DOCKER_COMMAND) inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $$container_id); \
	        inspect_exit_code=$$?; \
	        if [ $$inspect_exit_code -ne 0 ]; then \
	            raw_status="inspect_error"; \
	        else \
	            raw_status="$$inspect_output"; \
	        fi; \
	        if [ "$$raw_status" = "running" ]; then \
	            status="healthy"; \
	        elif [ "$$raw_status" = "inspect_error" ]; then \
	            status="error"; \
	        else \
	            status="$$raw_status"; \
	        fi; \
	    else \
	        status="starting"; \
	    fi; \
	    if [ "$$status" != "healthy" ]; then \
	        echo -n "."; \
	        sleep 1; \
	    fi; \
	    if [ "$$status" = "error" ]; then \
	        echo " Error inspecting DB container! Exit code: $$inspect_exit_code Output: $$inspect_output"; \
	        exit 1; \
	    fi; \
	done; echo " DB Status: $$status"
	@echo "4. Starting bot service ($(BOT_SERVICE)) (if not already running)..."
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) up -d $(BOT_SERVICE)
	@echo "5. Waiting for bot service ($(BOT_SERVICE)) to be running..."
	@running="false"; \
	while [ "$$running" != "true" ]; do \
	    container_id=$$($(COMPOSE_COMMAND) -f $(COMPOSE_FILE) ps -q $(BOT_SERVICE)); \
	    if [ -n "$$container_id" ]; then \
	        inspect_output=$$($(DOCKER_COMMAND) inspect --format='{{.State.Running}}' $$container_id); \
	        inspect_exit_code=$$?; \
	        if [ $$inspect_exit_code -ne 0 ]; then \
	            running="error"; \
	        else \
	            running="$$inspect_output"; \
	        fi; \
	    else \
	        running="false"; \
	    fi; \
	    if [ "$$running" != "true" ]; then \
	        echo -n "*"; \
	        sleep 1; \
	    fi; \
	    if [ "$$running" = "error" ]; then \
	        echo " Error inspecting Bot container! Exit code: $$inspect_exit_code Output: $$inspect_output"; \
	        exit 1; \
	    fi; \
	done; echo " Bot Status: $$running"
	@echo "6. Creating database tables via exec in $(BOT_SERVICE)..."
	# Add a small delay just in case the container is running but internal app not fully ready
	sleep 3
	# Execute the table creation script
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) exec $(BOT_SERVICE) python -c 'import asyncio; from src.db.engine import create_db_and_tables; print("--- Running create_db_and_tables ---"); asyncio.run(create_db_and_tables()); print("--- Finished create_db_and_tables ---")'
	@echo "7. Database and tables should be created."
	@echo "8. Database initialization complete."


.PHONY: db-start
db-start:
	@echo "Starting database service ($(DB_SERVICE))..."
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) up -d $(DB_SERVICE)
	@echo "Database service started."

.PHONY: db-stop
db-stop:
	@echo "Stopping database service ($(DB_SERVICE))..."
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) stop $(DB_SERVICE)
	@echo "Database service stopped."


# --- Alembic Migration Commands ---
# These commands run inside the 'bot' container

# Make sure the services are up before running migrations
MIGRATE_DEPS = up

.PHONY: migrate-init
migrate-init: $(MIGRATE_DEPS)
	@echo "Initializing Alembic environment inside $(BOT_SERVICE) container..."
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) exec $(BOT_SERVICE) alembic init -t async alembic
	@echo "Alembic initialization command sent to $(BOT_SERVICE) container. Check container logs for output."

.PHONY: migrate
migrate: $(MIGRATE_DEPS)
	@if [ -z "$(message)" ]; then \
		echo "Error: Migration message is required."; \
		echo "Usage: make migrate message='your migration message'"; \
		exit 1; \
	fi
	@echo "Generating new migration script inside $(BOT_SERVICE) container..."
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) exec $(BOT_SERVICE) alembic revision --autogenerate -m "$(message)"
	@echo "Migration generation command sent to $(BOT_SERVICE) container. Check container logs for output and review the generated script."

.PHONY: migrate-upgrade
migrate-upgrade: $(MIGRATE_DEPS)
	@echo "Applying pending migrations inside $(BOT_SERVICE) container..."
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) exec $(BOT_SERVICE) alembic upgrade head
	@echo "Upgrade command sent to $(BOT_SERVICE) container. Check container logs for output."

.PHONY: migrate-downgrade
migrate-downgrade: $(MIGRATE_DEPS)
	@if [ -z "$(revision)" ]; then \
		echo "Error: Target revision is required."; \
		echo "Usage: make migrate-downgrade revision=HEAD~1"; \
		exit 1; \
	fi
	@echo "Reverting migration inside $(BOT_SERVICE) container to revision $(revision)..."
	$(COMPOSE_COMMAND) -f $(COMPOSE_FILE) exec $(BOT_SERVICE) alembic downgrade $(revision)
	@echo "Downgrade command sent to $(BOT_SERVICE) container. Check container logs for output."

# --- Local Development Commands ---

.PHONY: install-deps
install-deps:
	@echo "Installing Python dependencies locally..."
	pip install -r requirements.txt
	@echo "Dependencies installed."

.PHONY: run-local
run-local: install-deps
	@echo "Running bot script locally (using python bot.py)..."
	@echo "Ensure your .env is configured for local DB access or Docker DB is running and accessible."
	python bot.py
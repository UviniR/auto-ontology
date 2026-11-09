# Running NVIDIA Auto Ontology --- Movie Data Lake

A repeatable guide for starting, stopping, checking, and backing up the
Auto Ontology installation.

## 1. Project details

This guide reflects the setup on the original Mac:

-   Project directory: `~/Repos/auto-ontology`
-   Web interface: <http://localhost:3000>
-   pgAdmin: <http://localhost:5050>
-   Docker Compose project: `auto-ontology`
-   PostgreSQL database: `auto_ontology`
-   PostgreSQL Docker volume: `auto-ontology_postgres_data`
-   Movie Lake folder: `Data/Movie_Lake`
-   SQLite sources:
    -   `Data/Movie_Lake/cmu_movies.db`
    -   `Data/Movie_Lake/tmdb_movies.db`
-   The Movie Lake folder is mounted read-only into the
    application/ingestion containers.
-   The local `embedding.py` was adjusted to use
    `inference_batch_size = 2` and `nim_http_max_concurrent = 1`. Keep
    this modification when synchronising the code to another Mac.

**Important:** The generated semantic terms, attributes, and
relationships are stored in PostgreSQL, not in Git and not in the SQLite
source files. The PostgreSQL Docker volume must be preserved.

## 2. Start Auto Ontology

1.  Open Docker Desktop and wait until its engine is running.

2.  Open Terminal.

3.  Move into the project directory:

    ``` bash
    cd ~/Repos/auto-ontology
    ```

4.  Start the services:

    ``` bash
    docker compose up -d
    ```

5.  Check service status:

    ``` bash
    docker compose ps
    ```

6.  Open the application:

    -   Auto Ontology: <http://localhost:3000>
    -   pgAdmin: <http://localhost:5050>

If a service is still starting, wait a little and run
`docker compose ps` again.

## 3. Stop Auto Ontology safely

From the project directory, run:

``` bash
docker compose stop
```

This stops the containers but keeps the PostgreSQL named volume and its
data.

You can now quit Docker Desktop or shut down the Mac normally. The
PostgreSQL volume remains on disk.

To use Auto Ontology again, follow **Section 2**.

## 4. Check logs if something does not work

Run these commands from `~/Repos/auto-ontology`.

Show the status of all services:

``` bash
docker compose ps
```

Show recent logs for all services:

``` bash
docker compose logs --since=10m
```

Show ingestion-service logs:

``` bash
docker compose logs --since=10m ingestion-service
```

Follow live ingestion logs:

``` bash
docker compose logs -f ingestion-service
```

Press `Ctrl+C` to stop following the logs. This does not stop the
containers.

## 5. Create a PostgreSQL backup

Create a database backup before moving to another Mac, making major
changes, or periodically as a safety copy.

1.  Start Docker Desktop.

2.  Start Auto Ontology if it is not already running:

    ``` bash
    cd ~/Repos/auto-ontology
    docker compose up -d
    ```

3.  Create a plain SQL backup in the project directory:

    ``` bash
    docker compose exec -T postgres pg_dump \
      -U postgres \
      -d auto_ontology \
      > auto_ontology_backup.sql
    ```

4.  Check that the file exists and is not empty:

    ``` bash
    ls -lh auto_ontology_backup.sql
    ```

The file `auto_ontology_backup.sql` contains the PostgreSQL database
contents, including the application's generated ontology data stored in
that database.

**Keep the backup private.** It may contain application data and
metadata. Do not commit it to a public Git repository. Store an
additional copy somewhere secure.

For a consistent backup, avoid running ingestion or semantic compilation
while the dump is being made.

## 6. Restore a PostgreSQL backup on another Mac

This is for restoring the existing ontology database to a second Mac. It
assumes that the same Auto Ontology project/version has been set up
there, Docker Desktop is running, and the backup file has been securely
transferred.

1.  Put `auto_ontology_backup.sql` in the second Mac's project
    directory.

2.  Make sure the second Mac's project has the required Compose
    configuration and `.env` file. Do not copy secrets into Git.

3.  Start the PostgreSQL service:

    ``` bash
    cd ~/Repos/auto-ontology
    docker compose up -d postgres
    ```

4.  Wait until PostgreSQL is healthy:

    ``` bash
    docker compose ps
    ```

5.  **Caution:** Restoring into an existing database can overwrite or
    conflict with its current contents. The following command drops and
    recreates the target database. Only run it on the second Mac if you
    are happy to replace the target `auto_ontology` database with the
    backup.

    ``` bash
    docker compose exec -T postgres dropdb \
      -U postgres --if-exists auto_ontology

    docker compose exec -T postgres createdb \
      -U postgres -O postgres auto_ontology
    ```

6.  Import the backup:

    ``` bash
    docker compose exec -T postgres psql \
      -U postgres \
      -d auto_ontology \
      < auto_ontology_backup.sql
    ```

7.  Start the rest of the application:

    ``` bash
    docker compose up -d
    ```

8.  Open <http://localhost:3000> and check that the expected terms and
    relationships are present.

**Do not run the drop/recreate commands on the original Mac.** Do not
run `docker compose down -v` on either Mac as part of normal start/stop
operations.

If the restore reports errors, stop and inspect the error before
retrying. The backup and restore should use compatible
application/database versions.

## 7. Git: what to synchronise

Git is for source code and configuration, not for the live PostgreSQL
database.

Recommended to commit (after reviewing for secrets): - Application
source-code changes you intentionally made. - `docker-compose.yml`. -
Documentation such as this guide. - Other non-secret project
configuration.

Do not commit: - `.env` or any file containing API keys, passwords, or
authentication secrets. - `auto_ontology_backup.sql`. - PostgreSQL data
directories or Docker volume contents. - Large/private source datasets
unless you have deliberately chosen a secure data-versioning approach.

Keep a separate secure copy of the `.env` settings for each Mac.
Recreate the Python virtual environment on the second Mac rather than
copying `.venv`.

## 8. Commands to remember

  Task                       Command
  -------------------------- -----------------------------------------------------
  Enter project directory    `cd ~/Repos/auto-ontology`
  Start                      `docker compose up -d`
  Check services             `docker compose ps`
  Stop safely                `docker compose stop`
  Recent logs                `docker compose logs --since=10m`
  Ingestion logs             `docker compose logs --since=10m ingestion-service`
  Create PostgreSQL backup   See Section 5

## 9. Critical safety reminders

-   **Safe normal stop:** `docker compose stop`
-   **Safe normal start:** `docker compose up -d`
-   **Do not use casually:** `docker compose down -v` --- the `-v`
    option removes Compose-managed volumes and can delete the PostgreSQL
    data containing your generated ontology.
-   Ordinary `docker compose down` stops and removes containers/networks
    but normally preserves named volumes; for routine use, prefer
    `docker compose stop`.
-   Never delete `auto-ontology_postgres_data` if you want to retain the
    generated ontology.
-   Keep at least one verified PostgreSQL backup separate from the Mac
    running Docker.
-   The SQLite source databases and PostgreSQL ontology database are
    different things. Back up both if you need a complete copy of the
    project.

------------------------------------------------------------------------

*Prepared for the current Movie Data Lake Auto Ontology setup. If the
project directory, database name, Compose services, or configuration
changes, update this guide accordingly.*

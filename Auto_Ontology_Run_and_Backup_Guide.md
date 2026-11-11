# Running NVIDIA Auto Ontology --- Movie Data Lake

A repeatable guide for starting, stopping, backing up, and restoring the
Auto Ontology installation on this Movie Data Lake project.

## 1. Project details

This guide reflects the setup on the original Mac:

-   Project directory: `~/Repos/auto-ontology`
-   Web interface: <http://localhost:3000>
-   Backend: `http://localhost:3001`
-   pgAdmin: <http://localhost:5050>
-   PostgreSQL database: `auto_ontology`
-   PostgreSQL Docker volume: `auto-ontology_postgres_data`
-   Movie Lake folder: `Data/Movie_Lake`
-   SQLite sources:
    -   `Data/Movie_Lake/cmu_movies.db`
    -   `Data/Movie_Lake/tmdb_movies.db`

The Movie Lake folder is mounted read-only into the application and
ingestion containers. The `.env` connection strings use the container
paths:

``` env
CONNECTION_STRINGS=sqlite:////data/movie_lake/cmu_movies.db,sqlite:////data/movie_lake/tmdb_movies.db
```

The Compose file must mount the folder into both `auto-ontology` and
`ingestion-service`:

``` yaml
volumes:
  - ./Data/Movie_Lake:/data/movie_lake:ro
```

The local `auto_ontology/utils/embedding.py` was adjusted to use:

``` python
inference_batch_size: int = 2
nim_http_max_concurrent: int = 1
```

Keep this code change when synchronising the project to another Mac.

**Important distinction:**

-   SQLite files contain the original movie data.
-   PostgreSQL contains Auto Ontology's application data, generated
    ontology/semantic metadata, and Discovery conversation history.
-   Git contains source code and committed configuration, not the live
    PostgreSQL database or SQLite data unless you deliberately add those
    files.

## 2. Start Auto Ontology

1.  Open Docker Desktop and wait until its engine is running.

2.  Open Terminal and move into the project directory:

    ``` bash
    cd ~/Repos/auto-ontology
    ```

3.  Start the services:

    ``` bash
    docker compose up -d
    ```

4.  Check service status:

    ``` bash
    docker compose ps
    ```

5.  Open the application:

    -   Auto Ontology: <http://localhost:3000>
    -   pgAdmin: <http://localhost:5050>

If a service is still starting, wait a little and run
`docker compose ps` again.

### If Docker tries to pull `auto-ontology:latest` or `auto-ontology-frontend:latest`

These project images are built locally and may not exist in a public
Docker registry. Build them from the checked-out source code:

``` bash
docker compose build auto-ontology auto-ontology-frontend ingestion-service
```

Then start the services:

``` bash
docker compose up -d
```

The build requires the project source code and its Docker build files to
be present.

## 3. Stop Auto Ontology safely

From the project directory, run:

``` bash
docker compose stop
```

This stops the containers but keeps the PostgreSQL named volume and its
data. You can now quit Docker Desktop or shut down the Mac normally. The
PostgreSQL volume remains on disk.

To use Auto Ontology again, follow Section 2.

## 4. Check logs if something does not work

Run these commands from `~/Repos/auto-ontology`.

Show service status:

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

## 5. Create and store a PostgreSQL backup

Create a database backup before moving to another Mac, before major
changes, and periodically as a safety copy.

1.  Start Docker Desktop.

2.  Move into the project directory:

    ``` bash
    cd ~/Repos/auto-ontology
    ```

3.  Make sure PostgreSQL is running. If the whole application is
    stopped, start PostgreSQL:

    ``` bash
    docker compose up -d postgres
    ```

4.  Create a plain SQL backup in the project directory:

    ``` bash
    docker compose exec -T postgres pg_dump \
      -U postgres \
      -d auto_ontology \
      > auto_ontology_backup.sql
    ```

5.  Check that the backup exists and is not empty:

    ``` bash
    ls -lh auto_ontology_backup.sql
    ```

6.  Optionally verify that the backup contains the Discovery
    conversation tables:

    ``` bash
    grep -E 'frontend\.(conversations|messages)' auto_ontology_backup.sql
    ```

    The backup should contain table definitions and data-copy sections
    for `frontend.conversations` and `frontend.messages`. These tables
    store conversation records and their messages. The full database
    dump includes all schemas in the `auto_ontology` database, including
    `public` and `frontend`.

### Where to store the backup

-   Keep `auto_ontology_backup.sql` outside Git.
-   Keep at least one additional copy somewhere separate from the Mac
    running Docker, such as an encrypted external drive or secure cloud
    storage.
-   Use a dated filename for historical backups, for example
    `auto_ontology_backup_2026-11-09.sql`.
-   Keep the backup private because it can contain application data,
    metadata, SQL content, and conversation messages.
-   Do not put the backup in a public Git repository or share it
    publicly.

For a consistent backup, avoid running ingestion or semantic compilation
while the dump is being made.

**A PostgreSQL backup does not contain your original SQLite movie files,
`.env`, source code, Docker images, or Docker volume itself.** Copy
those separately as described in Section 7.

## 6. Restore a PostgreSQL backup on another Mac

Use this procedure on the second Mac when you want to restore the
existing ontology and Discovery history. It assumes that the project
source code has been cloned, the required files have been copied, Docker
Desktop is running, and the backup is available in the project
directory.

### 6.1 Prepare the second Mac

1.  Install and start Docker Desktop.

2.  Clone the same project repository and check out the compatible
    version/commit used to create the backup:

    ``` bash
    mkdir -p ~/Repos
    cd ~/Repos
    git clone YOUR_GITHUB_REPOSITORY_URL
    cd auto-ontology
    ```

3.  Securely copy the `.env` file into the project directory. Do not
    commit it to Git.

4.  Copy the `Data/Movie_Lake` folder, including both SQLite database
    files, into the project directory.

5.  Copy `auto_ontology_backup.sql` into the project directory.

6.  Confirm that the Compose file contains the Movie Lake volume mounts
    and that the `.env` connection strings still point to
    `/data/movie_lake/...`.

### 6.2 Build the local application images

The application images may not be available from Docker Hub. Build them
from the local source code:

``` bash
docker compose build auto-ontology auto-ontology-frontend ingestion-service
```

### 6.3 Start PostgreSQL only

Start the database service first, before starting the application
services:

``` bash
docker compose up -d postgres
```

Wait until PostgreSQL is healthy:

``` bash
docker compose ps
```

### 6.4 Restore the backup

**Caution:** The following commands delete and recreate the target
`auto_ontology` database. Run them only on the second Mac when you
intend to replace that target database with the backup. Do not run them
on the original Mac if you want to preserve its current database.

``` bash
docker compose exec postgres dropdb \
  -U postgres --if-exists auto_ontology

docker compose exec postgres createdb \
  -U postgres -O postgres auto_ontology
```

Import the SQL backup:

``` bash
docker compose exec -T postgres psql \
  -U postgres \
  -d auto_ontology \
  < auto_ontology_backup.sql
```

If the import reports errors, stop and inspect them rather than
proceeding as though the restore succeeded.

### 6.5 Start the complete application

After the restore succeeds:

``` bash
docker compose up -d
```

Check the services:

``` bash
docker compose ps
```

Open <http://localhost:3000>, log in, and check that the expected
ontology terms, relationships, and Discovery conversations are present.
Open an older conversation to verify its messages.

The backup includes the `frontend` schema's user, conversation, and
message records. Log in using the same Auto Ontology user account. A
browser login session/cookie is not transferred by the database backup,
so you may need to log in again on the second Mac.

**Do not trigger a new ingestion or semantic compilation until you have
checked the restored data.** First confirm that the existing ontology
and conversations are present.

The backup and restore should use compatible application/database
versions. PostgreSQL database dumps do not include global PostgreSQL
roles; this setup expects the `postgres` role supplied by the Compose
PostgreSQL service.

## 7. What to transfer to another Mac

A complete move requires more than the Git repository.

  ----------------------------------------------------------------------------
  Item                         How to transfer it      What it contains
  ---------------------------- ----------------------- -----------------------
  Auto Ontology source code    Git clone/pull          Application code and
                                                       project files

  Modified `embedding.py`      Commit and push the     Reduced embedding
                               change                  batch/concurrency
                                                       settings

  `docker-compose.yml`         Git                     Service definitions and
                                                       volume mounts

  `.env`                       Secure manual transfer  Credentials, model
                                                       endpoints, and
                                                       connection settings

  `Data/Movie_Lake/`           Copy securely           The two original SQLite
                                                       databases

  `auto_ontology_backup.sql`   Copy securely           PostgreSQL application
                                                       data, ontology, and
                                                       Discovery history

  Python virtual environment   Recreate                Local Python
                                                       dependencies
  ----------------------------------------------------------------------------

Do not copy the Docker PostgreSQL data directory as a substitute for the
SQL backup. Use `pg_dump` and restore with `psql`.

Recreate the Python environment on the second Mac rather than copying
`.venv`. Follow the repository's dependency installation instructions.

## 8. Git: what to synchronise

Git is for source code and non-secret project configuration, not for the
live PostgreSQL database.

Recommended to commit, after reviewing for secrets:

-   Application source-code changes you intentionally made.
-   `docker-compose.yml`.
-   Documentation such as this guide.
-   Other non-secret project configuration.

Do not commit:

-   `.env` or any file containing API keys, passwords, or authentication
    secrets.
-   `auto_ontology_backup.sql`.
-   PostgreSQL data directories or Docker volume contents.
-   Large/private source datasets unless you have deliberately chosen a
    secure data-versioning approach.

Keep a separate secure copy of the `.env` settings for each Mac. Ensure
`.env` and database backups are ignored by Git.

## 9. Commands to remember

  -------------------------------------------------------------------------------------------------------------------
  Task                                Command
  ----------------------------------- -------------------------------------------------------------------------------
  Enter project directory             `cd ~/Repos/auto-ontology`

  Start                               `docker compose up -d`

  Build local app images              `docker compose build auto-ontology auto-ontology-frontend ingestion-service`

  Start PostgreSQL only               `docker compose up -d postgres`

  Check services                      `docker compose ps`

  Stop safely                         `docker compose stop`

  Recent logs                         `docker compose logs --since=10m`

  Ingestion logs                      `docker compose logs --since=10m ingestion-service`

  Create PostgreSQL backup            See Section 5

  Restore PostgreSQL backup           See Section 6
  -------------------------------------------------------------------------------------------------------------------

## 10. Critical safety reminders

-   Safe normal stop: `docker compose stop`.
-   Safe normal start: `docker compose up -d`.
-   Build the application images locally on a new Mac before starting if
    Compose reports that `auto-ontology` or `auto-ontology-frontend`
    cannot be pulled.
-   **Do not use casually:** `docker compose down -v`. The `-v` option
    removes Compose-managed volumes and can delete the PostgreSQL data
    containing your generated ontology and conversations.
-   Ordinary `docker compose down` removes containers and networks but
    normally preserves named volumes; for routine use, prefer
    `docker compose stop`.
-   Never delete `auto-ontology_postgres_data` if you want to retain the
    generated ontology and Discovery history.
-   Keep at least one verified PostgreSQL backup separate from the Mac
    running Docker.
-   The SQLite source databases and PostgreSQL application database are
    different things. Back up/copy both for a complete project transfer.
-   Never share `.env` or SQL backups publicly.

------------------------------------------------------------------------

*Prepared for the Movie Data Lake Auto Ontology setup. If the project
directory, database name, Compose services, or configuration changes,
update this guide accordingly.*

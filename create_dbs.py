
"""
Convert movie CSV datasets into TWO SQLite databases.

Database 1: cmu_movies.db
    - cmu_movies
    - cmu_actors

Database 2: tmdb_movies.db
    - TMDB_movies
    - IMDB_Reviews
"""

from pathlib import Path
import sqlite3
import pandas as pd


# ==================================================
# 1. CONFIGURATION
# ==================================================

DATA_DIR = Path("Data")
print(DATA_DIR)
DB_DIR = Path("Data/Movie_Lake")

CMU_DB = DB_DIR / "CMU_DB.db"
TMDB_DB = DB_DIR / "TMDB_DB.db"


# ==================================================
# 2. HELPER FUNCTIONS
# ==================================================

def load_csv(filename):

    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    df = pd.read_csv(path)

    # Remove accidental CSV index columns.
    df = df.loc[
        :,
        ~df.columns.astype(str).str.match(r"^Unnamed:")
    ]

    df.columns = df.columns.astype(str).str.strip()

    return df


def validate_columns(df, required, table):

    missing = set(required) - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing columns in {table}: {missing}"
        )


def validate_unique(df, column, table):

    if df[column].isna().any():
        raise ValueError(
            f"{table}.{column} contains NULL values"
        )

    if df[column].duplicated().any():
        raise ValueError(
            f"{table}.{column} contains duplicate values"
        )


def validate_foreign_key(
    child_df,
    child_column,
    parent_df,
    parent_column
):

    child_values = set(
        child_df[child_column].dropna().astype(str)
    )

    parent_values = set(
        parent_df[parent_column].dropna().astype(str)
    )

    unmatched = child_values - parent_values

    if unmatched:
        raise ValueError(
            f"Foreign key validation failed: "
            f"{child_column}. "
            f"Unmatched values: {list(unmatched)[:5]}"
        )


def print_database_tables(connection):

    tables = connection.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name NOT LIKE 'sqlite_%'
    """).fetchall()

    for (table,) in tables:

        count = connection.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        ).fetchone()[0]

        print(f"  {table}: {count} records")


# ==================================================
# 3. DATABASE 1: CMU
# ==================================================

def create_cmu_database():

    print("\nCreating CMU database...")

    # Load CSV files.
    movies = load_csv("cmu_movies.csv")
    actors = load_csv("cmu_actors.csv")

    # Validate expected columns.
    validate_columns(
        movies,
        [
            "movie_id",
            "title",
            "release_date",
            "revenue",
            "runtime",
            "plot_summary",
            "genres"
        ],
        "cmu_movies"
    )

    validate_columns(
        actors,
        [
            "freebase_actor_id",
            "character_name",
            "actor_name",
            "actor_gender",
            "movie_id"
        ],
        "cmu_actors"
    )

    # Keep identifiers as strings.
    movies["movie_id"] = movies["movie_id"].astype("string")
    actors["movie_id"] = actors["movie_id"].astype("string")
    actors["freebase_actor_id"] = (
        actors["freebase_actor_id"].astype("string")
    )

    # Validate movie primary key.
    validate_unique(movies, "movie_id", "cmu_movies")

    # Validate actor-to-movie relationship.
    validate_foreign_key(
        actors,
        "movie_id",
        movies,
        "movie_id"
    )

    # Remove duplicate actor/movie combinations
    actors = actors.drop_duplicates(
        subset=["freebase_actor_id", "movie_id"],
        keep="first"
    ).copy()    
    
    DB_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(CMU_DB) as conn:

        conn.execute("PRAGMA foreign_keys = ON")

        # Drop child before parent.
        conn.execute("DROP TABLE IF EXISTS cmu_actors")
        conn.execute("DROP TABLE IF EXISTS cmu_movies")

        # Parent table.
        conn.execute("""
            CREATE TABLE cmu_movies (

                movie_id TEXT PRIMARY KEY,

                title TEXT,
                release_date TEXT,
                revenue REAL,
                runtime REAL,
                plot_summary TEXT,
                genres TEXT

            )
        """)

        # Child table.
        conn.execute("""
            CREATE TABLE cmu_actors (

                freebase_actor_id TEXT NOT NULL,
                character_name TEXT,
                actor_name TEXT,
                actor_gender TEXT,

                movie_id TEXT NOT NULL,

                PRIMARY KEY (
                    freebase_actor_id,
                    movie_id
                ),

                FOREIGN KEY (movie_id)
                    REFERENCES cmu_movies(movie_id)

            )
        """)

        # Insert records.
        movies.to_sql(
            "cmu_movies",
            conn,
            if_exists="append",
            index=False
        )

        actors.to_sql(
            "cmu_actors",
            conn,
            if_exists="append",
            index=False
        )

        print("\nCMU database created successfully.")

        print_database_tables(conn)


# ==================================================
# 4. DATABASE 2: TMDB + IMDb REVIEWS
# ==================================================

def create_tmdb_database():

    print("\nCreating TMDB database...")

    # Load CSV files.
    movies = load_csv("tmdb_movies.csv")
    reviews = load_csv("imdb_reviews.csv")

    # Expected TMDB attributes.
    validate_columns(
        movies,
        [
            "movie_id",
            "name",
            "budget",
            "overview",
            "keywords",
            "backdrop_path",
            "poster_path",
            "vote_average",
            "vote_count",
            "original_language",
            "tagline",
            "popularity",
            "homepage",
            "production_companies",
            "production_countries",
            "spoken_languages",
            "imdb_id"
        ],
        "tmdb_movies"
    )

    validate_columns(
        reviews,
        ["imdb_id", "review"],
        "imdb_Reviews"
    )

    # Keep identifiers as strings.
    movies["movie_id"] = movies["movie_id"].astype("string")
    movies["imdb_id"] = movies["imdb_id"].astype("string")
    reviews["imdb_id"] = reviews["imdb_id"].astype("string")

    # Validate primary key.
    validate_unique(movies, "movie_id", "tmdb_movies")

    # IMDb ID is UNIQUE, not the primary key.
    validate_unique(movies, "imdb_id", "tmdb_movies")

    # Validate IMDb review relationship.
    validate_foreign_key(
        reviews,
        "imdb_id",
        movies,
        "imdb_id"
    )


    with sqlite3.connect(TMDB_DB) as conn:

        conn.execute("PRAGMA foreign_keys = ON")

        # Drop child before parent.
        conn.execute("DROP TABLE IF EXISTS imdb_Reviews")
        conn.execute("DROP TABLE IF EXISTS tmdb_movies")

        # Parent table.
        conn.execute("""
            CREATE TABLE tmdb_movies (

                movie_id TEXT PRIMARY KEY,

                name TEXT,
                budget REAL,
                overview TEXT,
                keywords TEXT,
                backdrop_path TEXT,
                poster_path TEXT,
                vote_average REAL,
                vote_count INTEGER,
                original_language TEXT,
                tagline TEXT,
                popularity REAL,
                homepage TEXT,
                production_companies TEXT,
                production_countries TEXT,
                spoken_languages TEXT,
                crew TEXT,

                imdb_id TEXT NOT NULL UNIQUE

            )
        """)

        # Child table.
        conn.execute("""
                     CREATE TABLE imdb_Reviews (
                         review_index INTEGER PRIMARY KEY,
                         imdb_id TEXT NOT NULL,
                         review TEXT,
                         FOREIGN KEY (imdb_id)
                         REFERENCES tmdb_movies(imdb_id)

            )
        """)

        # Insert records.
        movies.to_sql(
            "tmdb_movies",
            conn,
            if_exists="append",
            index=False
        )

        reviews.to_sql(
            "imdb_Reviews",
            conn,
            if_exists="append",
            index=False
        )

        print("\nTMDB database created successfully.")

        print_database_tables(conn)


# ==================================================
# 5. VERIFY DATABASES
# ==================================================

def verify_database(db_path):

    print(f"\nVerifying: {db_path}")

    with sqlite3.connect(db_path) as conn:

        conn.execute("PRAGMA foreign_keys = ON")

        violations = conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if violations:
            print("Foreign key violations:", violations)
        else:
            print("Foreign key integrity: PASSED")

        integrity = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        print("Database integrity:", integrity)

        tables = conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name NOT LIKE 'sqlite_%'
        """).fetchall()

        print("Number of tables:", len(tables))


# ==================================================
# 6. MAIN
# ==================================================

if __name__ == "__main__":

    create_cmu_database()

    create_tmdb_database()

    verify_database(CMU_DB)

    verify_database(TMDB_DB)

    print("\n================================")
    print("BOTH DATABASES CREATED!")
    print("================================")

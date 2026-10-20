import psycopg2


def get_db_connection():
    connection = psycopg2.connect(
        host="localhost",
        database="lost_found_db",
        user="postgres",
        password="postgres@2026",
        port="5432"
    )

    return connection
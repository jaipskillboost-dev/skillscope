"""
Creates the MySQL database if it is not there yet.

Django can create tables, but not the database that holds them, so this runs
first. Safe to run repeatedly -- it does nothing if the database exists.
"""
import os
import sys

import pymysql

NAME = os.environ.get("SKILLSCOPE_DB_NAME", "skillscope")
USER = os.environ.get("SKILLSCOPE_DB_USER", "root")
PASSWORD = os.environ.get("SKILLSCOPE_DB_PASSWORD", "springstudent")
HOST = os.environ.get("SKILLSCOPE_DB_HOST", "127.0.0.1")
PORT = int(os.environ.get("SKILLSCOPE_DB_PORT", "3306"))

try:
    connection = pymysql.connect(host=HOST, port=PORT, user=USER, password=PASSWORD)
except pymysql.err.OperationalError as error:
    print(f"\nCould not reach MySQL at {HOST}:{PORT} as '{USER}'.")
    print(f"  MySQL said: {error.args[1] if len(error.args) > 1 else error}")
    print("\nCheck that MySQL is running, then set your password with:")
    print("  set SKILLSCOPE_DB_PASSWORD=yourpassword")
    sys.exit(1)

with connection.cursor() as cursor:
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{NAME}` "
        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
connection.close()
print(f"Database '{NAME}' is ready.")

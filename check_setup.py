"""
Checks that everything SkillScope needs is present, and says plainly what is
missing and how to fix it.

Run on its own to check:        python check_setup.py
Run with --fix to set things up: python check_setup.py --fix

Called by option 1 of skillscope.bat. Safe to run as often as you like -- it
never destroys anything.
"""

import getpass
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FIX = "--fix" in sys.argv
ENV_FILE = BASE_DIR / ".env"

# Pick up anything a previous Setup saved, such as the MySQL password.
if ENV_FILE.exists():
    for _line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _value = _line.split("=", 1)
            os.environ.setdefault(_key.strip(), _value.strip())


def remember(key, value):
    """
    Save a setting into .env, next to manage.py, so it survives closing the
    window. The file is listed in .gitignore, so a password written here is
    never committed or shared.
    """
    lines = []
    if ENV_FILE.exists():
        lines = [
            line for line in ENV_FILE.read_text(encoding="utf-8").splitlines()
            if not line.strip().startswith(f"{key}=")
        ]
    if not lines:
        lines = ["# SkillScope local settings, written by Setup.",
                 "# Personal to this computer - see .gitignore.", ""]
    lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


GOOD, BAD, WARN = "  [ OK ]", "  [FAIL]", "  [ !! ]"
problems = []


def heading(text):
    print(f"\n{text}")
    print("  " + "-" * (len(text) + 2))


def fail(what, how_to_fix):
    print(f"{BAD} {what}")
    problems.append((what, how_to_fix))


# ---------------------------------------------------------------------------
# 1. Python
# ---------------------------------------------------------------------------

heading("Python")

version = sys.version_info
if version >= (3, 10):
    print(f"{GOOD} Python {version.major}.{version.minor}.{version.micro}")
else:
    fail(f"Python {version.major}.{version.minor} is too old",
         "Install Python 3.10 or newer from python.org")

in_venv = sys.prefix != sys.base_prefix
if in_venv:
    print(f"{GOOD} Running inside the project's virtual environment")
else:
    print(f"{WARN} Not in the virtual environment (that is fine for this check)")


# ---------------------------------------------------------------------------
# 2. Packages
# ---------------------------------------------------------------------------

heading("Required packages")

REQUIRED = [
    ("django", "Django", "the web framework itself"),
    ("pymysql", "PyMySQL", "lets Python talk to MySQL"),
    ("PIL", "pillow", "handles uploaded images"),
]

missing = []
for module, package, purpose in REQUIRED:
    try:
        imported = __import__(module)
        shown = getattr(imported, "__version__", "?")
        if module == "pymysql":
            # PyMySQL's __version__ attribute disagrees with its real release
            # number, so read the tuple instead.
            shown = ".".join(str(n) for n in imported.VERSION[:3])
        print(f"{GOOD} {package:10} {shown:12} - {purpose}")
    except ImportError:
        print(f"{BAD} {package:10} {'missing':12} - {purpose}")
        missing.append(package)

if missing and FIX:
    print("\n  Installing the missing packages...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r",
         str(BASE_DIR / "requirements.txt")],
        cwd=BASE_DIR)
    if result.returncode == 0:
        print(f"{GOOD} Packages installed. Run this check again to confirm.")
        missing = []
    else:
        fail("Could not install the packages",
             "Check your internet connection, then try again")
elif missing:
    fail(f"Missing packages: {', '.join(missing)}",
         "Run option 1 (Setup) from the menu, or: pip install -r requirements.txt")


# ---------------------------------------------------------------------------
# 3. MySQL
# ---------------------------------------------------------------------------

heading("MySQL")

DB_NAME = os.environ.get("SKILLSCOPE_DB_NAME", "skillscope")
DB_USER = os.environ.get("SKILLSCOPE_DB_USER", "root")
DB_PASSWORD = os.environ.get("SKILLSCOPE_DB_PASSWORD", "springstudent")
DB_HOST = os.environ.get("SKILLSCOPE_DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("SKILLSCOPE_DB_PORT", "3306"))

database_ready = False
if "PyMySQL" in missing:
    print(f"{WARN} Skipped - PyMySQL is not installed yet")
else:
    import pymysql

    try:
        connection = pymysql.connect(host=DB_HOST, port=DB_PORT,
                                     user=DB_USER, password=DB_PASSWORD)
        print(f"{GOOD} Connected to MySQL at {DB_HOST}:{DB_PORT} as '{DB_USER}'")

        with connection.cursor() as cursor:
            cursor.execute("SHOW DATABASES LIKE %s", (DB_NAME,))
            exists = cursor.fetchone() is not None

            if exists:
                print(f"{GOOD} Database '{DB_NAME}' exists")
                database_ready = True
            elif FIX:
                cursor.execute(
                    f"CREATE DATABASE `{DB_NAME}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                print(f"{GOOD} Database '{DB_NAME}' created")
                database_ready = True
            else:
                print(f"{BAD} Database '{DB_NAME}' does not exist")
                fail(f"Database '{DB_NAME}' missing",
                     "Run option 1 (Setup) from the menu")
        connection.close()

    except pymysql.err.OperationalError as error:
        detail = str(error.args[1] if len(error.args) > 1 else error)
        print(f"{BAD} Cannot reach MySQL: {detail}")

        if "Access denied" not in detail:
            fail("MySQL is not running, or is not reachable",
                 "Start the MySQL service, then run Setup again.\n"
                 "    On Windows: press Win+R, type services.msc,\n"
                 "    find MySQL, right-click it and choose Start")
        elif not FIX:
            fail("The MySQL password is wrong",
                 "Run Setup (option 1) - it will ask you for the right one")
        else:
            # Setup is running, so ask for the password rather than only
            # reporting that the stored one is wrong.
            print()
            print("  SkillScope needs your MySQL password.")
            print("  This is the password you chose when you installed MySQL,")
            print(f"  for the user '{DB_USER}'. It is kept only on this computer,")
            print("  in a file called .env, and is never shared or committed.")
            print()

            for attempt in range(1, 4):
                try:
                    entered = getpass.getpass(f"  MySQL password for '{DB_USER}': ")
                except (EOFError, KeyboardInterrupt):
                    print("\n  Cancelled.")
                    entered = None

                if not entered:
                    fail("No password given",
                         "Run Setup again when you have it to hand")
                    break

                try:
                    connection = pymysql.connect(
                        host=DB_HOST, port=DB_PORT, user=DB_USER, password=entered)
                except pymysql.err.OperationalError:
                    left = 3 - attempt
                    if left:
                        print(f"  That did not work. "
                              f"{left} {'try' if left == 1 else 'tries'} left.\n")
                        continue
                    fail("Could not sign in to MySQL",
                         "Check the password, or reset it in MySQL Workbench,\n"
                         "    then run Setup again")
                    break

                # It worked. Save it so this never has to be typed again.
                os.environ["SKILLSCOPE_DB_PASSWORD"] = entered
                remember("SKILLSCOPE_DB_PASSWORD", entered)
                print(f"\n{GOOD} Password accepted, and saved for next time")

                with connection.cursor() as cursor:
                    cursor.execute("SHOW DATABASES LIKE %s", (DB_NAME,))
                    if cursor.fetchone() is None:
                        cursor.execute(
                            f"CREATE DATABASE `{DB_NAME}` "
                            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                        print(f"{GOOD} Database '{DB_NAME}' created")
                    else:
                        print(f"{GOOD} Database '{DB_NAME}' exists")
                database_ready = True
                connection.close()
                break


# ---------------------------------------------------------------------------
# 4. Tables and demo data
# ---------------------------------------------------------------------------

heading("Database contents")

if not database_ready or missing:
    print(f"{WARN} Skipped - fix the problems above first")
else:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, str(BASE_DIR))
    import django

    django.setup()

    from django.db import connection as db
    from django.core.management import call_command

    tables = db.introspection.table_names()
    if "accounts_user" in tables:
        print(f"{GOOD} Tables built ({len(tables)} tables)")
    elif FIX:
        print("  Building the tables...")
        call_command("migrate", verbosity=0, interactive=False)
        print(f"{GOOD} Tables built")
    else:
        fail("Tables not built yet", "Run option 1 (Setup) from the menu")

    try:
        from accounts.models import Institution, User
        from learning.models import Course

        user_count = User.objects.count()
        if user_count:
            print(f"{GOOD} Demo data present - {user_count} users, "
                  f"{Institution.objects.count()} institutions, "
                  f"{Course.objects.count()} courses")
        elif FIX:
            print("  Loading the demo data...")
            call_command("seed_demo", verbosity=1)
        else:
            print(f"{WARN} No demo data yet - run option 1 (Setup)")
    except Exception as error:  # noqa: BLE001
        print(f"{WARN} Could not read the tables: {error}")


# ---------------------------------------------------------------------------
# 5. Project files
# ---------------------------------------------------------------------------

heading("Project files")

for relative, description in [
    ("static/vendor/bootstrap.min.css", "Bootstrap (page layout)"),
    ("static/vendor/chart.umd.min.js", "Chart.js (dashboard charts)"),
    ("static/vendor/qrcode.min.js", "qrcode.js (certificate QR codes)"),
    ("static/css/skillscope.css", "the SkillScope theme"),
    ("templates/base.html", "the page template"),
]:
    if (BASE_DIR / relative).exists():
        print(f"{GOOD} {description}")
    else:
        fail(f"Missing: {relative}", "The download is incomplete - unzip it again")


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------

print("\n" + "=" * 62)
if problems:
    print(f"{len(problems)} thing(s) need attention:\n")
    for what, how in problems:
        print(f"  * {what}")
        print(f"    -> {how}\n")
    sys.exit(1)

print("Everything is ready. Choose option 2 or 3 from the menu to start.")
sys.exit(0)

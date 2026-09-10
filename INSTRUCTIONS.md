# SkillScope — full instructions

Everything needed to install, run, present and troubleshoot SkillScope, written for
someone who has never used Django.

**Contents**

1. [What you need first](#1-what-you-need-first)
2. [Installing](#2-installing)
3. [The menu, option by option](#3-the-menu-option-by-option)
4. [Signing in](#4-signing-in)
5. [Walking through the whole system](#5-walking-through-the-whole-system)
6. [Presenting it](#6-presenting-it)
7. [When something goes wrong](#7-when-something-goes-wrong)
8. [Running it without the menu](#8-running-it-without-the-menu)
9. [Sharing the project](#9-sharing-the-project)
10. [Where things live in the code](#10-where-things-live-in-the-code)

---

## 1. What you need first

Two pieces of software. Neither can be bundled into the project.

### Python 3.10 or newer

Download from [python.org/downloads](https://www.python.org/downloads/).

> **During installation, tick "Add python.exe to PATH".**
> It is a small checkbox on the first screen and easy to miss. Without it, nothing else
> here will work and the error will not mention Python at all.

Check it worked — open Command Prompt and type:

```
python --version
```

You should see `Python 3.10.x` or higher. If it says *"not recognised"*, Python was
installed without that checkbox. Re-run the installer and choose **Modify**.

### MySQL 8

Download the **MySQL Community Server** from
[dev.mysql.com/downloads/mysql](https://dev.mysql.com/downloads/mysql/).

During setup you choose a password for the `root` user. **Write it down** — SkillScope
will ask for it once.

Check MySQL is running: press `Win + R`, type `services.msc`, press Enter, and look for
**MySQL80** in the list. Its status should say *Running*. If not, right-click it and
choose **Start**.

---

## 2. Installing

1. Unzip the project somewhere sensible — `Documents\skillscope` is fine.
2. Open the folder and **double-click `skillscope.bat`**.
3. Type **`1`** and press Enter.

Setup runs four steps and tells you what it is doing:

```
  [1/4] Looking for Python...
  [2/4] Preparing the virtual environment...
  [3/4] Installing the required packages...
  [4/4] Checking the database and demo data...
```

**The first run takes a few minutes** — it downloads Django and two other packages.
Later runs take seconds.

### If it asks for your MySQL password

This is normal on a new computer. SkillScope tries a default first, and when that fails
it asks:

```
  SkillScope needs your MySQL password.
  This is the password you chose when you installed MySQL,
  for the user 'root'. It is kept only on this computer,
  in a file called .env, and is never shared or committed.

  MySQL password for 'root':
```

Type it and press Enter. **Nothing appears as you type** — that is deliberate, so nobody
reading over your shoulder can see it. You get three attempts.

Once accepted it is saved in a file called `.env` next to `manage.py`, and you will never
be asked again. That file is excluded from Git, so your password is never uploaded or
shared.

### When it finishes

```
  Everything is ready. Choose option 2 or 3 from the menu to start.
```

Choose **2**, then open **http://localhost:8000** in your browser.

---

## 3. The menu, option by option

| Option | What it does | When to use it |
|---|---|---|
| **1. Setup** | Checks and installs everything missing | First time, or after an error |
| **2. Start (for building)** | Runs the site, shows full technical errors | While working on the code |
| **3. Start (for the demo)** | Runs the site, hides technical errors | Presenting to anyone |
| **4. Check status** | Reports what is and is not working | When something seems wrong |
| **5. Reset the demo data** | Wipes everything, reloads the original data | Before presenting |
| **6. Run the tests** | Runs all 44 automated checks | To prove the logic works |
| **7. Exit** | Closes the menu | |

To stop the site once it is running, press **Ctrl+C** in the black window.

### Why there are two ways to start

**Option 2** shows Django's full error page if something breaks — a long yellow-and-grey
page with the exact line of code. That is what you want while building.

**Option 3** shows a calm SkillScope page instead, reading *"Something went wrong at our
end"*. That is what you want in front of an audience. Same site, same data — only what an
error looks like changes.

Setup is safe to run as often as you like. It only fills in what is missing and never
deletes anything.

**Option 5 is the destructive one.** It deletes every account, course, upload and
certificate, then reloads the original demo data. It asks you to type `YES` first.

---

## 4. Signing in

Every seeded account uses the password **`skillscope123`**.

| Role | Email |
|---|---|
| Platform admin | `admin@skillscope.io` |
| Institute admin | `rekha.iyer@northline.edu` |
| Trainer | `vikram.c@northline.edu` |
| Learner | `aditya.menon@example.com` |
| Institute awaiting approval | `anil.kurup@harbourview.ac.in` |

That last account is useful: it is stuck on the "Awaiting verification" screen, so you can
sign in as the platform admin, approve it, and watch it gain access.

---

## 5. Walking through the whole system

Follow this once to understand every part. About fifteen minutes.

### As a visitor, not signed in

Open **http://localhost:8000**. The home page shows notices and the course catalogue.
Notice that courses appear here **only** from institutions that have been verified.

Click **Verify a certificate** in the top bar and type any nonsense, such as `ABC123`. It
correctly reports that no certificate matches — this page is public because an employer
checking a certificate will not have an account.

### As the platform admin

Sign in as `admin@skillscope.io`.

1. The dashboard counts every institution, course and certificate on the platform.
2. Go to **Institutions**. One shows a **Pending** badge — Harbourview Polytechnic.
3. Open it. You see what they submitted, and **Verify** and **Reject** buttons.
4. Click **Verify**. Their courses can now appear publicly.
5. Go to **Competency** and choose a subject. Trainers are ranked, and each score is drawn
   as three bars, so you can see *why* one ranks above another.
6. Click **Capability gaps**. Each subject is coloured by how many people can teach it.
   Red means nobody.

### As an institute admin

Sign in as `rekha.iyer@northline.edu`.

1. Everything here is limited to Northline Institute of Technology. You cannot see another
   institution's data at all — not through the menus, and not by editing the address bar.
2. Go to **Trainers** → **Add a trainer**. Fill it in. The sign-in details appear on screen
   afterwards, to pass to that person.
3. Go to **Courses** → **New course**, and assign a trainer to it.
4. **Competency** shows gaps for this institution only — subjects where *your* institute
   has nobody qualified.

### As a trainer

Sign in as `vikram.c@northline.edu`.

1. **My courses** lists only the courses assigned to you.
2. Open one and add material — a video, a slide deck, a PDF or a link. Large files show a
   progress bar as they upload.
3. Add an assessment, write some multiple-choice questions, and set a deadline.
4. **Results** shows who attempted it, their scores, and which questions were most often
   answered wrongly — useful for spotting a badly-worded question.

### As a learner

Sign in as `aditya.menon@example.com`.

1. Browse the catalogue and enrol on something.
2. Open each item and click **Mark done** — the progress ring climbs.
3. Sit the assessment. It is marked immediately, and you can review which answers were
   wrong.
4. Once everything is done and the assessment is passed, a **certificate** is issued.
5. Open the certificate. **Download as PDF** uses your browser's print dialog.
6. Scan the QR code with a phone, or copy the verification link into a private browser
   window — it works with no account.
7. **Change one character of the code** in the address bar. It correctly reports the
   certificate does not exist.

---

## 6. Presenting it

**Beforehand**

1. Run **option 5** to reset the demo data, so nothing you clicked earlier is on screen.
2. Start with **option 3**, not option 2, so no technical error can appear.
3. Open http://localhost:8000 and leave it on the home page.
4. Sign in to a second browser window as the platform admin, so you can switch roles
   without typing passwords in front of everyone.

**Everything works without internet.** Bootstrap, the charts and the QR library are all
inside the project, so venue wifi failing cannot affect the demo.

**A suggested order**, covered fully in [docs/demo-script.md](docs/demo-script.md):

1. Home page, signed out — a real catalogue, not an empty shell
2. Verify Harbourview Polytechnic live, so the approval gate is a thing people watch happen
3. Learner journey: enrol → study → assessment → certificate
4. Scan the QR, then break the code by one character
5. Finish on the capability gap heatmap — the screen that separates this from a course list

**If something does go wrong**, option 3 means the audience sees a calm SkillScope page
rather than a wall of code. Press Ctrl+C, start it again with option 3, and carry on.

---

## 7. When something goes wrong

**Start with option 4 (Check status).** It tests everything in order and tells you what is
broken and how to fix it, rather than showing an error message.

### "Python is not installed, or not on PATH"

Python is missing, or was installed without the PATH checkbox. Re-run the installer,
choose **Modify**, and tick **Add python.exe to PATH**.

### "Cannot reach MySQL" / "MySQL is not running"

MySQL is not started. `Win + R` → `services.msc` → find **MySQL80** → right-click →
**Start**. Then run option 1 again.

### "Access denied for user 'root'"

The saved password is wrong. Run **option 1** — it will ask for the right one.

If you have forgotten it, reset it in MySQL Workbench, then delete the `.env` file next to
`manage.py` and run option 1 again.

### "That port is already in use"

SkillScope is already running in another window. Close that window, or press Ctrl+C in it.

### The page loads but looks like plain text, no colours

The stylesheets did not load. Almost always means the project was unzipped incompletely —
check that `static/vendor/bootstrap.min.css` exists. Option 4 checks this for you.

### Could not install the packages

Usually no internet connection at the moment setup ran. Connect and run option 1 again —
it picks up where it stopped.

### Everything is broken and I want to start over

Delete the `.venv` folder, then run option 1. It rebuilds from scratch without touching
your data. To reset the data as well, use option 5 afterwards.

---

## 8. Running it without the menu

If you prefer typing commands:

```bash
cd skillscope

# First time only
python -m venv .venv
.venv\Scripts\activate               # Windows
source .venv/bin/activate            # Mac or Linux
pip install -r requirements.txt
python setup_db.py                   # creates the database
python manage.py migrate             # builds the tables
python manage.py seed_demo           # loads the demo data

# Every time
python manage.py runserver
```

Useful commands:

| Command | What it does |
|---|---|
| `python check_setup.py` | Reports what is and is not working |
| `python check_setup.py --fix` | Reports, and fixes what it can |
| `python manage.py seed_demo --force` | Wipes and reloads the demo data |
| `python manage.py test` | Runs all 44 tests |
| `python manage.py createsuperuser` | Makes a Django admin account |

### Settings you can change

Set these before starting, or put them in the `.env` file next to `manage.py`:

| Setting | Default | Purpose |
|---|---|---|
| `SKILLSCOPE_DB_PASSWORD` | *(empty)* | Your MySQL password |
| `SKILLSCOPE_DB_USER` | `root` | MySQL username |
| `SKILLSCOPE_DB_NAME` | `skillscope` | Database name |
| `SKILLSCOPE_DB_HOST` | `127.0.0.1` | Where MySQL is |
| `SKILLSCOPE_DB_PORT` | `3306` | MySQL's port |
| `SKILLSCOPE_DEBUG` | `1` | `0` hides technical errors — demo mode |

A real environment variable always beats the `.env` file, so you can override one
temporarily without editing anything.

---

## 9. Sharing the project

**Do not zip the whole folder.** Three folders must be left out:

| Leave out | Why |
|---|---|
| `.venv` | 76 MB, and contains paths to *your* computer. Breaks everywhere else. |
| `media` | Files people uploaded — not part of the project |
| `__pycache__` | Generated automatically |
| `.env` | **Your MySQL password** |

Excluding them takes the zip from about **80 MB to under 2 MB**.

If you are using Git, the included `.gitignore` already excludes all four.

To make the zip from a terminal:

```bash
tar --exclude=.venv --exclude=__pycache__ --exclude=media --exclude=.env \
    -czf skillscope.zip skillscope
```

Whoever receives it needs Python and MySQL, then runs `skillscope.bat` → option 1. It will
ask for *their* MySQL password and set everything up from nothing.

---

## 10. Where things live in the code

```
skillscope/
├── skillscope.bat        the menu
├── check_setup.py        what option 1 and option 4 run
├── setup_db.py           creates the MySQL database
├── manage.py             Django's command runner
├── requirements.txt      the exact package versions
│
├── config/
│   ├── settings.py       database details, upload limits, DEBUG
│   └── urls.py           every address in the site, in one file
│
├── accounts/             users, roles, institutions, profiles, sign-in
│   ├── models.py         User, Institution, Qualification, Experience, UserSkill
│   ├── views.py          register, sign in, apply, verify, profiles
│   └── permissions.py    the role and institution checks
│
├── learning/             courses through to certificates
│   ├── models.py         Subject, Course, Resource, Enrollment, Assessment,
│   │                     Question, Attempt, Certificate, Feedback, Announcement
│   ├── views.py          catalogue, enrol, study, assess, certify
│   ├── services.py       marking and certificate issuing
│   └── management/commands/seed_demo.py    builds the demo data
│
├── competency/
│   └── services.py       the 40/30/30 scoring engine
│
├── templates/            54 pages: auth, public, learner, trainer,
│                         institute, platform, and shared partials
├── static/
│   ├── css/skillscope.css    the whole theme; every colour is here
│   ├── js/skillscope.js      upload progress and busy buttons
│   └── vendor/               Bootstrap, Chart.js, qrcode.js
└── docs/demo-script.md   the 8-minute walkthrough
```

### Adding a feature

Every feature in SkillScope is the same four steps. To add one:

1. **Model** — add a class in the relevant `models.py`, then run
   `python manage.py makemigrations` and `python manage.py migrate`
2. **View** — add a function in `views.py` that fetches the data
3. **Template** — add an HTML file under `templates/`
4. **URL** — add one line in `config/urls.py` joining an address to the view

Copy an existing feature that resembles what you want. They all follow this shape, which
is why there is only one pattern to learn.

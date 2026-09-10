# SkillScope

A learning platform where **verified institutions** publish courses, **trainers**
teach them, and **learners** earn certificates anyone can check.

Built with Django and MySQL. One project, one command to run.

---

## Running it

You need **Python 3.10+** and **MySQL 8** running locally.

```bash
cd skillscope

# 1. Create the database (once)
mysql -u root -p -e "CREATE DATABASE skillscope CHARACTER SET utf8mb4;"

# 2. Install the dependencies
python -m venv .venv
.venv\Scripts\activate            # Windows;  source .venv/bin/activate on Mac/Linux
pip install -r requirements.txt

# 3. Build the tables and fill them with demo data
python manage.py migrate
python manage.py seed_demo

# 4. Start it
python manage.py runserver
```

Then open **http://localhost:8000**

If your MySQL username or password is different, change those two lines near the
top of `config/settings.py`. That is the only file you need to touch.

---

## Sign-in details

Every seeded account uses the password **`skillscope123`**.

| Role | Email | What they can do |
|---|---|---|
| Platform admin | `admin@skillscope.io` | Verify institutions, see everything |
| Institute admin | `rekha.iyer@northline.edu` | Create courses and trainer accounts |
| Trainer | `vikram.c@northline.edu` | Upload material, set assessments |
| Learner | `aditya.menon@example.com` | Enrol, learn, get certified |
| Pending institute | `anil.kurup@harbourview.ac.in` | Blocked until verified — verify this one live |

---

## The four roles

```
Institute admin signs up  ->  applies with a registration document  ->  PENDING
                                          |
                          Platform admin reviews and VERIFIES
                                          |
              Institute admin can now:  create courses
                                        create trainer accounts
                                        assign a trainer to a course
                                          |
              Trainer signs in  ->  uploads material, sets assessments
                                          |
              Learner signs up  ->  enrols, learns, is assessed, earns a certificate
```

| Role | Gate on signing up | What they can see |
|---|---|---|
| **Learner** | none — active immediately | published courses from verified institutions |
| **Trainer** | account created by an institute admin | only courses assigned to them |
| **Institute admin** | blocked until their institution is verified | only their own institution's data |
| **Platform admin** | seeded, cannot self-register | everything |

---

## How the code is laid out

```
skillscope/
  config/          settings, and every URL in one file
  accounts/        User, Institution, sign-in, profiles, both admin areas
  learning/        subjects, courses, material, assessments, certificates
  competency/      the trainer-to-subject scoring engine
  templates/       48 pages, grouped by who uses them
  static/          our CSS, plus Bootstrap, Chart.js and the QR library
  media/           uploaded files
```

Every feature is the same four steps, repeated:

1. **Model** — a Python class; Django creates the MySQL table from it
2. **View** — a function that fetches data and passes it to a page
3. **Template** — HTML that prints the data with `{% for %}` and `{{ }}`
4. **URL** — one line in `config/urls.py` connecting an address to the view

Learn that once and the other sixteen models are the same thing with different
field names. There are no `.sql` files in this project — the tables are built
from the model classes.

---

## Competency mapping

The part that makes this more than a course catalogue. Every trainer is scored
against every subject, out of 100:

```
40%   average skill proficiency on their profile, out of 5
30%   years of experience in that subject, capped at 10
30%   average rating from learners who took their courses, out of 5
      ------
      60 or above = qualified to teach that subject
```

Two rules are worth knowing:

- **Experience is capped at ten years**, so one very long career cannot swamp
  the other two factors.
- **An unrated trainer is scored as 3 out of 5**, not zero. Scoring them zero
  would mean a new trainer could never be recommended, and so could never earn
  the ratings that would fix it.

It drives two screens. **Ranked trainers** shows who should teach a subject,
with the three components drawn as bars so a ranking can be explained out loud.
The **gap heatmap** inverts it: for each subject, how many people could teach it
at all. Red means nobody — a subject that has to be hired for or trained into.

Institute admins see this for their own institution; platform admins see it
across the whole platform.

---

## Certificates

Issued automatically when a learner has worked through **all** the material
**and** passed the course assessment. Both conditions, checked on the server.

Each certificate carries two identifiers on purpose:

- a **serial number** (`SS-2026-000042`) that is readable and sequential, for
  quoting in an email
- a **verification code** (`K7QJ3MRTZP`) that is random, so a forged
  certificate cannot be validated by guessing the next number in the series

The QR code on the certificate carries the random code and points at
`/verify/<code>/`, a public page that needs no account. Change one character of
the code and it correctly reports "not found".

The certificate is an ordinary web page with a print stylesheet — the browser's
own print dialog produces the PDF, so there is no PDF library on the server.

---

## Security

- Passwords hashed with Django's PBKDF2 — never stored as text
- Sign-in by email, with a session cookie; CSRF tokens on every form
- Role checks and **institution checks** on every view (`accounts/permissions.py`)
- Assessments marked on the server from the stored answer key; the correct
  answers are never sent to the browser
- Deadlines enforced server-side, so posting directly to the submit address
  after closing time does nothing

The institution check is the one that matters most here. Because SkillScope
hosts many institutions at once, "is this person a trainer" is not enough on its
own — every query is also filtered by institution, or one institute could read
another's learner list by changing a number in the address bar.

---

## Tests

```bash
python manage.py test
```

Covers the competency arithmetic against hand-worked values, assessment marking
(including that answering everything "A" against a different answer key scores
zero), certificate rules, and tenant isolation between institutions.

---

## What is deliberately not here

No payments, no live video, no discussion forums, no email sending — a trainer's
sign-in details are shown to the institute admin on screen to pass on — and no
REST API. None of them are needed, and each would be one more thing to explain.

Bootstrap, Chart.js, the QR library and both fonts are **committed into this
repository** rather than loaded from a CDN, so the site looks right with no
internet connection.

# SkillScope

A learning platform where **verified institutions** publish courses, **trainers** teach them,
and **learners** earn certificates anyone can check.

Built with Django and MySQL. One project, one menu to run it, and no internet needed once
installed.

---

## Quick start

Double-click **`skillscope.bat`** and choose **option 1**. It finds what is missing, installs
it, asks for your MySQL password if it needs one, creates the database and loads the demo data.

Then choose **option 2** and open **http://localhost:8000**.

Step-by-step instructions, including what to do when something goes wrong, are in
**[INSTRUCTIONS.md](INSTRUCTIONS.md)**.

### Sign-in details

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

Each role sees only what belongs to it. An institute admin cannot reach another institution's
learners; a trainer cannot reach a course they were not assigned to.

| Role | Gate on signing up | What they can see |
|---|---|---|
| **Learner** | none — active immediately | published courses from verified institutions |
| **Trainer** | account created by an institute admin | only courses assigned to them |
| **Institute admin** | blocked until their institution is verified | only their own institution's data |
| **Platform admin** | seeded, cannot self-register | everything, across all institutions |

---

## How it flows

### 1. An institution joins

Nobody can publish a course until a person has approved the institution behind it.

```
   Institute admin signs up
   and describes the institution
              |
              v
       status: PENDING  ------------>  can sign in, but sees only
              |                        "Awaiting verification"
              v
   Platform admin reviews it
              |
        +-----+-----+
        |           |
     VERIFY       REJECT
        |           |
        v           v
   full access   told the reason,
                 can apply again
```

### 2. A course is built

Two people, deliberately. The institute decides *what* is taught and *who* teaches it;
the trainer decides *how*.

```
   Institute admin                         Trainer
   ---------------                         -------
   creates a trainer account  --------->   signs in with those details
   creates a course                                  |
   assigns the trainer        --------->    uploads material
                                            (video, PPT, PDF, links)
                                                     |
                                            writes the assessment
                                            and sets its deadline
                                                     |
                                                     v
                                            course is published
```

### 3. A learner studies

```
   browses courses from verified institutions
              |
              v
          enrols  ---------->  progress starts at 0%
              |
              v
   opens each item, marks it done  ---------->  progress climbs
              |
              v
   sits the assessment, before the deadline
              |
              v
   marked on the server in one pass
              |
        +-----+-----+
        |           |
     passed      failed
        |           |
        v           v
   certificate   can retry while
     issued      the deadline holds
        |
        v
   leaves feedback, which later
   feeds the trainer's competency score
```

The **answer key never reaches the browser**. Marking, the deadline check and certificate
issuing all happen on the server, so editing the page cannot award a pass.

### 4. A certificate is checked

A certificate is worth little if an employer cannot verify it.

```
   Issued only when:  every item done  AND  assessment passed
              |
              v
   Two identifiers, created together:
     serial number   SS-2026-000042    readable, sequential, quotable
     verify code     K7QJ3MRTZP        random, unguessable
              |
              v
   A QR code carrying the verify code is printed on the certificate
              |
              v
   Anyone scans it -- no account needed
              |
        +-----+-----+
        |           |
     matches    does not match
        |           |
        v           v
   shows learner,  "Certificate
   course, date,    not found"
   institution
```

The two identifiers are separate on purpose. The serial can be quoted in a letter; the random
code is what actually proves the certificate, so guessing the next serial in the series proves
nothing.

The certificate is an ordinary web page with a print stylesheet — the browser's own print
dialog produces the PDF, so there is no PDF library on the server.

### 5. Competency mapping

The part that makes this more than a course catalogue. It answers a question a course list
cannot: **who should teach this, and what can we not teach at all?**

```
   Three things the platform already knows
   ---------------------------------------
   skill rating for the subject   (from the trainer's profile)    x 40%
   years worked in the subject    (from their work history)       x 30%  --> score out of 100
   average rating from learners   (from course feedback)          x 30%
                                                                            |
                          +-------------------------------------------------+
                          |                                                 |
                          v                                                 v
                Ranked trainers                                   Capability gaps
                for one subject                                   across all subjects
                          |                                                 |
        each score drawn as its three parts,               0 qualified = RED
        so a ranking can be explained aloud                1-2 = AMBER,  3+ = GREEN
```

Two rules are worth knowing:

- **Experience is capped at ten years**, so one very long career cannot swamp the other two
  factors.
- **An unrated trainer scores 3 out of 5**, not zero. Scoring them zero would mean a new
  trainer could never be recommended, and so could never earn the ratings that would fix it.

Red on the heatmap means nobody can teach that subject at all — something to hire for or train
into. Institute admins see this for their own institution; the platform admin sees it across
every institution.

---

## How the code is laid out

```
skillscope/
├── skillscope.bat     the menu: setup, start, check status, reset, test
├── manage.py          Django's command runner
│
├── config/            settings, and every URL in one file
├── accounts/          WHO YOU ARE - users, roles, institutions, profiles
├── learning/          SUBJECT TO CERTIFICATE - courses, material, enrolment,
│                      assessments, certificates, feedback, notices
├── competency/        the trainer-to-subject scoring engine
│
├── templates/         54 pages, grouped by who uses them
├── static/            our theme, plus Bootstrap, Chart.js and the QR library
├── media/             uploaded files (not in this repository)
└── docs/              an 8-minute demo walkthrough
```

Three apps split by **question**, not by technical layer: `accounts` answers *who are you*,
`learning` answers *what are you studying*, `competency` answers *who should teach it*.

Every feature inside them is the same four steps, repeated:

1. **Model** — a Python class; Django builds the MySQL table from it
2. **View** — a function that fetches data and hands it to a page
3. **Template** — HTML that prints the data with `{% for %}` and `{{ }}`
4. **URL** — one line in `config/urls.py` joining an address to the view

Learn that once and the other sixteen models are the same thing with different field names.
There are no `.sql` files in this project — every table is built from its model class.

---

## Built with

| Layer | Technology |
|---|---|
| Language | Python 3.10 or newer |
| Framework | Django 5.0 |
| Database | MySQL 8 |
| Pages | Django templates, rendered on the server |
| Styling | Bootstrap 5 with a custom theme |
| Charts | Chart.js |
| QR codes | qrcode.js |

Bootstrap, Chart.js, the QR library and both fonts are **committed into this repository**
rather than loaded from a CDN, so the site looks and works correctly with no internet
connection — which matters when presenting somewhere with unreliable wifi.

---

## Security

- Passwords hashed with Django's PBKDF2 — never stored as text
- Sign-in by email with a session cookie; CSRF tokens on every form
- Role checks **and institution checks** on every view (`accounts/permissions.py`)
- Assessments marked on the server from the stored answer key; the correct answers are never
  sent to the browser
- Deadlines enforced server-side, so posting directly to the submit address after closing time
  does nothing
- Database credentials read from the environment, never committed

The institution check is the one that matters most here. Because SkillScope hosts many
institutions at once, "is this person a trainer" is not enough on its own — every query is also
filtered by institution, or one institute could read another's learner list by changing a
number in the address bar.

**Two known gaps**, stated plainly rather than hidden: uploaded files are **not access
controlled** (anyone with the URL can fetch one, including an institution's proof document),
and **file types are not restricted** on upload. Both are contained fixes rather than
redesigns.

---

## Tests

```bash
python manage.py test
```

Or option 6 from the menu. 44 tests, covering the competency arithmetic against hand-worked
values, assessment marking (including that answering everything "A" against a different answer
key scores zero), deadline enforcement, certificate rules, the custom error pages, and tenant
isolation between institutions.

---

## What is deliberately not here

No payments, no live video, no discussion forums, no email sending — a trainer's sign-in
details are shown to the institute admin on screen to pass on — and no REST API. None of them
are needed, and each would be one more thing to explain.

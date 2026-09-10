# SkillScope — demo script

About **8 minutes**. Every step below has been run and works.

**Before you start**

```bash
python manage.py runserver
```

Open `http://localhost:8000` in a normal window, and have a **private window**
ready — you will need it once, to prove certificate verification needs no
account.

All accounts use the password **`skillscope123`**.

---

## 1 · The public face (40 seconds)

Start signed out on the home page.

> "SkillScope is a learning platform. Institutions publish courses, learners
> take them, and every certificate can be checked by anyone."

Point at the notice panel and the catalogue.

**Say this:** *"Everything in the catalogue comes from an institution we have
verified. That is the first thing this platform does."*

---

## 2 · An institution applies (1 minute)

Sign in as **`anil.kurup@harbourview.ac.in`**.

He lands on **"Awaiting review"** and can reach nothing else.

**Say this:** *"Harbourview Polytechnic applied and uploaded a registration
document. Their admin can sign in, but until a platform administrator checks
that document he cannot create a single course."*

Try clicking anything — the navigation has nothing for him.

---

## 3 · The platform admin verifies them (1 minute)

Sign out. Sign in as **`admin@skillscope.io`**.

The dashboard shows **1 institution waiting**. Open **Institutions → Review**.

Walk through what is being checked: registration number, city, contact, and the
uploaded proof document.

Press **Verify this institution**.

**Say this:** *"That is the gate. Nothing an institution publishes reaches the
public until a person has looked at their paperwork."*

Go back and sign in as Anil again — briefly — to show he now has a full
dashboard. *(Optional if time is short.)*

---

## 4 · An institute admin sets up a course (1 minute)

Sign in as **`rekha.iyer@northline.edu`** (Northline Institute of Technology).

Show **Trainers**.

**Say this:** *"Trainers do not sign themselves up. The institution creates
their account — that is how an institution controls who teaches in its name."*

Open **Courses**. Point out that each course has an assigned trainer, and that
the trainer dropdown only ever contains Northline's own staff.

---

## 5 · Tenant isolation — the thing most teams miss (45 seconds)

Still signed in as Rekha, edit the address bar to open a **Cardinal Skills**
course directly:

```
http://localhost:8000/institute/courses/7/edit/
```

It returns **404 — not found**.

**Say this:** *"Many institutions share this one platform. A role check alone
would not be enough — every query is also filtered by institution. Rekha cannot
reach Cardinal's course even by typing its address, and it says 'not found'
rather than 'not allowed', so she cannot even learn it exists."*

This is the strongest 30 seconds in the demo. Do not skip it.

---

## 6 · The trainer's side (1 minute)

Sign in as **`vikram.c@northline.edu`**.

Open a course → show the uploaded material and the enrolled learners with their
progress bars.

Open an **assessment** → show:

- the questions, with the correct answer marked **for the trainer only**
- **participation** — who has submitted, out of who is enrolled
- **which questions caught people out** — the per-question difficulty analysis

**Say this:** *"This tells the trainer which question to rewrite, or which topic
to teach again."*

---

## 7 · The learner journey (2 minutes)

Sign in as **`aditya.menon@example.com`**.

1. **Dashboard** — courses in progress, assessments due
2. Open a course → open a piece of material → **Mark done** → *the progress bar
   moves*
3. Open an **assessment** → answer the questions → **Submit**
4. The score appears immediately, with every answer reviewed

**Say this:** *"Marking happens on the server against the stored answer key. The
correct answers are never sent to the browser, so there is nothing on this page
to edit."*

---

## 8 · Certificate and verification (1 minute 30)

If that completed a course, the certificate is issued automatically. Otherwise
open **Certificates** and pick one.

Show the certificate. Point at the QR code.

Press **Download as PDF** — the browser's print dialog opens. *(Cancel it; the
point is that it works.)*

Now the important part. Copy the **verification code**, open your **private
window**, and go to:

```
http://localhost:8000/verify/<code>/
```

It confirms the certificate — **with no account and no sign-in**.

Then **change one character of the code** and reload.

It says **"No certificate has this code."**

**Say this:** *"There are two identifiers on every certificate. The serial
number runs in order so it can be quoted. The verification code is random, so
you cannot forge one by guessing the next number in the series."*

---

## 9 · Competency mapping — the closer (1 minute 30)

Sign back in as **`admin@skillscope.io`** → **Competency**.

**Start with the heatmap.**

> "This is the question a training organisation actually has. Not 'who is our
> best trainer' — but **'what can we not teach at all?'**"

- **Cybersecurity — red.** Nobody scores 60. The best is 37%.
- **Machine Learning — red.** Nobody at all.
- **Web Development — green.** Four qualified trainers.

**Say this:** *"Those two red cells are a hiring plan."*

Now choose **UI/UX Design** in the dropdown.

Meera Pillai comes out at **98%**. Point at the three bars underneath:

> "Skill 40 out of 40, experience 30 out of 30, learner rating 27.8 out of 30 —
> 4.6 out of 5 from 8 learners. Nothing is hidden. Every ranking can be
> explained to the person who was not picked."

Finish there.

---

## If a judge asks

**"How do you know marking is not faked?"**
Answer every question "A" against an answer key of B,C,B,B,B — it scores 0 out
of 5. There is a test for exactly this, and the answer key never leaves the
server.

**"What if someone submits after the deadline?"**
The deadline is checked in `mark_attempt()` on the server, not just hidden in
the page. Posting directly to the submit address after closing time creates no
attempt at all.

**"Is competency mapping machine learning?"**
No, and deliberately not. It is a weighted average of three figures the platform
already collects, all three drawn on screen. A model nobody can question is
worse here than arithmetic everybody can.

**"Why is an unrated trainer given 3 out of 5?"**
Because scoring them zero would mean a new trainer is never recommended, so
never gets rated, so stays at zero forever.

**"Could one institution see another's learners?"**
No — step 5. Every query is filtered by institution, and there are tests for it.

---

## If something goes wrong on stage

- **Page will not load** — check the terminal running `runserver`.
- **Data looks wrong** — `python manage.py seed_demo --force` rebuilds it in
  about a minute. The random seed is fixed, so the same numbers come back.
- **No internet at the venue** — does not matter. Bootstrap, Chart.js, the QR
  library and both fonts are inside the repository.

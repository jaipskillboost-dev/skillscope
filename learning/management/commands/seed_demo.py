"""
Fills an empty database with a believable SkillScope.

Run with:  python manage.py seed_demo

Two things here are deliberate rather than decorative:

1. One institution is left PENDING, so the verification step can be performed
   live rather than described.
2. Trainer skills are uneven on purpose, so the competency heatmap shows real
   red and amber subjects. A heatmap where everything is green proves nothing,
   and an empty dashboard demos as a bug.

Everything uses a fixed random seed, so the same numbers come back every time.
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Institution, InstitutionStatus, InstitutionType, Role, User
from learning.models import (
    Announcement, AnnouncementType, Assessment, Attempt, AttemptAnswer, Course,
    CourseLevel, CourseStatus, Enrollment, EnrollmentStatus, Experience, Feedback,
    Qualification, Question, Resource, ResourceCompletion, ResourceType, Subject,
    UserSkill,
)
from learning.services import issue_certificate_if_earned

PASSWORD = "skillscope123"

SUBJECTS = [
    ("WEB", "Web Development", "Building websites and web applications."),
    ("DATA", "Data Science", "Turning data into decisions."),
    ("CLOUD", "Cloud Computing", "Running software on cloud infrastructure."),
    ("SEC", "Cybersecurity", "Protecting systems and the people who use them."),
    ("UIUX", "UI/UX Design", "Designing interfaces people can actually use."),
    ("ML", "Machine Learning", "Models that learn from data."),
    ("MKT", "Digital Marketing", "Reaching an audience online."),
    ("PM", "Project Management", "Delivering work on time and in scope."),
]

INSTITUTIONS = [
    dict(name="Northline Institute of Technology", reg="NIT-2019-4471", city="Pune",
         state="Maharashtra", kind=InstitutionType.COLLEGE, status=InstitutionStatus.VERIFIED,
         admin=("Rekha Iyer", "rekha.iyer@northline.edu", "Dean of Training")),
    dict(name="Cardinal Skills Academy", reg="CSA-2021-8830", city="Bengaluru",
         state="Karnataka", kind=InstitutionType.TRAINING_CENTRE, status=InstitutionStatus.VERIFIED,
         admin=("Daniel Fernandes", "daniel.f@cardinalskills.in", "Programme Head")),
    dict(name="Meridian Corporate Academy", reg="MCA-2020-1192", city="Hyderabad",
         state="Telangana", kind=InstitutionType.CORPORATE, status=InstitutionStatus.VERIFIED,
         admin=("Priya Raghavan", "priya.r@meridianacademy.com", "Learning Director")),
    # Left pending on purpose -- this is the one verified live during a demo.
    dict(name="Harbourview Polytechnic", reg="HVP-2024-0317", city="Kochi",
         state="Kerala", kind=InstitutionType.COLLEGE, status=InstitutionStatus.PENDING,
         admin=("Anil Kurup", "anil.kurup@harbourview.ac.in", "Training Coordinator")),
]

# (name, email, institution index, designation, [(subject code, skill, proficiency, years)])
#
# The spread is the point. Web Development and Data Science have several strong
# trainers; Cybersecurity has one borderline; Machine Learning has nobody at
# all -- which is what puts a red cell on the heatmap.
TRAINERS = [
    ("Vikram Chauhan", "vikram.c@northline.edu", 0, "Senior Instructor", [
        ("WEB", "React and modern JavaScript", 5, 9),
        ("WEB", "API design", 4, 7),
        ("UIUX", "Design systems", 3, 3),
    ]),
    ("Sneha Kulkarni", "sneha.k@northline.edu", 0, "Instructor", [
        ("DATA", "Python for analysis", 5, 7),
        ("DATA", "SQL and warehousing", 4, 6),
    ]),
    ("Arvind Nair", "arvind.n@northline.edu", 0, "Visiting Faculty", [
        ("PM", "Agile delivery", 4, 8),
        ("PM", "Stakeholder management", 3, 5),
    ]),
    ("Fatima Sheikh", "fatima.s@cardinalskills.in", 1, "Lead Trainer", [
        ("WEB", "Full-stack development", 5, 6),
        ("CLOUD", "Containers and Kubernetes", 4, 5),
    ]),
    ("Rohit Desai", "rohit.d@cardinalskills.in", 1, "Trainer", [
        ("CLOUD", "AWS architecture", 5, 8),
        ("CLOUD", "Infrastructure as code", 4, 4),
    ]),
    ("Meera Pillai", "meera.p@cardinalskills.in", 1, "Senior Trainer", [
        ("UIUX", "Interaction design", 5, 10),
        ("UIUX", "User research", 5, 8),
        ("MKT", "Content strategy", 3, 3),
    ]),
    ("Tarun Bhatt", "tarun.b@meridianacademy.com", 2, "Corporate Trainer", [
        ("MKT", "Performance marketing", 4, 6),
        ("MKT", "Analytics and attribution", 4, 5),
    ]),
    # Deliberately thin: enough to be listed for Cybersecurity, not enough to
    # clear the qualified threshold on his own.
    ("Nikhil Verma", "nikhil.v@meridianacademy.com", 2, "Associate Trainer", [
        ("SEC", "Secure coding basics", 2, 1),
    ]),
    # These two exist so Web Development reaches three qualified trainers and
    # shows green -- without a green subject the heatmap legend is untestable.
    ("Deepa Ranganathan", "deepa.r@meridianacademy.com", 2, "Senior Trainer", [
        ("WEB", "TypeScript and tooling", 5, 7),
        ("DATA", "Data visualisation", 3, 2),
    ]),
    ("Joseph Mathew", "joseph.m@northline.edu", 0, "Instructor", [
        ("WEB", "Backend services", 4, 6),
        ("PM", "Delivery planning", 3, 4),
    ]),
]

LEARNER_NAMES = [
    "Aditya Menon", "Kavya Reddy", "Ishaan Malhotra", "Ananya Bose", "Rahul Krishnan",
    "Nisha Agarwal", "Karthik Subramanian", "Divya Nambiar", "Siddharth Rao", "Pooja Mehta",
    "Arjun Thakur", "Shreya Ghosh", "Manish Patel", "Lakshmi Venkat", "Rohan Joshi",
    "Tanvi Shah", "Aakash Bhardwaj", "Sanjana Rao", "Vivek Anand", "Neha Kapoor",
    "Gaurav Sinha", "Ritika Chawla", "Harsh Vardhan", "Aisha Qureshi", "Naveen Kumar",
    "Swati Deshmukh", "Yash Trivedi", "Megha Saxena", "Imran Ali", "Preeti Bhalla",
]

COURSES = [
    # (institution index, trainer email, subject code, code, title, level, hours, description)
    (0, "vikram.c@northline.edu", "WEB", "WEB-101", "Building Modern Web Applications",
     CourseLevel.BEGINNER, 40,
     "Start from plain HTML and finish with a working React application backed by an API."),
    (0, "vikram.c@northline.edu", "WEB", "WEB-210", "API Design and Integration",
     CourseLevel.INTERMEDIATE, 24,
     "Design APIs other people can actually use, and consume them safely from a front end."),
    (0, "sneha.k@northline.edu", "DATA", "DATA-110", "Data Analysis with Python",
     CourseLevel.BEGINNER, 36,
     "Pandas, cleaning messy data, and drawing charts that answer a real question."),
    (0, "sneha.k@northline.edu", "DATA", "DATA-240", "SQL for Analysts",
     CourseLevel.INTERMEDIATE, 20,
     "Joins, window functions, and writing queries that stay readable six months later."),
    (0, "arvind.n@northline.edu", "PM", "PM-105", "Agile Delivery in Practice",
     CourseLevel.BEGINNER, 18,
     "Running a delivery team without turning the process into the product."),
    (1, "fatima.s@cardinalskills.in", "WEB", "WEB-150", "Full-Stack Web Engineering",
     CourseLevel.INTERMEDIATE, 48,
     "One application, end to end: database, server, interface and deployment."),
    (1, "rohit.d@cardinalskills.in", "CLOUD", "CLD-120", "AWS Foundations",
     CourseLevel.BEGINNER, 30,
     "The core AWS services, and how to reason about cost before the bill arrives."),
    (1, "rohit.d@cardinalskills.in", "CLOUD", "CLD-260", "Kubernetes in Production",
     CourseLevel.ADVANCED, 32,
     "Running containers reliably, and debugging them when they misbehave."),
    (1, "meera.p@cardinalskills.in", "UIUX", "UX-101", "User Experience Fundamentals",
     CourseLevel.BEGINNER, 28,
     "Research, prototyping and testing, with real users rather than assumptions."),
    (1, "meera.p@cardinalskills.in", "UIUX", "UX-230", "Design Systems at Scale",
     CourseLevel.ADVANCED, 26,
     "Building a component library a whole organisation can share."),
    (2, "tarun.b@meridianacademy.com", "MKT", "MKT-140", "Digital Marketing Analytics",
     CourseLevel.INTERMEDIATE, 22,
     "Attribution, funnels, and knowing which numbers are lying to you."),
    (2, "nikhil.v@meridianacademy.com", "SEC", "SEC-100", "Secure Coding Essentials",
     CourseLevel.BEGINNER, 16,
     "The handful of mistakes behind most vulnerabilities, and how to stop making them."),
]

MATERIAL = [
    ("Introduction and setup", ResourceType.VIDEO),
    ("Core concepts explained", ResourceType.PPT),
    ("Worked example walkthrough", ResourceType.VIDEO),
    ("Reference handbook", ResourceType.PDF),
    ("Practice exercises", ResourceType.DOC),
]

LIBRARY_ITEMS = [
    ("Onboarding guide for new learners", ResourceType.PDF),
    ("Recording: guest industry session", ResourceType.VIDEO),
    ("Slide template for trainers", ResourceType.PPT),
]

QUESTION_BANK = {
    "WEB": [
        ("Which HTTP status code means the request succeeded and created something?",
         "200 OK", "201 Created", "204 No Content", "302 Found", "B"),
        ("What does the `key` prop help React do when rendering a list?",
         "Sort the items", "Style each item", "Track which item changed",
         "Cache the list", "C"),
        ("Where should a secret API key be kept?",
         "In the front-end bundle", "In a public repository",
         "On the server, never sent to the browser", "In localStorage", "C"),
        ("What does CORS control?",
         "Database access", "Which origins may call your API",
         "How CSS is applied", "Server memory limits", "B"),
        ("Which is the correct way to prevent an SQL injection?",
         "Escaping quotes by hand", "Using parameterised queries",
         "Hiding the query", "Renaming the table", "B"),
    ],
    "DATA": [
        ("In pandas, what does `df.dropna()` do by default?",
         "Fills missing values", "Removes rows containing missing values",
         "Removes duplicate rows", "Sorts the frame", "B"),
        ("Which measure is least affected by an extreme outlier?",
         "Mean", "Median", "Standard deviation", "Range", "B"),
        ("What does a GROUP BY clause do in SQL?",
         "Filters rows", "Sorts results",
         "Collapses rows into groups for aggregation", "Joins two tables", "C"),
        ("A correlation of 0.9 between two variables means:",
         "One causes the other", "They move together closely",
         "They are unrelated", "The data is wrong", "B"),
        ("Which chart best shows how one value changes over time?",
         "Pie chart", "Line chart", "Scatter plot", "Treemap", "B"),
    ],
    "CLOUD": [
        ("What does an auto-scaling group do?",
         "Backs up data", "Adds or removes instances based on demand",
         "Encrypts traffic", "Routes DNS", "B"),
        ("In Kubernetes, what is the smallest deployable unit?",
         "Container", "Pod", "Node", "Cluster", "B"),
        ("What is object storage such as S3 best suited to?",
         "Running databases", "Storing files and large blobs",
         "Serving as a message queue", "Hosting a container", "B"),
        ("Which of these best reduces cloud cost?",
         "Larger instances always", "Right-sizing and switching off idle resources",
         "More availability zones", "Bigger disks", "B"),
        ("What does infrastructure as code give you?",
         "Faster networking", "Repeatable, reviewable environments",
         "Cheaper storage", "Automatic security", "B"),
    ],
    "UIUX": [
        ("What is the main purpose of a usability test?",
         "Prove the design is good", "Watch real people try to complete a task",
         "Choose brand colours", "Speed up the site", "B"),
        ("What is a design system?",
         "A single style guide PDF", "A shared set of reusable components and rules",
         "A prototyping tool", "A colour palette", "B"),
        ("Minimum recommended contrast ratio for normal body text is:",
         "2:1", "3:1", "4.5:1", "10:1", "C"),
        ("What does a wireframe deliberately leave out?",
         "Layout", "Content hierarchy", "Visual styling", "Navigation", "C"),
        ("Why keep touch targets at least 44px?",
         "It looks better", "Fingers are imprecise",
         "It loads faster", "It is required by HTML", "B"),
    ],
    "MKT": [
        ("What does a conversion rate measure?",
         "Total visitors", "Proportion of visitors who complete a goal",
         "Cost of an ad", "Time on page", "B"),
        ("Last-click attribution tends to over-credit:",
         "Early awareness channels", "The final channel before purchase",
         "Email only", "Offline channels", "B"),
        ("A high bounce rate on a landing page usually suggests:",
         "The page loaded quickly", "Visitors did not find what they expected",
         "The ad was cheap", "Strong SEO", "B"),
        ("What is A/B testing used for?",
         "Comparing two versions to see which performs better",
         "Backing up data", "Writing copy", "Buying ads", "A"),
        ("Which metric best reflects profitability of a campaign?",
         "Impressions", "Clicks", "Return on ad spend", "Followers", "C"),
    ],
    "PM": [
        ("What is the purpose of a sprint retrospective?",
         "Plan the next sprint's work", "Reflect on how the team worked and improve it",
         "Demo to stakeholders", "Estimate stories", "B"),
        ("Scope creep means:",
         "The team works faster", "Work is added without adjusting time or resources",
         "The budget increases", "The deadline moves", "B"),
        ("What does a burndown chart show?",
         "Team happiness", "Remaining work over time", "Cost per feature",
         "Number of bugs", "B"),
        ("A daily stand-up should mainly surface:",
         "Detailed technical design", "Progress and blockers",
         "Performance reviews", "Budget changes", "B"),
        ("Who decides priority of the product backlog?",
         "The developers", "The product owner", "The scrum master", "The client only", "B"),
    ],
    "SEC": [
        ("What does hashing a password protect against?",
         "Slow logins", "Stolen databases revealing plain passwords",
         "Network outages", "Weak passwords", "B"),
        ("What is the principle of least privilege?",
         "Give everyone admin", "Give each account only the access it needs",
         "Rotate passwords weekly", "Encrypt everything", "B"),
        ("Which is a sign of a phishing email?",
         "Correct spelling", "Urgent tone and an unexpected link",
         "Company logo", "A signature block", "B"),
        ("Why validate input on the server as well as the browser?",
         "It is faster", "The browser can be bypassed entirely",
         "It looks professional", "It reduces bandwidth", "B"),
        ("What does multi-factor authentication add?",
         "A longer password", "A second, different kind of proof",
         "Faster sign-in", "Encrypted storage", "B"),
    ],
}

NOTICES = [
    (AnnouncementType.ANNOUNCEMENT, "Three new institutions joined this month",
     "Northline, Cardinal Skills and Meridian have published their first courses on "
     "SkillScope. Browse the catalogue to see what is on offer.", True),
    (AnnouncementType.ACHIEVEMENT, "First 100 certificates issued",
     "Learners on SkillScope have now earned their first hundred verified certificates, "
     "each one checkable by anyone with the code.", False),
    (AnnouncementType.NEW_CONTENT, "Kubernetes in Production is now open",
     "Cardinal Skills Academy has published an advanced course on running containers "
     "reliably in production.", False),
    (AnnouncementType.NOTIFICATION, "Scheduled maintenance this Sunday",
     "SkillScope will be briefly unavailable on Sunday between 02:00 and 03:00 IST "
     "while we upgrade the platform.", False),
    (AnnouncementType.ACHIEVEMENT, "Meera Pillai rated highest in UI/UX Design",
     "Learner feedback puts Meera Pillai at the top of the UI/UX Design competency "
     "ranking this quarter.", False),
    (AnnouncementType.NEW_CONTENT, "Data Analysis with Python refreshed for 2026",
     "Northline Institute has updated the course material with new worked examples.", False),
]


class Command(BaseCommand):
    help = "Fill the database with realistic demo data for SkillScope."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force", action="store_true",
            help="Wipe the existing demo data and seed again.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if User.objects.exists() and not options["force"]:
            self.stdout.write(self.style.WARNING(
                "There is already data here. Run with --force to wipe and reseed."
            ))
            return

        if options["force"]:
            self.stdout.write("Clearing existing data...")
            for model in (AttemptAnswer, Attempt, Question, Assessment, ResourceCompletion,
                          Feedback, Enrollment, Resource, Course, Announcement,
                          UserSkill, Experience, Qualification, Subject):
                model.objects.all().delete()
            User.objects.all().delete()
            Institution.objects.all().delete()

        random.seed(42)
        now = timezone.now()

        # ------------------------------------------------------------ subjects
        subjects = {}
        for code, name, description in SUBJECTS:
            subjects[code] = Subject.objects.create(
                code=code, name=name, description=description
            )
        self.stdout.write(f"  {len(subjects)} subjects")

        # ------------------------------------------------- platform admin
        platform_admin = User.objects.create_user(
            email="admin@skillscope.io", password=PASSWORD,
            full_name="Sunita Balakrishnan", role=Role.PLATFORM_ADMIN,
            designation="Platform Administrator", is_staff=True, is_superuser=True,
        )

        # -------------------------------------------------- institutions
        institutions = []
        for spec in INSTITUTIONS:
            institution = Institution.objects.create(
                name=spec["name"], institution_type=spec["kind"],
                registration_no=spec["reg"], city=spec["city"], state=spec["state"],
                contact_email=spec["admin"][1], contact_phone="+91 80 4000 1000",
                status=spec["status"],
                description=f"{spec['name']} runs professional training programmes "
                            f"from {spec['city']}.",
                verified_at=now - timedelta(days=30) if spec["status"] == InstitutionStatus.VERIFIED else None,
                verified_by=platform_admin if spec["status"] == InstitutionStatus.VERIFIED else None,
            )
            name, email, designation = spec["admin"]
            User.objects.create_user(
                email=email, password=PASSWORD, full_name=name,
                role=Role.INSTITUTE_ADMIN, institution=institution, designation=designation,
            )
            institutions.append(institution)
        self.stdout.write(f"  {len(institutions)} institutions "
                          f"({sum(1 for i in institutions if i.status == 'PENDING')} left pending)")

        # ------------------------------------------------------ trainers
        trainers = {}
        for name, email, inst_index, designation, skills in TRAINERS:
            trainer = User.objects.create_user(
                email=email, password=PASSWORD, full_name=name, role=Role.TRAINER,
                institution=institutions[inst_index], designation=designation,
                bio=f"{designation} at {institutions[inst_index].name}.",
            )
            trainers[email] = trainer

            for subject_code, skill_name, proficiency, years in skills:
                UserSkill.objects.create(
                    user=trainer, subject=subjects[subject_code], skill_name=skill_name,
                    proficiency=proficiency, years_experience=Decimal(years),
                )

            # One work-history row per subject, using the longest of that
            # subject's skills. Two skills in the same subject are usually the
            # same job, so a row each would count those years twice.
            longest_per_subject = {}
            for subject_code, _skill, _proficiency, years in skills:
                longest_per_subject[subject_code] = max(
                    longest_per_subject.get(subject_code, 0), years
                )
            for subject_code, years in longest_per_subject.items():
                Experience.objects.create(
                    user=trainer, subject=subjects[subject_code],
                    organisation=institutions[inst_index].name, designation=designation,
                    from_year=now.year - years, currently_working=True,
                )
            Qualification.objects.create(
                user=trainer, degree="M.Tech Computer Science",
                institution_name="National Institute of Technology",
                year_of_passing=now.year - 10 - random.randint(0, 5),
                percentage=Decimal(str(round(random.uniform(68, 89), 2))),
            )
        self.stdout.write(f"  {len(trainers)} trainers")

        # ------------------------------------------------------ learners
        learners = []
        for index, name in enumerate(LEARNER_NAMES):
            first, last = name.split()[0].lower(), name.split()[-1].lower()
            learners.append(User.objects.create_user(
                email=f"{first}.{last}@example.com", password=PASSWORD,
                full_name=name, role=Role.LEARNER,
                designation=random.choice([
                    "Software Engineer", "Analyst", "Designer", "Graduate Trainee",
                    "Project Coordinator", "Marketing Executive",
                ]),
            ))
        self.stdout.write(f"  {len(learners)} learners")

        # ------------------------------------------------------- courses
        courses = []
        for inst_index, trainer_email, subject_code, code, title, level, hours, description \
                in COURSES:
            institution = institutions[inst_index]
            course = Course.objects.create(
                institution=institution, subject=subjects[subject_code],
                trainer=trainers[trainer_email], created_by=institution.members.filter(
                    role=Role.INSTITUTE_ADMIN).first(),
                code=code, title=title, description=description, level=level,
                duration_hours=hours, status=CourseStatus.PUBLISHED,
            )
            courses.append(course)

            for position, (material_title, kind) in enumerate(MATERIAL, start=1):
                Resource.objects.create(
                    course=course, institution=institution, subject=course.subject,
                    uploaded_by=course.trainer, title=f"{material_title}",
                    resource_type=kind, position=position,
                    link_url="https://example.com/material" if kind == ResourceType.LINK else "",
                    description=f"Part {position} of {course.title}.",
                )
        self.stdout.write(f"  {len(courses)} published courses, "
                          f"{Resource.objects.count()} pieces of material")

        # --------------------------------------------- library material
        for institution in institutions[:3]:
            trainer = institution.members.filter(role=Role.TRAINER).first()
            if not trainer:
                continue
            for title, kind in LIBRARY_ITEMS:
                Resource.objects.create(
                    course=None, institution=institution,
                    subject=random.choice(list(subjects.values())),
                    uploaded_by=trainer, title=title, resource_type=kind,
                    description="Shared across the institution, not tied to one course.",
                )

        # --------------------------------------------------- assessments
        for course in courses:
            bank = QUESTION_BANK.get(course.subject.code)
            if not bank:
                continue
            assessment = Assessment.objects.create(
                course=course, subject=course.subject, trainer=course.trainer,
                title=f"{course.title} - final assessment",
                instructions="Answer every question. You get one attempt.",
                deadline=now + timedelta(days=random.randint(10, 45)),
                duration_minutes=20, pass_percent=50,
            )
            for position, (text, a, b, c, d, correct) in enumerate(bank, start=1):
                Question.objects.create(
                    assessment=assessment, question_text=text,
                    option_a=a, option_b=b, option_c=c, option_d=d,
                    correct_option=correct, marks=1, position=position,
                )
        self.stdout.write(f"  {Assessment.objects.count()} assessments, "
                          f"{Question.objects.count()} questions")

        # ----------------------------------------- enrolments and history
        certificates = 0
        for learner in learners:
            for course in random.sample(courses, random.randint(1, 4)):
                enrollment = Enrollment.objects.create(
                    course=course, learner=learner,
                    enrolled_at=now - timedelta(days=random.randint(20, 120)),
                )

                resources = list(course.resources.all())
                # A third finish everything, a third get part way, a third have
                # barely started -- so progress bars and dashboards look real.
                bucket = random.random()
                if bucket < 0.35:
                    done = resources
                elif bucket < 0.7:
                    done = resources[: random.randint(1, max(1, len(resources) - 1))]
                else:
                    done = resources[:1] if resources else []

                for resource in done:
                    ResourceCompletion.objects.create(
                        enrollment=enrollment, resource=resource
                    )
                enrollment.recalculate_progress()

                assessment = course.assessments.first()
                if assessment and len(done) >= 3:
                    questions = list(assessment.questions.all())
                    # Stronger learners answer more correctly.
                    accuracy = random.uniform(0.4, 1.0)
                    attempt = Attempt.objects.create(
                        assessment=assessment, learner=learner,
                        total_marks=len(questions),
                        started_at=enrollment.enrolled_at + timedelta(days=5),
                        submitted_at=enrollment.enrolled_at + timedelta(days=5, minutes=18),
                    )
                    score = 0
                    for question in questions:
                        correct = random.random() < accuracy
                        chosen = question.correct_option if correct else random.choice(
                            [o for o in "ABCD" if o != question.correct_option]
                        )
                        if correct:
                            score += question.marks
                        AttemptAnswer.objects.create(
                            attempt=attempt, question=question,
                            selected_option=chosen, is_correct=correct,
                        )
                    percentage = Decimal(score) / Decimal(len(questions)) * 100
                    attempt.score = score
                    attempt.percentage = percentage.quantize(Decimal("0.01"))
                    attempt.passed = attempt.percentage >= assessment.pass_percent
                    attempt.save()

                # Feedback from anyone who got reasonably far. The trainer
                # rating here is what feeds the competency score.
                if len(done) >= 3 and random.random() < 0.75:
                    base = random.choice([3, 4, 4, 5, 5])
                    Feedback.objects.create(
                        course=course, learner=learner,
                        content_rating=min(5, max(1, base + random.choice([-1, 0, 0, 1]))),
                        trainer_rating=min(5, max(1, base + random.choice([0, 0, 1]))),
                        overall_rating=base,
                        comments=random.choice([
                            "Clear explanations and useful examples.",
                            "Paced well. The worked examples helped most.",
                            "Solid course. More practice material would help.",
                            "The trainer answered questions properly.",
                            "",
                        ]),
                    )

                if issue_certificate_if_earned(enrollment):
                    certificates += 1

        self.stdout.write(f"  {Enrollment.objects.count()} enrolments, "
                          f"{Attempt.objects.count()} attempts, "
                          f"{Feedback.objects.count()} reviews, "
                          f"{certificates} certificates")

        # -------------------------------------------------------- notices
        for kind, title, body, pinned in NOTICES:
            Announcement.objects.create(
                announcement_type=kind, title=title, body=body,
                posted_by=platform_admin, pinned=pinned,
                created_at=now - timedelta(days=random.randint(1, 25)),
            )

        self.stdout.write(self.style.SUCCESS("\nSkillScope is seeded.\n"))
        self.stdout.write(f"  Every account uses the password: {PASSWORD}\n")
        self.stdout.write("  Platform admin    admin@skillscope.io")
        self.stdout.write("  Institute admin   rekha.iyer@northline.edu")
        self.stdout.write("  Trainer           vikram.c@northline.edu")
        self.stdout.write("  Learner           aditya.menon@example.com")
        self.stdout.write("  Pending institute anil.kurup@harbourview.ac.in "
                          "(verify this one live)\n")

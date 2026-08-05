"""Curriculum catalog seed data (idempotent)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Institution, CurriculumCourse, CurriculumSubject, CurriculumUnit


def seed_curriculum(db: Session) -> None:
    """Seed the curriculum catalog. Idempotent — safe to call on every startup."""
    if db.query(Institution).first() is not None:
        return

    # -- Institution --
    institution = Institution(
        name="GLA University",
        short_name="GLA",
        description="Demo university",
        is_active=True,
    )
    db.add(institution)
    db.flush()

    # -- Program --
    program = CurriculumCourse(
        institution_id=institution.id,
        name="B.Tech CSE",
        code="BTECH-CSE",
        description="Bachelor of Technology in Computer Science and Engineering",
        duration=4,
        is_active=True,
    )
    db.add(program)
    db.flush()

    # -- Subjects (5 subjects, semesters 1-5) --
    subject_specs = [
        ("Data Structures", "DS", 1, 4, "Fundamentals of data structures and algorithms"),
        ("Operating Systems", "OS", 2, 4, "Operating system concepts and design"),
        ("Database Management Systems", "DBMS", 3, 3, "Relational databases and SQL"),
        ("Computer Networks", "CN", 4, 3, "Network protocols and architectures"),
        ("Machine Learning", "ML", 5, 3, "Introduction to machine learning"),
    ]

    subjects = []
    for name, code, semester, credits, description in subject_specs:
        subj = CurriculumSubject(
            program_id=program.id,
            name=name,
            code=code,
            semester=semester,
            credits=credits,
            description=description,
            is_active=True,
        )
        db.add(subj)
        subjects.append(subj)
    db.flush()

    # -- Units per subject (4-5 units each) --
    unit_specs = {
        subjects[0].id: [  # Data Structures
            (1, "Introduction to Data Structures"),
            (2, "Arrays and Linked Lists"),
            (3, "Stacks and Queues"),
            (4, "Trees and Binary Search Trees"),
            (5, "Graphs and Graph Algorithms"),
        ],
        subjects[1].id: [  # Operating Systems
            (1, "Introduction to Operating Systems"),
            (2, "Process Management"),
            (3, "Memory Management"),
            (4, "File Systems and I/O"),
        ],
        subjects[2].id: [  # DBMS
            (1, "Relational Model and SQL"),
            (2, "Database Design and Normalization"),
            (3, "Transaction Management and Concurrency"),
            (4, "Query Optimization"),
        ],
        subjects[3].id: [  # Computer Networks
            (1, "Introduction to Computer Networks"),
            (2, "Transport Layer"),
            (3, "Network Layer and Routing"),
            (4, "Application Layer Protocols"),
        ],
        subjects[4].id: [  # Machine Learning
            (1, "Introduction to Machine Learning"),
            (2, "Supervised Learning"),
            (3, "Unsupervised Learning"),
            (4, "Model Evaluation and Tuning"),
        ],
    }

    for subject_id, units in unit_specs.items():
        for unit_number, unit_name in units:
            db.add(CurriculumUnit(
                subject_id=subject_id,
                unit_number=unit_number,
                name=unit_name,
            ))

    db.commit()

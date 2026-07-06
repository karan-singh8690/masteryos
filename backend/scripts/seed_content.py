"""Seed Python interview content into the database.

Creates:
- 1 Subject: Python Technical Interview Prep
- 5 Concepts: Data Structures, OOP, Algorithms, Python Internals, System Design
- 15 Learning Objectives
- 10 Misconceptions
- 10 Question Templates (with template versions)
- Template-concept mappings

Run: python -m scripts.seed_content
"""

from __future__ import annotations

import asyncio
import sys
import os
from uuid import uuid4

# Add backend dir to path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.shared.config import get_settings
from app.infrastructure.database.orm.base import Base
from app.infrastructure.database.orm import identity, auth, background, beta, beta_ops, core, content, billing  # noqa: F401
from app.infrastructure.database.orm.content import (
    SubjectModel, ConceptModel, LearningObjectiveModel, MisconceptionModel,
    QuestionTemplateModel, TemplateVersionModel, TemplateConceptModel,
    ExplanationModel,
)
from app.infrastructure.database.orm.identity import UserModel


# ============================================================
# Content Definitions
# ============================================================

SUBJECT = {
    "code": "PY-INTERVIEW",
    "name": "Python Technical Interview Prep",
    "slug": "python-interview-prep",
    "description": "Master Python technical interviews with adaptive practice on data structures, algorithms, OOP, Python internals, and system design.",
}

CONCEPTS = [
    {
        "slug": "data-structures",
        "name": "Data Structures",
        "description": "Lists, dicts, sets, tuples, heapq, deque, and their time complexities.",
        "difficulty": "medium",
        "importance": "high",
        "objectives": [
            "Explain the time complexity of list append vs insert",
            "Implement a hash table from scratch",
            "Choose the right data structure for a given problem",
            "Explain how Python dicts are implemented (hash table + open addressing)",
            "Use heapq for priority queues",
        ],
        "misconceptions": [
            {"name": "List insert is O(1)", "description": "Believing list.insert(0, x) is constant time. It's O(n) because all elements must shift."},
            {"name": "Dicts preserve order always", "description": "While Python 3.7+ dicts preserve insertion order, relying on this for algorithm correctness is risky in interviews."},
        ],
    },
    {
        "slug": "oop-python",
        "name": "Object-Oriented Programming",
        "description": "Classes, inheritance, dunder methods, descriptors, metaclasses, and design patterns in Python.",
        "difficulty": "medium",
        "importance": "high",
        "objectives": [
            "Implement __init__, __repr__, __eq__, __hash__ correctly",
            "Explain MRO (Method Resolution Order) in multiple inheritance",
            "Use @property, @staticmethod, @classmethod appropriately",
            "Implement a context manager using __enter__ and __exit__",
            "Explain the difference between __new__ and __init__",
        ],
        "misconceptions": [
            {"name": "super() always calls the parent", "description": "super() follows MRO, which may not be the direct parent in multiple inheritance."},
            {"name": "@property is just a getter", "description": "@property creates a managed attribute with getter, setter, and deleter — not just a simple getter."},
        ],
    },
    {
        "slug": "algorithms",
        "name": "Algorithms",
        "description": "Sorting, searching, dynamic programming, graph traversal, and complexity analysis.",
        "difficulty": "hard",
        "importance": "high",
        "objectives": [
            "Implement binary search on a sorted array",
            "Explain when to use BFS vs DFS",
            "Solve a basic dynamic programming problem (e.g., fibonacci, knapsack)",
            "Analyze time and space complexity of an algorithm",
            "Implement merge sort and explain why it's O(n log n)",
        ],
        "misconceptions": [
            {"name": "Binary search works on any array", "description": "Binary search requires a SORTED array. Using it on unsorted data gives wrong results."},
            {"name": "DP is always faster than recursion", "description": "DP eliminates redundant computation but has space overhead. Memoized recursion can be equally efficient."},
        ],
    },
    {
        "slug": "python-internals",
        "name": "Python Internals",
        "description": "GIL, memory management, garbage collection, reference counting, and CPython implementation details.",
        "difficulty": "hard",
        "importance": "medium",
        "objectives": [
            "Explain the GIL and its impact on multi-threaded Python",
            "Describe Python's reference counting + cyclic GC",
            "Explain the difference between is and ==",
            "Describe how Python handles integer caching (-5 to 256)",
            "Explain what __slots__ does and when to use it",
        ],
        "misconceptions": [
            {"name": "Threads speed up CPU-bound Python", "description": "Due to the GIL, threads don't speed up CPU-bound tasks in CPython. Use multiprocessing instead."},
            {"name": "is and == are the same", "description": "is checks identity (same object in memory), == checks equality (same value). They can give different results."},
        ],
    },
    {
        "slug": "system-design",
        "name": "System Design",
        "description": "Scalability, caching, load balancing, databases, and API design for Python backend systems.",
        "difficulty": "hard",
        "importance": "medium",
        "objectives": [
            "Design a URL shortener with 1B URLs",
            "Explain horizontal vs vertical scaling",
            "Choose between SQL and NoSQL for a given use case",
            "Design a rate limiter using Redis",
            "Explain eventual consistency vs strong consistency",
        ],
        "misconceptions": [
            {"name": "NoSQL is always faster", "description": "NoSQL can be faster for specific access patterns but lacks joins and transactions. Choose based on requirements."},
        ],
    },
]

QUESTION_TEMPLATES = [
    {
        "code": "LIST-INSERT-COMPLEXITY",
        "title": "List Insert Time Complexity",
        "question_type": "multiple_choice",
        "difficulty_estimate": 0.3,
        "prompt_template": "What is the time complexity of inserting an element at the BEGINNING of a Python list of size n?",
        "choices": ["O(1)", "O(log n)", "O(n)", "O(n log n)"],
        "correct_answer": "O(n)",
        "explanation": "Inserting at the beginning of a list requires shifting all existing elements by one position. This is an O(n) operation. If you need frequent insertions at the front, use collections.deque which provides O(1) appendleft/popleft.",
        "concepts": ["data-structures"],
        "distractors": ["Common mistake: thinking list insert is O(1) because append is O(1)"],
    },
    {
        "code": "DICT-IMPLEMENTATION",
        "title": "Python Dict Implementation",
        "question_type": "multiple_choice",
        "difficulty_estimate": 0.5,
        "prompt_template": "How are Python dictionaries implemented internally (CPython 3.6+)?",
        "choices": ["Binary search tree", "Hash table with open addressing", "Linked list", "B-tree"],
        "correct_answer": "Hash table with open addressing",
        "explanation": "Python dicts use a hash table with open addressing. Since Python 3.6, they use a compact representation that separates the hash table entries from the actual key-value pairs, reducing memory usage and preserving insertion order.",
        "concepts": ["data-structures", "python-internals"],
        "distractors": ["Some think dicts use BSTs — they don't, BSTs would give O(log n) lookups instead of O(1)"],
    },
    {
        "code": "GIL-IMPACT",
        "title": "GIL Impact on Threading",
        "question_type": "multiple_choice",
        "difficulty_estimate": 0.6,
        "prompt_template": "What is the primary impact of the GIL (Global Interpreter Lock) on multi-threaded Python programs?",
        "choices": [
            "It prevents memory leaks",
            "It limits CPU-bound threads to running one at a time",
            "It improves I/O performance",
            "It enables true parallelism",
        ],
        "correct_answer": "It limits CPU-bound threads to running one at a time",
        "explanation": "The GIL ensures only one thread executes Python bytecode at a time. This means CPU-bound multi-threaded programs don't benefit from multiple cores. I/O-bound programs can still benefit from threading because the GIL is released during I/O operations. Use multiprocessing for CPU-bound parallelism.",
        "concepts": ["python-internals"],
        "distractors": ["Common confusion: thinking GIL affects I/O-bound programs the same as CPU-bound"],
    },
    {
        "code": "MRO-MULTIPLE-INHERITANCE",
        "title": "Method Resolution Order",
        "question_type": "multiple_choice",
        "difficulty_estimate": 0.7,
        "prompt_template": "In Python, what does MRO (Method Resolution Order) determine?",
        "choices": [
            "The order in which methods are defined in a class",
            "The order in which base classes are searched for a method",
            "The order in which instance variables are initialized",
            "The order in which decorators are applied",
        ],
        "correct_answer": "The order in which base classes are searched for a method",
        "explanation": "MRO determines the order in which base classes are searched when looking for a method or attribute. Python uses C3 linearization algorithm. You can view it with ClassName.__mro__ or ClassName.mro(). This is crucial for understanding diamond inheritance patterns.",
        "concepts": ["oop-python"],
        "distractors": ["Some think MRO is about variable initialization order — it's specifically about method/attribute lookup"],
    },
    {
        "code": "BINARY-SEARCH-REQUIREMENT",
        "title": "Binary Search Requirement",
        "question_type": "multiple_choice",
        "difficulty_estimate": 0.4,
        "prompt_template": "What is the key requirement for binary search to work correctly?",
        "choices": [
            "The array must be sorted",
            "The array must have even length",
            "The array must contain unique elements",
            "The array must be a list (not a tuple)",
        ],
        "correct_answer": "The array must be sorted",
        "explanation": "Binary search requires a SORTED array. It works by repeatedly dividing the search interval in half. If the array isn't sorted, the algorithm will compare against wrong elements and may skip the target entirely. Time complexity: O(log n).",
        "concepts": ["algorithms"],
        "distractors": ["Common mistake: thinking binary search works on any array"],
    },
    {
        "code": "CONTEXT-MANAGER",
        "title": "Context Manager Implementation",
        "question_type": "multiple_choice",
        "difficulty_estimate": 0.6,
        "prompt_template": "Which dunder methods must a class implement to be used as a context manager (with statement)?",
        "choices": [
            "__enter__ and __exit__",
            "__init__ and __del__",
            "__open__ and __close__",
            "__start__ and __stop__",
        ],
        "correct_answer": "__enter__ and __exit__",
        "explanation": "A context manager must implement __enter__ (called when entering the with block, return value is assigned to the as variable) and __exit__ (called when leaving the with block, receives exception info if an exception occurred). You can also use @contextmanager decorator from contextlib for a simpler approach using a generator.",
        "concepts": ["oop-python"],
        "distractors": ["Some think __init__/__del__ — these are constructor/destructor, not context manager methods"],
    },
    {
        "code": "IS-VS-EQ",
        "title": "is vs == in Python",
        "question_type": "multiple_choice",
        "difficulty_estimate": 0.5,
        "prompt_template": "What is the difference between 'is' and '==' in Python?",
        "choices": [
            "They are identical",
            "'is' checks identity, '==' checks equality",
            "'is' checks equality, '==' checks identity",
            "'is' is for strings, '==' is for numbers",
        ],
        "correct_answer": "'is' checks identity, '==' checks equality",
        "explanation": "'is' checks if two references point to the same object in memory (identity). '==' checks if two objects have the same value (equality). For example: a = [1,2]; b = [1,2]; a == b is True (same values) but a is b is False (different objects). Note: Python caches small integers (-5 to 256), so 1 is 1 is True, but this is an implementation detail.",
        "concepts": ["python-internals"],
        "distractors": ["Common confusion: thinking they're interchangeable"],
    },
    {
        "code": "DECORATOR-EXECUTION",
        "title": "Decorator Execution Order",
        "question_type": "multiple_choice",
        "difficulty_estimate": 0.7,
        "prompt_template": "If a function has decorators @A then @B (in that order, A on top), which executes first when the function is called?",
        "choices": [
            "A executes first",
            "B executes first",
            "They execute simultaneously",
            "Only A executes, B is ignored",
        ],
        "correct_answer": "B executes first",
        "explanation": "Decorators are applied bottom-up but the resulting wrapper executes top-down. @A on top of @B means: first B wraps the function, then A wraps B's wrapper. When called, A's wrapper runs first, which may call B's wrapper, which calls the original function. Think of it as nesting: A(B(func)).",
        "concepts": ["oop-python"],
        "distractors": ["Common mistake: thinking top decorator executes first — it's the outermost wrapper"],
    },
    {
        "code": "HEAPQ-OPERATION",
        "title": "heapq Push Complexity",
        "question_type": "multiple_choice",
        "difficulty_estimate": 0.5,
        "prompt_template": "What is the time complexity of heapq.heappush() on a heap of size n?",
        "choices": ["O(1)", "O(log n)", "O(n)", "O(n log n)"],
        "correct_answer": "O(log n)",
        "explanation": "heapq.heappush() has O(log n) time complexity. It adds the element at the end and then 'bubbles up' (sifts up) to maintain the heap invariant. Each comparison/swap is O(1), and the height of the heap is log(n), so total is O(log n). Python's heapq implements a min-heap.",
        "concepts": ["data-structures", "algorithms"],
        "distractors": ["Some think it's O(n) — that's heappop's worst case for the list, but the heap operation itself is O(log n)"],
    },
    {
        "code": "SLOTS-BENEFIT",
        "title": "__slots__ Purpose",
        "question_type": "multiple_choice",
        "difficulty_estimate": 0.7,
        "prompt_template": "What is the primary benefit of using __slots__ in a Python class?",
        "choices": [
            "It makes attributes private",
            "It reduces memory usage by preventing __dict__ creation",
            "It enables multiple inheritance",
            "It speeds up method calls",
        ],
        "correct_answer": "It reduces memory usage by preventing __dict__ creation",
        "explanation": "__slots__ defines a fixed set of attributes for a class, preventing the creation of __dict__ (the per-instance dictionary that normally stores attributes). This significantly reduces memory usage (often 40-50%) for classes with many instances. Trade-off: you can't add arbitrary attributes not in __slots__.",
        "concepts": ["python-internals", "oop-python"],
        "distractors": ["Common misconception: thinking __slots__ makes attributes private — it doesn't, use name mangling (__prefix) for that"],
    },
]


async def seed_content():
    """Seed Python interview content into the database."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url)

    # Create schemas first
    async with engine.begin() as conn:
        schemas = ["identity", "content", "learning", "assessment", "mastery", "scheduling", "administration", "analytics", "billing", "infrastructure"]
        for schema in schemas:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        # Check if already seeded
        existing = await session.execute(
            select(SubjectModel).where(SubjectModel.code == SUBJECT["code"])
        )
        if existing.scalar_one_or_none():
            print("Content already seeded. Skipping.")
            await engine.dispose()
            return

        # Get the first user as author
        user_result = await session.execute(select(UserModel).limit(1))
        author = user_result.scalar_one_or_none()
        author_id = author.id if author else uuid4()
        tenant_id = uuid4()  # Default tenant

        print(f"Seeding content (author: {author_id})...")

        # 1. Create subject
        subject = SubjectModel(
            id=uuid4(),
            tenant_id=tenant_id,
            code=SUBJECT["code"],
            name=SUBJECT["name"],
            slug=SUBJECT["slug"],
            description=SUBJECT["description"],
            status="published",
            published_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )
        session.add(subject)
        await session.flush()
        print(f"  ✅ Subject: {subject.name}")

        # 2. Create concepts
        concept_map = {}  # slug → model
        for c_data in CONCEPTS:
            concept = ConceptModel(
                id=uuid4(),
                subject_id=subject.id,
                slug=c_data["slug"],
                name=c_data["name"],
                description=c_data["description"],
                difficulty=c_data["difficulty"],
                importance=c_data["importance"],
                status="published",
                published_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            )
            session.add(concept)
            await session.flush()
            concept_map[c_data["slug"]] = concept
            print(f"  ✅ Concept: {concept.name}")

            # 3. Create learning objectives
            for obj_text in c_data.get("objectives", []):
                obj = LearningObjectiveModel(
                    id=uuid4(),
                    concept_id=concept.id,
                    statement=obj_text,
                    status="published",
                )
                session.add(obj)
            await session.flush()
            print(f"    → {len(c_data.get('objectives', []))} objectives")

            # 4. Create misconceptions
            for m_data in c_data.get("misconceptions", []):
                mis = MisconceptionModel(
                    id=uuid4(),
                    concept_id=concept.id,
                    name=m_data["name"],
                    description=m_data["description"],
                    status="published",
                )
                session.add(mis)
            await session.flush()
            print(f"    → {len(c_data.get('misconceptions', []))} misconceptions")

        # 5. Create question templates
        for qt_data in QUESTION_TEMPLATES:
            template = QuestionTemplateModel(
                id=uuid4(),
                subject_id=subject.id,
                code=qt_data["code"],
                question_type=qt_data["question_type"],
                status="published",
                published_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            )
            session.add(template)
            await session.flush()

            # Create template version
            version = TemplateVersionModel(
                id=uuid4(),
                template_id=template.id,
                version_number=1,
                parameter_schema={},
                prompt_template={"text": qt_data["prompt_template"]},
                correct_answer_generator={"value": qt_data["correct_answer"]},
                distractor_generator={"items": qt_data.get("distractors", [])} if qt_data.get("distractors") else None,
                explanation_template={"text": qt_data.get("explanation", "")},
                difficulty_estimate=qt_data.get("difficulty_estimate", "medium"),
                published_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            )
            session.add(version)
            await session.flush()

            # Create template-concept mappings
            for concept_slug in qt_data.get("concepts", []):
                concept = concept_map.get(concept_slug)
                if concept:
                    tc = TemplateConceptModel(
                        id=uuid4(),
                        template_version_id=version.id,
                        concept_id=concept.id,
                    )
                    session.add(tc)

            # Create explanation
            explanation = ExplanationModel(
                id=uuid4(),
                template_version_id=version.id,
                outcome_key="correct",
                content=qt_data.get("explanation", ""),
            )
            session.add(explanation)
            await session.flush()
            print(f"  ✅ Template: {template.code}")

        await session.commit()
        print(f"\n✅ Seed complete! Created:")
        print(f"   - 1 subject: {SUBJECT['name']}")
        print(f"   - {len(CONCEPTS)} concepts")
        print(f"   - {sum(len(c.get('objectives', [])) for c in CONCEPTS)} learning objectives")
        print(f"   - {sum(len(c.get('misconceptions', [])) for c in CONCEPTS)} misconceptions")
        print(f"   - {len(QUESTION_TEMPLATES)} question templates (with versions + explanations)")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_content())

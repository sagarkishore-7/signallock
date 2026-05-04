"""Synthetic profile generation for Phase 1 development."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass

from .schemas import Platform, PublicProfile, RoleSeniority


FIRST_NAMES = [
    "Avery",
    "Jordan",
    "Priya",
    "Sofia",
    "Marcus",
    "Elena",
    "Daniel",
    "Rina",
    "Leo",
    "Nina",
]

LAST_NAMES = [
    "Patel",
    "Khan",
    "Johnson",
    "Chen",
    "Garcia",
    "Singh",
    "Morgan",
    "Kim",
    "Brown",
    "Hughes",
]

LOCATIONS = [
    "Austin",
    "Berlin",
    "Boston",
    "Chicago",
    "London",
    "New York",
    "San Francisco",
    "Singapore",
]

INTERESTS = [
    "cycling",
    "hiking",
    "machine learning",
    "photography",
    "running",
    "security research",
    "travel",
    "writing",
]

EDUCATION = [
    "Georgia Tech",
    "MIT",
    "Stanford University",
    "University of Texas",
    "University of Washington",
]

EMAIL_FORMATS = [
    "first.last",
    "first_last",
    "flast",
    "firstlast",
]


@dataclass(frozen=True)
class TitleTemplate:
    """Title metadata used to generate realistic synthetic profiles."""

    title: str
    department: str
    seniority: RoleSeniority


TITLE_TEMPLATES = [
    TitleTemplate("Security Engineer", "Security", RoleSeniority.INDIVIDUAL_CONTRIBUTOR),
    TitleTemplate("Software Engineer", "Engineering", RoleSeniority.INDIVIDUAL_CONTRIBUTOR),
    TitleTemplate("Product Manager", "Product", RoleSeniority.MANAGER),
    TitleTemplate("Engineering Manager", "Engineering", RoleSeniority.MANAGER),
    TitleTemplate("Director of Security", "Security", RoleSeniority.DIRECTOR),
    TitleTemplate("Director of Finance", "Finance", RoleSeniority.DIRECTOR),
    TitleTemplate("VP of Engineering", "Engineering", RoleSeniority.VP),
    TitleTemplate("VP of Product", "Product", RoleSeniority.VP),
    TitleTemplate("Chief Financial Officer", "Finance", RoleSeniority.C_SUITE),
    TitleTemplate("Chief Information Security Officer", "Security", RoleSeniority.C_SUITE),
]

PLATFORM_POOL = [
    Platform.LINKEDIN,
    Platform.GITHUB,
    Platform.X,
    Platform.PERSONAL_WEBSITE,
    Platform.SPEAKER_BIO,
    Platform.UNIVERSITY_PROFILE,
    Platform.COMPANY_DIRECTORY,
]


def _build_username(first_name: str, last_name: str, rng: random.Random) -> str:
    """Create a realistic-looking username seed."""
    options = [
        f"{first_name.lower()}.{last_name.lower()}",
        f"{first_name[0].lower()}{last_name.lower()}",
        f"{first_name.lower()}{last_name.lower()}",
        f"{first_name.lower()}_{last_name.lower()}",
    ]
    return rng.choice(options)


def _build_bio(title: str, organization: str, location: str, interests: list[str]) -> str:
    """Generate a short public-facing bio string."""
    selected = ", ".join(interests[:2])
    return (
        f"{title} at {organization}. Based in {location}. "
        f"Interests include {selected}."
    )


def generate_synthetic_profiles(
    count: int,
    organization: str = "ExampleCorp",
    seed: int | None = None,
) -> list[PublicProfile]:
    """Generate a reproducible batch of synthetic public profiles."""
    if count <= 0:
        raise ValueError("count must be positive")

    rng = random.Random(seed)
    profiles: list[PublicProfile] = []

    for index in range(1, count + 1):
        first_name = rng.choice(FIRST_NAMES)
        last_name = rng.choice(LAST_NAMES)
        title_template = rng.choice(TITLE_TEMPLATES)
        preferred_name = first_name if rng.random() < 0.6 else None
        location = rng.choice(LOCATIONS)
        education = rng.choice(EDUCATION)
        interests = rng.sample(INTERESTS, k=2)
        username = _build_username(first_name, last_name, rng)
        platform_count = rng.randint(1, 4)
        platforms = rng.sample(PLATFORM_POOL, k=platform_count)
        tenure_start_year = rng.randint(2014, 2024)

        profile = PublicProfile(
            employee_id=f"EMP{index:04d}",
            full_name=f"{first_name} {last_name}",
            title=title_template.title,
            department=title_template.department,
            organization=organization,
            role_seniority=title_template.seniority,
            email_format=rng.choice(EMAIL_FORMATS),
            location=location,
            tenure_start_year=tenure_start_year,
            platforms=platforms,
            public_usernames=[username],
            interests=interests,
            preferred_name=preferred_name,
            education=education,
            bio=_build_bio(title_template.title, organization, location, interests),
        )
        profiles.append(profile)

    return profiles


def profiles_to_json(profiles: list[PublicProfile], pretty: bool = False) -> str:
    """Serialize a profile batch as JSON."""
    payload = [profile.to_dict() for profile in profiles]
    if pretty:
        return json.dumps(payload, indent=2)
    return json.dumps(payload)

# SignalLock Feature Schema

## Goal

This document defines the first-pass schema for public-profile data, normalized attribute vectors, and policy-relevant metadata. The schema is intentionally conservative and designed for synthetic or authorized data first.

## Design Principles

- keep exposure features separate from password-conditioned features
- prefer normalized tokens over raw free text
- support audit mode and interactive mode with the same base schemas
- minimize fields that could encourage over-collection

## Core Entities

### 1. `PublicProfile`

Represents an organization-approved or synthetic public-facing identity record.

Required fields:

- `employee_id`
- `full_name`
- `title`
- `department`
- `organization`
- `role_seniority`
- `email_format`
- `location`
- `tenure_start_year`
- `platforms`
- `public_usernames`
- `interests`

Optional fields:

- `preferred_name`
- `education`
- `bio`

## Enumerations

### `RoleSeniority`

- `INDIVIDUAL_CONTRIBUTOR`
- `MANAGER`
- `DIRECTOR`
- `VP`
- `C_SUITE`

### `Platform`

- `LINKEDIN`
- `GITHUB`
- `X`
- `PERSONAL_WEBSITE`
- `SPEAKER_BIO`
- `UNIVERSITY_PROFILE`
- `COMPANY_DIRECTORY`

### `RiskBand`

- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL`

## Exposure-Oriented Fields

These features should influence exposure scoring, not password scoring by themselves.

- `role_seniority`
- `department`
- `platform_count`
- `platform_diversity`
- `title_visibility`
- `public_year_markers`
- `organization_visibility`
- `bio_richness`
- `username_count`

## Password-Conditioned Fields

These features are computed only when a candidate password is present.

- overlap with full-name tokens
- overlap with preferred-name tokens
- overlap with public usernames
- overlap with organization tokens
- overlap with year markers
- overlap with location tokens
- overlap with interests
- presence of common contextual structures such as name-plus-year or org-plus-symbol

## Token Categories

The first implementation should normalize these token sets:

### Name Tokens

- first name
- last name
- preferred name
- common shortened forms when explicitly available

### Organization Tokens

- organization name words
- department words
- title keywords

### Temporal Tokens

- tenure start year
- graduation year if available
- other explicitly public year markers

### Identity Tokens

- usernames
- email local-part patterns

### Context Tokens

- city or location words
- interest or hobby keywords
- education institution tokens

## Minimal Validation Rules

- `employee_id` must be non-empty
- `full_name` must contain visible characters
- `tenure_start_year` must be between `1970` and `2100`
- `platforms` may be empty only in explicitly low-exposure synthetic cases
- `public_usernames` should be unique after normalization
- `interests` should be deduplicated after normalization

## Normalization Rules

- trim whitespace
- store token lists in lowercase for feature extraction
- remove empty list items
- keep the original display form only where needed for user-facing output

## Phase 1 Synthetic Data Coverage

Each synthetic profile should vary along:

- role seniority
- department
- organization type
- city / geography
- number of public platforms
- username style
- year-marker presence
- interest profile

This creates enough structured variation to start testing exposure and password-conditioning logic.

## Future Schema Extensions

Possible later additions:

- richer relationship graphs
- organization-specific naming conventions
- language or locale metadata
- explanation objects
- policy configuration objects

Those should be added only after the core profile schema is stable.

# Dataset Evidence

Status: in_review (Section 8)
Class: evidence
Last updated: 2026-02-12
Owner: Evidence Review
Depends on: `../README.md`, `../../02-domain/DATA_MODEL/CANONICAL_DATASETS.md`
Replaces: dataset artifacts in source corpus

## Purpose

Store raw and curated dataset artifacts used for protocol validation, modeling, and replay.

## Scope

1. reference captures,
2. sample sets,
3. derived benchmark datasets.

## Canonical Decisions

1. Dataset files remain immutable evidence.
2. Canonical dataset definitions live in Domain section; this section stores artifacts and provenance.
3. Large artifacts should include checksum metadata in accompanying catalog docs.

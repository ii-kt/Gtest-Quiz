from __future__ import annotations

import hashlib
import os
from typing import Dict, Tuple


ADAPTIVE_POLICY = "adaptive_mastery_v2"
CHAPTER_BALANCED_POLICY = "chapter_balanced_v1"
RANDOM_POLICY = "random_baseline_v1"

POLICY_VARIANTS: Tuple[str, ...] = (
    ADAPTIVE_POLICY,
    CHAPTER_BALANCED_POLICY,
    RANDOM_POLICY,
)

EXPERIMENT_NAME = "learning_policy_v1"


def normalize_policy_variant(value: str | None) -> str:
    if value in POLICY_VARIANTS:
        return str(value)
    return ADAPTIVE_POLICY


def active_policy_experiment() -> str:
    return os.getenv("GTEST_POLICY_EXPERIMENT", "").strip()


def assign_policy_variant(user_id: int, account_key: str) -> str:
    if active_policy_experiment() != EXPERIMENT_NAME:
        return ADAPTIVE_POLICY
    seed = f"{EXPERIMENT_NAME}:{user_id}:{account_key}".encode("utf-8")
    bucket = int(hashlib.sha256(seed).hexdigest()[:8], 16) % 100
    if bucket < 80:
        return ADAPTIVE_POLICY
    if bucket < 90:
        return CHAPTER_BALANCED_POLICY
    return RANDOM_POLICY


def experiment_summary() -> Dict[str, object]:
    return {
        "name": EXPERIMENT_NAME,
        "active": active_policy_experiment() == EXPERIMENT_NAME,
        "variants": list(POLICY_VARIANTS),
        "default": ADAPTIVE_POLICY,
    }

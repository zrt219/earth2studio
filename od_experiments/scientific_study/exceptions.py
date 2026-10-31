# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Custom exception hierarchy for anti-leakage and pipeline integrity verification.

Defines the authoritative error types required to enforce temporal separation,
cryptographic provenance, synthetic substitution prevention, chronological correctness,
and truthful model attribution under Project OD-EARTH2-001 / EO-OBSCURA.
"""

from __future__ import annotations


class AntiLeakageError(Exception):
    """Base exception for all anti-leakage and pipeline integrity violations."""

    pass


class TargetLeakageError(AntiLeakageError):
    """Raised when forecast output exhibits functional dependence on future verification truth."""

    pass


class ForbiddenFutureAccessError(AntiLeakageError, PermissionError):
    """Raised when forecast generation stage attempts to access data at or beyond valid time (t >= t_valid)."""

    pass


class SyntheticSubstitutionError(AntiLeakageError, ValueError):
    """Raised when a benchmark run contains synthetic interpolation, random residuals, or mock data."""

    pass


class ProvenanceIntegrityError(AntiLeakageError, ValueError):
    """Raised when artifact SHA-256 digests do not match sealed run_manifest.json."""

    pass


class ChronologyError(AntiLeakageError, ValueError):
    """Raised when initialization time, lead time, and verification valid time are misaligned or cross-epoch."""

    pass


class ModelIdentityMismatchError(AntiLeakageError, ValueError):
    """Raised when benchmark metadata misrepresents model architecture (e.g. labeling Persistence as FourCastNet)."""

    pass

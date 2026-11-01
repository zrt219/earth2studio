# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye, Origin Datum (https://origindatum.space, contact@origindatum.space)
# SPDX-License-Identifier: Apache-2.0

"""Stage A: Genuine Forecast Stage (Decoupled & Anti-Leakage Protected).

Performs forward prognostic forecast inference using only atmospheric initial
conditions at t0. Operates under strict temporal isolation: zero access to
verifying analysis at t >= t0 + Delta t.

Enforces runtime & AST anti-leakage guardrails:
1. Signature Isolation: Forecast generation functions and models must never
   accept ground-truth target tensors (`y_truth`, `target`, `verification_data`).
2. AST & Call-Stack Isolation: Forecast callables and active stack frames are
   inspected for forbidden target variables and linear target-shrinkage formulas.

Attribution: Zhane Daye, Origin Datum (https://origindatum.space, contact@origindatum.space)
"""

from __future__ import annotations

import ast
import datetime
import functools
import inspect
import json
import textwrap
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

import numpy as np

from od_experiments.scientific_study.exceptions import TargetLeakageError

F = TypeVar("F", bound=Callable[..., Any])

FORBIDDEN_TARGET_PARAMS: frozenset[str] = frozenset(
    {
        "y_truth",
        "target",
        "verification_data",
        "ground_truth",
        "truth_t2m",
        "truth_array",
        "verifying_truth",
        "future_truth",
    }
)

FORBIDDEN_AST_IDENTIFIERS: frozenset[str] = frozenset(
    {
        "y_truth",
        "truth_t2m",
        "verification_data",
        "verifying_truth",
        "future_truth",
        "neural_skill_factor",
        "atmospheric_delta",
    }
)


def inspect_callable_for_leakage(
    fn_or_obj: Any,
    *,
    forbid_verification_truth_param: bool = True,
) -> dict[str, Any]:
    """Inspect a callable or model object's signature and AST for target leakage.

    Raises `TargetLeakageError` if the callable accepts forbidden target parameters
    (`y_truth`, `target`, `verification_data`, etc.) or if its AST references
    ground-truth target identifiers or linear target-shrinkage formulas
    (e.g., `0.72 * (y_truth - x_0)`).
    """
    target_fn = fn_or_obj
    if not inspect.isfunction(target_fn) and not inspect.ismethod(target_fn):
        if hasattr(fn_or_obj, "forward") and callable(fn_or_obj.forward):
            target_fn = fn_or_obj.forward
        elif callable(fn_or_obj):
            target_fn = fn_or_obj.__call__

    forbidden_params = set(FORBIDDEN_TARGET_PARAMS)
    if forbid_verification_truth_param:
        forbidden_params.add("verification_truth")

    # 1. Signature Inspection
    try:
        sig = inspect.signature(target_fn)
    except (ValueError, TypeError):
        sig = None

    if sig is not None:
        param_names = set(sig.parameters.keys())
        leaked_params = param_names.intersection(forbidden_params)
        if leaked_params:
            raise TargetLeakageError(
                f"Signature isolation violation: forecast callable '{getattr(target_fn, '__name__', repr(target_fn))}' "
                f"accepts forbidden ground-truth target parameter(s): {sorted(leaked_params)}"
            )
    else:
        param_names = set()

    # 2. Closure / Bound Attribute Inspection on Model Instance
    for obj_candidate in (fn_or_obj, target_fn):
        if hasattr(obj_candidate, "__dict__"):
            obj_attrs = set(vars(obj_candidate).keys())
            leaked_attrs = obj_attrs.intersection(
                forbidden_params | FORBIDDEN_AST_IDENTIFIERS
            )
            if leaked_attrs:
                raise TargetLeakageError(
                    f"Object attribute isolation violation: forecast model stores forbidden "
                    f"ground-truth attribute(s): {sorted(leaked_attrs)}"
                )
        closure_vars = None
        try:
            closure_vars = inspect.getclosurevars(obj_candidate)
        except (TypeError, ValueError):
            closure_vars = None
        if closure_vars is not None:
            leaked_nonlocals = set(closure_vars.nonlocals.keys()).intersection(
                forbidden_params | FORBIDDEN_AST_IDENTIFIERS
            )
            if leaked_nonlocals:
                raise TargetLeakageError(
                    f"Closure isolation violation: forecast callable captures forbidden "
                    f"ground-truth nonlocal(s): {sorted(leaked_nonlocals)}"
                )
            leaked_globals = set(closure_vars.globals.keys()).intersection(
                forbidden_params | FORBIDDEN_AST_IDENTIFIERS
            )
            if leaked_globals:
                raise TargetLeakageError(
                    f"Global scope isolation violation: forecast callable references forbidden "
                    f"ground-truth global(s): {sorted(leaked_globals)}"
                )

    # 3. AST Source Inspection
    ast_checked = False
    try:
        src = textwrap.dedent(inspect.getsource(target_fn))
        tree = ast.parse(src)
        ast_checked = True
    except (OSError, TypeError, IndentationError, SyntaxError):
        tree = None

    if tree is not None:
        forbidden_ast_names = forbidden_params | FORBIDDEN_AST_IDENTIFIERS
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden_ast_names:
                raise TargetLeakageError(
                    f"AST isolation violation: forecast callable references forbidden "
                    f"ground-truth identifier '{node.id}'"
                )
            if isinstance(node, ast.Attribute) and node.attr in forbidden_ast_names:
                raise TargetLeakageError(
                    f"AST isolation violation: forecast callable accesses forbidden "
                    f"ground-truth attribute '{node.attr}'"
                )
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and (
                    node.value in forbidden_ast_names
                    or "verifying_truth" in node.value.lower()
                )
            ):
                raise TargetLeakageError(
                    f"AST isolation violation: forecast callable contains forbidden "
                    f"ground-truth string literal '{node.value}'"
                )
            # Detect linear shrinkage pattern: alpha * (truth - x0) or (truth - pers) * 0.72
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
                left_src = ast.unparse(node.left) if hasattr(ast, "unparse") else ""
                right_src = ast.unparse(node.right) if hasattr(ast, "unparse") else ""
                combined = f"{left_src} * {right_src}".lower()
                if any(
                    tok in combined
                    for tok in ("truth", "y_truth", "target", "verification_data")
                ):
                    raise TargetLeakageError(
                        f"AST isolation violation: linear target-shrinkage expression detected in forecast callable: '{combined}'"
                    )

    return {
        "signature_verified": True,
        "ast_verified": ast_checked,
        "parameters": sorted(param_names),
    }


def enforce_call_stack_isolation(
    *,
    check_caller_locals: bool = False,
    max_depth: int = 4,
) -> None:
    """Inspect active call stack to ensure forecast generation does not access target truth.

    Walks active stack frames and raises `TargetLeakageError` if a forecast generation
    frame declares or accesses forbidden ground-truth target parameters (`y_truth`,
    `target`, `verification_data`).
    """
    stack = inspect.stack()
    try:
        for depth, frame_info in enumerate(stack[1 : max_depth + 1], start=1):
            frame = frame_info.frame
            code = frame.f_code
            arg_count = (
                code.co_argcount
                + getattr(code, "co_kwonlyargcount", 0)
                + getattr(code, "co_posonlyargcount", 0)
            )
            arg_names = set(code.co_varnames[:arg_count])
            leaked_args = arg_names.intersection(FORBIDDEN_TARGET_PARAMS)
            if leaked_args:
                raise TargetLeakageError(
                    f"Call-stack signature isolation violation in frame '{code.co_name}' (depth={depth}): "
                    f"accepts forbidden target parameter(s) {sorted(leaked_args)}"
                )
            if check_caller_locals:
                leaked_locals = set(frame.f_locals.keys()).intersection(
                    FORBIDDEN_TARGET_PARAMS
                )
                if leaked_locals:
                    raise TargetLeakageError(
                        f"Call-stack variable isolation violation in frame '{code.co_name}' (depth={depth}): "
                        f"frame locals contain forbidden target tensor(s) {sorted(leaked_locals)}"
                    )
    finally:
        del stack


def anti_leakage_forecast_guard(fn: F) -> F:
    """Decorator enforcing strict signature, AST, and call-stack isolation on forecast functions."""
    inspect_callable_for_leakage(fn, forbid_verification_truth_param=True)

    @functools.wraps(fn)
    def _wrapped(*args: Any, **kwargs: Any) -> Any:
        leaked_kw = set(kwargs.keys()).intersection(
            FORBIDDEN_TARGET_PARAMS | {"verification_truth"}
        )
        if leaked_kw:
            raise TargetLeakageError(
                f"Runtime isolation violation: forecast function '{fn.__name__}' called with "
                f"forbidden ground-truth keyword argument(s): {sorted(leaked_kw)}"
            )
        inspect_callable_for_leakage(fn, forbid_verification_truth_param=True)
        enforce_call_stack_isolation(check_caller_locals=False, max_depth=3)
        return fn(*args, **kwargs)

    return _wrapped  # type: ignore[return-value]


def run_forecast(
    init_time: datetime.datetime,
    lead_time_hours: int = 24,
    model_family: str = "Persistence",
    model: Optional[Any] = None,
    checkpoint: Optional[str] = "identity",
    checkpoint_sha256: Optional[str] = None,
    initial_condition: Optional[np.ndarray] = None,
    data_source: Optional[Any] = None,
    verification_truth: Optional[np.ndarray] = None,
    output_dir: Path | str = "outputs/scientific_study_verified/forecast",
    variables: list[str] = ["t2m"],
    seed: int = 42,
    **kwargs: Any,
) -> Path:
    """Execute genuine prognostic forecast forward pass without future verification truth.

    Parameters
    ----------
    init_time : datetime.datetime
        Atmospheric initialization timestamp t0.
    lead_time_hours : int, optional
        Forecast lead time in hours (default: 24).
    model_family : str, optional
        Model architecture identifier ('Persistence', 'FourCastNet', etc.).
    model : Optional[Any], optional
        Model instance. If None and model_family == 'Persistence', runs identity.
    checkpoint : Optional[str], optional
        Checkpoint path or 'identity' for persistence baseline.
    checkpoint_sha256 : Optional[str], optional
        Cryptographic digest of model weights.
    initial_condition : Optional[np.ndarray], optional
        Pre-loaded initial state tensor at t0.
    data_source : Optional[Any], optional
        Data retrieval provider. Queried strictly at t0.
    verification_truth : Optional[np.ndarray], optional
        Legacy trap parameter for invariance testing. Strictly nullified and never accessed.
    output_dir : Path | str, optional
        Destination directory for raw forecast arrays.
    variables : list[str], optional
        Meteorological variables to predict.
    seed : int, optional
        Deterministic random seed.
    **kwargs : Any
        Additional keyword arguments. Any ground-truth target argument (`y_truth`,
        `target`, `verification_data`, `ground_truth`) immediately raises `TargetLeakageError`.

    Returns
    -------
    Path
        Path to serialized forecast array file (forecast_t2m.npy).
    """
    # Immediately erase legacy trap parameter so it cannot be read anywhere in this frame
    del verification_truth

    # 0. Runtime Signature, Kwargs & Call-Stack Isolation Guard
    if kwargs:
        leaked_kwargs = set(kwargs.keys()).intersection(FORBIDDEN_TARGET_PARAMS)
        if leaked_kwargs:
            raise TargetLeakageError(
                f"Signature isolation violation: run_forecast rejected forbidden ground-truth "
                f"parameter(s): {sorted(leaked_kwargs)}"
            )
        raise TypeError(
            f"run_forecast() got unexpected keyword argument(s): {sorted(kwargs.keys())}"
        )

    enforce_call_stack_isolation(check_caller_locals=False, max_depth=2)

    if model is not None:
        inspect_callable_for_leakage(model, forbid_verification_truth_param=True)

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    valid_time = init_time + datetime.timedelta(hours=lead_time_hours)

    # 1. Fetch initial condition strictly at t0
    if initial_condition is None:
        if data_source is not None:
            # Strictly queries init_time only!
            initial_condition = data_source(time=init_time, variable=variables)
        else:
            initial_condition = np.full((181, 360), 288.15, dtype=np.float32)

    if not isinstance(initial_condition, np.ndarray):
        initial_condition = np.asarray(initial_condition, dtype=np.float32)

    # 2. Genuine Model Forward Pass
    # Invariant: Output depends ONLY on initial state, model, and seed.
    # Verification truth is NEVER accessed or factored into the forecast.
    if model is not None and hasattr(model, "forward"):
        # Real model inference forward pass
        forecast_array = model.forward(initial_condition)
    elif model is not None and callable(model):
        forecast_array = model(initial_condition)
    elif model_family == "Persistence":
        # Genuine Persistence baseline: identity operator X(t0 + dt) == X(t0)
        forecast_array = initial_condition.copy()
    else:
        raise ValueError(
            f"Model instance or loader required for neural model family '{model_family}'. "
            "Cannot execute uninstantiated model."
        )

    # 3. Serialize Artifacts
    forecast_file = out_path / "forecast_t2m.npy"
    init_file = out_path / "initial_condition.npy"
    np.save(forecast_file, forecast_array)
    np.save(init_file, initial_condition)

    # 4. Write Stage A Metadata
    meta = {
        "init_time": init_time.isoformat(),
        "valid_time": valid_time.isoformat(),
        "lead_time_hours": lead_time_hours,
        "model_family": model_family,
        "checkpoint": checkpoint,
        "checkpoint_sha256": checkpoint_sha256,
        "variables": variables,
        "grid_shape": list(forecast_array.shape),
        "seed": seed,
    }
    (out_path / "forecast_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    return forecast_file

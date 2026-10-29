"""Compatibility access to required fields in the pinned DeepEval version.

DeepEval 4.3.1 declares built-in metric requirements on ``_required_params``.
Keep that internal API dependency here, rather than maintaining our own lists.
Custom GEval metrics still define their own ``evaluation_params``.
"""


def builtin_required_params(metric_class):
    """Copy a built-in metric's requirements without constructing a judge."""
    params = getattr(metric_class, "_required_params", None)
    if not isinstance(params, (list, tuple)):
        raise TypeError(
            f"{metric_class.__name__} does not expose DeepEval required fields. "
            "Check metrics/requirements.py when upgrading DeepEval."
        )
    return list(params)

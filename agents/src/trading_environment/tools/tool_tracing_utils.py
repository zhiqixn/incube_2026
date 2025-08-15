import json
import functools
from opentelemetry.trace import get_current_span, Status, StatusCode
from inspect import signature
from utils.logger import get_logger

logger = get_logger()


def trace_span_info(func):
    """
    Decorator for setting span attributes for function parameters and signature.
    Supports async functions.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        current_span = get_current_span()

        # Log function signature
        try:
            sig = str(signature(func))
            current_span.set_attribute("tool.parameters", sig)
        except Exception:
            current_span.set_attribute("tool.parameters", "Signature unavailable")

        # Log input parameters
        try:
            param_values = dict(signature(func).bind(*args, **kwargs).arguments)
            current_span.set_attribute(
                "input.value", json.dumps(param_values, indent=4)
            )
        except Exception as e:
            logger.error("Error logging input parameters: %s", e)
            current_span.set_attribute("input.value", str(param_values))

        try:
            result = await func(*args, **kwargs)
            current_span.set_attribute("status", "OK")
        except Exception as e:
            current_span.set_attribute("output.value", f"Exception: {e}")
            current_span.set_attribute("status", "ERROR")
            current_span.set_status(Status(StatusCode.ERROR))
            raise
        else:
            try:
                current_span.set_attribute("output.value", str(result))
            except Exception:
                current_span.set_attribute(
                    "output.value", "Output serialization failed"
                )
            return result

    return wrapper

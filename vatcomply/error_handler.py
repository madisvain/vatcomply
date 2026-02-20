"""
Custom error handler middleware for VATcomply API.

Maintains the existing {field: [messages]} error format for backwards compatibility.
"""

import logging

import dpath
import msgspec
from django_bolt.exceptions import RequestValidationError
from django_bolt.middleware_response import MiddlewareResponse

logger = logging.getLogger(__name__)


def _make_json_response(data: dict, status_code: int) -> MiddlewareResponse:
    """Create a MiddlewareResponse with JSON body."""
    body = msgspec.json.encode(data)
    return MiddlewareResponse(
        status_code=status_code,
        headers={"content-type": "application/json"},
        body=body,
    )


class CustomErrorMiddleware:
    """Convert validation errors to {field: [messages]} format and catch unhandled exceptions."""

    def __init__(self, get_response):
        self.get_response = get_response

    async def __call__(self, request):
        try:
            return await self.get_response(request)
        except RequestValidationError as exc:
            return self._handle_validation_error(exc)
        except Exception as exc:
            return self._handle_unexpected_error(exc)

    @staticmethod
    def _handle_validation_error(exc):
        errors = {}
        for error in exc.errors():
            # Filter out body/payload from location path
            fields = tuple(
                f for f in error.get("loc", []) if f not in ["body", "payload"]
            )
            message = error.get("msg", "")

            # Convert path to dpath format
            path = "/".join(str(x) for x in fields)

            # Check if the path already exists
            try:
                current_value = dpath.get(errors, path)
                # If the path exists, ensure it's a list and append the new message
                if not isinstance(current_value, list):
                    dpath.set(errors, path, [current_value])
                dpath.get(errors, path).append(message)
            except KeyError:
                # If the path doesn't exist, create it with a list containing the message
                dpath.new(errors, path, [message])

        return _make_json_response(errors, status_code=422)

    @staticmethod
    def _handle_unexpected_error(exc):
        logger.exception("Unhandled exception in API: %s", exc)
        return _make_json_response({"detail": "Internal server error"}, status_code=500)

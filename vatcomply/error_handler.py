"""
Custom error handler middleware for VATcomply API.

Maintains the existing {field: [messages]} error format for backwards compatibility.
"""

import dpath
from django_bolt.exceptions import RequestValidationError
from django_bolt.responses import JSON


class CustomErrorMiddleware:
    """Convert validation errors to {field: [messages]} format."""

    def __init__(self, get_response):
        self.get_response = get_response

    async def __call__(self, request):
        try:
            return await self.get_response(request)
        except RequestValidationError as exc:
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

            return JSON(errors, status_code=422)

from typing import Tuple, Union

import ujson
from django.http import HttpResponse
from pydantic import ValidationError


def loc_to_dot_sep(loc: Tuple[Union[str, int], ...]) -> str:
    path = ""
    for i, x in enumerate(loc):
        if isinstance(x, str):
            if i > 0:
                path += "."
            path += x
        elif isinstance(x, int):
            path += f"[{x}]"
        else:
            raise TypeError("Unexpected type")
    return path


class UJsonResponse(HttpResponse):
    def __init__(
        self,
        data,
        safe=True,
        **kwargs,
    ):
        # Convert pydantic ValidationError to dict
        if isinstance(data, ValidationError):
            errors = {}
            for error in data.errors():
                errors[loc_to_dot_sep(error["loc"])] = []
                errors[loc_to_dot_sep(error["loc"])].append(error["msg"])
            data = errors

        if safe and not isinstance(data, dict) and not isinstance(data, list):
            raise TypeError(
                "In order to allow non-dict or non-list objects to be serialized set the "
                "safe parameter to False."
            )

        kwargs.setdefault("content_type", "application/json")
        data = ujson.dumps(data, ensure_ascii=False).encode("utf-8")
        super().__init__(content=data, **kwargs)

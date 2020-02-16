from pydantic import PydanticValueError


class AlreadyExistsError(PydanticValueError):
    code = "already_exists"
    msg_template = "User with an email '{email}' already exists"

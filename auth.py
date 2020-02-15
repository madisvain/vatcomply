from starlette.authentication import AuthenticationBackend, AuthCredentials, AuthenticationError, SimpleUser

from settings import TESTING


class TokenAuthenticationBackend(AuthenticationBackend):
    """ https://github.com/encode/django-rest-framework/blob/master/rest_framework/authentication.py#L144
    """

    keyword = "Token"

    async def authenticate(self, request):
        if "authorization" not in request.headers:
            return

        auth = request.headers["authorization"].split()
        if not auth or auth[0].lower() != self.keyword.lower():
            return

        if len(auth) == 1:
            raise AuthenticationError("Invalid token header. No credentials provided.")
        elif len(auth) > 2:
            raise AuthenticationError("Invalid token header. Token string should not contain spaces.")

        # TODO: Implement validation
        return AuthCredentials(["authenticated"]), SimpleUser("username")

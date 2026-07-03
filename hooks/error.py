class _InternalError(Exception):
    def __init__(self, detail: str):
        super().__init__(detail)


class ExternalError(Exception):
    def __init__(self, detail: str):
        super().__init__(detail)


class Overload(_InternalError):
    def __init__(self, detail: str):
        super().__init__(detail)


class ResourceDuplication(_InternalError):
    """
    Custom exception for resource duplication.

    Args:
        message (str): The error message indicating the resource already exists.
    """

    def __init__(self, message: str = "Resource already exists."):
        super().__init__(message)


class ResourceNotFound(_InternalError):
    """
    Custom exception for resource not found.

    Args:
        message (str): The error message indicating the resource does not exist.
    """

    def __init__(self, message: str):
        super().__init__(message)


class BadUserRequest(ExternalError):
    """
    Custom exception for bad user request.

    Args:
        message (str): The error message indicating the request from users is in malform
    """

    def __init__(self, message: str):
        super().__init__(message)


class UnauthorizedAccess(ExternalError):
    """
    Custom exception for unauthorized access

    Args:
        message (str): The error message indicating the request from users is unauthorized to the external api
    """

    def __init__(self, message: str):
        super().__init__(message)


class TooManyRequests(ExternalError):
    """
    Custom exception for too many request

    Args:
        message (str): The error message indicating the request from users exceeded the quota for that API for the user
    """

    def __init__(self, message: str):
        super().__init__(message)


class ForbiddenAccess(ExternalError):
    """
    Custom exception for forbidden access to other resources

    Args:
        message (str): The error message indicating the request from users is forbidden
    """

    def __init__(self, message: str):
        super().__init__(message)

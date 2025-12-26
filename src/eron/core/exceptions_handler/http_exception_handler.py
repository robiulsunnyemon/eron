from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


# Handler for specific HTTP exceptions (e.g., 404, 403, 401)
async def http_exception_handler(_: Request, exc: Exception):
    """
    Global handler for Starlette/FastAPI HTTPExceptions.
    This ensures that all manual 'raise HTTPException' calls
    return a consistent JSON format.
    """

    # Check if the exception is an instance of StarletteHTTPException
    if isinstance(exc, StarletteHTTPException):
        print(f"status:error")
        print(f"message:{exc.detail}")
        print(f"code:{exc.status_code}")

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.detail,
                "code": exc.status_code
            },
        )

    # Fallback for generic internal server errors if they reach this handler
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "fail",
            "message": "An unexpected internal error occurred."
        }
    )
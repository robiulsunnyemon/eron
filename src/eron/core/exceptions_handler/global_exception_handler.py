
from fastapi import Request, status
from fastapi.responses import JSONResponse


# Handler for any unexpected errors
async def global_exception_handler(request: Request, exc: Exception):
    # Accessing app.debug from request.app
    debug_mode = request.app.debug
    print(f"Global Error Captured: {str(exc)}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "fail",
            "message": "An unexpected internal server error occurred. Please contact support.",
            "error_details": str(exc) if debug_mode else None
        },
    )
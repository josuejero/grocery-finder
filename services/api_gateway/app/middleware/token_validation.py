# app/middleware/token_validation.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import traceback
from app.core.utils import decode_token
from app.core.logging import logger

async def token_validation_middleware(request: Request, call_next):
    logger.debug(f"Request path: {request.url.path}")
    logger.debug(f"Request headers: {dict(request.headers)}")
    
    auth_header = request.headers.get('Authorization')
    if auth_header:
        try:
            token = auth_header.split(' ')[1]
            logger.debug(f"Validating token: {token[:20]}...")
            decode_token(token)
        except IndexError:
            logger.error("Token not found in Authorization header")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid authorization header format"}
            )
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )

    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
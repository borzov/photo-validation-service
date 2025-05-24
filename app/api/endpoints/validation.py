from typing import Any
from fastapi import APIRouter, HTTPException, UploadFile, File, status, BackgroundTasks
from fastapi.responses import JSONResponse
import uuid
import cv2
import numpy as np
from datetime import datetime
import os
import time
import asyncio
import magic
import io
from PIL import Image

from app.api.models.validation import ValidationResponse, ValidationResult
from app.db.repositories import ValidationRequestRepository
from app.storage.client import storage_client
from app.core.config import settings
from app.core.exceptions import FileValidationError, StorageError
from app.core.logging import get_logger
from app.worker.tasks import add_processing_task

logger = get_logger(__name__)

router = APIRouter()

def validate_image_file(content: bytes, filename: str) -> None:
    """
    Comprehensive image file validation.
    """
    # Check file extension
    allowed_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif')
    if not filename.lower().endswith(allowed_extensions):
        raise FileValidationError(
            message=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}",
            code="INVALID_FILE_FORMAT"
        )
    
    # Check file size
    if len(content) > settings.MAX_FILE_SIZE_BYTES:
        raise FileValidationError(
            message=f"File size exceeds {settings.MAX_FILE_SIZE_BYTES // 1024} KB limit",
            code="FILE_TOO_LARGE"
        )
    
    # Check minimum size
    if len(content) < 1024:  # Minimum 1KB
        raise FileValidationError(
            message="File is too small to be a valid image",
            code="FILE_TOO_SMALL"
        )
    
    # Check MIME type via python-magic
    try:
        mime_type = magic.from_buffer(content, mime=True)
        allowed_mime_types = [
            'image/jpeg', 'image/jpg', 'image/png', 'image/webp', 
            'image/bmp', 'image/tiff', 'image/x-ms-bmp'
        ]
        if mime_type not in allowed_mime_types:
            logger.warning(f"Unexpected MIME type: {mime_type}, but continuing validation")
    except Exception as e:
        logger.warning(f"Could not determine MIME type: {e}")
    
    # Check image decodability
    try:
        # Check via OpenCV
        nparr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise FileValidationError(
                message="File cannot be decoded as a valid image",
                code="INVALID_IMAGE_DATA"
            )
        
        # Check image dimensions
        height, width = img.shape[:2]
        total_pixels = height * width
        
        if total_pixels > settings.MAX_IMAGE_PIXELS:
            raise FileValidationError(
                message=f"Image is too large: {total_pixels} pixels (max: {settings.MAX_IMAGE_PIXELS})",
                code="IMAGE_TOO_LARGE"
            )
        
        if width < settings.MIN_IMAGE_WIDTH or height < settings.MIN_IMAGE_HEIGHT:
            raise FileValidationError(
                message=f"Image dimensions too small: {width}x{height} (min: {settings.MIN_IMAGE_WIDTH}x{settings.MIN_IMAGE_HEIGHT})",
                code="IMAGE_TOO_SMALL"
            )
        
        # Additional check via PIL for corrupted images
        try:
            pil_img = Image.open(io.BytesIO(content))
            pil_img.verify()
        except Exception as pil_e:
            logger.warning(f"PIL verification failed: {str(pil_e)}, but continuing")
            
    except FileValidationError:
        raise
    except Exception as e:
        raise FileValidationError(
            message=f"Error validating image: {str(e)}",
            code="IMAGE_VALIDATION_ERROR"
        )

@router.post(
    "/validate",
    response_model=ValidationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload photo for validation",
    description="Uploads a photo and initiates validation process"
)
async def validate_photo(
    file: UploadFile = File(..., description="Photo file for validation")
) -> Any:
    """
    Endpoint for uploading photo for validation.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Received validation request: {request_id}")
    
    try:
        # Check filename presence
        if not file.filename:
            raise FileValidationError(
                message="Filename is required",
                code="MISSING_FILENAME"
            )
        
        # Read file content
        content = await file.read()
        
        # Comprehensive file validation
        validate_image_file(content, file.filename)
        
        # Save file to storage
        file_path = f"{request_id}.jpg"
        storage_client.save_file(file_path, content)
        
        # Create database record
        ValidationRequestRepository.create(request_id, filename=file.filename, file_size=len(content))
        
        # Add processing task to queue
        await add_processing_task(request_id, file_path)
        
        return {"requestId": request_id}
    
    except FileValidationError as e:
        logger.warning(f"File validation error: {str(e)}", extra={"request_id": request_id})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    
    except StorageError as e:
        logger.error(f"Storage error: {str(e)}", extra={"request_id": request_id})
        # Update status in DB on error
        ValidationRequestRepository.update_error(
            request_id, error_message=f"Storage error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file to storage"
        )
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", extra={"request_id": request_id})
        # Update status in DB on error
        ValidationRequestRepository.update_error(
            request_id, error_message=f"Unexpected error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get(
    "/results/{request_id}",
    response_model=ValidationResult,
    summary="Get validation result",
    description="Returns validation status and result by request ID"
)
async def get_validation_result(
    request_id: str
) -> Any:
    """
    Endpoint for getting validation result by request ID.
    """
    logger.info(f"Retrieving results for request: {request_id}")
    
    try:
        # Get request from DB
        db_request = ValidationRequestRepository.get_by_id(request_id)
        
        if not db_request:
            logger.warning(f"Request not found: {request_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Request not found"
            )
        
        # Convert to response model
        # Important: create copy of data, don't use object directly
        result = db_request.to_dict()
        
        # Adapt keys for Pydantic model compliance (camelCase)
        if "overall_status" in result:
            result["overallStatus"] = result.pop("overall_status")
        if "created_at" in result:
            result["createdAt"] = result.pop("created_at")
        if "processed_at" in result:
            result["processedAt"] = result.pop("processed_at")
        if "error_message" in result:
            result["errorMessage"] = result.pop("error_message")
        if "request_id" in result:
            result["requestId"] = result.pop("request_id")
        if "processing_time" in result:
            result["processingTime"] = result.pop("processing_time")
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error retrieving results: {str(e)}", extra={"request_id": request_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve validation results"
        )

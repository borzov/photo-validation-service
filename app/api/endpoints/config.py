# Configuration management API endpoints

from fastapi import APIRouter, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import tempfile
import json
import os
from datetime import datetime

from app.config.manager import get_config_manager
from app.config.schema import ConfigurationSchema


router = APIRouter()


class ConfigUpdateRequest(BaseModel):
    """Request model for configuration updates"""
    updates: Dict[str, Any]
    validate: bool = True


class ConfigSectionUpdateRequest(BaseModel):
    """Request model for section-specific updates"""
    section_path: str
    value: Any
    validate: bool = True


class ConfigValidationRequest(BaseModel):
    """Request model for configuration validation"""
    config_data: Dict[str, Any]


@router.get("/", response_model=ConfigurationSchema)
async def get_configuration():
    """Get current configuration"""
    try:
        config_manager = get_config_manager()
        config = config_manager.get_config()
        return config
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration: {str(e)}"
        )


@router.get("/section/{section_path}")
async def get_configuration_section(section_path: str):
    """Get specific configuration section using dot notation"""
    try:
        config_manager = get_config_manager()
        section_data = config_manager.get_section(section_path)
        
        if section_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration section not found: {section_path}"
            )
        
        return {"section_path": section_path, "data": section_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration section: {str(e)}"
        )


@router.put("/", response_model=dict)
async def update_configuration(request: ConfigUpdateRequest):
    """Update configuration with partial data"""
    try:
        config_manager = get_config_manager()
        success, error_msg = config_manager.update_config(
            request.updates, 
            validate=request.validate
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Failed to update configuration"
            )
        
        return {
            "success": True,
            "message": "Configuration updated successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )


@router.put("/section", response_model=dict)
async def update_configuration_section(request: ConfigSectionUpdateRequest):
    """Update specific configuration section"""
    try:
        config_manager = get_config_manager()
        success, error_msg = config_manager.update_section(
            request.section_path, 
            request.value
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Failed to update configuration section"
            )
        
        return {
            "success": True,
            "message": f"Configuration section '{request.section_path}' updated successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration section: {str(e)}"
        )


@router.post("/validate", response_model=dict)
async def validate_configuration(request: ConfigValidationRequest):
    """Validate configuration data without saving"""
    try:
        config_manager = get_config_manager()
        is_valid, error_msg = config_manager.validate_config(request.config_data)
        
        return {
            "valid": is_valid,
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate configuration: {str(e)}"
        )


@router.post("/reset", response_model=dict)
async def reset_configuration():
    """Reset configuration to default values"""
    try:
        config_manager = get_config_manager()
        success = config_manager.reset_to_defaults()
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset configuration to defaults"
            )
        
        return {
            "success": True,
            "message": "Configuration reset to default values",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset configuration: {str(e)}"
        )


@router.get("/export")
async def export_configuration():
    """Export current configuration as JSON file"""
    try:
        config_manager = get_config_manager()
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.json', 
            delete=False,
            encoding='utf-8'
        )
        
        try:
            success = config_manager.export_config(temp_file.name)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to export configuration"
                )
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"photo_validation_config_{timestamp}.json"
            
            return FileResponse(
                path=temp_file.name,
                filename=filename,
                media_type="application/json",
                background=None  # File will be cleaned up by OS
            )
            
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            raise e
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export configuration: {str(e)}"
        )


@router.post("/import", response_model=dict)
async def import_configuration(
    file: UploadFile = File(...),
    validate: bool = True
):
    """Import configuration from uploaded JSON file"""
    try:
        if not file.filename.endswith('.json'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only JSON files are supported"
            )
        
        # Read uploaded file
        content = await file.read()
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.json', 
            delete=False,
            encoding='utf-8'
        )
        
        try:
            temp_file.write(content.decode('utf-8'))
            temp_file.close()
            
            config_manager = get_config_manager()
            success, error_msg = config_manager.import_config(
                temp_file.name, 
                validate=validate
            )
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg or "Failed to import configuration"
                )
            
            return {
                "success": True,
                "message": "Configuration imported successfully",
                "filename": file.filename,
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import configuration: {str(e)}"
        )


@router.post("/reload", response_model=dict)
async def reload_configuration():
    """Reload configuration from file"""
    try:
        config_manager = get_config_manager()
        config = config_manager.reload_config()
        
        return {
            "success": True,
            "message": "Configuration reloaded successfully",
            "version": config.version,
            "last_modified": config.last_modified.isoformat(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload configuration: {str(e)}"
        )


@router.get("/schema")
async def get_configuration_schema():
    """Get configuration schema for validation and form generation"""
    try:
        schema = ConfigurationSchema.schema()
        return {
            "schema": schema,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration schema: {str(e)}"
        )


@router.get("/defaults", response_model=ConfigurationSchema)
async def get_default_configuration():
    """Get default configuration values"""
    try:
        from app.config.defaults import get_default_config
        default_config = get_default_config()
        return default_config
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get default configuration: {str(e)}"
        ) 
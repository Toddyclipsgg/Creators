"""
API routes for cron-triggered maintenance operations.

This module provides protected API endpoints that can be called by cron jobs
to perform scheduled maintenance operations.
"""

import os
import uuid
from fastapi import FastAPI, APIRouter, HTTPException, Request, Depends
from fastapi.security import APIKeyHeader
from typing import Optional
from starlette.status import HTTP_403_FORBIDDEN
from supabase import create_client, Client
from daytona_sdk import Daytona, DaytonaConfig
from utils.logger import logger
from utils.config import config  # Import the central config

# Create a router for the cron API
router = APIRouter(tags=["cron"])

# API key validation
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: Optional[str] = Depends(api_key_header)):
    """Validate the API key from the request header using config."""
    if not config.CRON_API_KEY:
        logger.warning("No CRON_API_KEY set in configuration")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, 
            detail="API key authentication is not configured correctly"
        )
    
    if api_key_header != config.CRON_API_KEY:
        logger.warning(f"Invalid API key received: {api_key_header[:5]}...")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, 
            detail="Invalid API key"
        )
    
    return api_key_header

# Initialize the module with shared resources
db = None

def initialize(_db):
    """Initialize the cron API with resources from the main API."""
    global db
    db = _db
    logger.info("Initialized cron API with database connection")

@router.post("/auto-delete-old-sandboxes", status_code=200)
async def auto_delete_old_sandboxes(api_key: str = Depends(get_api_key)):
    """
    Fetch free-tier sandboxes > 24 hours old and delete them.
    
    This route is protected by an API key and is intended to be called by a cron job.
    """
    # Get Supabase credentials from config
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
        logger.error("Supabase URL or Service Role Key is missing in configuration")
        raise HTTPException(
            status_code=500,
            detail="Supabase configuration is incomplete."
        )

    # Configure Daytona client from config
    if not config.DAYTONA_API_KEY or not config.DAYTONA_SERVER_URL:
        logger.error("Daytona API Key or Server URL is missing in configuration")
        raise HTTPException(
            status_code=500,
            detail="Daytona configuration is incomplete for deletion."
        )

    daytona_config = DaytonaConfig(
        api_key=config.DAYTONA_API_KEY,
        api_url=config.DAYTONA_SERVER_URL,
        target=config.DAYTONA_TARGET  # Optional, can be None
    )
    daytona = Daytona(daytona_config)


    try:
        supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY)

        # Check total Daytona sandboxes
        total_sandboxes = -1 
        try:
            all_sandboxes = daytona.list()
            total_sandboxes = len(all_sandboxes)
            logger.info(f"Checked Daytona: Found {total_sandboxes} sandboxes.") # Keep this log


        except Exception as daytona_list_e:
            logger.error(f"Error fetching sandbox list from Daytona: {daytona_list_e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching sandbox list from Daytona: {str(daytona_list_e)}"
            )

        response = supabase.rpc('get_oldest_free_tier_sandboxes').execute()

        # Check for errors in the response
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error fetching data from Supabase: {response.error}")
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching data from Supabase: {str(response.error)}"
            )
        
        sandboxes_to_process = response.data if response.data else []
        old_free_tier_sandboxes_count = len(sandboxes_to_process)
        logger.info(f"Fetched {old_free_tier_sandboxes_count} oldest free tier projects from Supabase.")
        
        results = {
            "status": "success",
            "processed_count": 0,
            "successfully_deleted_count": 0,
            "total_sandboxes": total_sandboxes,
            "old_free_tier_sandboxes_count": old_free_tier_sandboxes_count,
            "errors": []
        }

        processed_count = 0
        successfully_deleted_count = 0
        errors = []
            
        for item in sandboxes_to_process:
            processed_count += 1
            project_id = item.get('project_id', 'Unknown Project')
            sandbox_data = item.get('sandbox', {})

            # Initialize log components
            log_prefix = f"[{processed_count}/{old_free_tier_sandboxes_count}] Project {project_id}"
            update_db_required = False
            sandbox_deleted_via_api = False
            daytona_sandbox_id = None
            reason = ""
            error_detail = None

            # Attempt Daytona deletion
            if isinstance(sandbox_data, dict) and 'id' in sandbox_data:
                try:
                    daytona_sandbox_id = str(sandbox_data['id'])  # Ensure it's a string
                    log_prefix += f" (Sandbox {daytona_sandbox_id})"
                    # Fetch the sandbox object first
                    # Consider adding a check if the sandbox exists in daytona first
                    # sandbox_to_delete = daytona.get_current_sandbox(daytona_sandbox_id)
                    # For now, directly try remove
                    daytona.remove(daytona_sandbox_id) # remove takes id directly
                    sandbox_deleted_via_api = True
                    update_db_required = True
                    reason = "Deleted via Daytona API"
                    successfully_deleted_count += 1
                    logger.info(f"{log_prefix}: Successfully deleted via Daytona API (Total deleted: {successfully_deleted_count})")
                except Exception as daytona_e:
                    reason = f"Daytona API delete error: {str(daytona_e)}"
                    error_detail = {"project_id": project_id, "sandbox_id": daytona_sandbox_id, "error": reason, "stage": "daytona_delete"}
                    if daytona_sandbox_id:
                        log_prefix += f" (Sandbox {daytona_sandbox_id})"
                    # Still mark as deleted in DB to prevent reprocessing.
                    update_db_required = True
                    logger.error(f"{log_prefix}: Error deleting via Daytona API: {str(daytona_e)}")
            elif sandbox_data == {}:
                reason = "Empty sandbox data in DB"
                update_db_required = True
            else:  # Handles null or other invalid states
                reason = "Invalid/null sandbox data in DB"
                update_db_required = True

            # Update Supabase if required (handles both successful deletes and cleanup cases)
            if update_db_required:
                update_payload = {'is_sandbox_deleted': True, 'sandbox': {}}
                try:
                    update_response = supabase.table('projects').update(update_payload).eq('project_id', project_id).execute()
                    if hasattr(update_response, 'error') and update_response.error:
                        supabase_error_msg = str(update_response.error)
                        logger.error(f"Supabase update error for {log_prefix}: {supabase_error_msg}")
                        if not error_detail: # Add error only if not already recorded from Daytona phase
                           error_detail = {"project_id": project_id, "sandbox_id": daytona_sandbox_id, "error": supabase_error_msg, "stage": "supabase_update"}
                        # Log the Supabase error immediately for non-API deletion cases
                        if not sandbox_deleted_via_api:
                            logger.warning(f"{log_prefix}: {reason}. Supabase update error: {supabase_error_msg}")
                    else:
                        # Log the DB update for non-API deletion cases
                        if not sandbox_deleted_via_api:
                            logger.info(f"{log_prefix}: {reason}. Marked as deleted in Supabase.")
                except Exception as update_e:
                    supabase_exception_msg = str(update_e)
                    logger.error(f"Supabase update exception for {log_prefix}: {supabase_exception_msg}")
                    if not error_detail:
                        error_detail = {"project_id": project_id, "sandbox_id": daytona_sandbox_id, "error": supabase_exception_msg, "stage": "supabase_update_exception"}
                    # Also log the Supabase exception immediately for non-API deletion cases
                    if not sandbox_deleted_via_api:
                        logger.error(f"{log_prefix}: {reason}. Supabase update exception: {supabase_exception_msg}")
                        
            if error_detail:
                errors.append(error_detail)

        # Update results with final counts and errors
        results["processed_count"] = processed_count
        results["successfully_deleted_count"] = successfully_deleted_count
        results["errors"] = errors

        logger.info(f"\nAutomatic sandbox cleanup finished. Processed {processed_count} projects from Supabase.")
        logger.info(f"Successfully deleted {successfully_deleted_count} sandboxes via Daytona API.")
        if errors:
            logger.warning(f"Encountered {len(errors)} errors during cleanup. Check response for details.")

        return results

    except Exception as e:
        logger.error(f"An uncaught error occurred during sandbox cleanup: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An uncaught error occurred during sandbox cleanup: {str(e)}"
        ) 
"""
Fetch free-tier > 24 hours old sandboxes and delete them. check @migrations/20250425165844_add_is_sandbox_deleted.sql
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import uuid
from daytona_sdk import Daytona, DaytonaConfig


load_dotenv()

# Get Supabase credentials from environment variables
supabase_url = os.environ.get("SUPABASE_URL")
# Use the service role key for administrative tasks like this
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not supabase_url or not supabase_key:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables are required.")
    exit(1)

# Configure Daytona client
daytona_api_key = os.getenv("DAYTONA_API_KEY")
daytona_server_url = os.getenv("DAYTONA_SERVER_URL")
daytona_target = os.getenv("DAYTONA_TARGET")

if not daytona_api_key or not daytona_server_url:
    print("Error: DAYTONA_API_KEY and DAYTONA_SERVER_URL environment variables are required for deletion.")
    # Decide if you want to exit or just log an error and potentially continue with DB updates only
    exit(1) 

daytona_config = DaytonaConfig(
    api_key=daytona_api_key,
    api_url=daytona_server_url,
    target=daytona_target # Optional, depending on your setup
)
daytona = Daytona(daytona_config)

# THRESHOLD_TO_TRIGGER_AUTO_DELETE_FREE_OLD_SANDBOXES = 1000 # Keep definition commented out

try:
    supabase: Client = create_client(supabase_url, supabase_key)

    # Check total Daytona sandboxes
    total_sandboxes = -1 
    try:
        all_sandboxes = daytona.list()
        total_sandboxes = len(all_sandboxes)
        print(f"Checked Daytona: Found {total_sandboxes} sandboxes.") # Keep this print

        # Comment out the threshold check block
        # if total_sandboxes <= THRESHOLD_TO_TRIGGER_AUTO_DELETE_FREE_OLD_SANDBOXES:
        #     print(f"Total sandboxes ({total_sandboxes}) <= threshold ({THRESHOLD_TO_TRIGGER_AUTO_DELETE_FREE_OLD_SANDBOXES}). Exiting.")
        #     exit(0) # Exit gracefully

    except Exception as daytona_list_e:
        # Still exit if we can't even list sandboxes
        print(f"Error fetching sandbox list from Daytona: {daytona_list_e}. Exiting.") 
        exit(1)

    # Fetch the oldest free tier projects regardless of the total sandbox count now
    response = supabase.rpc('get_oldest_free_tier_sandboxes').execute()

    # Check for errors in the response
    if hasattr(response, 'error') and response.error:
        print(f"Error fetching data from Supabase: {response.error}") 
    elif response.data:
        print(f"Fetched {len(response.data)} oldest free tier projects from Supabase.") 
        processed_count = 0
        successfully_deleted_count = 0
        for item in response.data:
            # Check if the successful deletion limit has been reached
            # [Deleted limit check block]

            processed_count += 1
            project_id = item['project_id']
            sandbox_data = item['sandbox']

            # Initialize log components
            # Use processed_count for the log index to show progress through the list
            log_prefix = f"[{processed_count}] Project {project_id}" 
            log_details = ""
            update_db_required = False
            sandbox_deleted_via_api = False
            daytona_sandbox_id = None
            daytona_error_msg = None
            supabase_error_msg = None
            reason = ""

            # Attempt Daytona deletion
            if isinstance(sandbox_data, dict) and 'id' in sandbox_data:
                try:
                    daytona_sandbox_id = str(sandbox_data['id']) # Ensure it's a string
                    log_prefix += f" (Sandbox {daytona_sandbox_id})" 
                    # Fetch the sandbox object first
                    sandbox_to_delete = daytona.get_current_sandbox(daytona_sandbox_id)
                    daytona.remove(sandbox_to_delete)
                    sandbox_deleted_via_api = True
                    update_db_required = True
                    reason = "Deleted via Daytona API"
                    successfully_deleted_count += 1
                    print(f"[ [92m+ [0m] {log_prefix}: Successfully deleted via Daytona API (Total deleted: {successfully_deleted_count})")
                except Exception as daytona_e:
                    daytona_error_msg = str(daytona_e)
                    reason = f"Daytona API delete error"
                    if daytona_sandbox_id:
                        log_prefix += f" (Sandbox {daytona_sandbox_id})"
                    # Still mark as deleted in DB to prevent reprocessing.
                    update_db_required = True
                    print(f"[[91m-[0m] {log_prefix}: Error deleting via Daytona API: {daytona_error_msg}")
            elif sandbox_data == {}:
                reason = "Empty sandbox data in DB"
                update_db_required = True
            else: # Handles null or other invalid states
                 reason = "Invalid/null sandbox data in DB"
                 update_db_required = True

            log_details += f"{reason}." 

            # Update Supabase if required (now handles both successful deletes and cleanup cases)
            if update_db_required:
                update_payload = {'is_sandbox_deleted': True, 'sandbox': {}}
                try:
                    update_response = supabase.table('projects').update(update_payload).eq('project_id', project_id).execute()
                    if hasattr(update_response, 'error') and update_response.error:
                        supabase_error_msg = str(update_response.error)
                        log_details += f" Supabase update error: {supabase_error_msg}."
                        # Also log the Supabase error immediately for non-API deletion cases
                        if not sandbox_deleted_via_api: 
                            print(f"[[93m![0m] {log_prefix}: {reason}. Supabase update error: {supabase_error_msg}")
                    else:
                        log_details += " Updated Supabase."
                        # Log the DB update for non-API deletion cases
                        if not sandbox_deleted_via_api:
                             print(f"[[93m![0m] {log_prefix}: {reason}. Marked as deleted in Supabase.")
                except Exception as update_e:
                    supabase_error_msg = str(update_e)
                    log_details += f" Supabase update exception: {supabase_error_msg}."
                     # Also log the Supabase exception immediately for non-API deletion cases
                    if not sandbox_deleted_via_api:
                        print(f"[[91m-[0m] {log_prefix}: {reason}. Supabase update exception: {supabase_error_msg}")
            

        # Add a final summary log after the loop
        print(f"\nScript finished. Processed {processed_count} projects from Supabase.")
        print(f"Successfully deleted {successfully_deleted_count} sandboxes via Daytona API.")

    else:
        print("No projects found or unexpected Supabase response format.") 

except Exception as e:
    print(f"An error occurred: {e}")

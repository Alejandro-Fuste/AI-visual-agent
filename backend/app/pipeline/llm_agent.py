import requests
import logging
from app.config import settings

logger = logging.getLogger(__name__)


def generate_actions(prompt: str, reasoning_output: dict) -> dict:
    """
    Generate action plan using the LLM API at http://127.0.0.1:5000
    
    Args:
        prompt: User's command (e.g., "Fill form with Jose de la Rosa")
        reasoning_output: Output from perception/reasoning stages
        
    Returns:
        Dict with action plan and metadata
    """
    logger.info(f"Calling LLM API for prompt: {prompt}")
    
    try:
        # Prepare the request to our LLM API
        # The LLM API expects: analysis_path or direct analysis_text + user_command
        
        llm_api_url = f"{settings.LLM_API_URL}/api/llm/parse"
        
        # For now, we'll send the reasoning output directly as analysis
        # In production, you might want to save this to a file and pass the path
        payload = {
            "user_command": prompt,
            "analysis_text": str(reasoning_output),  # Send reasoning output as analysis
        }
        
        logger.debug(f"Sending request to {llm_api_url}")
        
        response = requests.post(
            llm_api_url,
            json=payload,
            timeout=settings.LLM_API_TIMEOUT
        )
        
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("status") == "success":
            data = result.get("data", {})
            action_plan = data.get("action_plan", "")
            model = data.get("model", "unknown")
            
            logger.info(f"LLM API success (model: {model})")
            
            return {
                "action_plan": action_plan,
                "model": model,
                "user_command": prompt,
                "status": "success"
            }
        else:
            error_msg = result.get("error", "Unknown error from LLM API")
            logger.error(f"LLM API returned error: {error_msg}")
            return {
                "action_plan": "",
                "error": error_msg,
                "status": "error"
            }
    
    except requests.exceptions.Timeout:
        logger.error(f"LLM API timeout after {settings.LLM_API_TIMEOUT} seconds")
        return {
            "action_plan": "",
            "error": "LLM API request timed out",
            "status": "error"
        }
    
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to LLM API at {settings.LLM_API_URL}")
        return {
            "action_plan": "",
            "error": f"Cannot connect to LLM API. Make sure the API is running at {settings.LLM_API_URL}",
            "status": "error"
        }
    
    except Exception as e:
        logger.error(f"Unexpected error calling LLM API: {str(e)}")
        return {
            "action_plan": "",
            "error": f"Unexpected error: {str(e)}",
            "status": "error"
        }


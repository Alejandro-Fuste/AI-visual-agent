def analyze_elements(perception_output):
    """
    Pass through the OmniParser analysis to the LLM.
    In production, this could add additional semantic reasoning.
    """
    print("Passing OmniParser analysis to LLM...")
    
    # Simply pass through the analysis text from perception
    return {
        "analysis_text": perception_output.get("analysis_text", ""),
        "analysis_file": perception_output.get("analysis_file", ""),
        "reasoning_stage": "completed"
    }


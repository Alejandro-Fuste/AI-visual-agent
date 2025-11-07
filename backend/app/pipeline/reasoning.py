def analyze_elements(perception_output):
    print("Running BLIP reasoning step...")
    # TODO: integrate actual semantic reasoning
    return {"semantics": [{"element": e, "meaning": "submit action"} for e in perception_output["elements"]]}

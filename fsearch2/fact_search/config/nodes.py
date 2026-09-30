"""Node configuration settings.

Contains settings for the claim verification pipeline nodes.
"""

# Node settings
EVIDENCE_EVALUATION_CONFIG = {
    "temperature": 0.0,  # Zero temp for consistent results
    "template_dir": "data/templates",
    "template_predict": "dseek/dseek_predict_01_process_json_schema_v1.txt.jinja",
    # "generate_verdict_instructions": "generate_verdict_instructions_v1.txt",
    # "generate_verdict_instructions": "generate_verdict_instructions_v2.txt",
    "generate_verdict_instructions": "generate_verdict_instructions_v3.txt",  # v2 + evidence-only grounding
    # "model_name": "openai:gpt-5-nano",
    # "model_name": "openai:gpt-5-mini",
    "model_name": "openai:gpt-6.1-sol",
    "max_length": 50000
}

TEXT_REDUCER_CONFIG = {
    # "vectors": "data/fasttext/vectors/cc.cs.300.bin"
    "vectors": "data/fasttext/vectors/cc.en.300.bin"
}

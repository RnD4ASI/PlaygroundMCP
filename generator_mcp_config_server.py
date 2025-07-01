import json
from pathlib import Path # Ensure Path is imported if used in configs
from mcp.server.fastmcp import FastMCP

# Attempt to import the Generator class
try:
    from generator import Generator
    # Initialize the singleton. This should be the only place it's explicitly initialized
    # if this server is run. Other modules should rely on the singleton pattern.
    generator_singleton = Generator()
except ImportError:
    print("Error: Could not import Generator class from generator.py. Ensure it's in PYTHONPATH.")
    Generator = None
    generator_singleton = None
except Exception as e:
    print(f"Error initializing Generator: {e}")
    generator_singleton = None


mcp = FastMCP("generator_config_server")

def convert_to_serializable(obj):
    """Helper function to convert non-serializable objects like Path to strings."""
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(i) for i in obj]
    elif isinstance(obj, Path):
        return str(obj)
    # Add other type conversions if necessary, e.g., for specific objects
    try: # Attempt general serialization for unknown types
        json.dumps(obj)
        return obj
    except (TypeError, OverflowError):
        return str(obj) # Fallback to string representation

@mcp.resource("generator://config")
def get_generator_configuration() -> dict:
    """
    Provides static configuration details of the Generator instance.
    This includes main configuration, model configurations, and default model names.
    """
    if generator_singleton is None or not hasattr(generator_singleton, '_initialized') or not generator_singleton._initialized:
        return {"error": "Generator instance is not available or not initialized."}

    try:
        # Deep copy and then convert, to avoid altering the live config objects if they contain Paths
        main_config_serializable = convert_to_serializable(json.loads(json.dumps(generator_singleton.main_config, default=str)))
        model_config_serializable = convert_to_serializable(json.loads(json.dumps(generator_singleton.model_config, default=str)))

        config_data = {
            "main_config": main_config_serializable,
            "model_config": model_config_serializable,
            "default_embedding_model": generator_singleton.default_embedding_model,
            "default_completion_model": generator_singleton.default_completion_model,
            "default_reasoning_model": generator_singleton.default_reasoning_model,
            "default_hf_embedding_model": generator_singleton.default_hf_embedding_model,
            "default_hf_completion_model": generator_singleton.default_hf_completion_model,
            "default_hf_reranker_model": generator_singleton.default_hf_reranker_model,
            "default_hf_ocr_model": generator_singleton.default_hf_ocr_model,
            "hf_model_dir": str(generator_singleton.hf_model_dir),
        }
        # Final check for safety, though convert_to_serializable should handle most things.
        return json.loads(json.dumps(config_data, default=str))
    except AttributeError as ae:
        return {"error": f"Generator instance is missing an expected attribute: {ae}"}
    except Exception as e:
        return {"error": f"Error accessing generator configuration: {str(e)}"}

@mcp.resource("generator://status")
def get_generator_status() -> dict:
    """
    Provides dynamic status information of the Generator instance.
    This includes initialization state and basic cache information.
    """
    if generator_singleton is None or not hasattr(generator_singleton, '_initialized') or not generator_singleton._initialized:
        return {"error": "Generator instance is not available or not initialized."}

    try:
        embedding_cache_size = len(generator_singleton.embedding_model_cache) if hasattr(generator_singleton, 'embedding_model_cache') else "N/A"
        completion_cache_size = len(generator_singleton.completion_model_cache) if hasattr(generator_singleton, 'completion_model_cache') else "N/A"

        hf_embedding_model_status = type(generator_singleton.hf_embedding_model).__name__ if hasattr(generator_singleton, 'hf_embedding_model') and generator_singleton.hf_embedding_model else "Not loaded"
        hf_completion_model_status = type(generator_singleton.hf_completion_model).__name__ if hasattr(generator_singleton, 'hf_completion_model') and generator_singleton.hf_completion_model else "Not loaded"

        status_data = {
            "initialized": generator_singleton._initialized, # Relies on Generator setting this flag
            "embedding_model_cache_size": embedding_cache_size,
            "completion_model_cache_size": completion_cache_size,
            "hf_embedding_model_loaded": hf_embedding_model_status,
            "hf_completion_model_loaded": hf_completion_model_status,
            "last_cleanup_time": str(generator_singleton._last_cleanup_time) if hasattr(generator_singleton, '_last_cleanup_time') else "N/A",
            "mcp_client_manager_initialized": generator_singleton.mcp_client_manager._initialized if hasattr(generator_singleton, 'mcp_client_manager') else "N/A",
            "mcp_client_available_tools_count": len(generator_singleton.mcp_client_manager.available_tools) if hasattr(generator_singleton, 'mcp_client_manager') else "N/A",
        }
        return json.loads(json.dumps(status_data, default=str))
    except AttributeError as ae:
        return {"error": f"Generator instance is missing an expected attribute for status: {ae}"}
    except Exception as e:
        return {"error": f"Error accessing generator status: {str(e)}"}

if __name__ == "__main__":
    # This server relies on the Generator singleton being initialized.
    if generator_singleton is not None and hasattr(generator_singleton, '_initialized') and generator_singleton._initialized :
        print("Starting Generator MCP Config Server...")
        mcp.run(transport='stdio')
    elif generator_singleton is not None and not hasattr(generator_singleton, '_initialized'):
        print("Generator instance was created but seems not initialized. Config server cannot reliably start.")
    else: # generator_singleton is None
        print("Generator class could not be imported or instance created. Config server cannot start.")

ifrom flask import Flask, request, jsonify
import requests
import logging
import os
from typing import Dict, Any

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'localhost')
OLLAMA_PORT = os.getenv('OLLAMA_PORT', '11434')
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"

def check_model_availability() -> bool:
    """Check if the DeepSeek model is available and ready"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        models = response.json().get('models', [])
        return any(model['name'] == 'deepseek-r1:7b' for model in models)
    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking model availability: {e}")
        return False

def process_model_request(prompt: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Send request to Ollama model and process response"""
    try:
        # Prepare request for the model
        payload = {
            "model": "deepseek-r1:7b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": parameters.get('temperature', 0.7),
                "top_p": parameters.get('top_p', 0.9),
                "max_tokens": parameters.get('max_tokens', 2048)
            }
        }

        logger.info(f"Sending request to model at {OLLAMA_BASE_URL}")

        # Make request to Ollama
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=30  # 30 second timeout
        )

        response.raise_for_status()
        return response.json()

    except requests.exceptions.Timeout:
        raise Exception("Model request timed out")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error communicating with model: {str(e)}")

@app.route('/api/generate', methods=['POST'])
def generate():
    """Handle incoming API requests"""
    try:
        # Log incoming request
        logger.info("Received generation request")

        # Validate request data
        if not request.is_json:
            return jsonify({
                "success": False,
                "error": "Request must be JSON"
            }), 400

        data = request.json
        prompt = data.get('prompt')

        if not prompt:
            return jsonify({
                "success": False,
                "error": "Prompt is required"
            }), 400

        # Check model availability
        if not check_model_availability():
            return jsonify({
                "success": False,
                "error": "Model is not available"
            }), 503

        # Process request through model
        result = process_model_request(prompt, data)

        # Structure the response
        formatted_response = {
            "success": True,
            "data": {
                "text": result.get('response', ''),
                "metadata": {
                    "model": "deepseek-r1:7b",
                    "total_tokens": result.get('total_tokens', 0),
                    "completion_time": result.get('eval_time', 0)
                }
            }
        }

        logger.info("Successfully processed request")
        return jsonify(formatted_response)

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Check health of both API and model"""
    try:
        # Check connection to Ollama
        response = requests.get(f"{OLLAMA_BASE_URL}/api/version")
        model_available = check_model_availability()

        if response.status_code == 200 and model_available:
            return jsonify({
                "status": "healthy",
                "version": response.json().get('version', 'unknown'),
                "model_available": True
            })
        else:
            return jsonify({
                "status": "unhealthy",
                "model_available": model_available,
                "error": "Service not fully operational"
            }), 503

    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from config import get_settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/server.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def load_test_results() -> Dict[str, List]:
    """Load test results from JSON file"""
    settings = get_settings()
    try:
        with open(settings.RESULTS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Results file {settings.RESULTS_FILE} not found. Creating new file.")
        # Create empty results file
        results = {"test_results": []}
        save_test_results(results)
        return results
    except json.JSONDecodeError:
        logger.error(f"Error decoding {settings.RESULTS_FILE}. Creating new file.")
        results = {"test_results": []}
        save_test_results(results)
        return results

def save_test_results(results: Dict[str, List]) -> bool:
    """Save test results to JSON file"""
    settings = get_settings()
    try:
        with open(settings.RESULTS_FILE, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        return True
    except Exception as e:
        logger.error(f"Error saving test results: {str(e)}")
        return False

def update_test_result(test_result: Dict[str, Any]) -> bool:
    """Add or update a test result in the results file"""
    results = load_test_results()
    
    # Check if this test already has results
    for i, result in enumerate(results["test_results"]):
        if result.get("test_case_key") == test_result["test_case_key"]:
            # Update existing result
            results["test_results"][i] = test_result
            return save_test_results(results)
    
    # Add new result
    results["test_results"].append(test_result)
    return save_test_results(results)

def get_completed_test_keys() -> List[str]:
    """Get list of test case keys that have been completed"""
    results = load_test_results()
    return [result["test_case_key"] for result in results["test_results"]
            if result.get("overall_result") in ["Pass", "Fail"]]

def log_test_execution(test_case_key: str, message: str) -> None:
    """Log test execution information to a file"""
    settings = get_settings()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = os.path.join(settings.LOGS_DIR, f"{test_case_key}.log")
    
    with open(log_file, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")

def is_test_completed(test_case_key: str) -> bool:
    """Check if a test case has been completed"""
    completed_keys = get_completed_test_keys()
    return test_case_key in completed_keys
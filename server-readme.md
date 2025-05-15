# Test Automation Server

A FastAPI-based server component that integrates with Jira to manage and automate functional testing workflows using AI operators.

## Overview

This server component connects to Jira to fetch test cases, prepares prompts for test execution, and records test results. It works in conjunction with a Chrome extension to automate functional testing using an AI operator.

### Key Features

- Fetch incomplete test cases from Jira
- Generate comprehensive test prompts including dependencies
- Process and store test execution results
- Track test case execution status across Jira and local records

## Getting Started

### Prerequisites

- Python 3.8+
- Jira account with appropriate permissions
- Test cases configured in Jira

### Installation

1. Clone the repository:
   ```
   git clone [your-repo-url]
   cd [your-repo-name]
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   Create a `.env` file in the root directory with the following content:
   ```
   # Jira Configuration
   JIRA_URL=your_jira_url
   JIRA_USER=your_jira_username
   JIRA_TOKEN=your_jira_api_token
   PROJECT_KEY=your_jira_project_key
   
   # API Configuration
   APP_NAME=Jira Test Case Extractor
   API_VERSION=1.0.0
   DEBUG=False
   ```

### Running the Server

Start the server using Uvicorn:
```
uvicorn main:app --reload
```

The server will be available at `http://localhost:8000`.

## API Endpoints

### GET `/`
- Root endpoint for API health check

### GET `/incomplete-tests`
- Returns all incomplete tests that need to be executed
- Calculates incomplete tests by:
  - Checking tests in "To Do" status in Jira
  - Excluding tests in "Done" status
  - Excluding tests completed locally

### POST `/get-test-prompt`
- Generates a prompt for a specific test case including all dependencies
- Request body: `{"test_case_key": "QA-XX"}`
- Returns a formatted prompt for the AI operator

### POST `/send-test-results`
- Records test execution results
- Request body:
  ```json
  {
    "test_case_key": "string",
    "results": [
      {
        "test_step": "string",
        "log_or_error": "string",
        "result": "string",
        "timestamp": "string"
      }
    ],
    "overall_result": "string"
  }
  ```

## Project Structure

- `main.py`: FastAPI application entry point
- `config.py`: Configuration settings
- `jira_client.py`: Jira API integration
- `dependency_resolver.py`: Resolves test case dependencies
- `prompt_generator.py`: Generates AI operator prompts
- `models.py`: Pydantic models for request/response validation
- `utils.py`: Utility functions
- `test_cases.json`: Local cache of test cases
- `test_results.json`: Storage for test execution results

## Dependencies

- fastapi: 0.103.1
- uvicorn: 0.23.2
- pydantic: 2.3.0
- pydantic-settings: 2.0.3
- jira: 3.5.2
- python-dotenv: 1.0.0
- requests: 2.31.0

## Workflow

1. The server fetches test cases from Jira
2. When the Chrome extension requests a test case, the server:
   - Fetches the test case details from Jira
   - Resolves any dependencies
   - Generates a formatted prompt
   - Returns the prompt to the extension
3. After test execution, the extension sends results back to the server
4. The server records results and updates the test case status
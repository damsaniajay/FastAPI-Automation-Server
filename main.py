from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import uvicorn
from datetime import datetime
from typing import Dict, List, Any, Optional

from jira_client import JiraClient
from config import get_settings
from dependency_resolver import DependencyResolver
from prompt_generator import generate_prompt
from models import TestPromptRequest, TestResultSubmission, TestStepResult
from utils import (
    load_test_results, 
    save_test_results, 
    update_test_result, 
    get_completed_test_keys,
    log_test_execution,
    is_test_completed
)

import logging
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Web/Mobile App Testing Automation", 
    description="API to fetch test cases from Jira and run them automatically"
)

# Add CORS middleware for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your extension's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency for Jira client
def get_jira_client():
    settings = get_settings()
    return JiraClient(
        jira_url=settings.JIRA_URL,
        jira_user=settings.JIRA_USER,
        jira_token=settings.JIRA_TOKEN,
        project_key=settings.PROJECT_KEY
    )

# Dependency for dependency resolver
def get_dependency_resolver(jira_client: JiraClient = Depends(get_jira_client)):
    return DependencyResolver(jira_client)

@app.get("/")
async def root():
    return {"message": "Web/Mobile App Testing Automation API is running"}

@app.get("/incomplete-tests")
async def get_incomplete_tests(jira_client: JiraClient = Depends(get_jira_client)):
    """
    Get all incomplete tests that need to be executed
    
    Calculates incomplete tests by subtracting:
    1. Tests in "Done" status in Jira
    2. Tests completed locally
    from the tests in "To Do" status
    """
    try:
        # Get tests from different statuses
        todo_tests = jira_client.get_test_cases_by_status("To Do")
        in_progress_tests = jira_client.get_test_cases_by_status("In Progress")
        done_tests = jira_client.get_test_cases_by_status("Done")
        
        # Get completed tests from our local tracking
        completed_keys = get_completed_test_keys()
        
        # Create sets of test keys for easy subtraction
        todo_keys = {test["key"] for test in todo_tests}
        in_progress_keys = {test["key"] for test in in_progress_tests}
        done_keys = {test["key"] for test in done_tests}
        
        # All active test keys (To Do + In Progress)
        active_keys = todo_keys.union(in_progress_keys)
        
        # Calculate incomplete keys by subtracting done and locally completed keys
        incomplete_keys = active_keys - done_keys - set(completed_keys)
        
        # Create minimal test objects with only key and summary
        incomplete_tests = []
        for test in todo_tests + in_progress_tests:
            if test["key"] in incomplete_keys:
                incomplete_tests.append({
                    "key": test["key"],
                    "summary": test["summary"],
                    "status": test["status"]
                })
        
        return JSONResponse(content={
            "incomplete_tests": incomplete_tests,
            "count": len(incomplete_tests)
        })
    except Exception as e:
        logger.error(f"Error getting incomplete tests: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get-test-prompt")
async def get_test_prompt(
    request: TestPromptRequest,
    jira_client: JiraClient = Depends(get_jira_client)
):
    """
    Get a prompt for a specific test case including all dependencies
    """
    try:
        # Get the requested test case
        test_case = jira_client.get_test_case_by_key(request.test_case_key)
        if not test_case:
            return JSONResponse(
                status_code=404,
                content={"message": f"Test case {request.test_case_key} not found"}
            )
        
        # Check if the test is already completed locally
        completed_keys = get_completed_test_keys()
        if request.test_case_key in completed_keys:
            return JSONResponse(
                status_code=400,
                content={"message": f"Test case {request.test_case_key} is already completed locally"}
            )
        
        # Check if the test is in Done status in Jira
        done_tests = jira_client.get_test_cases_by_status("Done")
        done_keys = {test["key"] for test in done_tests}
        if request.test_case_key in done_keys:
            return JSONResponse(
                status_code=400,
                content={"message": f"Test case {request.test_case_key} is already marked as Done in Jira"}
            )
            
        # Generate prompt for the test case
        prompt = generate_prompt(test_case)
        
        # Log that this test is being executed
        log_test_execution(test_case["key"], "Starting test execution")
        
        return JSONResponse(content={
            "prompt": prompt
        })
    except Exception as e:
        logger.error(f"Error generating test prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-test-results")
async def send_test_results(
    submission: TestResultSubmission,
    background_tasks: BackgroundTasks,
    jira_client: JiraClient = Depends(get_jira_client)
):
    """
    Send test execution results back to the server
    """
    try:
        
        
        # Create test result record
        test_result = {
            "test_case_key": submission.test_case_key,
            "steps_results": [result.dict() for result in submission.results],
            "overall_result": submission.overall_result,  
            "timestamp": datetime.now()
        }
        
        # Update local test results
        update_successful = update_test_result(test_result)
        
        if not update_successful:
            return JSONResponse(
                status_code=500,
                content={"message": "Failed to update test results"}
            )
        
        # Force refresh completed test keys after update
        # This ensures we have the most current list
        completed_keys = get_completed_test_keys()
        
        # Log completion of test
        log_message = f"Test completed with result: {submission.overall_result}"
        log_test_execution(submission.test_case_key, log_message)
        
        # Get list of incomplete tests to inform the client if there are more tests to run
        # Get tests from different statuses
        todo_tests = jira_client.get_test_cases_by_status("To Do")
        in_progress_tests = jira_client.get_test_cases_by_status("In Progress")
        done_tests = jira_client.get_test_cases_by_status("Done")
        
        # Create sets of test keys for easy subtraction
        todo_keys = {test["key"] for test in todo_tests}
        in_progress_keys = {test["key"] for test in in_progress_tests}
        done_keys = {test["key"] for test in done_tests}
        
        # All active test keys (To Do + In Progress)
        active_keys = todo_keys.union(in_progress_keys)
        
        # Calculate incomplete keys by subtracting done and locally completed keys
        incomplete_keys = active_keys - done_keys - set(completed_keys)
        
        response_data = {
            "message": "Test results saved successfully",
            "status": "completed",
            "has_more_tests": len(incomplete_keys) > 0,
            "remaining_test_count": len(incomplete_keys)
        }
        
        return JSONResponse(content=response_data)
    except Exception as e:
        logger.error(f"Error processing test results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Add this to run the application directly with uvicorn when script is executed
if __name__ == "__main__":
    # You can customize port and other settings here
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
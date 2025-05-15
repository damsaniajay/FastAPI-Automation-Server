from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class TestStep(BaseModel):
    test: str
    test_step: str
    expected_output: str

class TestCase(BaseModel):
    key: str
    id: str
    summary: str
    status: str
    test_steps: List[TestStep]

class TestResult(BaseModel):
    test_case_key: str
    steps_results: List[Dict[str, Any]]
    overall_result: str
    timestamp: datetime
    
class TestStepResult(BaseModel):
    test_step: str
    log_or_error: str
    result: str
    timestamp: str
    

class TestPromptRequest(BaseModel):
    test_case_key: Optional[str] = None  # If None, server will select next test

class TestResultSubmission(BaseModel):
    test_case_key: str
    results: List[TestStepResult]
    overall_result: str
    
    
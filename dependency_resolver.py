from typing import List, Dict, Any, Set, Optional
import logging
from jira_client import JiraClient
from utils import get_completed_test_keys, is_test_completed

logger = logging.getLogger(__name__)

class DependencyResolver:
    def __init__(self, jira_client: JiraClient):
        self.jira_client = jira_client
        self.completed_tests = set(get_completed_test_keys())
        
    def refresh_completed_tests(self):
        """Refresh the list of completed tests"""
        self.completed_tests = set(get_completed_test_keys())
        
    def find_executable_tests(self, status: str = "To Do") -> List[Dict[str, Any]]:
        """
        Find tests with the given status that have all dependencies resolved
        
        Args:
            status: Test status to filter by (default: "To Do")
            
        Returns:
            List of executable test cases
        """
        # Get all tests with the specified status
        test_cases = self.jira_client.get_test_cases_by_status(status)
        
        # Filter for tests that are ready to execute (dependencies completed)
        executable_tests = []
        for test in test_cases:
            if self._can_execute_test(test):
                executable_tests.append(test)
                
        return executable_tests
    
    def get_next_test(self) -> Optional[Dict[str, Any]]:
        """
        Get the next test that should be executed
        
        Returns:
            A test case dict or None if no executable tests
        """
        executable_tests = self.find_executable_tests()
        
        # If no executable tests, return None
        if not executable_tests:
            return None
            
        # Return the first test in the list
        # This is a simple strategy - you could implement more complex prioritization
        return executable_tests[0]
    
    def _can_execute_test(self, test: Dict[str, Any]) -> bool:
        """
        Determine if a test can be executed based on its dependencies
        
        Args:
            test: The test case dict
            
        Returns:
            True if test can be executed, False otherwise
        """
        # If test is already completed, we don't need to execute it again
        if test["key"] in self.completed_tests:
            return False
            
        # Find all dependencies for this test
        dependencies = self._find_dependencies(test["key"])
        
        # Check if all dependencies are completed
        return all(dep_key in self.completed_tests for dep_key in dependencies)
    
    def _find_dependencies(self, test_key: str) -> List[str]:
        """
        Find all dependencies (blocked by) for a test case
        
        Args:
            test_key: The test case key
            
        Returns:
            List of test case keys that this test depends on
        """
        test_case = self.jira_client.get_test_case_by_key(test_key)
        if not test_case:
            return []
            
        # Get direct dependencies from Jira links
        dependencies = []
        
        # Find linked issues using Jira API (via jira_client)
        try:
            issue = self.jira_client.jira.issue(test_key)
            if hasattr(issue.fields, 'issuelinks') and issue.fields.issuelinks:
                for link in issue.fields.issuelinks:
                    # Check for "blocked by" relationship
                    if hasattr(link, 'inwardIssue') and link.type.name.lower() in ['blocks', 'is blocked by']:
                        dependencies.append(link.inwardIssue.key)
                    elif hasattr(link, 'outwardIssue') and link.type.name.lower() == 'blocks' and 'outward' in link.type.inward.lower():
                        dependencies.append(link.outwardIssue.key)
        except Exception as e:
            logger.error(f"Error finding dependencies for {test_key}: {str(e)}")
        
        return dependencies
        
    def gather_test_with_dependencies(self, test_key: str) -> Dict[str, Any]:
        """
        Gather a test case with all its dependencies
        
        Args:
            test_key: The test case key
            
        Returns:
            Test case with all dependency test steps included
        """
        # Get the main test case
        test_case = self.jira_client.get_test_case_by_key(test_key)
        if not test_case:
            logger.error(f"Test case {test_key} not found")
            return None
            
        return test_case  # The jira_client now handles combining test steps internally
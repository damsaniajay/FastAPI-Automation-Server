from jira import JIRA
import re
from typing import List, Dict, Any, Optional

class JiraClient:
    def __init__(self, jira_url: str, jira_user: str, jira_token: str, project_key: str):
        """
        Initialize Jira client
        
        Args:
            jira_url: The URL of the Jira instance (e.g., https://your-domain.atlassian.net)
            jira_user: The email address of the Jira user
            jira_token: The API token for authentication
            project_key: The project key in Jira
        """
        self.jira_url = jira_url
        self.project_key = project_key
        
        # Initialize Jira client
        try:
            self.jira = JIRA(
                server=jira_url,
                basic_auth=(jira_user, jira_token)
            )
            # Test connection
            self.jira.myself()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Jira: {str(e)}")
    
    def get_test_cases_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Get all test cases with the specified status
        
        Args:
            status: The status of test cases to fetch (e.g., "To Do", "In Progress", "Done")
            
        Returns:
            List of test cases in JSON format
        """
        jql_query = f'project = {self.project_key} AND status = "{status}" ORDER BY created DESC'
        
        # Get issues matching the JQL query
        issues = self.jira.search_issues(jql_query, maxResults=100)
        
        # Process issues
        test_cases = []
        for issue in issues:
            test_case = self._process_test_case(issue)
            if test_case:
                test_cases.append(test_case)
        
        return test_cases
    
    def get_test_case_by_key(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific test case by its issue key
        
        Args:
            issue_key: The Jira issue key (e.g., PROJECT-123)
            
        Returns:
            Test case in JSON format or None if not found
        """
        try:
            issue = self.jira.issue(issue_key)
            return self._process_test_case(issue)
        except Exception as e:
            print(f"Error getting test case {issue_key}: {str(e)}")
            return None
    
    def _find_blocking_issues(self, issue) -> List[str]:
        """
        Find issues that are blocking this issue
        
        Args:
            issue: The Jira issue object
            
        Returns:
            List of issue keys that are blocking this issue
        """
        blocking_issues = []
        
        # Check for issue links
        if hasattr(issue.fields, 'issuelinks') and issue.fields.issuelinks:
            for link in issue.fields.issuelinks:
                # Handle different link types
                if hasattr(link, 'inwardIssue') and link.type.name.lower() in ['blocks', 'is blocked by']:
                    blocking_issues.append(link.inwardIssue.key)
                elif hasattr(link, 'outwardIssue') and link.type.name.lower() == 'blocks' and 'outward' in link.type.inward.lower():
                    # This means the link type is reversed (the current issue is blocked by the outward issue)
                    blocking_issues.append(link.outwardIssue.key)
        
        return blocking_issues
    
    def _process_test_case(self, issue) -> Dict[str, Any]:
        """
        Process a Jira issue and extract test case information
        
        Args:
            issue: The Jira issue object
            
        Returns:
            Test case information in JSON format
        """
        # Extract basic issue information
        test_case = {
            "key": issue.key,
            "id": issue.id,
            "summary": issue.fields.summary,
            "status": issue.fields.status.name,
            "test_steps": []
        }
        
        # Check for blocking issues (but don't include in output)
        blocking_issue_keys = self._find_blocking_issues(issue)
        
        # Process the test steps including blocking issues' steps
        if blocking_issue_keys:
            blocking_steps = []
            
            # Get steps from blocking issues first
            for blocking_key in blocking_issue_keys:
                try:
                    blocking_issue = self.jira.issue(blocking_key)
                    
                    # Extract test steps from blocking issue if it has a description
                    if blocking_issue.fields.description:
                        blocking_steps.extend(self._extract_test_steps_from_description(blocking_issue.fields.description))
                except Exception as e:
                    print(f"Error processing blocking issue {blocking_key}: {str(e)}")
            
            # Add original test case steps after blocking steps
            if issue.fields.description:
                test_case["test_steps"] = blocking_steps + self._extract_test_steps_from_description(issue.fields.description)
            else:
                test_case["test_steps"] = blocking_steps
        else:
            # No blocking issues, just use the original description
            if issue.fields.description:
                test_case["test_steps"] = self._extract_test_steps_from_description(issue.fields.description)
        
        return test_case
    
    def _extract_test_steps_from_description(self, description: str) -> List[Dict[str, str]]:
        """
        Extract test steps from the issue description
        
        Args:
            description: The issue description containing test steps table
            
        Returns:
            List of test steps with test, test step, and expected output
        """
        test_steps = []
        
        # Handle different table formats in Jira descriptions
        # Format 1: Jira markdown tables
        if "||" in description:
            # Split by lines and process each row
            lines = description.split('\n')
            header_found = False
            
            for line in lines:
                if line.startswith('||') and not header_found:
                    header_found = True
                    continue
                
                if line.startswith('|') and header_found:
                    # Extract cells from table row
                    cells = line.split('|')
                    
                    # Clean up cells (remove empty entries and strip whitespace)
                    cells = [cell.strip() for cell in cells if cell.strip()]
                    
                    if len(cells) >= 3:
                        test_steps.append({
                            "test": cells[0],
                            "test_step": cells[1],
                            "expected_output": cells[2]
                        })
        
        # Format 2: HTML tables
        elif "<table>" in description or "<tbody>" in description:
            # Extract rows from HTML table
            rows = re.findall(r'<tr>(.*?)</tr>', description, re.DOTALL)
            
            for row in rows[1:]:  # Skip header row
                # Extract cells from row
                cells = re.findall(r'<td>(.*?)</td>', row, re.DOTALL)
                
                if len(cells) >= 3:
                    test_steps.append({
                        "test": cells[0],
                        "test_step": cells[1],
                        "expected_output": cells[2]
                    })
        
        return test_steps
"""
Task Interpreter - Uses LLM to understand user intent and structure tasks properly
"""

import json
from typing import Dict, List, Optional, Tuple
from core.services.llm import llm_service


class TaskInterpreter:
    """
    Interprets natural language tasks using LLM to determine:
    - What type of operation (file creation, folder creation, etc.)
    - Target paths and names
    - Any content or specifications
    """

    async def interpret_task(self, task: str) -> Dict:
        """
        Use LLM to interpret a natural language task into structured format.

        Returns a dictionary with:
        - operation: What to do (create_file, create_folder, etc.)
        - targets: List of items to create/modify
        - details: Additional details like content, location, etc.
        """

        prompt = f"""
        Analyze this task and extract the structured information:

        Task: "{task}"

        Return a JSON object with:
        - operation: One of [create_file, create_folder, modify_file, delete_file, delete_folder, other]
        - targets: Array of objects, each with:
          - type: "file" or "folder"
          - name: The name of the file/folder
          - path: The full path (including parent folders if specified)
          - content: (for files) The content to write, or null if not specified

        Examples:
        Task: "create a file called test.txt with hello world"
        Result: {{"operation": "create_file", "targets": [{{"type": "file", "name": "test.txt", "path": "test.txt", "content": "hello world"}}]}}

        Task: "create a file called index.js in the src folder"
        Result: {{"operation": "create_file", "targets": [{{"type": "file", "name": "index.js", "path": "src/index.js", "content": null}}]}}

        Task: "create a folder called components"
        Result: {{"operation": "create_folder", "targets": [{{"type": "folder", "name": "components", "path": "components", "content": null}}]}}

        Analyze the task and return ONLY the JSON object, no other text.
        """

        try:
            response = await llm_service.complete(
                prompt=prompt,
                max_tokens=500
            )

            if response:
                # Extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())

            # Fallback to basic interpretation
            return self._basic_interpretation(task)

        except Exception as e:
            print(f"LLM interpretation failed: {e}")
            return self._basic_interpretation(task)

    def _basic_interpretation(self, task: str) -> Dict:
        """
        Fallback basic interpretation when LLM is unavailable.
        """
        task_lower = task.lower()

        # Simple heuristics
        if "folder" in task_lower or "directory" in task_lower:
            operation = "create_folder"
            target_type = "folder"
        elif ".js" in task or ".py" in task or ".md" in task or "file" in task_lower:
            operation = "create_file"
            target_type = "file"
        else:
            operation = "other"
            target_type = "unknown"

        # Try to extract name
        import re
        name_match = re.search(r'(?:called|named)\s+([a-zA-Z0-9_\-\.]+)', task, re.IGNORECASE)
        name = name_match.group(1) if name_match else "unknown"

        return {
            "operation": operation,
            "targets": [{
                "type": target_type,
                "name": name,
                "path": name,
                "content": None
            }]
        }


# Global instance
task_interpreter = TaskInterpreter()
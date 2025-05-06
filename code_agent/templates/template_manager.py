"""
Template manager for the Code Agent CLI.

This module handles loading and using templates for agent creation.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# Default template directory
TEMPLATE_DIR = Path(__file__).parent / "agents"


class TemplateManager:
    """Manages templates for agent creation."""

    def __init__(self, template_dir: Optional[Path] = None):
        """Initialize the template manager.

        Args:
            template_dir: Directory containing templates. Default is TEMPLATE_DIR.
        """
        self.template_dir = template_dir or TEMPLATE_DIR
        self.templates = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Load all templates from the template directory."""
        if not self.template_dir.exists():
            raise FileNotFoundError(f"Template directory not found: {self.template_dir}")

        for template_file in self.template_dir.glob("*.yaml"):
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    template_data = yaml.safe_load(f)

                # Validate template has required fields
                required_fields = ["name", "description", "id", "files"]
                if not all(field in template_data for field in required_fields):
                    print(f"Warning: Template {template_file} missing required fields. Skipping.")
                    continue

                template_id = template_data["id"]
                self.templates[template_id] = template_data
            except Exception as e:
                print(f"Error loading template {template_file}: {e}")

    def get_available_templates(self) -> List[Dict[str, str]]:
        """Get a list of available templates with their metadata.

        Returns:
            List of dictionaries containing template metadata.
        """
        return [
            {
                "id": template_id,
                "name": template_data["name"],
                "description": template_data["description"],
                "default_model": template_data.get("default_model", ""),
            }
            for template_id, template_data in self.templates.items()
        ]

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific template by ID.

        Args:
            template_id: ID of the template to retrieve.

        Returns:
            Template data or None if not found.
        """
        return self.templates.get(template_id)

    def generate_agent(self, template_id: str, agent_folder: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Generate agent files from a template.

        Args:
            template_id: ID of the template to use.
            agent_folder: Folder to create the agent in.
            params: Parameters to use for template substitution.

        Returns:
            Tuple of (success, message).
        """
        template = self.get_template(template_id)
        if not template:
            return False, f"Template '{template_id}' not found."

        # Create agent folder if it doesn't exist
        os.makedirs(agent_folder, exist_ok=True)

        # Generate files from template
        for filename, content in template["files"].items():
            file_path = os.path.join(agent_folder, filename)
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    # Format content with params
                    formatted_content = content.format(**params)
                    f.write(formatted_content)
            except Exception as e:
                return False, f"Error creating file {filename}: {e}"

        # Return success with setup instructions
        setup_instructions = template.get("setup_instructions", "Agent created successfully.")
        formatted_instructions = setup_instructions.format(agent_folder=agent_folder, **params)

        return True, formatted_instructions


# Singleton instance
_manager: Optional[TemplateManager] = None


def get_template_manager() -> TemplateManager:
    """Get the singleton template manager instance."""
    global _manager
    if _manager is None:
        _manager = TemplateManager()
    return _manager

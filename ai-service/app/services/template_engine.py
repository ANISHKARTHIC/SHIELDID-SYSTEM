import os
import yaml
import logging
from typing import Dict, Any, List

logger = logging.getLogger("template_engine")

class DocumentTemplateEngine:
    def __init__(self, templates_dir: str = None):
        if not templates_dir:
            # Default to adjacent templates directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.templates_dir = os.path.join(base_dir, "templates")
        else:
            self.templates_dir = templates_dir
            
        self.templates: Dict[str, dict] = {}
        self.load_templates()

    def load_templates(self):
        """Loads all YAML templates from the templates directory"""
        if not os.path.exists(self.templates_dir):
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return
            
        for filename in os.listdir(self.templates_dir):
            if filename.endswith((".yml", ".yaml")):
                filepath = os.path.join(self.templates_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        template = yaml.safe_load(f)
                        if template and 'doc_type' in template:
                            # Use doc_type + country as a key or just doc_type
                            key = template['doc_type']
                            self.templates[key] = template
                            logger.info(f"Loaded template: {template.get('name')} [{key}]")
                except Exception as e:
                    logger.error(f"Failed to load template {filename}: {e}")

    def get_template(self, doc_type: str) -> dict:
        return self.templates.get(doc_type)

    def get_all_templates(self) -> List[dict]:
        return list(self.templates.values())

template_engine = DocumentTemplateEngine()

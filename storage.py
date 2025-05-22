import json
import os
from datetime import datetime
from typing import Dict, Optional, List, Any

class LocalStorage:
    def __init__(self, storage_dir: str = "results"):
        """Initialize storage with directory path"""
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    def save_result(self, 
                   original_text: str, 
                   model_outputs: Dict[str, str], 
                   final_output: str,
                   processing_times: Dict[str, float] = None,
                   section_type: str = None) -> str:
        """
        Save a result to local storage and return the file path
        
        Args:
            original_text: The original text that was processed
            model_outputs: Dictionary of model outputs (model_name -> output)
            final_output: The final consolidated output
            processing_times: Dictionary of processing times (model_name -> time in seconds)
            section_type: The type of memo section being edited
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"memo_edit_{timestamp}.json"
        filepath = os.path.join(self.storage_dir, filename)
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "original_text": original_text,
            "model_outputs": model_outputs,
            "final_output": final_output
        }
        
        # Add processing times if provided
        if processing_times:
            data["processing_times"] = processing_times
            
        # Add section type if provided
        if section_type:
            data["section_type"] = section_type
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def list_results(self) -> List[str]:
        """
        List all available result files
        """
        if not os.path.exists(self.storage_dir):
            return []
        
        files = [f for f in os.listdir(self.storage_dir) if f.endswith('.json')]
        return sorted(files, reverse=True)  # Most recent first
    
    def load_result(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Load a specific result by filename
        """
        filepath = os.path.join(self.storage_dir, filename)
        
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            return None 
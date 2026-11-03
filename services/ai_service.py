"""
NyayaGuide AI Integration Service
Thin wrapper encapsulating LLM configuration and dispatch.
"""
from typing import Dict, Any, List, Optional
from legal.answer import generate_grounded_legal_analysis

class AIService:
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model

    def explain_provisions(
        self,
        query_text: str,
        provisions: List[Dict[str, Any]],
        jurisdiction_name: str,
        incident_date: Optional[str] = None
    ) -> Dict[str, Any]:
        return generate_grounded_legal_analysis(
            query_text=query_text,
            retrieved_provisions=provisions,
            jurisdiction_name=jurisdiction_name,
            incident_date=incident_date,
            api_key=self.api_key
        )

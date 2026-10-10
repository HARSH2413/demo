import json
from app.interfaces.llm import ILLM
from app.core.logger import logger

class QueryExpansionService:
    def __init__(self, llm: ILLM):
        self.llm = llm

    def expand(self, query: str, history: list) -> dict:
        """
        Uses ONE LLM call to return:
        - a rewritten query (resolving pronouns from history)
        - 2-3 variants of the rewritten query
        """
        history_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in history[-6:]]) if history else "None"
        
        system_prompt = (
            "You are a search query optimizer. Given a user's question and recent chat history, "
            "generate an optimized JSON object containing:\n"
            "1. 'rewritten_query': The question rewritten to be standalone, resolving any pronouns (it, this) using history.\n"
            "2. 'variants': A list of up to 3 alternative phrasings of the standalone question to improve search recall.\n"
            "Rules:\n"
            "- Only output valid JSON.\n"
            "- No markdown blocks or extra text.\n"
            "- Keep queries concise and search-friendly.\n"
            "- Preserve exact dates, acronyms, and names.\n"
            "- If the question introduces a specific new topic, subject, or article (e.g. Article 22, Section 54), focus purely on that new topic and DO NOT mix in previous unrelated topics from history.\n"
            "- Variants should genuinely differ in wording but mean the same thing.\n"
        )
        
        user_prompt = f"History:\n{history_text}\n\nCurrent Question: {query}"
        
        try:
            response = self.llm.generate_response(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.2)
            
            # Clean up markdown formatting if present
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
                
            data = json.loads(cleaned.strip())
            
            rewritten = data.get("rewritten_query", query)
            variants = data.get("variants", [])
            
            # Remove duplicates
            unique_variants = []
            for v in variants:
                if v and isinstance(v, str) and v.lower() not in [u.lower() for u in unique_variants] and v.lower() != rewritten.lower():
                    unique_variants.append(v)
                    
            return {
                "rewritten_query": rewritten,
                "variants": unique_variants[:3]
            }
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return {
                "rewritten_query": query,
                "variants": []
            }

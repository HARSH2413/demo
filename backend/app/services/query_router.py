import re

class RuleBasedQueryRouter:
    """
    Determines if a query is a FOLLOW_UP (requiring conversation context)
    or NORMAL (standalone).
    Uses conservative rules to avoid unnecessary LLM calls.
    """
    
    def route(self, query: str, history_len: int) -> dict:
        if history_len == 0:
            return {"route": "normal"}

        clean_query = query.strip().lower()
        
        # 1. Very short queries
        if len(clean_query.split()) <= 3:
            return {"route": "follow_up"}
            
        # 2. Follow-up starters
        starters = ["what about", "how about", "and what", "and ", "also "]
        for s in starters:
            if clean_query.startswith(s):
                return {"route": "follow_up"}
                
        # 3. Context-dependent pronouns
        pronouns = ["it", "this", "that", "they", "them", "their", "his", "her", "those", "these", "he", "she"]
        words = set(re.findall(r'\b\w+\b', clean_query))
        
        if any(p in words for p in pronouns):
            return {"route": "follow_up"}
            
        return {"route": "normal"}

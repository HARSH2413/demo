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
            
        # 2. Follow-up conversational starters
        starters = ["what about", "how about", "and what", "and ", "also ", "why ", "why?"]
        for s in starters:
            if clean_query.startswith(s):
                return {"route": "follow_up"}
                
        # 3. Context-dependent pronouns (ignoring document references like 'this pdf')
        doc_refs = ["this pdf", "this doc", "this document", "the pdf", "the document", "the file"]
        has_doc_ref = any(d in clean_query for d in doc_refs)
        
        pronouns = ["it", "they", "them", "their", "his", "her", "those", "these", "he", "she"]
        if not has_doc_ref:
            pronouns.extend(["this", "that"])
            
        words = set(re.findall(r'\b\w+\b', clean_query))
        if any(p in words for p in pronouns):
            return {"route": "follow_up"}
            
        return {"route": "normal"}

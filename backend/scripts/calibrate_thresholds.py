import os
import sys
from fastembed.rerank.cross_encoder import TextCrossEncoder
import math

def run_calibration():
    print("=== RERANKER SCORE DISTRIBUTION CALIBRATION ===")
    print("Model: Xenova/ms-marco-MiniLM-L-12-v2")
    
    # Initialize reranker
    model = TextCrossEncoder(model_name="Xenova/ms-marco-MiniLM-L-12-v2")
    
    # Define test pairs (Query -> Passages)
    tests = [
        {
            "query": "What is the employee's PF contribution?",
            "passages": [
                "The employee's Provident Fund (PF) contribution is 12% of their basic salary.", # Strong match
                "The employer will match the employee's 401k up to 5%.", # Weak match / Tangential
                "Our cafeteria menu includes pizza on Fridays.", # Total noise
            ]
        },
        {
            "query": "How many days notice is required for resignation?",
            "passages": [
                "Employees must provide at least 30 days written notice before resigning.", # Strong match
                "If you need to take sick leave, please notify your manager.", # Weak match
                "The building is closed on national holidays.", # Total noise
            ]
        }
    ]
    
    all_strong = []
    all_weak = []
    all_noise = []
    
    for t in tests:
        query = t["query"]
        passages = t["passages"]
        
        scores = list(model.rerank(query, passages))
        
        print(f"\nQuery: '{query}'")
        for i, score_entry in enumerate(scores):
            if isinstance(score_entry, float):
                raw = score_entry
            else:
                raw = float(getattr(score_entry, 'score', score_entry))
                
            norm = 1.0 / (1.0 + math.exp(-raw))
            
            label = ["Strong Match", "Weak Match", "Total Noise"][i]
            print(f"  [{label}] Raw Logit: {raw:6.2f}  |  Sigmoid Normalized: {norm:5.3f}")
            
            if i == 0: all_strong.append(norm)
            if i == 1: all_weak.append(norm)
            if i == 2: all_noise.append(norm)

    print("\n=== SUMMARY DISTRIBUTION ===")
    print(f"Strong Matches (Avg): {sum(all_strong)/len(all_strong):.3f}")
    print(f"Weak Matches   (Avg): {sum(all_weak)/len(all_weak):.3f}")
    print(f"Total Noise    (Avg): {sum(all_noise)/len(all_noise):.3f}")
    
    print("\n=== THRESHOLD RECOMMENDATIONS ===")
    print("Based on this sigmoid distribution:")
    print("1. ANSWER_MIN_RELEVANCE_SCORE should be placed just above Total Noise to safely block garbage while allowing tangential context.")
    print("2. MIN_RELEVANCE_SCORE should be placed near Weak Match levels to preserve slightly relevant results.")
    print("3. High-confidence assertions (determine_confidence) should trigger at >= 0.50 (where Sigmoid flips).")

if __name__ == "__main__":
    run_calibration()

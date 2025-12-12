# agents/transaction_agent.py
"""
Transaction agent: loads cleaned CSV and applies policy rules (direct violations).
Uses data/transacoes_bancarias.csv produced by scripts/ingest_transactions.py
"""
import pandas as pd
import re
from pathlib import Path

DATA_CSV = Path("data/transacoes_bancarias.csv")
POLICY_FILE = Path("data/politica_compliance.txt")  # for reference. :contentReference[oaicite:3]{index=3}

# RULES: basic examples mapped from policy
def rule_large_expense(row):
    # Any single expense > 500 -> requires PO
    return row['amount'] > 500.0

def rule_event_category_above_5(row):
    # "Outros" not allowed above 5 USD — approximate by description containing 'outros' or 'diversos'
    desc = str(row.get("description","")).lower()
    if ("outros" in desc or "diversos" in desc) and row['amount'] > 5.0:
        return True
    return False

def rule_prohibited_item(row):
    # List of forbidden items from Section 3
    desc = str(row.get("description","")).lower() + " " + str(row.get("beneficiary","")).lower()
    forbidden = ["stripper","algema","algemas","kit de mágica","magica","armas","nunchaku","katana","baralho marcado","pombos"]
    for f in forbidden:
        if f in desc:
            return True
    return False

RULES = [
    {"id":"R1","fn":rule_large_expense,"severity":"high","explain":"Despesa acima de US$500 requer PO e aprovação do CFO (Seção 1.3)."},
    {"id":"R2","fn":rule_event_category_above_5,"severity":"medium","explain":"Categoria 'Outros' não é aceitável para valores acima de US$5 (Seção 2)."},
    {"id":"R3","fn":rule_prohibited_item,"severity":"critical","explain":"Item proibido de acordo com Lista Negra (Seção 3)."}
]

class TransactionAgent:
    def __init__(self):
        if not DATA_CSV.exists():
            raise RuntimeError("Clean transactions CSV not found. Run scripts/ingest_transactions.py first.")
        self.df = pd.read_csv(DATA_CSV, parse_dates=["date"], dayfirst=False)
        # ensure amount numeric
        self.df['amount'] = self.df['amount'].astype(float)

    def run_rules(self):
        violations = []
        for idx, row in self.df.iterrows():
            for r in RULES:
                try:
                    if r["fn"](row):
                        violations.append({
                            "row_index": int(idx),
                            "date": str(row.get("date")),
                            "beneficiary": row.get("beneficiary"),
                            "amount": row.get("amount"),
                            "rule_id": r["id"],
                            "severity": r["severity"],
                            "explain": r["explain"],
                            "description": row.get("description")
                        })
                except Exception as e:
                    print("Error evaluating rule", r["id"], e)
        return violations

if __name__ == "__main__":
    ta = TransactionAgent()
    v = ta.run_rules()
    import json, pprint
    pprint.pprint(v)

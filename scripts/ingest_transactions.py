# scripts/ingest_transactions.py
"""
Simple CSV loader that normalizes the transactions and writes a cleaned CSV for agents.
Assumes CSV contains at least: date, description, beneficiary, amount
"""
import sys, os
# Add the workspace root to Python path
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_root)

from pathlib import Path
import pandas as pd
import re

DATA_DIR = Path("data")
IN_CSV = DATA_DIR / "transacoes_bancarias.csv"
OUT_CSV = DATA_DIR / "transacoes_bancarias.csv"

def normalize_amount(x):
    if pd.isna(x): return 0.0
    x = str(x).replace("$", "").replace(",", "").strip()
    try:
        return float(x)
    except:
        # try european format
        x = x.replace(".", "").replace(",", ".")
        try:
            return float(x)
        except:
            return 0.0

def ingest_transactions():
    df = pd.read_csv(IN_CSV)
    # normalize columns heuristic
    # lower case colnames
    df.columns = [c.strip().lower() for c in df.columns]
    # required columns: date, description, beneficiary, amount
    # try to find amount-like column
    amount_cols = [c for c in df.columns if 'amount' in c or 'valor' in c or 'amount' in c or 'value' in c]
    if len(amount_cols)==0:
        # try to guess numeric column
        numeric_cols = df.select_dtypes(include='number').columns
        amount_col = numeric_cols[0] if len(numeric_cols)>0 else df.columns[-1]
    else:
        amount_col = amount_cols[0]
    df['amount'] = df[amount_col].apply(normalize_amount)
    date_cols = [c for c in df.columns if 'date' in c or 'data' in c]
    if len(date_cols)>0:
        df['date'] = pd.to_datetime(df[date_cols[0]], errors='coerce')
    else:
        df['date'] = pd.to_datetime('today')
    # beneficiary heuristics
    beneficiary_cols = [c for c in df.columns if 'benef' in c or 'supplier' in c or 'payee' in c or 'destinatario' in c]
    if len(beneficiary_cols)>0:
        df['beneficiary'] = df[beneficiary_cols[0]]
    else:
        # try description split
        if 'description' in df.columns:
            df['beneficiary'] = df['description'].apply(lambda x: str(x).split()[0])
        else:
            df['beneficiary'] = 'unknown'
    # save cleaned CSV
    df.to_csv(OUT_CSV, index=False)
    print(f"Normalized transactions written to {OUT_CSV}")

if __name__ == "__main__":
    ingest_transactions()

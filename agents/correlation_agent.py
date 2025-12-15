# agents/correlation_agent.py
"""
Agente de Correlação: conecta transações suspeitas com evidências em e-mails.
Sistema de pontuação:
- proximidade temporal (mesmo dia = 40pts, ±1 dia = 35pts, ±2-3 dias = 25pts, ±4-7 dias = 15pts)
- correspondência semântica de beneficiário/descrição no e-mail => até 30 pontos
- menção ao valor no e-mail (exata ou aproximada) => até 20 pontos
- presença de palavras-chave suspeitas => até 10 pontos (máx. 30 no total)
- padrões de remetente/destinatário => até 15 pontos
- relevância do assunto do e-mail => até 10 pontos
Total possível: 115 pontos (normalizado para 100)
"""
from datetime import timedelta, datetime
from dateutil import parser as dtparser
from pathlib import Path
import json, re
from agents.transaction_agent import TransactionAgent
from agents.email_agent import EmailAgent, SUSPICIOUS_KEYWORDS

class CorrelationAgent:
    def __init__(self, days_window=7):
        self.ta = TransactionAgent()
        self.ea = EmailAgent()
        self.days_window = days_window
        
        # Padrões suspeitos estendidos
        self.suspicious_patterns = [
            "destruir", "apagar", "mascarar", "conta alternativa", "não conte",
            "mascarar custos", "pagar em espécie", "WUPHF", "Tech Solutions",
            "não registrar", "recibo", "walkie-talkies", "câmeras", "algemas",
            "kit de ilusionismo", "operação", "fênix", "toby", "conspiração",
            "dividir a compra", "smurf", "fazer desaparecer", "destruir evidências",
            "conta não corporativa", "cartão corporativo"
        ]
        
        # Palavras-chave financeiras que sugerem transações comerciais
        self.financial_keywords = [
            "pagamento", "fatura", "nota fiscal", "recibo", "transferência",
            "depósito", "reembolso", "compra", "venda", "contrato", "acordo"
        ]
        
        # Remetentes VIP (executivos, RH, gerência)
        self.vip_senders = [
            "michael.scott", "jan.levinson", "david.wallace", "toby.flenderson",
            "angela.martin", "oscar.martinez"
        ]

    def calculate_temporal_score(self, days_diff):
        """Calcula pontuação baseada na proximidade temporal"""
        if days_diff == 0:
            return 40  # Mesmo dia - correlação mais alta
        elif days_diff == 1:
            return 35  # Dia seguinte/anterior - muito alta
        elif days_diff <= 3:
            return 25  # Dentro de 2-3 dias - média-alta
        elif days_diff <= 5:
            return 15  # Dentro de 4-5 dias - média
        elif days_diff <= 7:
            return 8   # Dentro de 6-7 dias - baixa
        else:
            return 0

    def calculate_amount_score(self, tx_amount, email_body):
        """Verifica se o valor é mencionado no e-mail"""
        score = 0
        amount_int = int(tx_amount)
        amount_str = str(amount_int)
        
        # Correspondência exata
        if amount_str in email_body:
            score += 20
        # Correspondência aproximada (±10%)
        else:
            for nearby in range(amount_int - int(amount_int * 0.1), amount_int + int(amount_int * 0.1) + 1):
                if str(nearby) in email_body:
                    score += 15
                    break
        
        # Verifica símbolos de moeda próximos a números
        if re.search(rf'\$\s*{amount_int}\b', email_body):
            score += 5
        
        return min(score, 20)

    def calculate_keyword_score(self, email_body, email_subject):
        """Calcula pontuação baseada em palavras-chave suspeitas"""
        score = 0
        body_lower = email_body.lower()
        subject_lower = email_subject.lower()
        
        # Palavras-chave suspeitas (peso alto)
        for keyword in self.suspicious_patterns:
            if keyword in body_lower:
                score += 3
            if keyword in subject_lower:
                score += 2
        
        # Palavras-chave financeiras (peso médio)
        for keyword in self.financial_keywords:
            if keyword in body_lower:
                score += 1
        
        return min(score, 30)

    def calculate_sender_score(self, email_from):
        """Calcula pontuação baseada na importância do remetente"""
        score = 0
        email_lower = email_from.lower()
        
        # Remetentes VIP recebem pontuação de correlação mais alta
        for vip in self.vip_senders:
            if vip in email_lower:
                score += 15
                break
        
        return score

    def calculate_beneficiary_score(self, tx_benef, tx_desc, email_body, email_subject):
        """Calcula pontuação baseada na correspondência de beneficiário/descrição"""
        score = 0
        body_lower = email_body.lower()
        subject_lower = email_subject.lower()
        
        # Correspondência de beneficiário
        if tx_benef and tx_benef != "unknown" and len(tx_benef) > 3:
            if tx_benef in body_lower:
                score += 20
            if tx_benef in subject_lower:
                score += 10
        
        # Correspondência de descrição (se existir e for significativa)
        if tx_desc and len(tx_desc) > 3:
            desc_words = tx_desc.split()
            for word in desc_words:
                if len(word) > 3 and word in body_lower:
                    score += 2
        
        return min(score, 30)

    def calculate_subject_relevance(self, email_subject):
        """Calcula pontuação baseada na relevância do assunto"""
        score = 0
        subject_lower = email_subject.lower()
        
        relevant_subjects = [
            "urgente", "confidencial", "importante", "privado", "atenção",
            "pagamento", "fatura", "recibo", "transferência", "acordo"
        ]
        
        for term in relevant_subjects:
            if term in subject_lower:
                score += 3
        
        return min(score, 10)

    def correlate_all(self):
        """Correlação aprimorada com melhor pontuação"""
        results = []
        
        # Carrega e-mails parseados
        parsed_emails = []
        p = Path("data/emails_parsed.jsonl")
        if p.exists():
            with p.open("r", encoding="utf-8") as fo:
                for l in fo:
                    parsed_emails.append(json.loads(l))
        
        # Processa cada transação
        for idx, tx in self.ta.df.iterrows():
            tx_date = tx.get("date")
            tx_amount = float(tx.get("amount", 0.0))
            tx_benef = str(tx.get("beneficiary", "")).lower()
            tx_desc = str(tx.get("description", "")).lower() if 'description' in tx else ''
            
            candidates = []
            
            for e in parsed_emails:
                if not e.get("date"):
                    continue
                
                try:
                    ed = dtparser.parse(e["date"], dayfirst=False)
                except:
                    continue
                
                days_diff = abs((ed - pd_to_dt(tx_date)).days) if tx_date is not None else 9999
                
                if days_diff <= self.days_window:
                    email_body = e.get("body") or ""
                    email_subject = e.get("subject") or ""
                    email_from = e.get("from") or ""
                    
                    # Calcula pontuações individuais
                    temporal_score = self.calculate_temporal_score(days_diff)
                    amount_score = self.calculate_amount_score(tx_amount, email_body)
                    keyword_score = self.calculate_keyword_score(email_body, email_subject)
                    sender_score = self.calculate_sender_score(email_from)
                    beneficiary_score = self.calculate_beneficiary_score(
                        tx_benef, tx_desc, email_body, email_subject
                    )
                    subject_score = self.calculate_subject_relevance(email_subject)
                    
                    # Pontuação total
                    total_score = (
                        temporal_score +
                        amount_score +
                        keyword_score +
                        sender_score +
                        beneficiary_score +
                        subject_score
                    )
                    
                    # Normaliza para 100 (máximo possível é 115)
                    normalized_score = min((total_score / 115) * 100, 100)
                    
                    if normalized_score > 0:
                        candidates.append({
                            "email": e,
                            "score": normalized_score,
                            "days_diff": days_diff,
                            "score_breakdown": {
                                "temporal": temporal_score,
                                "amount": amount_score,
                                "keywords": keyword_score,
                                "sender": sender_score,
                                "beneficiary": beneficiary_score,
                                "subject": subject_score
                            }
                        })
            
            if candidates:
                candidates.sort(key=lambda x: x["score"], reverse=True)
                best = candidates[0]
                results.append({
                    "tx_index": int(idx),
                    "transaction": {
                        "date": str(tx.get("date")),
                        "beneficiary": tx.get("beneficiary"),
                        "amount": tx.get("amount"),
                        "description": tx.get("description", "")
                    },
                    "best_match": best
                })
        
        return results

def pd_to_dt(pdts):
    # função auxiliar para criar datetime do python a partir de pandas Timestamp
    if pdts is None:
        return datetime.now()
    try:
        return pdts.to_pydatetime()
    except:
        return dtparser.parse(str(pdts))

if __name__ == "__main__":
    ca = CorrelationAgent()
    out = ca.correlate_all()
    import pprint
    pprint.pprint(out)

# Dunder Auditor

Projeto: Chatbot/Agentes de Auditoria para Dunder Mifflin (Scranton).

Arquivos de dados (fornecidos):
- `data/politica_compliance.txt`. :contentReference[oaicite:4]{index=4}
- `data/emails.txt`. :contentReference[oaicite:5]{index=5}
- `/mnt/data/transacoes_bancarias.csv` -> copie para `data/`.

Instalação:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# editar .env com sua chave OPENAI_API_KEY

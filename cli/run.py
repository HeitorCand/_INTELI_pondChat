# cli/run.py
import sys, os

# Add the workspace root to Python path
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_root)

from dotenv import load_dotenv
load_dotenv()

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich import box
import subprocess
import json

from agents.rag_policy_agent import RAGPolicyAgent
from agents.email_agent import EmailAgent
from agents.transaction_agent import TransactionAgent
from agents.correlation_agent import CorrelationAgent

app = typer.Typer(help="🔍 Dunder Auditor - Sistema de Compliance")
console = Console()

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Menu interativo do Dunder Auditor"""
    if ctx.invoked_subcommand is None:
        show_menu()

@app.command()
def ingest():
    """Ingestar todos os dados (Policy, Emails, Transactions)"""
    python_path = os.path.join(workspace_root, ".venv", "bin", "python")
    if not os.path.exists(python_path):
        python_path = "python3"
    
    scripts = [
        ("Policy", "scripts/ingest_policy.py"),
        ("Emails", "scripts/ingest_emails.py"),
        ("Transactions", "scripts/ingest_transactions.py")
    ]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for name, script in scripts:
            task = progress.add_task(f"Processando {name}...", total=None)
            result = subprocess.run(
                [python_path, script], 
                cwd=workspace_root,
                capture_output=True
            )
            progress.remove_task(task)
            
            if result.returncode == 0:
                console.print(f"✅ {name} concluído", style="green")
            else:
                console.print(f"❌ {name} falhou", style="red")
                console.print(result.stderr.decode(), style="red dim")
    
    console.print("\n✨ Ingestão completa!", style="bold green")

@app.command()
def rag():
    """Responder pergunta usando RAG sobre a política de compliance"""
    console.print("\n[bold yellow]🤔 Carregando agente RAG...[/bold yellow]")
    agent = RAGPolicyAgent()
    console.print("\n[bold cyan]❓ Pergunta sobre a política:[/bold cyan]")
    q = input("➤ ")
    
    with console.status("[bold green]Processando pergunta...", spinner="dots"):
        out = agent.answer(q)
    
    # Parse the response to format it better
    try:
        lines = out.split('\n')
        resposta = ""
        razao = ""
        evidencias_text = []
        
        current_section = None
        for line in lines:
            if line.startswith('RESPOSTA:'):
                resposta = line.replace('RESPOSTA:', '').strip()
                current_section = 'resposta'
            elif line.startswith('RAZÃO:'):
                razao = line.replace('RAZÃO:', '').strip()
                current_section = 'razao'
            elif line.startswith('EVIDÊNCIAS:') or line.startswith('EVIDENCIAS:'):
                current_section = 'evidencias'
            elif current_section == 'resposta' and line.strip() and not line.startswith('RAZÃO'):
                resposta += " " + line.strip()
            elif current_section == 'razao' and line.strip() and not line.startswith('EVIDÊNCIAS') and not line.startswith('EVIDENCIAS'):
                razao += " " + line.strip()
            elif current_section == 'evidencias' and line.strip():
                evidencias_text.append(line.strip())
        
        # Display formatted response
        console.print("\n")
        console.print(Panel(resposta, title="💡 Resposta", border_style="green", box=box.ROUNDED))
        console.print(Panel(razao, title="📋 Razão", border_style="blue", box=box.ROUNDED))
        
        # Get the chunks used for this answer
        console.print("\n[bold cyan]📚 Chunks Utilizados:[/bold cyan]\n")
        hits = agent.retrieve(q)
        
        # Create table for chunks
        table = Table(title="� Evidências da Base de Conhecimento", box=box.ROUNDED, show_header=True, header_style="bold yellow")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Chunk ID", style="yellow", width=10)
        table.add_column("Score", style="green", width=12)
        table.add_column("Preview", style="white")
        
        for i, hit in enumerate(hits, 1):
            chunk_id = hit['meta'].get('chunk_id', 'N/A')
            score = f"{hit['score']:.4f}"
            text_preview = hit['meta'].get('text', '')[:80] + "..."
            
            table.add_row(
                str(i),
                str(chunk_id),
                score,
                text_preview
            )
        
        console.print(table)
        
        # Show full text of each chunk
        console.print("\n[bold cyan]📄 Texto Completo dos Chunks:[/bold cyan]\n")
        for i, hit in enumerate(hits, 1):
            chunk_id = hit['meta'].get('chunk_id', 'N/A')
            score = hit['score']
            text = hit['meta'].get('text', '')
            
            chunk_panel = f"""[bold]Score de Similaridade:[/bold] {score:.4f}

{text}"""
            
            console.print(Panel(
                chunk_panel,
                title=f"📑 Chunk #{chunk_id}",
                border_style="yellow",
                box=box.ROUNDED
            ))
        
    except Exception as e:
        # Fallback to simple output
        console.print(Panel(out, title="📄 Resposta", border_style="cyan", box=box.ROUNDED))
        console.print(f"\n[dim red]Debug: {str(e)}[/dim red]")

@app.command()
def emails():
    """Scan de e-mails para detectar conspirações"""
    console.print("\n[bold yellow]📧 Carregando agente de e-mails...[/bold yellow]")
    agent = EmailAgent()
    
    with console.status("[bold green]🔍 Analisando e-mails...", spinner="dots"):
        out = agent.detect_conspiracy()
    
    console.print("\n")
    
    if isinstance(out, dict) and 'verdict' in out:
        # Display verdict
        verdict = out.get('verdict', 'Desconhecido')
        verdict_color = "red" if verdict == "Sim" else "green"
        
        console.print(Panel(
            f"[bold {verdict_color}]{verdict}[/bold {verdict_color}]",
            title="🕵️ Conspiração Detectada?",
            border_style=verdict_color,
            box=box.DOUBLE
        ))
        
        # Display evidence
        evidence = out.get('evidence', [])
        if evidence:
            console.print(f"\n[bold yellow]📋 Evidências Encontradas: {len(evidence)}[/bold yellow]\n")
            
            # Create table for evidence
            table = Table(title="🔍 Detalhes das Evidências", box=box.ROUNDED, show_header=True, header_style="bold red")
            table.add_column("#", style="cyan", width=4)
            table.add_column("Tipo", style="yellow", width=10)
            table.add_column("De", style="green", width=20)
            table.add_column("Para", style="blue", width=20)
            table.add_column("Assunto", style="white", width=30)
            table.add_column("Indicadores", style="red")
            
            for i, ev in enumerate(evidence, 1):
                ev_type = ev.get('type', 'N/A')
                email = ev.get('email', {})
                
                if ev_type == "keyword":
                    hits = ", ".join(ev.get('hits', [])[:3])
                    table.add_row(
                        str(i),
                        "🔑 Keyword",
                        str(email.get('from', 'N/A'))[:20],
                        str(email.get('to', 'N/A'))[:20],
                        str(email.get('subject', 'N/A'))[:30],
                        hits
                    )
                elif ev_type == "semantic":
                    chunk = ev.get('chunk', {})
                    chunk_text = chunk.get('text', '')[:50]
                    table.add_row(
                        str(i),
                        "🧠 Semantic",
                        str(email.get('from', 'N/A'))[:20],
                        str(email.get('to', 'N/A'))[:20],
                        str(email.get('subject', 'N/A'))[:30],
                        chunk_text + "..."
                    )
            
            console.print(table)
            
            # Show ALL emails
            console.print(f"\n[bold cyan]📨 Todos os E-mails Suspeitos ({len(evidence)}):[/bold cyan]\n")
            for i, ev in enumerate(evidence, 1):
                email = ev.get('email', {})
                body_preview = (email.get('body', '') or '')[:200]
                
                email_panel = f"""[bold]De:[/bold] {email.get('from', 'N/A')}
[bold]Para:[/bold] {email.get('to', 'N/A')}
[bold]Assunto:[/bold] {email.get('subject', 'N/A')}
[bold]Data:[/bold] {email.get('date', 'N/A')}

[dim]{body_preview}...[/dim]"""
                
                console.print(Panel(
                    email_panel,
                    title=f"📧 E-mail #{i}",
                    border_style="yellow",
                    box=box.ROUNDED
                ))
        else:
            console.print("\n[bold green]✅ Nenhuma evidência de conspiração encontrada![/bold green]")
    else:
        # Fallback to pretty print
        import pprint
        console.print(Panel(pprint.pformat(out), title="📄 Resultado", border_style="cyan", box=box.ROUNDED))

@app.command()
def transactions():
    """Scan de transações bancárias (regras diretas)"""
    console.print("\n[bold yellow]💳 Carregando agente de transações...[/bold yellow]")
    agent = TransactionAgent()
    
    with console.status("[bold green]🔍 Analisando transações...", spinner="dots"):
        out = agent.run_rules()
    
    console.print("\n")
    
    if isinstance(out, list) and out:
        # Create table for violations
        table = Table(title="⚠️ Violações Detectadas", box=box.ROUNDED, show_header=True, header_style="bold red")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Data", style="yellow")
        table.add_column("Descrição", style="white")
        table.add_column("Valor", style="green", justify="right")
        table.add_column("Violação", style="red")
        
        for i, violation in enumerate(out, 1):
            table.add_row(
                str(i),
                str(violation.get('date', 'N/A'))[:10],
                str(violation.get('description', 'N/A'))[:40],
                f"${violation.get('amount', 0):,.2f}",
                str(violation.get('rule_violated', 'N/A'))[:50]
            )
        
        console.print(table)
        console.print(f"\n[bold red]Total de violações: {len(out)}[/bold red]")
    elif isinstance(out, list):
        console.print(Panel(
            "[bold green]✅ Nenhuma violação detectada![/bold green]",
            title="✨ Resultado",
            border_style="green",
            box=box.ROUNDED
        ))
    else:
        import pprint
        console.print(Panel(pprint.pformat(out), title="📄 Resultado", border_style="cyan", box=box.ROUNDED))

@app.command()
def correlate():
    """Correlacionar transações com e-mails e política"""
    console.print("\n[bold yellow]🔗 Carregando agente de correlação...[/bold yellow]")
    agent = CorrelationAgent()
    
    with console.status("[bold green]🔍 Correlacionando dados...", spinner="dots"):
        out = agent.correlate_all()
    
    console.print("\n")
    
    if isinstance(out, list) and out:
        total_correlations = len(out)
        
        # Classify by risk level
        high_risk = [c for c in out if c.get('best_match', {}).get('score', 0) >= 60]
        medium_risk = [c for c in out if 45 <= c.get('best_match', {}).get('score', 0) < 60]
        low_risk = [c for c in out if c.get('best_match', {}).get('score', 0) < 45]
        
        # Show summary statistics
        summary_text = f"""[bold cyan]Total de Correlações:[/bold cyan] {total_correlations}

[bold red]🔴 Alto Risco (Score ≥ 60):[/bold red] {len(high_risk)}
[bold yellow]🟡 Médio Risco (45 ≤ Score < 60):[/bold yellow] {len(medium_risk)}
[bold green]🟢 Baixo Risco (Score < 45):[/bold green] {len(low_risk)}"""
        
        console.print(Panel(summary_text, title="📊 Resumo Executivo", box=box.DOUBLE, border_style="cyan"))
        
        # Show high risk correlations first
        priority_list = high_risk + medium_risk
        
        if priority_list:
            console.print(f"\n[bold red]⚠️  ATENÇÃO: {len(priority_list)} Correlações Prioritárias Detectadas[/bold red]\n")
            show_limit = min(15, len(priority_list))
        else:
            console.print(f"\n[bold green]✅ Nenhuma correlação de alto risco detectada[/bold green]")
            console.print(f"[dim]Mostrando primeiras 10 correlações de baixo risco...[/dim]\n")
            show_limit = min(10, len(low_risk))
            priority_list = low_risk
        
        # Show detailed cards for priority correlations
        for i, corr in enumerate(priority_list[:show_limit], 1):
            tx = corr.get('transaction', {})
            match = corr.get('best_match', {})
            email = match.get('email', {})
            score = match.get('score', 0)
            breakdown = match.get('score_breakdown', {})
            
            # Create correlation card with score breakdown
            correlation_content = f"""[bold]Transação:[/bold]
  • Data: {tx.get('date', 'N/A')}
  • Valor: ${tx.get('amount', 0):,.2f}
  • Beneficiário: {tx.get('beneficiary', 'unknown')}
  • Descrição: {tx.get('description', 'N/A') or 'Vazio'}
  • Index: {corr.get('tx_index', 'N/A')}

[bold]E-mail Correlacionado:[/bold]
  • Score Total: {score:.1f}/100 pontos
  • Diferença Temporal: {match.get('days_diff', 0)} dia(s)
  • De: {email.get('from', 'N/A')}
  • Para: {email.get('to', 'N/A')}
  • Assunto: {email.get('subject', 'N/A')}
  • Data: {email.get('date', 'N/A')}

[bold]Breakdown do Score:[/bold]
  • ⏱️  Temporal: {breakdown.get('temporal', 0):.0f} pts
  • 💰 Valor Mencionado: {breakdown.get('amount', 0):.0f} pts
  • 🔑 Keywords Suspeitas: {breakdown.get('keywords', 0):.0f} pts
  • 👤 Importância Remetente: {breakdown.get('sender', 0):.0f} pts
  • 🎯 Match Beneficiário: {breakdown.get('beneficiary', 0):.0f} pts
  • 📧 Relevância Assunto: {breakdown.get('subject', 0):.0f} pts

[bold]Corpo do E-mail:[/bold]
{(email.get('body', '') or 'Sem conteúdo')[:250]}..."""
            
            # Determine border and risk level
            if score >= 60:
                border_color = "red"
                risk_emoji = "🔴"
                risk_label = "ALTO RISCO"
            elif score >= 45:
                border_color = "yellow"
                risk_emoji = "🟡"
                risk_label = "MÉDIO RISCO"
            else:
                border_color = "green"
                risk_emoji = "🟢"
                risk_label = "BAIXO RISCO"
            
            console.print(Panel(
                correlation_content,
                title=f"{risk_emoji} Correlação #{i} - {risk_label} (Score: {score:.1f})",
                border_style=border_color,
                box=box.HEAVY
            ))
        
        if len(priority_list) > show_limit:
            console.print(f"\n[dim]... e mais {len(priority_list) - show_limit} correlações prioritárias não mostradas.[/dim]")
        
        # Summary table by email sender
        console.print("\n[bold cyan]📊 Análise por Remetente:[/bold cyan]\n")
        sender_stats = {}
        
        for corr in out:
            email = corr.get('best_match', {}).get('email', {})
            sender = email.get('from', 'Unknown')
            amount = corr.get('transaction', {}).get('amount', 0)
            score = corr.get('best_match', {}).get('score', 0)
            
            if sender not in sender_stats:
                sender_stats[sender] = {
                    'count': 0,
                    'total_amount': 0,
                    'avg_score': 0,
                    'high_risk_count': 0,
                    'scores': []
                }
            
            sender_stats[sender]['count'] += 1
            sender_stats[sender]['total_amount'] += amount
            sender_stats[sender]['scores'].append(score)
            if score >= 60:
                sender_stats[sender]['high_risk_count'] += 1
        
        # Calculate averages
        for sender, stats in sender_stats.items():
            stats['avg_score'] = sum(stats['scores']) / len(stats['scores'])
        
        summary_table = Table(
            title="👥 Atividade por Remetente (Ordenado por Score Médio)",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        summary_table.add_column("Remetente", style="yellow")
        summary_table.add_column("# Total", style="cyan", justify="right")
        summary_table.add_column("# Alto Risco", style="red", justify="right")
        summary_table.add_column("Score Médio", style="white", justify="right")
        summary_table.add_column("Valor Total", style="green", justify="right")
        
        # Sort by average score (descending)
        for sender, stats in sorted(sender_stats.items(), key=lambda x: x[1]['avg_score'], reverse=True)[:20]:
            avg_score_color = "red" if stats['avg_score'] >= 60 else "yellow" if stats['avg_score'] >= 45 else "green"
            summary_table.add_row(
                sender[:45],
                str(stats['count']),
                f"[red]{stats['high_risk_count']}[/red]" if stats['high_risk_count'] > 0 else "0",
                f"[{avg_score_color}]{stats['avg_score']:.1f}[/{avg_score_color}]",
                f"${stats['total_amount']:,.2f}"
            )
        
        console.print(summary_table)
        
        # Show statistics
        console.print(f"\n[bold cyan]📈 Estatísticas Gerais:[/bold cyan]")
        total_amount = sum(c.get('transaction', {}).get('amount', 0) for c in out)
        avg_score = sum(c.get('best_match', {}).get('score', 0) for c in out) / len(out)
        
        stats_text = f"""• Total de Transações Correlacionadas: {total_correlations}
• Valor Total Movimentado: ${total_amount:,.2f}
• Score Médio: {avg_score:.1f}
• Período Analisado: {len(set(c.get('transaction', {}).get('date', '')[:10] for c in out))} datas únicas"""
        
        console.print(Panel(stats_text, border_style="blue", box=box.ROUNDED))
        
    else:
        import pprint
        console.print(Panel(pprint.pformat(out), title="📄 Resultado", border_style="cyan", box=box.ROUNDED))

def show_menu():
    """Display interactive menu and handle user choices"""
    while True:
        console.print("\n" + "="*60, style="bold blue")
        console.print("🔍 DUNDER AUDITOR - Sistema de Compliance", style="bold cyan", justify="center")
        console.print("="*60 + "\n", style="bold blue")
        
        console.print("📋 [bold yellow]Menu de Opções:[/bold yellow]\n")
        console.print("  [bold green]1.[/bold green] Ingestar tudo (Policy, Emails, Transactions)")
        console.print("  [bold green]2.[/bold green] Responder pergunta (RAG política)")
        console.print("  [bold green]3.[/bold green] Scan e-mails (conspiração)")
        console.print("  [bold green]4.[/bold green] Scan transações (regras diretas)")
        console.print("  [bold green]5.[/bold green] Correlacionar transações")
        console.print("  [bold red]0.[/bold red] Sair\n")
        console.print("="*60, style="bold blue")
        
        choice = typer.prompt("\nEscolha uma opção [0-5]")
        
        try:
            if choice == "0":
                console.print("\n👋 [bold green]Até logo![/bold green]")
                break
            elif choice == "1":
                ingest()
            elif choice == "2":
                rag()
            elif choice == "3":
                emails()
            elif choice == "4":
                transactions()
            elif choice == "5":
                correlate()
            else:
                console.print("\n❌ [bold red]Opção inválida![/bold red] Tente novamente.")
                continue
            
            console.print("\n✅ [dim]Pressione ENTER para continuar...[/dim]")
            input()
        except KeyboardInterrupt:
            console.print("\n\n👋 [bold green]Até logo![/bold green]")
            break
        except Exception as e:
            console.print(f"\n❌ [bold red]Erro:[/bold red] {str(e)}", style="red")
            console.print("\n✅ [dim]Pressione ENTER para continuar...[/dim]")
            input()

if __name__ == "__main__":
    app()

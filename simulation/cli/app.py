"""Interactive CLI client for the AI Readiness Simulation Game.

Uses Rich for beautiful terminal output. No Textual dependency issues.

Run with:  python3 -m cli [--server http://localhost:8000]
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Optional

import httpx
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text


console = Console()

DIM_NAMES = {
    1: "Data/Model Marketplace", 2: "Generated Content", 3: "Cross-Domain",
    4: "Contextualization", 5: "AI Integration", 6: "Human Interface",
    7: "Strategy Alignment", 8: "Collaboration", 9: "Human Impact",
    10: "AI & Policies", 11: "AI for Inclusion", 12: "Granular Priorities",
    13: "Digital Infrastructure",
}


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

class APIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base = base_url.rstrip("/")
        self._http = httpx.Client(base_url=self.base, timeout=600.0)

    def register(self, country: str, name: str) -> dict:
        return self._http.post("/delegates/register", json={
            "country_name": country, "delegate_name": name,
        }).json()

    def submit_scenario(self, sid: str, text: str) -> dict:
        return self._http.post(f"/delegates/{sid}/scenario", json={
            "input_text": text, "input_method": "narrative",
        }).json()

    def dashboard(self, sid: str) -> dict:
        return self._http.get(f"/game/{sid}/dashboard").json()

    def clarify(self, sid: str, question: str) -> dict:
        return self._http.post(f"/game/{sid}/clarify", json={
            "question": question,
        }).json()

    def whatif(self, sid: str, question: str) -> dict:
        return self._http.post(f"/game/{sid}/whatif", json={
            "question": question,
        }).json()

    def decide(self, sid: str, text: str) -> dict:
        return self._http.post(f"/game/{sid}/decide", json={
            "decision_text": text,
        }).json()

    def impact_preview(self, sid: str, dim: int, delta: float) -> dict:
        return self._http.post(
            f"/game/{sid}/impact-preview",
            params={"dimension_id": dim, "delta": delta},
        ).json()

    def stats(self) -> dict:
        return self._http.get("/game/stats/overview").json()

    def agents(self) -> list:
        return self._http.get("/game/agents/list").json()

    def health(self) -> bool:
        try:
            return self._http.get("/health").status_code == 200
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def show_banner():
    console.print(Panel.fit(
        "[bold cyan]AI Readiness Simulation Game[/]\n"
        "[dim]ITU AI Ready Framework 2.0 — January 2026[/]",
        border_style="cyan",
    ))


def show_help():
    console.print(Panel(
        "[bold]Commands:[/]\n\n"
        "  [cyan]assess[/]    — Submit your country scenario for assessment (F2)\n"
        "  [cyan]clarify[/]   — Ask a clarification about the framework (F3)\n"
        "  [cyan]whatif[/]    — Run a what-if analysis on a policy change (F4)\n"
        "  [cyan]decide[/]    — Announce a policy/strategy decision (F5)\n"
        "  [cyan]dashboard[/] — View current dimension scores (F6)\n"
        "  [cyan]impact[/]    — Preview causal impact of a dimension change\n"
        "  [cyan]agents[/]    — List available agents\n"
        "  [cyan]stats[/]     — Show game statistics\n"
        "  [cyan]help[/]      — Show this help\n"
        "  [cyan]quit[/]      — Exit the game\n\n"
        "[bold]13 Dimensions:[/]\n" +
        "\n".join(f"  D{k:2d}: {v}" for k, v in DIM_NAMES.items()),
        title="Help",
        border_style="green",
    ))


def show_scores_table(scores: dict):
    table = Table(title="Dimension Scores", show_header=True, header_style="bold cyan")
    table.add_column("D#", style="dim", width=4)
    table.add_column("Dimension", width=25)
    table.add_column("Score", justify="right", width=6)
    table.add_column("Maturity", width=14)
    table.add_column("Confidence", justify="right", width=10)

    for dim_id in range(1, 14):
        name = DIM_NAMES[dim_id]
        info = scores.get(name, {})
        score = info.get("score", None)

        if score is not None:
            score_str = f"{score:.1f}"
            if score >= 3.5:
                style = "green"
            elif score >= 2.0:
                style = "yellow"
            else:
                style = "red"
        else:
            score_str = "---"
            style = "dim"

        table.add_row(
            str(dim_id),
            name,
            Text(score_str, style=style),
            info.get("maturity", "---"),
            f"{info.get('confidence', 0):.0%}" if score is not None else "---",
        )
    console.print(table)


def show_assessment(resp: dict, country: str):
    console.print(f"\n[bold cyan]Assessment Results — {country}[/]")
    console.print(f"Overall Score: [bold]{resp.get('overall_score', 'N/A')}[/] / 5.0")
    console.print(f"Maturity: [bold]{resp.get('overall_maturity', 'N/A')}[/]\n")

    scores = resp.get("scores", {})
    if scores:
        show_scores_table(scores)

    gaps = resp.get("top_gaps", [])
    if gaps:
        console.print("\n[bold red]Top Gaps:[/]")
        for g in gaps[:5]:
            console.print(f"  [{g.get('priority', '')}] {g.get('dimension_name', '')} — {g.get('score', 0):.1f}/5.0")

    strengths = resp.get("top_strengths", [])
    if strengths:
        console.print("\n[bold green]Top Strengths:[/]")
        for s in strengths[:3]:
            console.print(f"  {s.get('dimension', '')} — {s.get('score', 0):.1f}/5.0")


def show_whatif(resp: dict, country: str):
    console.print(f"\n[bold cyan]What-If Analysis — {country}[/]")
    console.print(f"Question: [italic]{resp.get('question', '')}[/]\n")

    comp = resp.get("comparison", {})
    if isinstance(comp, dict) and "dimensions" in comp:
        console.print(f"Overall: {comp.get('overall_before', 0):.2f} → {comp.get('overall_after', 0):.2f} ({comp.get('overall_delta', 0):+.2f})")

        improved = comp.get("improved", [])
        if improved:
            console.print("\n[green]Improved:[/]")
            for d in improved:
                console.print(f"  D{d['dimension_id']} {d['dimension_name']}: {d['before']:.1f} → {d['after']:.1f} ({d['delta']:+.2f})")

        declined = comp.get("declined", [])
        if declined:
            console.print("\n[red]Declined:[/]")
            for d in declined:
                console.print(f"  D{d['dimension_id']} {d['dimension_name']}: {d['before']:.1f} → {d['after']:.1f} ({d['delta']:+.2f})")

    causal = resp.get("causal_effects", {})
    if causal:
        console.print("\n[yellow]Causal Cascade Effects:[/]")
        for dim_id, effect in causal.items():
            dname = DIM_NAMES.get(int(dim_id), f"D{dim_id}")
            console.print(f"  D{dim_id} ({dname}): {effect:+.3f}")

    narrative = resp.get("agent_narrative", "")
    if narrative:
        console.print(f"\n[dim]Agent Analysis:[/] {narrative[:500]}")


def show_decision(resp: dict, country: str):
    console.print(f"\n[bold cyan]Decision Recorded — {country}[/]")
    console.print(f"Decision: [italic]{resp.get('decision', '')}[/]")
    console.print(f"Decision ID: {resp.get('decision_id', '')}")
    console.print(f"Affected Dimensions: {resp.get('affected_dimensions', [])}\n")

    comp = resp.get("comparison")
    if comp and isinstance(comp, dict) and "dimensions" in comp:
        console.print(f"Overall: {comp.get('overall_before', 0):.2f} → {comp.get('overall_after', 0):.2f} ({comp.get('overall_delta', 0):+.2f})")
        for d in comp.get("dimensions", []):
            if d["delta"] != 0:
                color = "green" if d["delta"] > 0 else "red"
                console.print(f"  [{color}]D{d['dimension_id']} {d['dimension_name']}: {d['before']:.1f} → {d['after']:.1f} ({d['delta']:+.2f})[/]")

    narrative = resp.get("agent_narrative", "")
    if narrative:
        console.print(f"\n[dim]Agent Analysis:[/] {narrative[:500]}")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AI Readiness Simulation Game — CLI")
    parser.add_argument("--server", default="http://localhost:8000", help="Server URL")
    args = parser.parse_args()

    api = APIClient(args.server)

    show_banner()

    # Check server
    if not api.health():
        console.print("[bold red]Server not reachable![/]")
        console.print(f"Start the server first:\n  cd simulation && PYTHONPATH=. python3 -m server.main")
        sys.exit(1)

    console.print("[green]Server connected.[/]\n")

    # Registration
    country = Prompt.ask("[cyan]Country name[/]", default="Ethiopia")
    delegate = Prompt.ask("[cyan]Delegate name[/]", default="Delegate")

    with console.status("Registering..."):
        resp = api.register(country, delegate)

    session_id = resp["session_id"]
    console.print(f"\n[green]Registered![/] Session: {session_id[:8]}...")
    console.print(f"Welcome, [bold]{delegate}[/] representing [bold]{country}[/].\n")
    console.print("Type [cyan]help[/] for commands.\n")

    # REPL
    while True:
        try:
            raw = Prompt.ask(f"[bold cyan]{country}[/]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/]")
            break

        cmd = raw.strip().lower()

        if not cmd:
            continue

        elif cmd in ("quit", "exit", "q"):
            console.print("[dim]Goodbye![/]")
            break

        elif cmd in ("help", "h", "?"):
            show_help()

        elif cmd == "agents":
            agents = api.agents()
            table = Table(title="Agents", header_style="bold cyan")
            table.add_column("Agent", width=20)
            table.add_column("Dimensions", width=15)
            table.add_column("Description", width=50)
            for a in agents:
                table.add_row(a["name"], str(a["dimensions"]), a["description"][:50])
            console.print(table)

        elif cmd == "stats":
            with console.status("Loading..."):
                st = api.stats()
            console.print_json(data=st)

        elif cmd == "dashboard":
            with console.status("Loading dashboard..."):
                resp = api.dashboard(session_id)
            scenario = resp.get("scenario")
            if scenario:
                show_scores_table(scenario.get("scores", {}))
                console.print(f"\nOverall: [bold]{scenario.get('overall_score', 'N/A')}[/] — {scenario.get('overall_maturity', 'N/A')}")
                decisions = resp.get("decisions", [])
                if decisions:
                    console.print(f"\nDecisions ({len(decisions)}):")
                    for d in decisions[-5:]:
                        console.print(f"  - {d['text'][:70]}")
            else:
                console.print("[yellow]No scenario assessed yet. Use 'assess' first.[/]")

        elif cmd == "assess":
            console.print("[dim]Describe your country's AI readiness status.[/]")
            console.print("[dim]Include details about data, infrastructure, policies, skills, etc.[/]")
            console.print("[dim]Type your description (press Enter twice to submit):[/]\n")

            lines = []
            while True:
                try:
                    line = input()
                except EOFError:
                    break
                if line == "" and lines and lines[-1] == "":
                    lines.pop()
                    break
                lines.append(line)
            text = "\n".join(lines).strip()
            if not text:
                console.print("[yellow]No input provided.[/]")
                continue

            try:
                with console.status("[bold]Assessing — 6 agents analyzing your scenario (this may take a few minutes)...[/]"):
                    resp = api.submit_scenario(session_id, text)
                show_assessment(resp, country)
            except httpx.ReadTimeout:
                console.print("[red]Assessment timed out. The LLM may be overloaded. Try again.[/]")
            except Exception as e:
                console.print(f"[red]Assessment failed: {e}[/]")

        elif cmd == "clarify":
            question = Prompt.ask("[cyan]Your question[/]")
            if not question.strip():
                continue
            try:
                with console.status("Processing clarification..."):
                    resp = api.clarify(session_id, question)
                console.print(f"\n[bold cyan]Clarification[/]")
                console.print(f"Q: [italic]{resp.get('question', question)}[/]")
                answer = resp.get('answer', 'No answer')
                console.print(Panel(answer, title="Answer", border_style="cyan"))
                console.print(f"Related Dimensions: {resp.get('related_dimensions', [])}")
                console.print(f"Agent: {resp.get('agent', 'unknown')}")
            except httpx.ReadTimeout:
                console.print("[red]Timed out. Try again.[/]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/]")

        elif cmd == "whatif":
            question = Prompt.ask("[cyan]What-if question[/]")
            if not question.strip():
                continue
            try:
                with console.status("[bold]Running what-if analysis (cache + agents + causal graph)...[/]"):
                    resp = api.whatif(session_id, question)
                show_whatif(resp, country)
            except httpx.ReadTimeout:
                console.print("[red]What-if timed out. Try again.[/]")
            except Exception as e:
                console.print(f"[red]What-if failed: {e}[/]")

        elif cmd == "decide":
            decision = Prompt.ask("[cyan]Policy/strategy decision[/]")
            if not decision.strip():
                continue
            try:
                with console.status("[bold]Recording decision and recalculating scores...[/]"):
                    resp = api.decide(session_id, decision)
                show_decision(resp, country)
            except httpx.ReadTimeout:
                console.print("[red]Decision timed out. Try again.[/]")
            except Exception as e:
                console.print(f"[red]Decision failed: {e}[/]")

        elif cmd == "impact":
            try:
                dim = int(Prompt.ask("[cyan]Dimension ID (1-13)[/]"))
                delta = float(Prompt.ask("[cyan]Score change (e.g. +1.0 or -0.5)[/]"))
            except ValueError:
                console.print("[red]Invalid input.[/]")
                continue
            resp = api.impact_preview(session_id, dim, delta)
            console.print(f"\n[bold cyan]Impact Preview: D{dim} ({DIM_NAMES.get(dim, '?')}) {delta:+.1f}[/]")
            effects = resp.get("cascading_effects", {})
            if effects:
                for d, e in effects.items():
                    dname = DIM_NAMES.get(int(d), f"D{d}")
                    color = "green" if e > 0 else "red"
                    console.print(f"  [{color}]D{d} ({dname}): {e:+.3f}[/]")
            else:
                console.print("  [dim]No cascading effects.[/]")

        else:
            # Default: treat as clarification question
            try:
                with console.status("Processing (first query may take a minute while the LLM loads)..."):
                    resp = api.clarify(session_id, raw)
                console.print(f"\n[bold cyan]Answer[/]")
                console.print(resp.get("answer", "No answer"))
                dims = resp.get("related_dimensions", [])
                if dims:
                    console.print(f"[dim]Related dimensions: {dims}[/]")
            except httpx.ReadTimeout:
                console.print("[red]Request timed out. The LLM may still be loading. Try again.[/]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/]")


if __name__ == "__main__":
    main()

"""
Web UI — FastAPI + HTMX web interface for the Horror GameMaster.

Provides a browser-based horror experience with atmospheric design,
dark mode, and HTMX for seamless interactions.

Horror GameMaster — BrierStudios
"""

from __future__ import annotations

import json
from typing import Optional

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from gamemaster import GameMaster, GameConfig


# ── HTML Template ────────────────────────────────────────────────────

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Horror GameMaster</title>
    <script src="https://unpkg.com/htmx.org@1.9.8"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;700&display=swap');

        :root {
            --bg: #0a0a0a;
            --bg-secondary: #111111;
            --text: #c8c8c8;
            --text-dim: #666666;
            --accent: #8b0000;
            --accent-bright: #cc0000;
            --border: #1a1a1a;
            --glow: 0 0 10px rgba(139, 0, 0, 0.3);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'Crimson Text', serif;
            font-size: 18px;
            line-height: 1.8;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .container {
            max-width: 720px;
            width: 100%;
            padding: 2rem;
            margin: 0 auto;
        }

        /* Header */
        .header {
            text-align: center;
            padding: 3rem 0 2rem;
            border-bottom: 1px solid var(--border);
            margin-bottom: 2rem;
        }

        .header h1 {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.5rem;
            letter-spacing: 0.3em;
            color: var(--accent);
            text-shadow: var(--glow);
        }

        .header .subtitle {
            font-size: 0.9rem;
            color: var(--text-dim);
            margin-top: 0.5rem;
        }

        /* HUD */
        .hud {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            padding: 1rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 4px;
            margin-bottom: 2rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
        }

        .hud-item {
            text-align: center;
        }

        .hud-label {
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }

        .hud-value {
            color: var(--text);
            font-weight: 700;
            margin-top: 0.25rem;
        }

        /* Tension Bar */
        .tension-bar {
            width: 100%;
            height: 4px;
            background: var(--border);
            border-radius: 2px;
            overflow: hidden;
            margin-top: 0.5rem;
        }

        .tension-fill {
            height: 100%;
            background: var(--accent);
            transition: width 0.5s ease, background 0.5s ease;
            box-shadow: var(--glow);
        }

        /* Narrative */
        .narrative {
            padding: 2rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 4px;
            margin-bottom: 2rem;
            min-height: 200px;
            animation: fadeIn 1s ease;
        }

        .narrative p {
            margin-bottom: 1rem;
        }

        .narrative p:last-child {
            margin-bottom: 0;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Choices */
        .choices {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }

        .choice {
            display: block;
            padding: 1rem 1.5rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 4px;
            color: var(--text);
            font-family: 'Crimson Text', serif;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: left;
            width: 100%;
        }

        .choice:hover {
            border-color: var(--accent);
            background: rgba(139, 0, 0, 0.1);
            box-shadow: var(--glow);
            transform: translateX(4px);
        }

        .choice-number {
            color: var(--accent-bright);
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            margin-right: 0.75rem;
        }

        /* Free Input */
        .free-input {
            display: flex;
            gap: 0.75rem;
            margin-top: 1rem;
        }

        .free-input input {
            flex: 1;
            padding: 0.75rem 1rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 4px;
            color: var(--text);
            font-family: 'Crimson Text', serif;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.3s ease;
        }

        .free-input input:focus {
            border-color: var(--accent);
            box-shadow: var(--glow);
        }

        .free-input button {
            padding: 0.75rem 1.5rem;
            background: var(--accent);
            border: none;
            border-radius: 4px;
            color: white;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            cursor: pointer;
            transition: background 0.3s ease;
        }

        .free-input button:hover {
            background: var(--accent-bright);
        }

        /* Loading */
        .loading {
            text-align: center;
            color: var(--text-dim);
            padding: 2rem;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 0.5; }
            50% { opacity: 1; }
        }

        /* Entity indicator */
        .entity-alert {
            color: #ff4444;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            padding: 0.5rem;
            border: 1px solid #ff4444;
            border-radius: 4px;
            margin-bottom: 1rem;
            animation: flicker 3s infinite;
        }

        @keyframes flicker {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.8; }
            25%, 75% { opacity: 0.9; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>HORROR GAMEMASTER</h1>
            <div class="subtitle">BrierStudios — Procedural Terror Engine</div>
        </div>

        <div id="game">
            <!-- HUD -->
            <div class="hud" id="hud">
                <div class="hud-item">
                    <div class="hud-label">Tension</div>
                    <div class="hud-value" id="tension-value">CALM</div>
                    <div class="tension-bar">
                        <div class="tension-fill" id="tension-bar" style="width: 10%"></div>
                    </div>
                </div>
                <div class="hud-item">
                    <div class="hud-label">Level</div>
                    <div class="hud-value" id="level-value">1/10</div>
                </div>
                <div class="hud-item">
                    <div class="hud-label">Bravery</div>
                    <div class="hud-value" id="bravery-value">NERVOUS</div>
                </div>
                <div class="hud-item">
                    <div class="hud-label">Turn</div>
                    <div class="hud-value" id="turn-value">0</div>
                </div>
            </div>

            <!-- Narrative -->
            <div class="narrative" id="narrative">
                <div class="loading">The darkness gathers...</div>
            </div>

            <!-- Choices -->
            <div class="choices" id="choices">
                <button class="choice" hx-post="/start" hx-target="#game" hx-swap="innerHTML">
                    <span class="choice-number">[▶]</span> Begin the nightmare
                </button>
            </div>
        </div>
    </div>

    <script>
        // Update HUD from response headers
        document.addEventListener('htmx:afterRequest', function(event) {
            const headers = event.detail.xhr.getResponseHeader;
            if (headers('X-Tension')) {
                document.getElementById('tension-value').textContent = headers('X-Tension-State');
                document.getElementById('tension-bar').style.width = (parseFloat(headers('X-Tension')) * 100) + '%';
                document.getElementById('level-value').textContent = headers('X-Level') + '/10';
                document.getElementById('bravery-value').textContent = headers('X-Bravery');
                document.getElementById('turn-value').textContent = headers('X-Turn');
            }
        });
    </script>
</body>
</html>
"""


# ── Game State for Web ───────────────────────────────────────────────


class WebGameState:
    """Manages game state for the web interface."""

    def __init__(self):
        self.gm: Optional[GameMaster] = None
        self.started: bool = False

    def start(self) -> dict:
        """Start a new game."""
        self.gm = GameMaster(GameConfig(
            session_id="web_session",
            pacing=0.5,
            enable_npc=True,
            enable_doppelganger=True,
        ))
        self.started = True
        state = self.gm.start()
        return self._state_to_dict(state)

    def action(self, player_input: str) -> dict:
        """Process a player action."""
        if not self.gm:
            return self.start()
        state = self.gm.process_action(player_input)
        return self._state_to_dict(state)

    def _state_to_dict(self, state) -> dict:
        """Convert GameState to dict for web rendering."""
        return {
            "narrative": state.narrative,
            "choices": state.choices,
            "tension": self.gm.tension.tension,
            "tension_state": self.gm.tension.state.value,
            "level": self.gm.tension.escalation_level,
            "bravery": self.gm.analyzer.get_bravery_index().value,
            "turn": state.turn,
            "location": state.location,
            "game_over": state.game_over,
            "ending": state.ending,
        }


# ── FastAPI App ──────────────────────────────────────────────────────


def create_app() -> "FastAPI":
    """Create the FastAPI application."""
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI is required: pip install fastapi uvicorn")

    app = FastAPI(title="Horror GameMaster", version="1.0.0")
    game_state = WebGameState()

    @app.get("/", response_class=HTMLResponse)
    async def index():
        """Serve the main page."""
        return HTML_TEMPLATE

    @app.post("/start")
    async def start_game():
        """Start a new game."""
        state = game_state.start()
        return _render_game(state)

    @app.post("/action")
    async def player_action(request: Request):
        """Process a player action."""
        form = await request.form()
        player_input = form.get("input", "")
        if not player_input:
            # Get from choice
            player_input = form.get("choice", "")
        state = game_state.action(str(player_input))
        return _render_game(state)

    def _render_game(state: dict) -> HTMLResponse:
        """Render the game state as HTML."""
        narrative_html = ""
        for para in state["narrative"].split("\n\n"):
            if para.strip():
                narrative_html += f"<p>{para.strip()}</p>"

        choices_html = ""
        for i, choice in enumerate(state["choices"], 1):
            choices_html += f"""
            <button class="choice"
                    hx-post="/action"
                    hx-vals='{{"choice": "{choice}"}}'
                    hx-target="#game"
                    hx-swap="innerHTML">
                <span class="choice-number">[{i}]</span> {choice}
            </button>
            """

        if state["game_over"]:
            choices_html = f"""
            <div class="narrative">
                <p><strong>ENDING</strong></p>
                <p>{state['ending']}</p>
            </div>
            <button class="choice" hx-post="/start" hx-target="#game" hx-swap="innerHTML">
                <span class="choice-number">[▶]</span> Play again
            </button>
            """

        tension_pct = int(state["tension"] * 100)
        tension_state = state["tension_state"].upper()

        html = f"""
        <!-- HUD -->
        <div class="hud" id="hud">
            <div class="hud-item">
                <div class="hud-label">Tension</div>
                <div class="hud-value">{tension_state}</div>
                <div class="tension-bar">
                    <div class="tension-fill" style="width: {tension_pct}%"></div>
                </div>
            </div>
            <div class="hud-item">
                <div class="hud-label">Level</div>
                <div class="hud-value">{state['level']}/10</div>
            </div>
            <div class="hud-item">
                <div class="hud-label">Bravery</div>
                <div class="hud-value">{state['bravery'].upper()}</div>
            </div>
            <div class="hud-item">
                <div class="hud-label">Turn</div>
                <div class="hud-value">{state['turn']}</div>
            </div>
        </div>

        <!-- Narrative -->
        <div class="narrative" id="narrative">
            {narrative_html}
        </div>

        <!-- Choices -->
        <div class="choices" id="choices">
            {choices_html}
            <div class="free-input">
                <input type="text" name="input" placeholder="Or type your own action..."
                       hx-post="/action"
                       hx-trigger="keydown[key=='Enter']"
                       hx-target="#game"
                       hx-swap="innerHTML"
                       hx-vals='{{"input": ""}}'
                       _="on keydown[key=='Enter'] if my.value != '' then
                            set @hx-vals to JSON.stringify({{input: my.value}})
                          end">
                <button hx-post="/action"
                        hx-include="[name='input']"
                        hx-target="#game"
                        hx-swap="innerHTML">
                    ACT
                </button>
            </div>
        </div>
        """

        return HTMLResponse(content=html)

    return app


# ── Entry Point ──────────────────────────────────────────────────────


def main():
    """Run the web server."""
    import argparse

    parser = argparse.ArgumentParser(description="Horror GameMaster — Web UI")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    args = parser.parse_args()

    if not FASTAPI_AVAILABLE:
        print("FastAPI not installed. Install with: pip install fastapi uvicorn")
        return

    app = create_app()

    import uvicorn
    print(f"\n  Horror GameMaster Web UI")
    print(f"  http://{args.host}:{args.port}\n")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

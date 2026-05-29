"""
Terminal UI — Rich-based terminal interface for the Horror GameMaster.

Immersive horror experience with typing effects, color-coded narration,
tension visualization, and choice system.

Horror GameMaster — BrierStudios
"""

from __future__ import annotations

import time


try:
    from rich.align import Align
    from rich.columns import Columns
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress_bar import ProgressBar
    from rich.style import Style
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from gamemaster import GameConfig, GameMaster, GameState
from pattern_analyzer import BraveryIndex
from tension_manager import TensionState


# ── Color Palette ────────────────────────────────────────────────────


class HorrorColors:
    """Color palette for the horror terminal UI."""

    # Tension states
    CALM = "dim white"
    UNEASY = "yellow"
    TENSE = "dark_orange"
    TERRIFYING = "red"
    PEAK = "bold bright_red"
    AFTERMATH = "dim cyan"

    # UI elements
    NARRATIVE = "white"
    CHOICE = "cyan"
    CHOICE_NUMBER = "bold bright_cyan"
    HUD = "dim white"
    HUD_VALUE = "bold white"
    ENTITY = "bold magenta"
    NPC = "bold yellow"
    DOPPELGANGER = "bold bright_magenta"
    DIVIDER = "dim bright_black"
    PROMPT = "bold bright_cyan"
    ERROR = "bold red"
    SUCCESS = "green"

    # Fear types
    FEAR_COLORS = {
        "psychological": "magenta",
        "darkness": "bright_black",
        "isolation": "dim cyan",
        "body_horror": "dark_red",
        "paranoia": "yellow",
        "loss_of_control": "red",
        "jumpscare": "bright_red",
        "false_security": "green",
    }


# ── Terminal UI ──────────────────────────────────────────────────────


class HorrorTerminalUI:
    """
    Rich-based terminal UI for the Horror GameMaster.

    Provides an immersive horror experience with:
    - Typing effect for narrative text
    - Color-coded narration based on tension
    - Tension bar visualization
    - Choice system with numbered options
    - HUD showing game state
    - Dividers and atmospheric formatting

    Usage:
        ui = HorrorTerminalUI()
        ui.run()
    """

    def __init__(self, config: GameConfig | None = None):
        if not RICH_AVAILABLE:
            raise ImportError("Rich is required: pip install rich")

        self.console = Console()
        self.gm = GameMaster(
            config
            or GameConfig(
                session_id="terminal_session",
                pacing=0.5,
                enable_npc=True,
                enable_doppelganger=True,
            )
        )
        self.state: GameState | None = None
        self._typing_speed = 0.03  # Seconds per character
        self._running = False

    # ── Main Loop ────────────────────────────────────────────────────

    def run(self) -> None:
        """Run the main game loop."""
        self._running = True
        self._show_intro()
        self.state = self.gm.start()

        while self._running and not self.state.game_over:
            self._display_state()
            action = self._get_choice()
            if action is None:
                break
            self.state = self.gm.process_action(action)

        if self.state.game_over:
            self._show_ending()

        self._show_outro()

    # ── Display ──────────────────────────────────────────────────────

    def _show_intro(self) -> None:
        """Show the game introduction."""
        self.console.clear()
        self.console.print()

        title = """
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║              ᚺ  O  R  R  O  R                           ║
    ║              G  A  M  E  M  A  S  T  E  R               ║
    ║                                                          ║
    ║              ─── BrierStudios ───                        ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
        """
        self.console.print(title, style="bold bright_red")
        self.console.print()
        self._type_text("The darkness awaits. Your fears will be your guide.", style="dim white")
        self.console.print()
        self._type_text("Press Enter to begin...", style="dim cyan")
        input()

    def _show_outro(self) -> None:
        """Show the game outro."""
        self.console.print()
        self.console.print("═" * 60, style=HorrorColors.DIVIDER)
        self.console.print()
        self._type_text("The session ends. The darkness retreats. For now.", style="dim white")
        self.console.print()
        self.console.print("Thank you for playing Horror GameMaster.", style="dim cyan")
        self.console.print()

    def _show_ending(self) -> None:
        """Show the game ending."""
        self.console.print()
        self.console.print("═" * 60, style=HorrorColors.DIVIDER)
        self.console.print()
        self.console.print("ENDING", style="bold bright_red", justify="center")
        self.console.print()
        self._type_text(self.state.ending, style="white")
        self.console.print()

    def _display_state(self) -> None:
        """Display the current game state."""
        # Divider
        self.console.print()
        self.console.print("─" * 60, style=HorrorColors.DIVIDER)

        # HUD
        self._display_hud()

        # Narrative
        self.console.print()
        self._display_narrative()

        # Choices
        self.console.print()
        self._display_choices()

    def _display_hud(self) -> None:
        """Display the game HUD."""
        tension = self.gm.tension
        analyzer = self.gm.analyzer

        # Tension bar
        tension_color = self._get_tension_color(tension.state)
        tension_bar = self._make_tension_bar(tension.tension)
        tension_text = Text()
        tension_text.append("  TENSION ", style=HorrorColors.HUD)
        tension_text.append(f"[{tension.state.value.upper()}]", style=tension_color)
        tension_text.append(f" {tension_bar}", style=tension_color)

        # Escalation
        escalation = tension.get_escalation_level()
        esc_text = Text()
        esc_text.append("  LEVEL   ", style=HorrorColors.HUD)
        esc_text.append(f"{escalation.level}/10", style=HorrorColors.HUD_VALUE)
        esc_text.append(f" ({escalation.name})", style="dim white")

        # Bravery
        bravery = analyzer.get_bravery_index()
        brave_text = Text()
        brave_text.append("  BRAVERY ", style=HorrorColors.HUD)
        brave_text.append(f"{bravery.value.upper()}", style=self._get_bravery_color(bravery))

        # Turn
        turn_text = Text()
        turn_text.append("  TURN    ", style=HorrorColors.HUD)
        turn_text.append(f"{self.state.turn}", style=HorrorColors.HUD_VALUE)

        # Location
        loc_text = Text()
        loc_text.append("  WHERE   ", style=HorrorColors.HUD)
        loc_text.append(self.state.location, style=HorrorColors.HUD_VALUE)

        # Print HUD
        self.console.print(tension_text)
        self.console.print(esc_text)
        self.console.print(brave_text)
        self.console.print(turn_text)
        self.console.print(loc_text)

        # Cooldown indicator
        if tension.cooldown.state.value == "active":
            self.console.print("  ⏳ COOLDOWN ACTIVE", style="dim yellow")

        # False security indicator
        if tension.false_security.active:
            self.console.print("  🕊️ FALSE SECURITY", style="dim green")

    def _display_narrative(self) -> None:
        """Display the narrative with typing effect."""
        narrative = self.state.narrative
        if not narrative:
            return

        # Determine style based on tension
        tension_state = self.gm.tension.state
        if tension_state == TensionState.PEAK:
            style = HorrorColors.PEAK
        elif tension_state == TensionState.TERRIFYING:
            style = HorrorColors.TERRIFYING
        elif tension_state == TensionState.TENSE:
            style = HorrorColors.TENSE
        elif tension_state == TensionState.AFTERMATH:
            style = HorrorColors.AFTERMATH
        else:
            style = HorrorColors.NARRATIVE

        self.console.print()
        self._type_text(narrative, style=style)

    def _display_choices(self) -> None:
        """Display the player's choices."""
        choices = self.state.choices
        if not choices:
            return

        self.console.print()
        self.console.print("  What do you do?", style=HorrorColors.PROMPT)
        self.console.print()

        for i, choice in enumerate(choices, 1):
            number_text = Text()
            number_text.append(f"    [{i}] ", style=HorrorColors.CHOICE_NUMBER)
            number_text.append(choice, style=HorrorColors.CHOICE)
            self.console.print(number_text)

        self.console.print()

    # ── Input ────────────────────────────────────────────────────────

    def _get_choice(self) -> str | None:
        """Get player's choice."""
        choices = self.state.choices
        if not choices:
            return self._get_free_input()

        while True:
            try:
                self.console.print("  > ", style=HorrorColors.PROMPT, end="")
                user_input = input().strip()

                if not user_input:
                    continue

                if user_input.lower() in ("quit", "exit", "q"):
                    self._running = False
                    return None

                # Check if it's a number choice
                if user_input.isdigit():
                    idx = int(user_input) - 1
                    if 0 <= idx < len(choices):
                        return choices[idx]
                    else:
                        self.console.print(f"  Choose 1-{len(choices)}", style=HorrorColors.ERROR)
                        continue

                # Free text input
                return user_input

            except (KeyboardInterrupt, EOFError):
                self._running = False
                return None

    def _get_free_input(self) -> str | None:
        """Get free text input."""
        try:
            self.console.print("  > ", style=HorrorColors.PROMPT, end="")
            user_input = input().strip()
            if user_input.lower() in ("quit", "exit", "q"):
                self._running = False
                return None
            return user_input
        except (KeyboardInterrupt, EOFError):
            self._running = False
            return None

    # ── Typing Effect ────────────────────────────────────────────────

    def _type_text(self, text: str, style: str = "white") -> None:
        """Display text with a typing effect."""
        styled_text = Text(style=style)
        for char in text:
            styled_text.append(char)
            self.console.print(styled_text, end="")
            styled_text = Text(style=style)
            if char in ".!?\n":
                time.sleep(self._typing_speed * 3)
            elif char == ",":
                time.sleep(self._typing_speed * 2)
            elif char != " ":
                time.sleep(self._typing_speed)
        self.console.print()  # Newline

    # ── Tension Visualization ────────────────────────────────────────

    def _make_tension_bar(self, tension: float) -> str:
        """Create a visual tension bar."""
        width = 20
        filled = int(tension * width)
        empty = width - filled

        if tension < 0.3:
            bar_char = "░"
        elif tension < 0.6:
            bar_char = "▒"
        elif tension < 0.8:
            bar_char = "▓"
        else:
            bar_char = "█"

        return f"[{bar_char * filled}{'·' * empty}] {tension:.0%}"

    def _get_tension_color(self, state: TensionState) -> str:
        """Get color for tension state."""
        colors = {
            TensionState.CALM: HorrorColors.CALM,
            TensionState.UNEASY: HorrorColors.UNEASY,
            TensionState.TENSE: HorrorColors.TENSE,
            TensionState.TERRIFYING: HorrorColors.TERRIFYING,
            TensionState.PEAK: HorrorColors.PEAK,
            TensionState.AFTERMATH: HorrorColors.AFTERMATH,
        }
        return colors.get(state, "white")

    def _get_bravery_color(self, bravery: BraveryIndex) -> str:
        """Get color for bravery index."""
        colors = {
            BraveryIndex.FROZEN: "bold bright_red",
            BraveryIndex.PANICKING: "red",
            BraveryIndex.NERVOUS: "yellow",
            BraveryIndex.BRAVE: "green",
            BraveryIndex.FEARLESS: "bold bright_green",
        }
        return colors.get(bravery, "white")


# ── Simple CLI (no Rich) ─────────────────────────────────────────────


class SimpleHorrorUI:
    """
    Simple terminal UI without Rich dependency.
    Fallback for systems without Rich installed.
    """

    def __init__(self, config: GameConfig | None = None):
        self.gm = GameMaster(config or GameConfig(session_id="simple_session"))
        self.state: GameState | None = None
        self._running = False

    def run(self) -> None:
        """Run the game loop."""
        self._running = True
        print("\n" + "=" * 60)
        print("  HORROR GAMEMASTER — BrierStudios")
        print("=" * 60)
        print("\nPress Enter to begin...")
        input()

        self.state = self.gm.start()

        while self._running and not self.state.game_over:
            self._display_state()
            action = self._get_input()
            if action is None:
                break
            self.state = self.gm.process_action(action)

        if self.state.game_over:
            print("\n" + "=" * 60)
            print("  ENDING")
            print("=" * 60)
            print(self.state.ending)

        print("\nThank you for playing Horror GameMaster.\n")

    def _display_state(self) -> None:
        """Display game state."""
        print(f"\n{'─' * 60}")
        print(f"  TENSION: [{self.gm.tension.state.value.upper()}] {self.gm.tension.tension:.0%}")
        print(
            f"  LEVEL:   {self.gm.tension.escalation_level}/10 ({self.gm.tension.get_escalation_level().name})"
        )
        print(f"  TURN:    {self.state.turn}")
        print(f"  WHERE:   {self.state.location}")
        print(f"{'─' * 60}")
        print()

        # Narrative
        print(self.state.narrative)
        print()

        # Choices
        if self.state.choices:
            print("  What do you do?")
            for i, choice in enumerate(self.state.choices, 1):
                print(f"    [{i}] {choice}")
            print()

    def _get_input(self) -> str | None:
        """Get player input."""
        choices = self.state.choices
        try:
            user_input = input("  > ").strip()
            if not user_input:
                return None
            if user_input.lower() in ("quit", "exit", "q"):
                self._running = False
                return None
            if user_input.isdigit() and choices:
                idx = int(user_input) - 1
                if 0 <= idx < len(choices):
                    return choices[idx]
            return user_input
        except (KeyboardInterrupt, EOFError):
            self._running = False
            return None


# ── Entry Point ──────────────────────────────────────────────────────


def main():
    """Entry point for the Horror GameMaster terminal UI."""
    import argparse

    parser = argparse.ArgumentParser(description="Horror GameMaster — Terminal UI")
    parser.add_argument("--simple", action="store_true", help="Use simple UI (no Rich)")
    parser.add_argument("--pacing", type=float, default=0.5, help="Pacing (0=slow, 1=fast)")
    parser.add_argument("--fear", default="psychological", help="Primary fear type")
    parser.add_argument("--voice", default="detached", help="Narrator voice")
    parser.add_argument("--no-npc", action="store_true", help="Disable NPCs")
    parser.add_argument("--no-doppelganger", action="store_true", help="Disable doppelganger")
    args = parser.parse_args()

    config = GameConfig(
        session_id="cli_session",
        pacing=args.pacing,
        fear_type_focus=args.fear,
        narrator_voice=args.voice,
        enable_npc=not args.no_npc,
        enable_doppelganger=not args.no_doppelganger,
    )

    if args.simple or not RICH_AVAILABLE:
        ui = SimpleHorrorUI(config)
    else:
        ui = HorrorTerminalUI(config)

    ui.run()


if __name__ == "__main__":
    main()

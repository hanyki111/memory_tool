"""Interactive tutorial system for memory_tool."""

from typing import List, Dict
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


class Tutorial:
    """Interactive tutorial for memory_tool commands."""

    def __init__(self):
        """Initialize tutorial."""
        self.console = Console()
        self.lessons = self._get_lessons()

    def _get_lessons(self) -> List[Dict]:
        """Get tutorial lessons.

        Returns:
            List of lesson dictionaries
        """
        return [
            {
                "id": "basics",
                "title": "Basics: Recording and Searching",
                "description": "Learn how to record timeline entries and search them",
                "content": [
                    "1. Record a timeline entry:",
                    "   m \"Your message here\"",
                    "",
                    "2. Search for entries:",
                    "   ms \"search query\"",
                    "",
                    "3. View today's timeline:",
                    "   mtoday",
                    "",
                    "4. View this week's timeline:",
                    "   mweek",
                ],
            },
            {
                "id": "context",
                "title": "Claude Code Integration",
                "description": "Learn how to integrate with Claude Code",
                "content": [
                    "1. Generate context for Claude:",
                    "   mcontext",
                    "",
                    "2. This creates .claude/memory-context.md",
                    "3. Claude reads this automatically",
                    "",
                    "4. Keep context fresh by running:",
                    "   mcontext",
                    "   After major changes",
                ],
            },
            {
                "id": "plans",
                "title": "Task Planning",
                "description": "Learn how to create and manage plans",
                "content": [
                    "1. Create a new plan:",
                    "   mplan create \"Project Name\"",
                    "",
                    "2. Add tasks to plan:",
                    "   mplan add \"Project Name\" \"Task description\"",
                    "",
                    "3. List all plans:",
                    "   mplan list",
                    "",
                    "4. Mark task as done:",
                    "   mplan done \"Project Name\" \"Task description\"",
                ],
            },
            {
                "id": "advanced",
                "title": "Advanced Features",
                "description": "Learn advanced search and automation",
                "content": [
                    "1. Semantic search (requires vector extra):",
                    "   ms --semantic \"query\"",
                    "",
                    "2. Hybrid search (best results):",
                    "   ms --hybrid \"query\"",
                    "",
                    "3. Timeline summary (requires llm extra):",
                    "   msummary today",
                    "   msummary week",
                    "",
                    "4. Interactive search browser:",
                    "   mbrowse",
                ],
            },
            {
                "id": "completion",
                "title": "Shell Completion",
                "description": "Enable tab completion for commands",
                "content": [
                    "1. Install bash completion:",
                    "   mcompletion install bash",
                    "",
                    "2. Install zsh completion:",
                    "   mcompletion install zsh",
                    "",
                    "3. Install PowerShell completion:",
                    "   mcompletion install powershell",
                    "",
                    "4. Reload your shell after installation",
                ],
            },
        ]

    def run(self, lesson_id: str = None):
        """Run interactive tutorial.

        Args:
            lesson_id: Specific lesson ID to show, or None for menu
        """
        if lesson_id:
            # Show specific lesson
            lesson = next((l for l in self.lessons if l["id"] == lesson_id), None)
            if lesson:
                self._show_lesson(lesson)
            else:
                self.console.print(f"[red]ERROR[/red] Lesson not found: {lesson_id}")
        else:
            # Show menu
            self._show_menu()

    def _show_menu(self):
        """Show tutorial menu."""
        self.console.print(
            Panel.fit(
                "[bold cyan]Memory Tool Tutorial[/bold cyan]\n\n"
                "Learn how to use memory_tool commands",
                border_style="cyan",
            )
        )
        self.console.print()

        # List lessons
        self.console.print("[bold]Available Lessons:[/bold]\n")
        for i, lesson in enumerate(self.lessons, 1):
            self.console.print(f"  {i}. [cyan]{lesson['title']}[/cyan]")
            self.console.print(f"     {lesson['description']}")
            self.console.print()

        # Get user choice
        choice = Prompt.ask(
            "[bold]Select a lesson (1-{}) or 'q' to quit[/bold]".format(len(self.lessons)),
            choices=[str(i) for i in range(1, len(self.lessons) + 1)] + ["q"],
            default="q",
        )

        if choice == "q":
            self.console.print("[yellow]Tutorial closed[/yellow]")
            return

        # Show selected lesson
        lesson_index = int(choice) - 1
        self._show_lesson(self.lessons[lesson_index])

        # Ask if user wants to see another lesson
        self.console.print()
        if Prompt.ask("[bold]View another lesson?[/bold]", choices=["y", "n"], default="n") == "y":
            self._show_menu()

    def _show_lesson(self, lesson: Dict):
        """Show a single lesson.

        Args:
            lesson: Lesson dictionary
        """
        self.console.print()
        self.console.print(
            Panel.fit(
                f"[bold cyan]{lesson['title']}[/bold cyan]\n\n"
                f"{lesson['description']}",
                border_style="cyan",
            )
        )
        self.console.print()

        # Show content
        for line in lesson["content"]:
            self.console.print(line)

        self.console.print()

    def list_lessons(self):
        """List all available lessons."""
        self.console.print("[bold cyan]Available Tutorial Lessons:[/bold cyan]\n")
        for lesson in self.lessons:
            self.console.print(f"  [cyan]{lesson['id']}[/cyan]: {lesson['title']}")
            self.console.print(f"    {lesson['description']}")
            self.console.print()

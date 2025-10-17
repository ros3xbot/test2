import subprocess
import os
import sys
from rich.panel import Panel
from rich.text import Text
from rich.console import Console
from app.menus.util import pause
from app.menus.util_helper import live_loading, print_panel
from app.config.theme_config import get_theme

console = Console()

def is_rebase_in_progress():
    return os.path.exists(".git/rebase-apply") or os.path.exists(".git/rebase-merge")

def git_pull_rebase():
    theme = get_theme()
    result = {"status": None, "error": None, "output": ""}

    if is_rebase_in_progress():
        text = Text.from_markup(
            "[bold yellow]⚠️ Rebase sebelumnya belum selesai[/]\n\n"
            "[yellow]Selesaikan dengan `git rebase --continue` atau batalkan dengan `git rebase --abort`[/]"
        )
        console.print(Panel(text, title="📥 Status Update CLI", border_style=theme["border_warning"], padding=(1, 2), expand=True))
        pause()
        sys.exit(1)

    def run_git():
        try:
            subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], check=True, stdout=subprocess.DEVNULL)
            output = subprocess.run(
                ['git', 'pull', '--rebase'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            result["status"] = "success"
            result["output"] = output.stdout.strip()
        except subprocess.CalledProcessError as e:
            result["status"] = "fail"
            result["error"] = e.stderr.strip()
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

    with live_loading("🔄 Menarik update dari repository...", theme):
        run_git()

    if result["status"] == "success":
        text = Text.from_markup(
            f"✅ [bold green]Git pull --rebase berhasil[/]\n\n[white]{result['output']}[/]"
        )
        console.print(Panel(text, title="📥 Status Update CLI", border_style=theme["border_success"], padding=(1, 2), expand=True))

    elif result["status"] == "fail":
        text = Text.from_markup(
            f"❌ [bold red]Git pull gagal[/]\n\n[red]{result['error']}[/]"
        )
        console.print(Panel(text, title="📥 Status Update CLI", border_style=theme["border_err"], padding=(1, 2), expand=True))
        pause()
        sys.exit(1)

    else:
        text = Text.from_markup(
            f"⚠️ [bold yellow]Error saat menjalankan git pull[/]\n\n[yellow]{result['error']}[/]"
        )
        console.print(Panel(text, title="📥 Status Update CLI", border_style=theme["border_warning"], padding=(1, 2), expand=True))
        pause()
        sys.exit(1)

def run_main():
    import main
    main.main()

if __name__ == "__main__":
    git_pull_rebase()
    run_main()

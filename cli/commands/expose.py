"""
gillie expose — Expose the Gillie API via nginx reverse proxy.

Subcommands:
  install   Generate nginx config and optionally obtain SSL certificate
  remove    Remove nginx config and disable the site
  status    Show current expose configuration
  reload    Reload nginx to apply changes
"""
import os
import shutil
import subprocess
import typer
from rich.console import Console
from rich.table import Table
from rich import box

from cli.config.manager import config_exists, load_config, save_config

console = Console()

app = typer.Typer(help="Expose the API via nginx reverse proxy (HTTP/HTTPS).")

NGINX_SITES_AVAILABLE = "/etc/nginx/sites-available/gillie"
NGINX_SITES_ENABLED   = "/etc/nginx/sites-enabled/gillie"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _require_config():
    if not config_exists():
        console.print("[red]✗[/red] No config found. Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)


def _require_root():
    if os.geteuid() != 0:
        console.print("[red]✗[/red] This command requires root privileges. Run with [bold]sudo[/bold].")
        raise typer.Exit(1)


def _require_nginx():
    if not shutil.which("nginx"):
        console.print("[red]✗[/red] nginx not found.")
        console.print("  Install it with: [bold cyan]sudo apt install nginx -y[/bold cyan]")
        raise typer.Exit(1)


def _nginx_config_http(domain: str, port: int) -> str:
    return f"""\
server {{
    listen 80;
    server_name {domain};

    client_max_body_size 50M;

    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
    }}
}}
"""


def _nginx_config_https(domain: str, port: int) -> str:
    return f"""\
server {{
    listen 80;
    server_name {domain};
    return 301 https://$server_name$request_uri;
}}

server {{
    listen 443 ssl;
    server_name {domain};

    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    client_max_body_size 50M;

    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
    }}
}}
"""


def _write_nginx_config(content: str):
    with open(NGINX_SITES_AVAILABLE, "w") as f:
        f.write(content)

    # Enable site via symlink
    if os.path.exists(NGINX_SITES_ENABLED):
        os.remove(NGINX_SITES_ENABLED)
    os.symlink(NGINX_SITES_AVAILABLE, NGINX_SITES_ENABLED)


def _nginx_test() -> bool:
    result = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
    if result.returncode != 0:
        console.print("[red]✗[/red] nginx config test failed:")
        console.print(f"[dim]{result.stderr}[/dim]")
        return False
    return True


def _nginx_reload():
    subprocess.run(["systemctl", "reload", "nginx"], check=True)


# ── Commands ─────────────────────────────────────────────────────────────────

@app.command("install")
def install(
    domain: str = typer.Option(None, "--domain", "-d", help="Domain or IP to serve (e.g. api.midominio.com)"),
    port:   int  = typer.Option(None, "--port",   "-p", help="Local API port (default: from config or 8000)"),
    ssl:    bool = typer.Option(False, "--ssl/--no-ssl",  help="Obtain SSL certificate via Let's Encrypt (certbot)"),
    email:  str  = typer.Option(None, "--email",  "-e", help="Email for Let's Encrypt notifications (required with --ssl)"),
):
    """
    Install nginx reverse proxy config for the Gillie API.

    With [bold]--ssl[/bold] it also runs certbot to obtain a Let's Encrypt certificate.
    Requires root (sudo).

    Examples:

      [cyan]sudo gillie expose install --domain api.ejemplo.com[/cyan]

      [cyan]sudo gillie expose install --domain api.ejemplo.com --ssl --email tu@email.com[/cyan]
    """
    _require_root()
    _require_nginx()
    _require_config()

    config = load_config()

    # Resolve domain interactively if not provided
    if not domain:
        saved = config.expose.domain
        domain = typer.prompt("Domain or public IP", default=saved or "")
        if not domain:
            console.print("[red]✗[/red] Domain is required.")
            raise typer.Exit(1)

    # Resolve port
    if port is None:
        port = config.expose.port or config.server.port or 8000

    # Resolve SSL email
    if ssl and not email:
        saved_email = config.expose.email
        email = typer.prompt("Email for Let's Encrypt", default=saved_email or "")
        if not email:
            console.print("[red]✗[/red] Email is required for SSL.")
            raise typer.Exit(1)

    console.print()
    console.print(f"✨🐙 Setting up nginx for [bold cyan]{domain}[/bold cyan]")
    console.print(f"  port : [bold]{port}[/bold]")
    console.print(f"  SSL  : [bold]{'yes' if ssl else 'no (HTTP only)'}[/bold]")
    console.print()

    # Step 1: Write HTTP config (needed for certbot challenge even in SSL mode)
    console.print("[dim]→ Writing nginx config...[/dim]")
    _write_nginx_config(_nginx_config_http(domain, port))

    if not _nginx_test():
        raise typer.Exit(1)
    _nginx_reload()
    console.print("[green]✓[/green] nginx config installed and reloaded (HTTP)")

    # Step 2: SSL via certbot
    if ssl:
        if not shutil.which("certbot"):
            console.print("[yellow]⚠[/yellow]  certbot not found. Installing...")
            subprocess.run(["apt", "install", "certbot", "python3-certbot-nginx", "-y"], check=True)

        console.print()
        console.print("[dim]→ Running certbot...[/dim]")
        certbot_cmd = [
            "certbot", "--nginx",
            "-d", domain,
            "--non-interactive",
            "--agree-tos",
            "-m", email,
        ]
        result = subprocess.run(certbot_cmd)
        if result.returncode != 0:
            console.print("[red]✗[/red] certbot failed. Make sure DNS for the domain points to this server.")
            raise typer.Exit(1)

        # Step 3: Replace config with full HTTPS version
        console.print("[dim]→ Writing HTTPS nginx config...[/dim]")
        _write_nginx_config(_nginx_config_https(domain, port))

        if not _nginx_test():
            raise typer.Exit(1)
        _nginx_reload()
        console.print("[green]✓[/green] SSL configured. nginx reloaded.")

    # Save expose config
    config.expose.domain = domain
    config.expose.port = port
    config.expose.ssl = ssl
    config.expose.email = email or config.expose.email
    save_config(config)

    console.print()
    console.print("[green]✓[/green] Done!")
    console.print()
    proto = "https" if ssl else "http"
    console.print(f"  Your API is now accessible at: [bold cyan]{proto}://{domain}[/bold cyan]")
    console.print(f"  Docs: [bold cyan]{proto}://{domain}/docs[/bold cyan]")
    console.print()


@app.command("remove")
def remove():
    """Remove the nginx config and disable the Gillie site. Requires root (sudo)."""
    _require_root()
    _require_nginx()

    removed = False

    if os.path.exists(NGINX_SITES_ENABLED):
        os.remove(NGINX_SITES_ENABLED)
        console.print("[green]✓[/green] Removed symlink from sites-enabled")
        removed = True

    if os.path.exists(NGINX_SITES_AVAILABLE):
        os.remove(NGINX_SITES_AVAILABLE)
        console.print("[green]✓[/green] Removed config from sites-available")
        removed = True

    if not removed:
        console.print("[yellow]⚠[/yellow]  No nginx config found for Gillie.")
        return

    if _nginx_test():
        _nginx_reload()
        console.print("[green]✓[/green] nginx reloaded.")

    console.print()
    console.print("[green]✓[/green] Gillie site removed from nginx.")
    console.print()


@app.command("reload")
def reload():
    """Reload nginx to apply configuration changes. Requires root (sudo)."""
    _require_root()
    _require_nginx()

    if not _nginx_test():
        raise typer.Exit(1)

    _nginx_reload()
    console.print("[green]✓[/green] nginx reloaded.")


@app.command("status")
def status():
    """Show current expose configuration and nginx status."""
    _require_config()

    config = load_config()
    e = config.expose

    nginx_installed = bool(shutil.which("nginx"))
    config_exists_flag = os.path.exists(NGINX_SITES_AVAILABLE)
    enabled = os.path.exists(NGINX_SITES_ENABLED)

    console.print()
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Key", style="bold dim")
    table.add_column("Value")

    table.add_row("Domain",  e.domain or "[dim]not set[/dim]")
    table.add_row("Port",    str(e.port) if e.port else "[dim]not set[/dim]")
    table.add_row("SSL",     "[green]yes[/green]" if e.ssl else "no")
    table.add_row("nginx",   "[green]installed[/green]" if nginx_installed else "[red]not found[/red]")
    table.add_row("Config",  "[green]present[/green]" if config_exists_flag else "[dim]not installed[/dim]")
    table.add_row("Enabled", "[green]yes[/green]" if enabled else "[dim]no[/dim]")

    if e.domain:
        proto = "https" if e.ssl else "http"
        table.add_row("URL", f"[cyan]{proto}://{e.domain}[/cyan]")

    console.print(table)
    console.print()

    if not e.domain:
        console.print("  Run [bold cyan]sudo gillie expose install --domain tu-dominio.com[/bold cyan] to set up.")
        console.print()

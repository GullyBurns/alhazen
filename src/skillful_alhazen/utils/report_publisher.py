#!/usr/bin/env python3
"""
Report Publisher — Render TypeDB knowledge base data as static HTML reports.

Skill-agnostic engine. Each skill provides:
  1. A `collect-report-data` CLI subcommand emitting JSON to stdout
  2. A `report_templates/` directory with Jinja2 templates extending base.html.j2

This engine consumes that JSON + template and produces self-contained HTML.

Usage:
    # Render from JSON file
    python report_publisher.py render --data report.json --template path/to/template.html.j2

    # Publish to GitHub Pages
    python report_publisher.py publish --report ~/.alhazen/reports/my-report/ --project benchling

    # Site management
    python report_publisher.py init-site --repo sciknow-io/alhazen-reports
    python report_publisher.py add-project --slug benchling --title "Benchling"
    python report_publisher.py list-projects
"""

import argparse
import base64
import getpass
import hashlib
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

import jinja2
import markdown as md_lib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SHARED_TEMPLATES_DIR = PROJECT_ROOT / "local_resources" / "report_templates"
REPORTS_DIR = Path(os.getenv("ALHAZEN_REPORTS_DIR",
                             Path.home() / ".alhazen" / "reports"))
SITE_REPO_DIR = REPORTS_DIR / ".site-repo"
PASSPHRASES_FILE = REPORTS_DIR / ".passphrases.json"


def slugify(text: str) -> str:
    """Convert text to filesystem-safe slug."""
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s[:80].strip("-")


def md_to_html(text: str) -> str:
    """Convert markdown string to HTML."""
    if not text:
        return ""
    return md_lib.markdown(
        text,
        extensions=["tables", "fenced_code", "codehilite", "toc", "nl2br"],
    )


# ---------------------------------------------------------------------------
# Template Environment
# ---------------------------------------------------------------------------

def build_jinja_env(extra_template_dirs: list[Path] | None = None) -> jinja2.Environment:
    """Create Jinja2 environment with shared base + skill template dirs."""
    search_paths = [str(SHARED_TEMPLATES_DIR)]
    if extra_template_dirs:
        for d in extra_template_dirs:
            if d.is_dir():
                search_paths.append(str(d))

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(search_paths),
        autoescape=jinja2.select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # Custom filters
    env.filters["md"] = md_to_html
    env.filters["slugify"] = slugify
    return env


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render_report(data: dict, template_path: str,
                  output_dir: Path | None = None,
                  extra_template_dirs: list[Path] | None = None) -> Path:
    """Render a report from JSON data + Jinja2 template.

    Args:
        data: Report Data Schema dict (with meta, sections, etc.)
        template_path: Template filename or relative path
        output_dir: Where to write output (default: auto from slug)
        extra_template_dirs: Additional Jinja2 search paths (skill template dirs)

    Returns:
        Path to the output directory containing index.html
    """
    meta = data.get("meta", {})
    title = meta.get("title", "Untitled Report")
    slug = slugify(title)

    if output_dir is None:
        output_dir = REPORTS_DIR / slug
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Read static assets to inline
    css_path = SHARED_TEMPLATES_DIR / "static" / "style.css"
    js_path = SHARED_TEMPLATES_DIR / "static" / "report.js"
    inline_css = css_path.read_text() if css_path.exists() else ""
    inline_js = js_path.read_text() if js_path.exists() else ""

    # Pre-process: convert markdown sections to HTML
    for section in data.get("sections", []):
        if section.get("type") == "markdown" and "content" in section:
            section["content_html"] = md_to_html(section["content"])
        if section.get("type") == "quote-block" and "content" in section:
            section["content_html"] = md_to_html(section["content"])

    for appendix in data.get("appendices", []):
        for item in appendix.get("items", []):
            if "content" in item:
                item["content_html"] = md_to_html(item["content"])

    # Build template environment
    env = build_jinja_env(extra_template_dirs)

    # Resolve template
    try:
        template = env.get_template(template_path)
    except jinja2.TemplateNotFound:
        # Try as absolute/relative path
        abs_path = Path(template_path)
        if abs_path.exists():
            env.loader = jinja2.FileSystemLoader(
                [str(abs_path.parent), str(SHARED_TEMPLATES_DIR)]
                + ([str(d) for d in (extra_template_dirs or [])])
            )
            template = env.get_template(abs_path.name)
        else:
            print(json.dumps({"success": False, "error": f"Template not found: {template_path}"}))
            sys.exit(1)

    # Build raw JSON for the embedded data viewer (safe for JS embedding)
    raw_json = json.dumps(data, indent=2, default=str)

    # Render
    html = template.render(
        data=data,
        meta=meta,
        sections=data.get("sections", []),
        appendices=data.get("appendices", []),
        inline_css=inline_css,
        inline_js=inline_js,
        raw_json=raw_json,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    # Write output
    index_path = output_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")

    # Also save the data JSON for reference
    data_path = output_dir / "data.json"
    data_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    return output_dir


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------

def cmd_render(args):
    """Render JSON data through a Jinja2 template to produce HTML."""
    # Read data from file or stdin
    if args.data:
        data_path = Path(args.data)
        if not data_path.exists():
            print(json.dumps({"success": False, "error": f"Data file not found: {args.data}"}))
            sys.exit(1)
        data = json.loads(data_path.read_text())
    else:
        data = json.load(sys.stdin)

    # Resolve extra template dirs from skill path
    extra_dirs = []
    if args.skill_templates:
        p = Path(args.skill_templates)
        if p.is_dir():
            extra_dirs.append(p)

    output = Path(args.output) if args.output else None
    result_dir = render_report(
        data=data,
        template_path=args.template,
        output_dir=output,
        extra_template_dirs=extra_dirs,
    )

    print(json.dumps({
        "success": True,
        "output_dir": str(result_dir),
        "index": str(result_dir / "index.html"),
        "title": data.get("meta", {}).get("title", "Untitled"),
    }))


def cmd_preview(args):
    """Start a local HTTP server to preview a report."""
    report_dir = Path(args.report)
    if not (report_dir / "index.html").exists():
        print(f"Error: No index.html found in {report_dir}")
        sys.exit(1)

    port = args.port
    os.chdir(report_dir)

    handler = http.server.SimpleHTTPRequestHandler
    server = http.server.HTTPServer(("", port), handler)

    url = f"http://localhost:{port}"
    print(f"Serving report from {report_dir}")
    print(f"Open: {url}")
    print("Press Ctrl+C to stop.")

    # Open browser after a short delay
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


def cmd_list(args):
    """List all exported reports."""
    if not REPORTS_DIR.exists():
        print(json.dumps({"success": True, "reports": []}))
        return

    reports = []
    for d in sorted(REPORTS_DIR.iterdir()):
        if d.is_dir() and (d / "index.html").exists():
            # Try to read data.json for metadata
            meta = {}
            data_file = d / "data.json"
            if data_file.exists():
                try:
                    full = json.loads(data_file.read_text())
                    meta = full.get("meta", {})
                except (json.JSONDecodeError, OSError):
                    pass

            stat = (d / "index.html").stat()
            reports.append({
                "slug": d.name,
                "path": str(d),
                "title": meta.get("title", d.name),
                "skill": meta.get("skill", "unknown"),
                "exported_at": meta.get("exported_at", ""),
                "size_kb": round(stat.st_size / 1024, 1),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

    print(json.dumps({"success": True, "reports": reports}, indent=2))


# ---------------------------------------------------------------------------
# Encryption
# ---------------------------------------------------------------------------

def encrypt_html(html_body: str, passphrase: str) -> tuple[str, str, str]:
    """AES-256-GCM encrypt HTML content with a passphrase.

    Returns (ciphertext_b64, salt_b64, nonce_b64).
    """
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, 100_000)
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, html_body.encode("utf-8"), None)
    return (
        base64.b64encode(ct).decode(),
        base64.b64encode(salt).decode(),
        base64.b64encode(nonce).decode(),
    )


def wrap_encrypted(html_path: Path, passphrase: str, title: str = "",
                   project: str = "") -> str:
    """Read an HTML file, encrypt it, and return the encryption stub HTML."""
    html_body = html_path.read_text(encoding="utf-8")
    ct_b64, salt_b64, nonce_b64 = encrypt_html(html_body, passphrase)

    env = build_jinja_env()
    template = env.get_template("encrypt-stub.html.j2")
    return template.render(
        title=title,
        project=project,
        ciphertext=ct_b64,
        salt=salt_b64,
        nonce=nonce_b64,
    )


# ---------------------------------------------------------------------------
# Site Management Helpers
# ---------------------------------------------------------------------------

def _load_site_json(site_dir: Path) -> dict:
    """Load site.json from the site repo."""
    path = site_dir / "site.json"
    if path.exists():
        return json.loads(path.read_text())
    return {
        "site": {
            "title": "Skillful Alhazen — Investigation Reports",
            "owner": "Gully Burns",
            "default_access": "encrypted",
        },
        "projects": [],
    }


def _save_site_json(site_dir: Path, data: dict):
    """Write site.json to the site repo."""
    (site_dir / "site.json").write_text(json.dumps(data, indent=2, default=str))


def _load_passphrases() -> dict:
    """Load project passphrases from local (gitignored) file."""
    if PASSPHRASES_FILE.exists():
        return json.loads(PASSPHRASES_FILE.read_text())
    return {}


def _save_passphrases(data: dict):
    """Save project passphrases."""
    PASSPHRASES_FILE.parent.mkdir(parents=True, exist_ok=True)
    PASSPHRASES_FILE.write_text(json.dumps(data, indent=2))


def _ensure_site_repo(repo: str | None = None) -> Path:
    """Clone or pull the site repo. Returns path to local checkout."""
    if SITE_REPO_DIR.exists() and (SITE_REPO_DIR / ".git").exists():
        # Pull latest
        subprocess.run(["git", "pull", "--quiet"], cwd=SITE_REPO_DIR,
                        capture_output=True)
        return SITE_REPO_DIR

    if not repo:
        print(json.dumps({"success": False,
                           "error": "No site repo found. Run init-site first."}))
        sys.exit(1)

    # Clone
    SITE_REPO_DIR.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["gh", "repo", "clone", repo, str(SITE_REPO_DIR)],
                    check=True, capture_output=True)
    return SITE_REPO_DIR


def _regenerate_indexes(site_dir: Path):
    """Regenerate site index and all project index pages."""
    site_data = _load_site_json(site_dir)
    css_path = SHARED_TEMPLATES_DIR / "static" / "style.css"
    inline_css = css_path.read_text() if css_path.exists() else ""
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    env = build_jinja_env()

    # Site index
    tpl = env.get_template("site-index.html.j2")
    html = tpl.render(
        site=site_data["site"],
        projects=site_data["projects"],
        inline_css=inline_css,
        generated_at=generated_at,
    )
    (site_dir / "index.html").write_text(html, encoding="utf-8")

    # Project indexes
    tpl = env.get_template("project-index.html.j2")
    for project in site_data["projects"]:
        proj_dir = site_dir / project["slug"]
        proj_dir.mkdir(parents=True, exist_ok=True)
        html = tpl.render(
            project=project,
            inline_css=inline_css,
            generated_at=generated_at,
        )
        (proj_dir / "index.html").write_text(html, encoding="utf-8")


def _git_commit_and_push(site_dir: Path, message: str):
    """Stage all changes, commit, and push."""
    subprocess.run(["git", "add", "-A"], cwd=site_dir, capture_output=True)

    # Check if there are changes to commit
    result = subprocess.run(["git", "diff", "--cached", "--quiet"],
                             cwd=site_dir, capture_output=True)
    if result.returncode == 0:
        return  # Nothing to commit

    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=site_dir, capture_output=True, check=True,
    )
    subprocess.run(["git", "push", "-u", "origin", "HEAD"],
                    cwd=site_dir, capture_output=True, check=True)


# ---------------------------------------------------------------------------
# Phase 2 CLI Commands
# ---------------------------------------------------------------------------

def cmd_init_site(args):
    """Create the GitHub Pages repo and initialize site structure."""
    repo = args.repo

    # Create the repo via gh CLI
    visibility = "--private" if args.private else "--public"
    result = subprocess.run(
        ["gh", "repo", "create", repo, visibility, "--clone",
         "--description", "Skillful Alhazen investigation reports"],
        capture_output=True, text=True, cwd=str(REPORTS_DIR),
    )

    if result.returncode != 0 and "already exists" in result.stderr:
        # Repo exists, just clone it
        _ensure_site_repo(repo)
    elif result.returncode != 0:
        print(json.dumps({"success": False, "error": result.stderr.strip()}))
        sys.exit(1)
    else:
        # gh repo create --clone puts it in a subdir named after the repo
        repo_name = repo.split("/")[-1]
        cloned_dir = REPORTS_DIR / repo_name
        if cloned_dir.exists() and cloned_dir != SITE_REPO_DIR:
            if SITE_REPO_DIR.exists():
                shutil.rmtree(SITE_REPO_DIR)
            cloned_dir.rename(SITE_REPO_DIR)

    site_dir = SITE_REPO_DIR

    # Initialize site.json
    site_data = _load_site_json(site_dir)
    _save_site_json(site_dir, site_data)

    # Create .nojekyll to disable Jekyll processing
    (site_dir / ".nojekyll").touch()

    # Generate initial index
    _regenerate_indexes(site_dir)

    # Commit and push
    _git_commit_and_push(site_dir, "Initialize Alhazen reports site")

    print(json.dumps({
        "success": True,
        "repo": repo,
        "site_dir": str(site_dir),
        "message": f"Site initialized. Enable GitHub Pages on {repo} (Settings > Pages > Deploy from branch main).",
    }))


def cmd_add_project(args):
    """Register a new project in site.json."""
    site_dir = _ensure_site_repo()
    site_data = _load_site_json(site_dir)

    # Check if project already exists
    existing = [p for p in site_data["projects"] if p["slug"] == args.slug]
    if existing:
        print(json.dumps({"success": False,
                           "error": f"Project '{args.slug}' already exists"}))
        sys.exit(1)

    # Get passphrase
    passphrase = args.passphrase
    if not passphrase and args.slug != "public":
        passphrase = getpass.getpass(f"Passphrase for project '{args.slug}': ")

    project = {
        "slug": args.slug,
        "title": args.title,
        "description": args.description or "",
        "access": "public" if args.slug == "public" else "encrypted",
        "reports": [],
    }

    site_data["projects"].append(project)
    _save_site_json(site_dir, site_data)

    # Save passphrase locally
    if passphrase:
        pp = _load_passphrases()
        pp[args.slug] = passphrase
        _save_passphrases(pp)

    # Create project directory and index
    _regenerate_indexes(site_dir)

    _git_commit_and_push(site_dir, f"Add project: {args.title}")

    print(json.dumps({
        "success": True,
        "project": args.slug,
        "title": args.title,
        "access": project["access"],
    }))


def cmd_list_projects(args):
    """Show projects and their reports from site.json."""
    site_dir = _ensure_site_repo()
    site_data = _load_site_json(site_dir)

    print(json.dumps({
        "success": True,
        "site": site_data["site"],
        "projects": site_data["projects"],
    }, indent=2))


def cmd_publish(args):
    """Publish a report to the GitHub Pages site."""
    report_dir = Path(args.report)
    if not (report_dir / "index.html").exists():
        print(json.dumps({"success": False,
                           "error": f"No index.html in {report_dir}"}))
        sys.exit(1)

    site_dir = _ensure_site_repo(args.repo)
    site_data = _load_site_json(site_dir)

    # Find or validate project
    project_slug = args.project
    project = None
    for p in site_data["projects"]:
        if p["slug"] == project_slug:
            project = p
            break

    if not project:
        print(json.dumps({"success": False,
                           "error": f"Project '{project_slug}' not found. Run add-project first."}))
        sys.exit(1)

    # Determine report slug from data.json or directory name
    report_meta = {}
    data_file = report_dir / "data.json"
    if data_file.exists():
        full_data = json.loads(data_file.read_text())
        report_meta = full_data.get("meta", {})

    report_slug = slugify(report_meta.get("title", report_dir.name))

    # Destination in site repo
    dest_dir = site_dir / project_slug / report_slug
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Copy data.json (always unencrypted -- it's the structured data artifact)
    if data_file.exists():
        shutil.copy2(data_file, dest_dir / "data.json")

    # Handle encryption
    is_public = args.public or project.get("access") == "public"

    if is_public:
        # Copy index.html as-is
        shutil.copy2(report_dir / "index.html", dest_dir / "index.html")
    else:
        # Encrypt
        pp = _load_passphrases()
        passphrase = pp.get(project_slug)
        if not passphrase:
            passphrase = getpass.getpass(
                f"Passphrase for project '{project_slug}': ")
            pp[project_slug] = passphrase
            _save_passphrases(pp)

        encrypted_html = wrap_encrypted(
            report_dir / "index.html",
            passphrase,
            title=report_meta.get("title", report_slug),
            project=project.get("title", project_slug),
        )
        (dest_dir / "index.html").write_text(encrypted_html, encoding="utf-8")

    # Update site.json
    report_entry = {
        "slug": report_slug,
        "title": report_meta.get("title", report_slug),
        "skill": report_meta.get("skill", ""),
        "source_id": report_meta.get("source_id", ""),
        "exported_at": report_meta.get("exported_at", ""),
        "access": "public" if is_public else "encrypted",
    }

    # Replace if already exists, otherwise append
    existing = [r for r in project["reports"] if r["slug"] == report_slug]
    if existing:
        project["reports"] = [
            report_entry if r["slug"] == report_slug else r
            for r in project["reports"]
        ]
    else:
        project["reports"].append(report_entry)

    _save_site_json(site_dir, site_data)

    # Regenerate indexes
    _regenerate_indexes(site_dir)

    # Commit and push
    _git_commit_and_push(
        site_dir,
        f"Publish: {report_meta.get('title', report_slug)} -> {project_slug}/",
    )

    print(json.dumps({
        "success": True,
        "project": project_slug,
        "report": report_slug,
        "encrypted": not is_public,
        "path": f"{project_slug}/{report_slug}/",
        "dest": str(dest_dir),
    }))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Report Publisher - render TypeDB data as static HTML reports"
    )
    sub = parser.add_subparsers(dest="command")

    # render
    p_render = sub.add_parser("render", help="Render JSON data to HTML report")
    p_render.add_argument("--data", help="Path to JSON data file (default: stdin)")
    p_render.add_argument("--template", required=True,
                          help="Template filename or path (e.g., investigation-report.html.j2)")
    p_render.add_argument("--output", help="Output directory (default: ~/.alhazen/reports/<slug>/)")
    p_render.add_argument("--skill-templates",
                          help="Additional template directory (skill's report_templates/)")
    p_render.set_defaults(func=cmd_render)

    # preview
    p_preview = sub.add_parser("preview", help="Preview an exported report in browser")
    p_preview.add_argument("--report", required=True, help="Path to report directory")
    p_preview.add_argument("--port", type=int, default=8765, help="HTTP server port")
    p_preview.add_argument("--no-browser", action="store_true", help="Don't open browser")
    p_preview.set_defaults(func=cmd_preview)

    # list
    p_list = sub.add_parser("list", help="List exported reports")
    p_list.set_defaults(func=cmd_list)

    # init-site
    p_init = sub.add_parser("init-site", help="Create GitHub Pages repo for reports")
    p_init.add_argument("--repo", required=True,
                         help="GitHub repo (e.g., sciknow-io/alhazen-reports)")
    p_init.add_argument("--private", action="store_true", default=True,
                         help="Create as private repo (default)")
    p_init.set_defaults(func=cmd_init_site)

    # add-project
    p_proj = sub.add_parser("add-project", help="Register a new project")
    p_proj.add_argument("--slug", required=True, help="Project slug (e.g., benchling)")
    p_proj.add_argument("--title", required=True, help="Project title")
    p_proj.add_argument("--description", default="", help="Project description")
    p_proj.add_argument("--passphrase", help="Encryption passphrase (prompted if omitted)")
    p_proj.set_defaults(func=cmd_add_project)

    # list-projects
    p_lp = sub.add_parser("list-projects", help="Show projects and reports")
    p_lp.set_defaults(func=cmd_list_projects)

    # publish
    p_pub = sub.add_parser("publish", help="Publish a report to GitHub Pages")
    p_pub.add_argument("--report", required=True, help="Path to report directory")
    p_pub.add_argument("--project", required=True, help="Project slug to publish under")
    p_pub.add_argument("--repo", help="GitHub repo (uses existing clone if omitted)")
    p_pub.add_argument("--public", action="store_true",
                        help="Skip encryption for this report")
    p_pub.set_defaults(func=cmd_publish)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()

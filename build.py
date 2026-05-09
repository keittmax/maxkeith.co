#!/usr/bin/env python3
"""
maxkeith.co — static site builder
Run:    python build.py
Output: _site/
"""

import os
import re
import shutil
from pathlib import Path
from datetime import datetime

import markdown
import yaml

# ── Config ───────────────────────────────────────────────────────────────────
SITE_TITLE    = "max keith"
SITE_URL      = "https://maxkeith.co"
POSTS_DIR     = Path("posts")
PAGES_DIR     = Path("pages")
MEDIA_DIR     = Path("media")
STATIC_DIR    = Path("static")
TEMPLATES_DIR = Path("templates")
OUTPUT_DIR    = Path("_site")

# ── Template engine ───────────────────────────────────────────────────────────
_template_cache = {}

def load_template(name: str) -> str:
    if name not in _template_cache:
        _template_cache[name] = (TEMPLATES_DIR / f"{name}.html").read_text(encoding="utf-8")
    return _template_cache[name]

def tpl_render(template: str, **ctx) -> str:
    """
    Minimal template renderer.
    Supports: {{key}}, {{#key}}...{{/key}} (show block if truthy), {{#key}}...{{/key}} (hide if falsy).
    """
    # Conditional blocks: {{#key}}content{{/key}}
    def replace_block(m):
        key, inner = m.group(1), m.group(2)
        val = ctx.get(key, "")
        return inner if val else ""
    result = re.sub(r'\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}', replace_block, template, flags=re.DOTALL)
    # Simple substitution: {{key}}
    for key, value in ctx.items():
        result = result.replace(f"{{{{{key}}}}}", str(value) if value is not None else "")
    return result

def render_page(inner_template: str, **ctx) -> str:
    """Wrap inner template in base layout."""
    inner = tpl_render(load_template(inner_template), **ctx)
    return tpl_render(load_template("base"), content=inner, **ctx)

# ── Markdown ──────────────────────────────────────────────────────────────────
def render_md(text: str) -> str:
    md = markdown.Markdown(extensions=["extra", "smarty"])
    return md.convert(text)

# ── Frontmatter ───────────────────────────────────────────────────────────────
def parse_post(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if match:
        meta = yaml.safe_load(match.group(1)) or {}
        body_md = match.group(2)
    else:
        meta = {}
        body_md = text

    # Date
    if "date" in meta:
        raw = meta["date"]
        date = raw if isinstance(raw, datetime) else datetime.strptime(str(raw), "%Y-%m-%d")
    else:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", path.name)
        date = datetime.strptime(m.group(1), "%Y-%m-%d") if m else datetime.today()

    # Slug — strip date prefix from filename
    stem = re.sub(r"^\d{4}-\d{2}-\d{2}-?", "", path.stem)
    slug = _slugify(stem) if stem else _slugify(meta.get("title", "")) or path.stem

    # Tags
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]

    return {
        "slug":     slug,
        "date":     date,
        "date_str": date.strftime("%-d %b %Y").lower(),
        "year":     date.year,
        "title":    meta.get("title", ""),
        "tags":     tags,
        "type":     meta.get("type", "short"),   # short | long
        "body":     render_md(body_md),
        "url":      f"/posts/{slug}/",
    }

def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")

# ── Post HTML snippets ────────────────────────────────────────────────────────
def tag_links(tags: list) -> str:
    return " ".join(
        f'<a href="/tags/{_slugify(t)}/" class="tag">{t}</a>' for t in tags
    )

def post_card(post: dict, *, full: bool = True) -> str:
    meta_str = post["date_str"]
    tl = tag_links(post["tags"])
    if tl:
        meta_str += f" · {tl}"

    if post["type"] == "short" or not post["title"]:
        # Show full content inline
        return f"""
<article class="post post--short">
  <div class="post-meta">{meta_str}</div>
  <div class="post-body">{post["body"]}</div>
</article>"""
    else:
        # Title + excerpt + read more
        excerpt = re.sub(r"<[^>]+>", "", post["body"])[:220].strip()
        if len(excerpt) >= 220:
            excerpt += "…"
        return f"""
<article class="post post--long">
  <div class="post-meta">{meta_str}</div>
  <h2 class="post-title"><a href="{post["url"]}">{post["title"]}</a></h2>
  <p class="post-excerpt">{excerpt}</p>
  <a href="{post["url"]}" class="read-more">→ read more</a>
</article>"""

# ── Builders ──────────────────────────────────────────────────────────────────
def build_index(posts: list):
    html = "".join(post_card(p) for p in posts)
    out = OUTPUT_DIR / "index.html"
    out.write_text(render_page("index",
        page_title=SITE_TITLE,
        page_heading="",
        posts_html=html,
    ))

def build_posts(posts: list):
    for post in posts:
        out_dir = OUTPUT_DIR / "posts" / post["slug"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(render_page("post",
            page_title=f'{post["title"]} — {SITE_TITLE}' if post["title"] else SITE_TITLE,
            title=post["title"],
            date=post["date_str"],
            tags_html=tag_links(post["tags"]),
            body=post["body"],
        ))

    # /posts/ listing — same as index for now
    html = "".join(post_card(p) for p in posts)
    out_dir = OUTPUT_DIR / "posts"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(render_page("index",
        page_title=f"posts — {SITE_TITLE}",
        page_heading="posts",
        posts_html=html,
    ))

def build_tags(posts: list):
    # Collect all tags
    tag_map: dict[str, list] = {}
    for post in posts:
        for tag in post["tags"]:
            tag_map.setdefault(tag, []).append(post)

    # Individual tag pages
    for tag, tag_posts in tag_map.items():
        slug = _slugify(tag)
        out_dir = OUTPUT_DIR / "tags" / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        html = "".join(post_card(p) for p in tag_posts)
        (out_dir / "index.html").write_text(render_page("index",
            page_title=f"#{tag} — {SITE_TITLE}",
            page_heading=f"#{tag}",
            posts_html=html,
        ))

    # /tags/ index — list all tags
    tag_list_html = "<ul class='archive-list'>\n"
    for tag in sorted(tag_map.keys()):
        slug = _slugify(tag)
        count = len(tag_map[tag])
        tag_list_html += f'<li><a href="/tags/{slug}/">#{tag}</a> <span class="archive-date">({count})</span></li>\n'
    tag_list_html += "</ul>"

    out_dir = OUTPUT_DIR / "tags"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(render_page("tags",
        page_title=f"tags — {SITE_TITLE}",
        tags_html=tag_list_html,
    ))

def build_archive(posts: list):
    by_year: dict[int, list] = {}
    for post in posts:
        by_year.setdefault(post["year"], []).append(post)

    html = ""
    for year in sorted(by_year.keys(), reverse=True):
        html += f'<h2 class="archive-year">{year}</h2>\n<ul class="archive-list">\n'
        for post in by_year[year]:
            label = post["title"] or post["date_str"]
            html += f'<li><span class="archive-date">{post["date_str"]}</span><a href="{post["url"]}">{label}</a></li>\n'
        html += "</ul>\n"

    out_dir = OUTPUT_DIR / "archive"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(render_page("index",
        page_title=f"archive — {SITE_TITLE}",
        page_heading="archive",
        posts_html=html,
    ))

def build_currently():
    src = Path("currently.md")
    content = render_md(src.read_text(encoding="utf-8")) if src.exists() else "<p>—</p>"
    out_dir = OUTPUT_DIR / "currently"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(render_page("index",
        page_title=f"currently — {SITE_TITLE}",
        page_heading="currently",
        posts_html=f'<div class="currently-body">{content}</div>',
    ))

def build_about():
    content = """
<div class="about-page">
  <figure class="about-photo">
    <img src="/media/about/cover.jpg" alt="max keith">
    <figcaption>llegando a la meta de Kima22</figcaption>
  </figure>
  <div class="about-text">
    <p>Hola.</p>
    <p><em>Este es mi <strong>cyber baúl</strong> donde guardo los .txt y .jpeg de las cosas que he hecho.</em></p>
    <p>∞</p>
  </div>
</div>
"""
    out_dir = OUTPUT_DIR / "about"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(render_page("index",
        page_title=f"about — {SITE_TITLE}",
        page_heading="",
        posts_html=content,
    ))

def copy_static():
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, OUTPUT_DIR / "static", dirs_exist_ok=True)
    if MEDIA_DIR.exists():
        shutil.copytree(MEDIA_DIR, OUTPUT_DIR / "media", dirs_exist_ok=True)
    if PAGES_DIR.exists():
        for item in PAGES_DIR.iterdir():
            dst = OUTPUT_DIR / item.name
            if item.is_file():
                shutil.copy2(item, dst)
            elif item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Clean output
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir()

    # Load all posts, newest first
    post_files = sorted(POSTS_DIR.glob("*.md"), reverse=True)
    posts = [parse_post(f) for f in post_files]
    print(f"  {len(posts)} post(s) found")

    build_index(posts)
    build_posts(posts)
    build_tags(posts)
    build_archive(posts)
    build_currently()
    build_about()
    copy_static()

    print(f"  built → {OUTPUT_DIR}/")

if __name__ == "__main__":
    print("building maxkeith.co...")
    main()
    print("done.")

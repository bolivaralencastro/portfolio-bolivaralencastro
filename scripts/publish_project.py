#!/usr/bin/env python3
"""
Gera e publica copy social para um projeto do portfolio.

Uso:
    python3 scripts/publish_project.py --project-slug fotografia-instagram --dry-run
    python3 scripts/publish_project.py --project-slug fotografia-instagram
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.error
from pathlib import Path

import instagram_post
import linkedin_post

ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = ROOT / "projects"
BASE_URL = "https://bolivaralencastro.com.br"
UTM_MEDIUM = "social"

UTM_CAMPAIGNS = {
    "linkedin": "project-launch",
    "instagram": "project-launch",
}

PROJECT_OVERRIDES = {
    "fotografia-instagram": {
        "linkedin": (
            "Publiquei no site uma pagina nova: {title}.\n\n"
            "Ela reune ensaios fotograficos que ajudam a explicar uma parte importante "
            "da minha atuacao profissional. No LinkedIn eu costumo falar mais sobre "
            "produto, interface e decisao de design. Aqui, quis deixar mais visivel "
            "como a fotografia tambem sustenta esse trabalho: no contato humano proximo, "
            "na direcao, na composicao, no ritmo, na experimentacao e no cuidado tecnico.\n\n"
            "Nao tratei isso como um projeto fechado, mas como um conjunto de ensaios "
            "que mostra como fotografia e design se misturam na minha pratica.\n\n"
            "A pagina esta aqui:\n"
            "{url}\n\n"
            "#Fotografia #Design #Produto #Portfolio"
        ),
        "instagram": (
            "Reuni no site alguns ensaios que nasceram por aqui.\n\n"
            "No Instagram vivem as fotografias. No site, elas ganharam outro tempo, em "
            "sequencia, fora da pressa do feed.\n\n"
            "{title} junta esse arquivo de encontros, luz, corpo e presenca num mesmo lugar.\n\n"
            "Se quiser ver o projeto completo, link na bio.\n\n"
            "#fotografia #arquivovisual #portfolio"
        ),
    }
}


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = value.replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", value).strip()


def build_tracked_url(url: str, source: str, campaign: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query = dict(pairs)
    query["utm_source"] = source
    query["utm_medium"] = UTM_MEDIUM
    query["utm_campaign"] = campaign
    return urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(query)))


def extract_project_meta(project_slug: str) -> dict:
    html_path = PROJECTS_DIR / f"{project_slug}.html"
    if not html_path.exists():
        raise FileNotFoundError(f"Projeto nao encontrado: {html_path}")

    content = html_path.read_text(encoding="utf-8")

    title_match = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.DOTALL)
    desc_match = re.search(r'<meta name="description" content="([^"]+)"', content)
    lead_match = re.search(r'<p class="lead">(.*?)</p>', content, re.DOTALL)

    title = clean_text(title_match.group(1)) if title_match else project_slug
    description = clean_text(desc_match.group(1)) if desc_match else ""
    lead = clean_text(lead_match.group(1)) if lead_match else ""

    image_candidates = [
        ROOT / "assets" / "images" / "projects" / project_slug / "card.jpg",
        ROOT / "assets" / "images" / "projects" / project_slug / "card.png",
        ROOT / "assets" / "images" / "projects" / project_slug / "cover.jpg",
        ROOT / "assets" / "images" / "projects" / project_slug / "cover.png",
        ROOT / "assets" / "images" / "projects" / project_slug / "card.webp",
        ROOT / "assets" / "images" / "projects" / project_slug / "cover.webp",
    ]
    image_path = next((path for path in image_candidates if path.exists()), None)
    public_image_url = (
        f"{BASE_URL}/{image_path.relative_to(ROOT).as_posix()}"
        if image_path
        else ""
    )
    instagram_image_url = ""
    if image_path and image_path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
        instagram_image_url = public_image_url

    return {
        "slug": project_slug,
        "title": title,
        "description": description,
        "lead": lead,
        "url": f"{BASE_URL}/projects/{project_slug}.html",
        "image_path": image_path,
        "image_url": public_image_url,
        "instagram_image_url": instagram_image_url,
    }


def default_linkedin_text(meta: dict, tracked_url: str) -> str:
    return (
        f"Publiquei no site um novo projeto: {meta['title']}.\n\n"
        f"{meta['description']}\n\n"
        f"Levei esse material para o portfolio porque ele pede uma leitura mais lenta "
        f"do que a do feed. O projeto completo esta aqui:\n{tracked_url}\n\n"
        "#Portfolio #Fotografia #Arquivo"
    )


def default_instagram_text(meta: dict) -> str:
    return (
        f"Esse projeto ganhou uma pagina propria no site.\n\n"
        f"{meta['title']} junta imagens, sequencias e um modo de olhar que eu queria "
        f"tirar da logica rapida do feed.\n\n"
        f"Se quiser ver completo, link na bio.\n\n"
        f"#fotografia #portfolio #arquivovisual"
    )


def generate_social_post(project_slug: str, platform: str) -> dict:
    meta = extract_project_meta(project_slug)
    tracked_url = build_tracked_url(
        meta["url"], platform, UTM_CAMPAIGNS.get(platform, "project-launch")
    )

    overrides = PROJECT_OVERRIDES.get(project_slug, {})
    template = overrides.get(platform)

    if template:
        text = template.format(title=meta["title"], url=tracked_url)
    elif platform == "linkedin":
        text = default_linkedin_text(meta, tracked_url)
    elif platform == "instagram":
        text = default_instagram_text(meta)
    else:
        raise ValueError(f"Plataforma nao suportada: {platform}")

    return {
        "platform": platform,
        "slug": meta["slug"],
        "title": meta["title"],
        "url": tracked_url,
        "image_url": meta["image_url"],
        "image_path": meta["image_path"],
        "instagram_image_url": meta["instagram_image_url"],
        "text": text,
    }


def print_result(result: dict) -> None:
    print(f"--- {result['platform'].capitalize()} ---")
    print(f"Titulo: {result['title']}")
    print(f"URL: {result['url']}")
    if result["image_url"]:
        print(f"Imagem: {result['image_url']}")
    print("Texto:")
    print(result["text"])
    print()


def serialize_result(result: dict) -> dict:
    data = dict(result)
    image_path = data.get("image_path")
    if image_path is not None:
        data["image_path"] = str(image_path)
    return data


def publish_linkedin(result: dict, allow_duplicate: bool) -> str:
    env = linkedin_post.load_env()
    token = env.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "LINKEDIN_ACCESS_TOKEN nao encontrado no .env. Rode python3 scripts/linkedin_auth.py"
        )

    author_urn = linkedin_post.get_member_urn(token, env)
    meta = {
        "slug": result["slug"],
        "title": result["title"],
        "description": result["text"].split("\n\n", 1)[0],
        "url": f"{BASE_URL}/projects/{result['slug']}.html",
        "image_path": result["image_path"],
    }
    signature = linkedin_post.build_publish_signature(author_urn, meta)
    if not allow_duplicate and linkedin_post.is_recent_duplicate(signature):
        raise RuntimeError(
            "Publicacao do LinkedIn bloqueada para evitar duplicata acidental. "
            "Use --allow-duplicate para repetir."
        )

    image_urn = None
    if result["image_path"]:
        upload_url, image_urn = linkedin_post.register_image_upload(token, author_urn)
        linkedin_post.upload_image(upload_url, result["image_path"], token)

    payload: dict = {
        "author": author_urn,
        "commentary": result["text"],
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    if image_urn:
        payload["content"] = {"media": {"id": image_urn}}
    else:
        payload["content"] = {
            "article": {
                "source": result["url"],
                "title": result["title"],
                "description": result["text"].split("\n\n", 1)[0],
            }
        }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{linkedin_post.LI_API}/posts",
        data=data,
        headers=linkedin_post._api_headers(token),
        method="POST",
    )
    with urllib.request.urlopen(req, context=linkedin_post.SSL_CONTEXT) as resp:
        resp.read()
        share_urn = resp.headers.get("x-restli-id", "")

    linkedin_post.save_publish_state(signature, share_urn)
    return share_urn


def publish_instagram(result: dict) -> tuple[str, str | None]:
    env = instagram_post.load_env()
    token = env.get("INSTAGRAM_ACCESS_TOKEN", "").strip()
    user_id = env.get("INSTAGRAM_USER_ID", "").strip()
    if not token or not user_id:
        raise RuntimeError(
            "Credenciais do Instagram ausentes no .env. Rode python3 scripts/instagram_auth.py"
        )
    if not result["instagram_image_url"]:
        raise RuntimeError(
            "Projeto sem card.jpg/card.png ou cover.jpg/cover.png publico. "
            "Instagram exige JPG/PNG por URL."
        )

    container_id = instagram_post.create_media_container(
        user_id,
        token,
        result["instagram_image_url"],
        result["text"],
    )

    import time

    for _ in range(10):
        status = instagram_post.check_container_status(container_id, token)
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise RuntimeError("Container do Instagram retornou erro de processamento.")
        time.sleep(3)
    else:
        raise RuntimeError("Container do Instagram nao ficou pronto a tempo.")

    media_id = instagram_post.publish_container(user_id, token, container_id)
    permalink = instagram_post.get_media_permalink(media_id, token)
    return media_id, permalink


def publish_results(results: list[dict], dry_run: bool, allow_duplicate: bool) -> int:
    for result in results:
        print_result(result)

    if dry_run:
        print("Dry run: nada publicado.")
        return 0

    exit_code = 0
    for result in results:
        try:
            if result["platform"] == "linkedin":
                share_urn = publish_linkedin(result, allow_duplicate)
                print(f"LinkedIn publicado: {share_urn or 'sem URN retornado'}")
            elif result["platform"] == "instagram":
                media_id, permalink = publish_instagram(result)
                if permalink:
                    print(f"Instagram publicado: {permalink}")
                else:
                    print(f"Instagram publicado. Media ID: {media_id}")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode()
            print(f"Erro ao publicar em {result['platform']}: HTTP {exc.code} {body}", file=sys.stderr)
            exit_code = 1
        except Exception as exc:
            print(f"Erro ao publicar em {result['platform']}: {exc}", file=sys.stderr)
            exit_code = 1

    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera copy social para projetos.")
    parser.add_argument(
        "--project-slug",
        default="fotografia-instagram",
        help="Slug do projeto em projects/<slug>.html",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o conteudo sem publicar.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Retorna o conteudo em JSON.",
    )
    parser.add_argument(
        "--allow-duplicate",
        action="store_true",
        help="Permite repetir o mesmo texto no LinkedIn em janela curta.",
    )
    parser.add_argument(
        "--only",
        choices=["linkedin", "instagram"],
        help="Publica apenas um canal.",
    )
    args = parser.parse_args()

    platforms = [args.only] if args.only else ["linkedin", "instagram"]
    results = [generate_social_post(args.project_slug, platform) for platform in platforms]

    if args.json:
        print(json.dumps([serialize_result(result) for result in results], ensure_ascii=False, indent=2))
        return 0

    return publish_results(results, args.dry_run, args.allow_duplicate)


if __name__ == "__main__":
    raise SystemExit(main())

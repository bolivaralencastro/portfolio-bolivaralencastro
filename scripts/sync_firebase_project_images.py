#!/usr/bin/env python3
"""Download project images from Firebase Storage into organized local folders."""

from __future__ import annotations

import pathlib
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError

PROJECT_FILES = {
    "branding-identidade-visual": [
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/projects/503c255c-a147-4e8f-91bf-ea76f850e7f1-bolivar-alencastro-rascunhos-marcas.webp",
            "cover.webp",
        ),
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/projects/7354ea31-5681-4e00-9413-1d0ab3059eb5-bolivar-alencastro-rascunhos-marcas.webp",
            "og.webp",
        ),
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/posts/61a54273-e3b9-41ba-876f-9c427575525c/images/11318d31-0aeb-464c-b3ac-cd08b0059aeb-Kirinus-Escola-de-Dança.webp",
            "gallery-01-kirinus-escola-de-danca.webp",
        ),
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/posts/61a54273-e3b9-41ba-876f-9c427575525c/images/717b42ba-dd4c-4788-a7a0-1e8769846e8a-debate.webp",
            "gallery-02-debate-diario.webp",
        ),
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/posts/61a54273-e3b9-41ba-876f-9c427575525c/images/7779c807-ecc0-49bc-b311-9b95f48b42ef-Posh.webp",
            "gallery-03-posh-10-anos.webp",
        ),
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/posts/61a54273-e3b9-41ba-876f-9c427575525c/images/bb9505bc-8a08-4634-8913-e44dad74c708-Floripa-Futuro.webp",
            "gallery-04-instituto-floripa-futuro.webp",
        ),
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/posts/61a54273-e3b9-41ba-876f-9c427575525c/images/9e219b67-3049-45e8-871e-6a70dc2aaa84-imersao-em-danca.webp",
            "gallery-05-imersao-em-danca.webp",
        ),
    ],
    "kirinus-escola-de-danca": [
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/projects/2804c225-2e81-462a-93c4-aefefb93ec86-kirinus-escola-de-danca-maquete.webp",
            "cover.webp",
        ),
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/projects/59011057-4f13-42b2-a01b-a6253a55ca3d-assets_task_01k3vg8dj7fghvtrdbfb0raqzw_1756491045_img_0.webp",
            "og.webp",
        ),
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/posts/PxXG1Ao2SpfN06aT3BnC/images/c65e0d4a-b4e3-4841-951c-ad2827c5c5c2-753b1eb3-7fb9-4d4d-bfb6-01c8b7230bfc.png",
            "gallery-01-kirinus-escola-de-danca.png",
        ),
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/posts/PxXG1Ao2SpfN06aT3BnC/images/12276243-80be-4c4a-9f9e-d1c09b5b8756-d15eb4fe-f341-43c8-af17-4bab988eac3f.webp",
            "gallery-02-kirinus-identidade-visual.webp",
        ),
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/posts/PxXG1Ao2SpfN06aT3BnC/images/07493d4c-5983-4373-91e2-47dd0baa49db-c509d03a-a2ae-4f4a-a058-e297629f0b7e.jpg",
            "gallery-03-kirinus-material-promocional.jpg",
        ),
    ],
    "keeps-learning-konquest": [
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/projects/ab53d1b2-6d66-4d97-bf45-157fe053fe01-keeps-learning-por-bolivar-alencastro.webp",
            "cover.webp",
        ),
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/projects/47a93498-c7f2-4c51-8e4e-2d3417110034-keeps-learning.webp",
            "og.webp",
        ),
        (
            "https://firebasestorage.googleapis.com/v0/b/alencastro-portfolio.firebasestorage.app/o/public%2Fposts%2FaZ4WwpiRPDSNzydqcD56%2Fimages%2F7145a3f6-5316-4085-8141-3e7db5a09ac2-mock-konquest.webp?alt=media",
            "gallery-01-konquest-mockup.webp",
        ),
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/posts/aZ4WwpiRPDSNzydqcD56/images/df004c06-5077-4963-af9c-8a26e93474b6-keeps-learning-logo.png",
            "gallery-02-keeps-learning-logo.png",
        ),
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/posts/aZ4WwpiRPDSNzydqcD56/images/e1169cad-86c0-42d5-8710-bfef88ca4039-identidade-visual-keeps-papelaria.webp",
            "gallery-03-keeps-learning-papelaria.webp",
        ),
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/posts/aZ4WwpiRPDSNzydqcD56/images/cb097504-34f6-4497-ac20-ba2b4f47d466-identidade-visual-keeps-uniforma.webp",
            "gallery-04-keeps-learning-uniforme.webp",
        ),
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/posts/aZ4WwpiRPDSNzydqcD56/images/b10f3960-67c9-47dc-8d3d-d65390fdf355-Identidade-visual-keeps-desktop.webp",
            "gallery-05-keeps-learning-desktop.webp",
        ),
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/projects/3288eb6d-4843-464c-931e-ff3d060eef52-blo-bolivar-alencastro-Um-olhar-nostalgico-para-Internet-1024x576.png",
            "gallery-06-blog-um-olhar-nostalgico-1024x576.png",
        ),
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/projects/746e9467-5994-41fa-81cb-435a18c72d7f-blog-bolivar-alencastro-som-familiar-vertical-1024x576.png",
            "gallery-07-blog-som-familiar-vertical-1024x576.png",
        ),
    ],
    "intelbras-opl-cidades-invisiveis": [
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/projects/830c89ed-4b76-4416-90af-218276fb1021-camera-intelbras.webp",
            "cover.webp",
        ),
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/projects/7740aad2-b785-4a21-ad7f-23564638f4a7-enhanced_97cb3b6a-3cad-44c0-8d68-196e1426cf54.png",
            "og.png",
        ),
        (
            "https://storage.googleapis.com/alencastro-portfolio.firebasestorage.app/public/posts/yY5euMZTjeg7NofLpwrv/images/6a000845-b760-461e-94cf-1ac075f3a40d-fotos-da-opl.webp",
            "gallery-01-opl-produto.webp",
        ),
    ],
}


def download(url: str, target: pathlib.Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    parsed = urllib.parse.urlsplit(url)
    encoded_path = urllib.parse.quote(parsed.path, safe="/%")
    encoded_query = urllib.parse.quote_plus(parsed.query, safe="=&")
    safe_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, encoded_path, encoded_query, parsed.fragment))
    with urllib.request.urlopen(safe_url, timeout=30) as response:
        data = response.read()
    target.write_bytes(data)


def main() -> int:
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    base_dir = repo_root / "assets" / "images" / "projects"

    downloaded = 0
    for project_slug, items in PROJECT_FILES.items():
        for url, filename in items:
            output = base_dir / project_slug / filename
            try:
                download(url, output)
                downloaded += 1
                print(f"downloaded: {output.relative_to(repo_root).as_posix()}")
            except (HTTPError, URLError, TimeoutError) as exc:
                print(f"failed: {url} -> {output.relative_to(repo_root).as_posix()} ({exc})")

    print(f"done: {downloaded} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

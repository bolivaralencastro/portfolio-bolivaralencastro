#!/usr/bin/env python3

from __future__ import annotations

import argparse
from http.cookiejar import MozillaCookieJar
from pathlib import Path

import browser_cookie3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exporta cookies do Instagram do Chrome para arquivo Netscape."
    )
    parser.add_argument(
        "output",
        help="Caminho do arquivo de saída em formato Netscape.",
    )
    parser.add_argument(
        "--browser",
        default="chrome",
        choices=["chrome", "chromium", "edge", "firefox", "opera", "brave", "vivaldi"],
        help="Navegador de origem dos cookies. Padrão: chrome.",
    )
    parser.add_argument(
        "--domain",
        default="instagram.com",
        help="Domínio para filtrar cookies. Padrão: instagram.com.",
    )
    return parser.parse_args()


def load_cookies(browser: str, domain: str):
    loaders = {
        "chrome": browser_cookie3.chrome,
        "chromium": browser_cookie3.chromium,
        "edge": browser_cookie3.edge,
        "firefox": browser_cookie3.firefox,
        "opera": browser_cookie3.opera,
        "brave": browser_cookie3.brave,
        "vivaldi": browser_cookie3.vivaldi,
    }
    return loaders[browser](domain_name=domain)


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    source_jar = load_cookies(args.browser, args.domain)
    jar = MozillaCookieJar(str(output_path))
    count = 0
    for cookie in source_jar:
        jar.set_cookie(cookie)
        count += 1

    if count == 0:
        raise SystemExit(f"Nenhum cookie encontrado para {args.domain} em {args.browser}.")

    jar.save(ignore_discard=True, ignore_expires=True)
    print(f"Saved {count} cookies to {output_path}")


if __name__ == "__main__":
    main()
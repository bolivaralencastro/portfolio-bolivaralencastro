#!/usr/bin/env python3
"""
Captura itens salvos via navegador autenticado e alimenta o banco de curadoria.

O script usa o Chrome DevTools Protocol em uma sessão já logada. Ele não usa APIs
privadas nem credenciais da plataforma; apenas lê os links que a própria página
renderiza para o usuário autenticado.

Uso:
    python3 scripts/social_capture_browser.py linkedin-saved
    python3 scripts/social_capture_browser.py instagram-saved
    python3 scripts/social_capture_browser.py all
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import socket
import ssl
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from social_curation import connect  # noqa: E402


DEFAULT_PORT = 9333
LINKEDIN_SAVED_URL = "https://www.linkedin.com/my-items/saved-posts/"
INSTAGRAM_SAVED_URL = "https://www.instagram.com/{profile}/saved/all-posts/"


@dataclass(frozen=True)
class CapturedItem:
    source: str
    kind: str
    url: str
    title: str = ""
    text: str = ""
    author: str = ""
    author_handle: str = ""
    platform_post_id: str = ""
    raw_json: str = ""
    origin_file: str = ""

    @property
    def fingerprint(self) -> str:
        raw = f"{self.source}|{self.kind}|{self.url}|{self.author}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class CDP:
    def __init__(self, ws_url: str, timeout: int = 90):
        parsed = urllib.parse.urlparse(ws_url)
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or (443 if parsed.scheme == "wss" else 80)
        self.path = parsed.path
        raw = socket.create_connection((self.host, self.port), timeout=10)
        raw.settimeout(timeout)
        self.sock = ssl.wrap_socket(raw, server_hostname=self.host) if parsed.scheme == "wss" else raw
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode())
        resp = self.sock.recv(4096)
        if b" 101 " not in resp:
            raise RuntimeError(resp.decode(errors="replace"))
        self.next_id = 1

    def _send_frame(self, payload: str) -> None:
        data = payload.encode()
        header = bytearray([0x81])
        if len(data) < 126:
            header.append(0x80 | len(data))
        elif len(data) < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", len(data)))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", len(data)))
        mask = os.urandom(4)
        header.extend(mask)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(header + masked)

    def _read_exact(self, n: int) -> bytes:
        chunks: list[bytes] = []
        remaining = n
        while remaining:
            chunk = self.sock.recv(remaining)
            if not chunk:
                raise EOFError("socket closed")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _recv_frame(self) -> str | None:
        b1, b2 = self._read_exact(2)
        opcode = b1 & 0x0F
        length = b2 & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]
        mask = self._read_exact(4) if b2 & 0x80 else b""
        data = self._read_exact(length)
        if mask:
            data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        if opcode == 8:
            raise EOFError("websocket closed")
        if opcode in (1, 2):
            return data.decode(errors="replace")
        return None

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        msg_id = self.next_id
        self.next_id += 1
        self._send_frame(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
        while True:
            frame = self._recv_frame()
            if not frame:
                continue
            msg = json.loads(frame)
            if msg.get("id") == msg_id:
                if "error" in msg:
                    raise RuntimeError(json.dumps(msg["error"], ensure_ascii=False))
                return msg.get("result", {})

    def evaluate(self, expression: str, timeout_ms: int = 60000) -> Any:
        result = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": True,
                "returnByValue": True,
                "timeout": timeout_ms,
            },
        )
        return result.get("result", {}).get("value")


def get_ws_url(port: int) -> str:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
            pages = json.loads(response.read())
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Chrome DevTools nao encontrado. Inicie o Chrome assim:\n"
            "open -na 'Google Chrome' --args --remote-debugging-port=9333\n"
            "Depois, abra as paginas com login ativo e rode novamente."
        ) from exc
    for page in pages:
        if page.get("type") == "page":
            return page["webSocketDebuggerUrl"]
    raise RuntimeError("Nenhuma aba Chrome com DevTools encontrada")


def canonical_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/") + "/", "", "", ""))


def capture_js(source: str, scrolls: int, delay_ms: int, limit: int) -> str:
        if source == "linkedin":
                pattern = r"linkedin\.com\/(feed\/update|posts|pulse)\/"
        else:
                pattern = r"instagram\.com\/(p|reel|tv)\/"

        return fr"""
        (async () => {{
            const matches = new RegExp({pattern!r});
            const items = new Map();
            const clean = (value) => (value || '').replace(/\s+/g, ' ').trim();
            const pick = (...values) => values.map(v => clean(v)).find(Boolean) || '';
            const canonical = (href) => {{
                const u = new URL(href, location.href);
                u.search = '';
                u.hash = '';
                return u.href;
            }};
            const extractPostId = (url) => {{
                if (/linkedin\.com/.test(url)) {{
                    const m = url.match(/activity:(\d+)/);
                    return m ? m[1] : '';
                }}
                const m = url.match(/instagram\.com\/(?:p|reel|tv)\/([^/]+)/);
                return m ? m[1] : '';
            }};
            const profileFromHref = (href) => {{
                if (!href) return '';
                const m = href.match(/instagram\.com\/([^/?#]+)/);
                return m ? m[1] : '';
            }};
            const collect = () => {{
                for (const anchor of document.querySelectorAll('a[href]')) {{
                    const url = canonical(anchor.href);
                    if (!matches.test(url) || items.has(url)) continue;
                    const card = anchor.closest('article, li, [data-urn], .feed-shared-update-v2, [role="article"], div');
                    const authorAnchor = card && card.querySelector('a[href*="/in/"], a[href*="/company/"], a[href^="https://www.instagram.com/"]');
                    const title = pick(
                        anchor.getAttribute('aria-label'),
                        anchor.innerText,
                        anchor.textContent,
                        card && card.querySelector('h1, h2, h3') && card.querySelector('h1, h2, h3').textContent
                    ).slice(0, 240);
                    const text = pick(
                        card && card.innerText,
                        anchor.getAttribute('aria-label'),
                        title
                    ).slice(0, 4000);
                    const author = pick(
                        authorAnchor && authorAnchor.textContent,
                        card && card.querySelector('[data-anonymize="person-name"]') && card.querySelector('[data-anonymize="person-name"]').textContent,
                        ''
                    ).slice(0, 120);
                    const authorHandle = pick(profileFromHref(authorAnchor && authorAnchor.href), '').slice(0, 120);
                    const payload = {{
                        page: location.href,
                        cardTag: card && card.tagName,
                        anchorText: clean(anchor.textContent).slice(0, 180),
                        authorHref: authorAnchor && authorAnchor.href || ''
                    }};
                    items.set(url, {{
                        url,
                        title,
                        text,
                        author,
                        author_handle: authorHandle,
                        platform_post_id: extractPostId(url),
                        raw_json: JSON.stringify(payload)
                    }});
                }}
            }};
            for (let i = 0; i <= {scrolls}; i++) {{
                collect();
                if (items.size >= {limit}) break;
                window.scrollBy(0, Math.floor(window.innerHeight * 0.9));
                await new Promise(resolve => setTimeout(resolve, {delay_ms}));
            }}
            collect();
            return {{
                url: location.href,
                title: document.title,
                count: items.size,
                items: Array.from(items.values()).slice(0, {limit})
            }};
        }})()
        """


def detail_capture_js(source: str) -> str:
    if source == "linkedin":
        return r"""
        (() => {
          const clean = (v) => (v || '').replace(/\s+/g, ' ').trim();
          const pick = (...vs) => vs.map(v => clean(v)).find(Boolean) || '';
          const getMeta = (n) => {
            const el = document.querySelector(`meta[property="${n}"], meta[name="${n}"]`);
            return el && el.content ? clean(el.content) : '';
          };
          const dedup = (s) => {
            const t = clean(s);
            const h = Math.floor(t.length / 2);
            const a = t.slice(0, h), b = t.slice(h);
            return (a === b) ? a : t;
          };
          // On individual post pages LinkedIn uses .update-components-actor__title for the name
                      const titleEl = document.querySelector('.update-components-actor__title span[aria-hidden="true"]') ||
                                      document.querySelector('.update-components-actor__title') ||
                                      document.querySelector('.update-components-actor__name');
                    // Prefer aria-hidden span which contains only the name (no headline duplication)
                    const ariaSpan = titleEl && titleEl.querySelector('span[aria-hidden="true"]');
                    const actorName = ariaSpan ? clean(ariaSpan.textContent) : (titleEl ? dedup(titleEl.textContent) : '');
          const actorSubEl = document.querySelector('.update-components-actor__description');
          const actorSub = actorSubEl ? clean(actorSubEl.textContent) : '';
          const metaLinkEl = document.querySelector('.update-components-actor__meta-link') ||
                             document.querySelector('.update-components-actor__container-link, .update-components-actor__container > a');
          const actorHref = metaLinkEl ? metaLinkEl.href : '';
          const authorHandle = (() => {
                        const m = actorHref.match(/linkedin\.com\/(?:in|company|showcase)\/([^/?#]+)/);
            return m ? m[1] : '';
          })();
          const author = actorName.slice(0, 180);
          const article = document.querySelector('article, .feed-shared-update-v2, [role="main"]');
          const bodyText = pick(
            article && article.innerText,
            document.body && document.body.innerText,
            ''
          );
          const ogTitle = getMeta('og:title');
          const ogDesc = getMeta('og:description');
          const title = pick(ogTitle, document.title, bodyText.split('\n')[0] || '').slice(0, 240);
          const text = pick(bodyText, ogDesc, '').slice(0, 12000);
          const canonicalEl = document.querySelector('link[rel="canonical"]');
          const canonical = canonicalEl && canonicalEl.href ? canonicalEl.href : location.href;
          const postIdMatch = canonical.match(/activity:(\d+)/);
          const platformPostId = postIdMatch ? postIdMatch[1] : '';
          return {
            title, text, author,
            author_handle: authorHandle,
            author_sub: actorSub,
            platform_post_id: platformPostId,
            canonical_url: canonical,
            raw_json: JSON.stringify({
              page_title: document.title,
              og_title: ogTitle,
              og_description: ogDesc,
              actor_href: actorHref,
            }),
          };
        })()
        """
    return r"""
    (() => {
      const clean = (v) => (v || '').replace(/\s+/g, ' ').trim();
      const pick = (...vs) => vs.map(v => clean(v)).find(Boolean) || '';
      const getMeta = (n) => {
        const el = document.querySelector(`meta[property="${n}"], meta[name="${n}"]`);
        return el && el.content ? clean(el.content) : '';
      };
      const ogDesc = getMeta('og:description');
    const descMatch = ogDesc.match(/(?:[-\u2013]\s*)?(\S+)\s+(?:on|no)\s+\w/i);
    const authorHandle = descMatch ? descMatch[1].replace(/^@/, '') : '';
      const article = document.querySelector('article');
      const headerAnchor = article && article.querySelector('header a[href^="/"]');
      const headerHandle = (() => {
        const h = headerAnchor && headerAnchor.href ? headerAnchor.href : '';
        const m = h.match(/instagram\.com\/([^/?#]+)/);
        return m ? m[1] : '';
      })();
      const finalHandle = authorHandle || headerHandle;
      const ogTitle = getMeta('og:title');
      const colonIdx = ogDesc.indexOf(': "');
      const caption = colonIdx >= 0 ? ogDesc.slice(colonIdx + 3).replace(/"$/, '') : ogDesc;
      const title = pick(ogTitle, caption.split('\n')[0] || '', document.title).slice(0, 240);
      const text = pick(caption, ogDesc, article && article.innerText, '').slice(0, 12000);
      const canonicalEl = document.querySelector('link[rel="canonical"]');
      const canonical = canonicalEl && canonicalEl.href ? canonicalEl.href : location.href;
      const postIdMatch = canonical.match(/instagram\.com\/(?:p|reel|tv)\/([^/]+)/);
      const platformPostId = postIdMatch ? postIdMatch[1] : '';
      return {
        title, text,
        author: finalHandle,
        author_handle: finalHandle,
        platform_post_id: platformPostId,
        canonical_url: canonical,
        raw_json: JSON.stringify({
          page_title: document.title,
          og_title: ogTitle,
          og_description: ogDesc.slice(0, 400),
        }),
      };
    })()
    """


def capture_post_details(
    cdp: CDP,
    source: str,
    url: str,
    delay_ms: int = 1800,
    timeout_ms: int = 60000,
) -> dict:
    try:
        cdp.call("Page.navigate", {"url": url})
        time.sleep(max(delay_ms / 1000, 1.5))
        result = cdp.evaluate(detail_capture_js(source))
        if isinstance(result, dict):
            return result
    except Exception as exc:
        print(f"  capture_post_details erro {url}: {exc}")
    return {}


def open_and_capture(
    cdp: CDP,
    url: str,
    source: str,
    scrolls: int,
    delay_ms: int,
    limit: int,
    hydrate_details: bool,
    detail_delay_ms: int,
    detail_timeout_ms: int,
) -> list[CapturedItem]:
    cdp.call("Runtime.enable")
    cdp.call("Page.enable")
    cdp.call("Page.navigate", {"url": url})
    time.sleep(5)
    data = cdp.evaluate(capture_js(source, scrolls, delay_ms, limit))
    if not isinstance(data, dict):
        return []

    items: list[CapturedItem] = []
    for raw in data.get("items", []):
        item_url = canonical_url(str(raw.get("url", "")))
        if not item_url:
            continue
        raw_json = str(raw.get("raw_json") or "")
        if not raw_json:
            raw_json = json.dumps(raw, ensure_ascii=False)
        items.append(
            CapturedItem(
                source=source,
                kind="saved",
                url=item_url,
                title=str(raw.get("title") or ""),
                text=str(raw.get("text") or ""),
                author=str(raw.get("author") or ""),
                author_handle=str(raw.get("author_handle") or ""),
                platform_post_id=str(raw.get("platform_post_id") or ""),
                raw_json=raw_json,
                origin_file=f"browser:{source}-saved",
            )
        )
    unique_items = list({item.url: item for item in items}.values())
    if not hydrate_details:
        return unique_items

    enriched: list[CapturedItem] = []
    for idx, item in enumerate(unique_items, start=1):
        try:
            detail = capture_post_details(cdp, source, item.url, detail_delay_ms, detail_timeout_ms)
        except Exception as exc:
            print(f"{source}: detalhe falhou [{idx}/{len(unique_items)}] {item.url} -> {exc}")
            enriched.append(item)
            continue

        detail_text = str(detail.get("text") or "")
        detail_title = str(detail.get("title") or "")
        detail_author = str(detail.get("author") or "")
        detail_handle = str(detail.get("author_handle") or "")
        detail_post_id = str(detail.get("platform_post_id") or "")
        detail_url = canonical_url(str(detail.get("canonical_url") or item.url))
        detail_raw_json = str(detail.get("raw_json") or "")

        enriched.append(
            CapturedItem(
                source=item.source,
                kind=item.kind,
                url=detail_url,
                title=detail_title or item.title,
                text=detail_text if len(detail_text) > len(item.text) else item.text,
                author=detail_author or item.author,
                author_handle=detail_handle or item.author_handle,
                platform_post_id=detail_post_id or item.platform_post_id,
                raw_json=detail_raw_json or item.raw_json,
                origin_file=item.origin_file,
            )
        )
        print(f"{source}: detalhe ok [{idx}/{len(unique_items)}] {detail_url}")
    return list({item.url: item for item in enriched}.values())


def insert_items(items: list[CapturedItem]) -> tuple[int, int]:
    con = connect()
    found = 0
    inserted = 0
    today = datetime.now().date().isoformat()
    for item in items:
        found += 1
        cur = con.execute(
            """
            INSERT OR IGNORE INTO social_items
            (fingerprint, source, kind, url, date, title, text, author, author_handle, platform_post_id, raw_json, origin_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.fingerprint,
                item.source,
                item.kind,
                item.url,
                today,
                item.title,
                item.text,
                item.author,
                item.author_handle,
                item.platform_post_id,
                item.raw_json,
                item.origin_file,
            ),
        )
        inserted += cur.rowcount
    con.commit()
    con.close()
    return found, inserted


def update_authors(cdp: CDP, source: str, delay_ms: int, timeout_ms: int) -> int:
    """Re-visit posts with empty author and update author/author_handle fields."""
    con = connect()
    rows = con.execute(
        "SELECT fingerprint, url FROM social_items WHERE source=? AND (author IS NULL OR author='') ORDER BY date DESC",
        (source,),
    ).fetchall()
    con.close()
    updated = 0
    for idx, (fingerprint, url) in enumerate(rows, 1):
        detail = capture_post_details(cdp, source, url, delay_ms, timeout_ms)
        if not detail:
            print(f"  sem detalhe [{idx}/{len(rows)}] {url}")
            continue
        author = detail.get("author", "")
        author_handle = detail.get("author_handle", "")
        text = detail.get("text", "")
        raw_json = detail.get("raw_json", "")
        if author or text:
            con = connect()
            con.execute(
                """UPDATE social_items SET author=?, author_handle=?, text=CASE WHEN (text IS NULL OR text='') THEN ? ELSE text END, raw_json=CASE WHEN (raw_json IS NULL OR raw_json='') THEN ? ELSE raw_json END WHERE fingerprint=?""",
                (author, author_handle, text, raw_json, fingerprint),
            )
            con.commit()
            con.close()
            updated += 1
        print(f"  {source} autor=[{author or '—'}] [{idx}/{len(rows)}] {url}")
    return updated


def run_target(cdp: CDP, target: str, args: argparse.Namespace) -> tuple[int, int]:
    if target == "linkedin-saved":
        items = open_and_capture(
            cdp,
            LINKEDIN_SAVED_URL,
            "linkedin",
            args.scrolls,
            args.delay_ms,
            args.limit,
            args.hydrate_details,
            args.detail_delay_ms,
            args.detail_timeout_ms,
        )
    elif target == "instagram-saved":
        url = INSTAGRAM_SAVED_URL.format(profile=args.instagram_profile)
        items = open_and_capture(
            cdp,
            url,
            "instagram",
            args.scrolls,
            args.delay_ms,
            args.limit,
            args.hydrate_details,
            args.detail_delay_ms,
            args.detail_timeout_ms,
        )
    else:
        raise ValueError(target)
    found, inserted = insert_items(items)
    print(f"{target}: encontrados={found} novos={inserted}")
    return found, inserted


def main() -> None:
    parser = argparse.ArgumentParser(description="Captura itens salvos pelo navegador autenticado")
    parser.add_argument("target", choices=["linkedin-saved", "instagram-saved", "all"])
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--scrolls", type=int, default=5)
    parser.add_argument("--delay-ms", type=int, default=1200)
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--instagram-profile", default="bolivar.alencastro")
    parser.add_argument("--no-hydrate-details", action="store_false", dest="hydrate_details")
    parser.add_argument("--detail-delay-ms", type=int, default=1800)
    parser.add_argument("--detail-timeout-ms", type=int, default=60000)
    parser.add_argument("--update-authors", action="store_true", help="Re-visit posts with empty author and update; skip normal capture")
    parser.set_defaults(hydrate_details=True)
    args = parser.parse_args()

    cdp = CDP(get_ws_url(args.port))

    if args.update_authors:
        sources = ["linkedin", "instagram"] if args.target == "all" else [args.target.replace("-saved", "")]
        for src in sources:
            n = update_authors(cdp, src, args.detail_delay_ms, args.detail_timeout_ms)
            print(f"{src}: atualizados={n}")
        return

    targets = ["linkedin-saved", "instagram-saved"] if args.target == "all" else [args.target]
    total_found = 0
    total_inserted = 0
    for target in targets:
        found, inserted = run_target(cdp, target, args)
        total_found += found
        total_inserted += inserted
    print(f"Total: encontrados={total_found} novos={total_inserted}")


if __name__ == "__main__":
    main()

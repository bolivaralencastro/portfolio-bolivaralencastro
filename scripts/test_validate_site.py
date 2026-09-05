"""Regression tests for failures that previously passed the public-site validator."""

import json
from pathlib import Path
import struct
import tempfile
import unittest

from build_site_metadata import SITE_CSP_CONTENT, VERSIONED_ASSETS, apply_versioned_asset_refs
from image_metadata import image_metadata
from validate_site import PageMeta, PageParser, extract_jsonld_types, validate_page_policy, validate_page_images


class SitePolicyTests(unittest.TestCase):
    def page(self, source):
        page = PageMeta(Path("index.html"), "index.html", canonical="https://bolivaralencastro.com.br/", csp_content=SITE_CSP_CONTENT)
        PageParser(page).feed(source)
        return page

    def errors(self, source):
        errors = []
        validate_page_policy(self.page(source), errors)
        return errors

    def test_inline_code_styles_handlers_and_javascript_urls_fail(self):
        for source in ('<style>p{color:red}</style>', '<p style="color:red">x</p>', '<script>alert(1)</script>', '<button onclick="go()">x</button>', '<a href="javascript:go()">x</a>'):
            with self.subTest(source=source):
                self.assertTrue(self.errors(source))

    def test_valid_jsonld_is_data_and_invalid_jsonld_fails(self):
        self.assertFalse(self.errors('<script type="application/ld+json">{"@type":"BlogPosting"}</script>'))
        for payload in ('{"@type":"BlogPosting",}', ''):
            self.assertTrue(self.errors(f'<script type="application/ld+json">{payload}</script>'))
            self.assertEqual(extract_jsonld_types(payload), set())

    def test_csp_cannot_be_missing_or_weakened(self):
        for csp in ('', SITE_CSP_CONTENT + " script-src 'unsafe-inline';"):
            page = self.page('')
            page.csp_content = csp
            errors = []
            validate_page_policy(page, errors)
            self.assertTrue(errors)

    def test_all_registered_assets_get_versioned(self):
        versions = {path: "a123bc" for path in VERSIONED_ASSETS}
        for path in versions:
            source = f'<link rel="stylesheet" href="{path}">' if path.endswith('.css') else f'<script src="{path}" defer></script>'
            updated = apply_versioned_asset_refs(source, versions)
            self.assertIn('?v=a123bc', updated)
            self.assertFalse(self.errors(updated))
            self.assertEqual(updated, apply_versioned_asset_refs(updated, versions))

    def test_unregistered_assets_fail(self):
        self.assertTrue(self.errors('<script src="/assets/js/unregistered.js?v=abc" defer></script>'))

    def test_raster_dimensions_and_truncated_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture'
            fixtures = [
                (b'\x89PNG\r\n\x1a\n' + b'\0' * 8 + struct.pack('>II', 2400, 1200), ('PNG', 2400, 1200)),
                (b'\xff\xd8\xff\xc0\x00\x0b\x08' + struct.pack('>HH', 630, 1200) + b'\x01\x01\x11\x00', ('JPEG', 1200, 630)),
                (b'RIFF' + struct.pack('<I', 22) + b'WEBPVP8X' + struct.pack('<I', 10) + b'\0' * 4 + (1199).to_bytes(3, 'little') + (629).to_bytes(3, 'little'), ('WEBP', 1200, 630)),
            ]
            for data, expected in fixtures:
                path.write_bytes(data)
                image_metadata.cache_clear()
                self.assertEqual(image_metadata(path), expected)
            path.write_bytes(b'\xff\xd8\xff')
            image_metadata.cache_clear()
            with self.assertRaises(ValueError):
                image_metadata(path)

    def test_image_budget_dimensions_attributes_and_social_format(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'large.png'
            path.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\0' * 8 + struct.pack('>II', 2400, 1200) + b'\0' * 500000)
            page = self.page('<img src="/large.png">')
            page.og_image = 'https://bolivaralencastro.com.br/large.png'
            errors = []
            validate_page_images(root, page, errors)
            for expected in ('500KB', '2000px', 'width', 'height', 'decoding', 'JPEG 1200x630', '300KB'):
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_missing_image_fails_but_empty_dialog_placeholder_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            errors = []
            validate_page_images(Path(directory), self.page('<img src="/missing.webp" width="10" height="10" decoding="async">'), errors)
            self.assertTrue(any('missing image' in error for error in errors))
            errors = []
            validate_page_images(Path(directory), self.page('<dialog><img src="" alt="Imagem ampliada"></dialog>'), errors)
            self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()

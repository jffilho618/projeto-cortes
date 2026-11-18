"""Teste obrigatório R-08 (AD-7): Área Segura Unificada 9:16 nas legendas .ass."""
import re
import tempfile
import unittest
from pathlib import Path

import render_clips


class TestSafeZoneCaptions(unittest.TestCase):
    def test_aspect_9_16_uses_safe_margin_v_450(self):
        tw, th, font_size, margin_v = render_clips.ASPECTS["9:16"]
        self.assertEqual((tw, th), (1080, 1920))
        self.assertGreaterEqual(margin_v, 440, "AD-7 exige margin_v >= 440px (padrão 450px) em 9:16")
        self.assertEqual(margin_v, 450)

    def test_build_ass_9_16_enforces_safe_zone_margins(self):
        words = [
            {"word": "Olha", "start": 0.0, "end": 0.4},
            {"word": "esse", "start": 0.4, "end": 0.8},
            {"word": "lance!", "start": 0.8, "end": 1.4},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            ass_path = Path(tmp) / "test_9_16.ass"
            tw, th, font_size, margin_v = render_clips.ASPECTS["9:16"]
            render_clips.build_ass(
                words, 0.0, 1.5, ass_path, tw, th, font_size, margin_v
            )
            content = ass_path.read_text(encoding="utf-8")

        style_line = next(
            (line for line in content.splitlines() if line.startswith("Style: Cap,")),
            None,
        )
        self.assertIsNotNone(style_line, "Linha Style: Cap não encontrada no arquivo .ass")
        fields = style_line.split(",")
        # Format: ..., Alignment(18), MarginL(19), MarginR(20), MarginV(21), Encoding(22)
        margin_l = int(fields[19])
        margin_r = int(fields[20])
        actual_margin_v = int(fields[21])

        self.assertGreaterEqual(margin_l, 80, "MarginL deve ser >= 80px em 1080x1920")
        self.assertGreaterEqual(margin_r, 160, "MarginR deve ser >= 160px em 1080x1920 para fugir dos botões laterais")
        self.assertGreaterEqual(actual_margin_v, 440, "MarginV deve ser >= 440px em 1080x1920")

    def test_make_detector_uses_local_yunet_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            kind, det = render_clips._make_detector(Path(tmp) / "work")
            self.assertEqual(kind, "yunet")
            self.assertIsNotNone(det)


if __name__ == "__main__":
    unittest.main()

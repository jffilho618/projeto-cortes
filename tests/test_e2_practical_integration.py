"""Testes de integração prática do Épico 2 (resolução de CLI agy/claude, persistência UI->DB e /api/db/status)."""
import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path


class TestE2PracticalIntegration(unittest.TestCase):
    def test_resolve_cli_binary_finds_agy_outside_path(self):
        from picorte.config import resolve_cli_binary

        agy_bin = resolve_cli_binary("agy")
        expected = Path.home() / ".gemini" / "bin" / "agy"
        if expected.exists():
            self.assertIsNotNone(agy_bin)
            self.assertTrue(Path(agy_bin).exists())

    def test_studio_sync_persists_video_and_clips_for_mcp(self):
        from picorte.db.connection import Database
        from picorte.mcp.server import PicorteMCPServer
        from picorte.services.studio_service import StudioService

        with tempfile.TemporaryDirectory() as tmp:
            db = Database(f"sqlite:///{Path(tmp) / 'sync.db'}")
            db.init_schema()
            service = StudioService(db)
            mcp = PicorteMCPServer(service=service)

            proj_state = {
                "id": "abc123def456",
                "source": "/tmp/live_gta6.mp4",
                "video": "/tmp/live_gta6.mp4",
                "status": "complete",
                "options": {"aspect": "9:16", "ai_mode": "gemini"},
            }
            segments = [
                {
                    "id": "001",
                    "start": 12.0,
                    "end": 54.0,
                    "overall": 9.3,
                    "llm_mode_used": "gemini",
                    "proposed_title": "Fuga impossível no GTA 6",
                    "context_banner_2s": "5 estrelas de polícia",
                    "pinned_comment_debate": "Como ele sobreviveu?",
                }
            ]
            outputs = [str(Path(tmp) / "001-fuga.mp4")]

            synced = service.sync_studio_project(
                proj_state, segments=segments, outputs=outputs, workdir=Path(tmp)
            )
            self.assertEqual(synced["video"]["id"], "studio-abc123def456")

            clips_via_mcp = mcp.call_tool("picorte_listar_cortes", {"video_id": synced["video"]["id"]})
            self.assertEqual(len(clips_via_mcp), 1)
            self.assertEqual(clips_via_mcp[0]["llm_mode_used"], "gemini")
            self.assertEqual(clips_via_mcp[0]["proposed_title"], "Fuga impossível no GTA 6")
            self.assertEqual(clips_via_mcp[0]["mp4_path"], outputs[0])

    def test_dashboard_exposes_db_status_endpoint(self):
        import dashboard

        with tempfile.TemporaryDirectory() as tmp:
            httpd = dashboard.make_server(Path(tmp), port=0)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{httpd.server_port}"
                with urllib.request.urlopen(base + "/api/db/status") as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                self.assertIn("gpu_profile", payload)
                self.assertIn("total_clips", payload)
                self.assertIn("total_sources", payload)
            finally:
                httpd.shutdown()
                httpd.server_close()
                httpd.app.close()
                thread.join()


if __name__ == "__main__":
    unittest.main()

"""Testes TDD para a camada unificada picorte/services/ (AD-10), Servidor MCP e Skill picorte-operador (Story 2.4)."""
import json
import tempfile
import unittest
from pathlib import Path


class TestMcpAndService(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test_service.db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_servico_sincroniza_politicas_sem_o_mcp_importar_o_escudo(self):
        """AD-10: o boot do MCP sincroniza as políticas (B6) pelo StudioService, nunca pelo risk_shield direto."""
        from picorte.db.connection import Database
        from picorte.services.studio_service import StudioService

        db = Database(f"sqlite:///{self.db_path}")
        db.init_schema()
        self.assertEqual(db.fetch_one("SELECT COUNT(*) AS n FROM publisher_policies")["n"], 0)
        StudioService(db).risk_sync_publisher_policies()
        self.assertGreater(db.fetch_one("SELECT COUNT(*) AS n FROM publisher_policies")["n"], 0)

    def test_studio_service_and_mcp_parity(self):
        from picorte.db.connection import Database
        from picorte.mcp.server import PicorteMCPServer
        from picorte.services.studio_service import StudioService

        db = Database(f"sqlite:///{self.db_path}")
        db.init_schema()
        service = StudioService(db)
        mcp = PicorteMCPServer(service=service)

        # 1. Cadastrar fonte via ferramenta MCP
        created = mcp.call_tool(
            "picorte_cadastrar_fonte",
            {
                "name": "Gaules",
                "platform": "twitch",
                "channel_handle": "gaules",
                "permission_status": "liberada",
                "evidence_url": "https://twitch.tv/gaules",
                "default_game_slug": "cs2",
            },
        )
        self.assertEqual(created["permission_status"], "liberada")
        source_id = created["id"]

        # 2. Listar fontes pela camada de serviço e conferir paridade
        sources = service.list_sources()
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["id"], source_id)

        # 3. Enfileirar vídeo via MCP: fila única do Estúdio (B5, história 6.4)
        from unittest import mock
        with mock.patch("picorte.services.estudio_conexao.enfileirar_no_estudio",
                        return_value={"projetos": [{"id": "abc123def456", "status": "queued"}]}) as fila:
            video = mcp.call_tool("picorte_enfileirar_video", {"source_url": "https://twitch.tv/videos/999"})
        fila.assert_called_once_with(["https://twitch.tv/videos/999"], None)
        self.assertEqual(video["projetos"][0]["status"], "queued")

        # 4. Consultar status da fila e GPU via MCP
        status = mcp.call_tool("picorte_status_fila", {})
        self.assertIn("gpu_profile", status)
        self.assertEqual(status["total_sources"], 1)
        self.assertEqual(status["total_videos"], 0)  # o MCP não cria mais linha "queued" fantasma

        # 5. Validar protocolo JSON-RPC MCP initialize + tools/list + tools/call
        init_resp = mcp.handle_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        self.assertEqual(init_resp["result"]["serverInfo"]["name"], "picorte-mcp")

        tools_resp = mcp.handle_jsonrpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tool_names = {t["name"] for t in tools_resp["result"]["tools"]}
        self.assertTrue(
            {"picorte_status_fila", "picorte_cadastrar_fonte", "picorte_atualizar_permissao", "picorte_enfileirar_video", "picorte_listar_cortes"}.issubset(tool_names)
        )

    def test_skill_picorte_operador_exists_and_is_linked(self):
        src = Path("skills/picorte-operador/SKILL.md")
        link = Path(".claude/skills/picorte-operador/SKILL.md")
        self.assertTrue(src.is_file(), "skills/picorte-operador/SKILL.md ausente")
        self.assertTrue(link.exists(), ".claude/skills/picorte-operador/SKILL.md ausente")
        content = src.read_text(encoding="utf-8")
        self.assertIn("name: picorte-operador", content)
        self.assertIn("picorte_mcp", content)


if __name__ == "__main__":
    unittest.main()

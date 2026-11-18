"""Servidor MCP (Model Context Protocol via stdio JSON-RPC) do Picorte (AD-10 / Story 2.4).

Uso no Claude Code / Antigravity:
    python -m picorte.mcp.server
"""
from __future__ import annotations

import json
import sys
from typing import Any

from picorte.services.studio_service import StudioService


class PicorteMCPServer:
    """Expõe as operações de StudioService via ferramentas MCP padrão."""

    def __init__(self, service: StudioService | None = None) -> None:
        self.service = service or StudioService()

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "picorte_status_fila",
                "description": "Mostra o perfil de GPU/VRAM detectado, total de fontes, vídeos na fila e cortes gerados.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "picorte_listar_fontes",
                "description": "Lista todas as fontes cadastradas e seus status de permissão P1.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "picorte_cadastrar_fonte",
                "description": "Cadastra uma nova fonte (Twitch, Kick, YouTube ou local) com seu status de permissão P1.",
                "inputSchema": {
                    "type": "object",
                    "required": ["name", "platform", "channel_handle"],
                    "properties": {
                        "name": {"type": "string"},
                        "platform": {"type": "string"},
                        "channel_handle": {"type": "string"},
                        "permission_status": {"type": "string", "default": "desconhecida"},
                        "evidence_url": {"type": "string", "default": ""},
                        "default_game_slug": {"type": "string", "default": ""},
                    },
                },
            },
            {
                "name": "picorte_atualizar_permissao",
                "description": "Altera o status de permissão P1 de uma fonte (liberada, contrato, campanha_ativa, lista_negra, etc.).",
                "inputSchema": {
                    "type": "object",
                    "required": ["source_id", "permission_status"],
                    "properties": {
                        "source_id": {"type": "string"},
                        "permission_status": {"type": "string"},
                        "evidence_url": {"type": "string"},
                    },
                },
            },
            {
                "name": "picorte_enfileirar_video",
                "description": "Enfileira um VOD, live ou arquivo local no banco canônico do Picorte.",
                "inputSchema": {
                    "type": "object",
                    "required": ["source_url"],
                    "properties": {
                        "source_url": {"type": "string"},
                        "source_id": {"type": "string"},
                        "origin_type": {"type": "string", "default": "vod"},
                        "game_slug": {"type": "string", "default": ""},
                        "workdir_path": {"type": "string", "default": ""},
                    },
                },
            },
            {
                "name": "picorte_listar_cortes",
                "description": "Lista os cortes gerados com suas notas multimodais (chat, áudio, visão, texto), llm_mode_used e status de risco.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"video_id": {"type": "string"}},
                },
            },
        ]

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        args = arguments or {}
        if name == "picorte_status_fila":
            return self.service.status_fila()
        if name == "picorte_listar_fontes":
            return self.service.list_sources()
        if name == "picorte_cadastrar_fonte":
            return self.service.create_source(
                name=args["name"],
                platform=args["platform"],
                channel_handle=args["channel_handle"],
                permission_status=args.get("permission_status", "desconhecida"),
                evidence_url=args.get("evidence_url", ""),
                default_game_slug=args.get("default_game_slug", ""),
            )
        if name == "picorte_atualizar_permissao":
            return self.service.update_source_permission(
                args["source_id"],
                args["permission_status"],
                evidence_url=args.get("evidence_url"),
            )
        if name == "picorte_enfileirar_video":
            return self.service.enqueue_video(
                source_url=args["source_url"],
                source_id=args.get("source_id"),
                origin_type=args.get("origin_type", "vod"),
                game_slug=args.get("game_slug", ""),
                workdir_path=args.get("workdir_path", ""),
            )
        if name == "picorte_listar_cortes":
            return self.service.list_clips(video_id=args.get("video_id"))
        raise ValueError(f"Ferramenta MCP desconhecida: {name}")

    def handle_jsonrpc(self, request: dict[str, Any]) -> dict[str, Any] | None:
        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params") or {}

        if method == "notifications/initialized":
            return None
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "picorte-mcp", "version": "0.1.0"},
                },
            }
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": self.list_tools()}}
        if method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments") or {}
            try:
                output = self.call_tool(tool_name, tool_args)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(output, ensure_ascii=False, indent=2)}],
                        "isError": False,
                    },
                }
            except Exception as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Erro: {exc}"}],
                        "isError": True,
                    },
                }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Método não suportado: {method}"},
        }


def main() -> None:
    server = PicorteMCPServer()
    for line in sys.stdin:
        raw = line.strip()
        if not raw:
            continue
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            continue
        resp = server.handle_jsonrpc(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()

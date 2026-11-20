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

    def __init__(self, service: StudioService | None = None, *, db: Any = None) -> None:
        self.service = service or (StudioService(db=db) if db is not None else StudioService())

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
            {
                "name": "picorte_buscar_por_pergunta",
                "description": "Busca trechos específicos em um projeto/VOD usando pergunta livre em linguagem natural (Query-Driven Clipping).",
                "inputSchema": {
                    "type": "object",
                    "required": ["workdir", "query"],
                    "properties": {
                        "workdir": {"type": "string"},
                        "query": {"type": "string"},
                        "ai_mode": {"type": "string", "default": "claude"},
                        "min_score": {"type": "number", "default": 7.5},
                    },
                },
            },
            {
                "name": "picorte_atualizar_dossie",
                "description": "Cria ou atualiza um dossiê cultural de jogo em picorte/ai/game_dossiers/<slug>.json.",
                "inputSchema": {
                    "type": "object",
                    "required": ["slug", "display_name"],
                    "properties": {
                        "slug": {"type": "string"},
                        "display_name": {"type": "string"},
                        "aliases": {"type": "array", "items": {"type": "string"}, "default": []},
                        "cultural_callbacks": {"type": "array", "items": {"type": "string"}, "default": []},
                        "hot_details_to_watch": {"type": "array", "items": {"type": "string"}, "default": []},
                        "spoiler_watch_p1": {"type": "array", "items": {"type": "string"}, "default": []},
                        "dossiers_dir": {"type": "string"},
                    },
                },
            },
            {
                "name": "picorte_auditar_risco",
                "description": "Audita um corte nos portões P1 do Épico 4 (fonte, política do jogo, Selo Verde 15s, Copy Hygiene, Cadência, YPP/TikTok) retornando RiskVerdict por rede.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source_id": {"type": "string"},
                        "channel_handle": {"type": "string"},
                        "clip_id": {"type": "string"},
                        "game_slug": {"type": "string", "default": ""},
                        "title": {"type": "string", "default": ""},
                        "description": {"type": "string", "default": ""},
                        "source_credit": {"type": "string", "default": ""},
                    },
                },
            },
            {
                "name": "picorte_politicas_jogo",
                "description": "Consulta as políticas de copyright/spoiler/rádio de uma publisher/jogo no catálogo e banco.",
                "inputSchema": {
                    "type": "object",
                    "required": ["game_slug"],
                    "properties": {"game_slug": {"type": "string"}},
                },
            },
            {
                "name": "picorte_pausar_fonte",
                "description": "Aciona o Disjuntor Global P1 (transação única): trava a fonte (pausada_por_claim ou pausada_emergencia), registra claim_event, pausa publicações pendentes em todas as redes e bloqueia vídeos na fila.",
                "inputSchema": {
                    "type": "object",
                    "required": ["source_id"],
                    "properties": {
                        "source_id": {"type": "string"},
                        "claim_type": {
                            "type": "string",
                            "default": "copyright_claim",
                            "description": "Use 'manual_emergency' para pausa manual (status pausada_emergencia).",
                        },
                        "details": {"type": "string", "default": ""},
                        "reason": {"type": "string", "default": "", "description": "Motivo legível da pausa."},
                    },
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
        if name == "picorte_buscar_por_pergunta":
            import score_clips
            segments, used_mode = score_clips.select(
                args["workdir"],
                min_score=float(args.get("min_score", 7.5)),
                ai_mode=str(args.get("ai_mode", "claude")),
                query=str(args["query"]),
            )
            return {"mode": used_mode, "count": len(segments), "segments": segments}
        if name == "picorte_atualizar_dossie":
            from pathlib import Path
            from picorte.ai.dossier_updater import save_dossier
            out_path = save_dossier(
                args["slug"],
                display_name=args["display_name"],
                aliases=args.get("aliases") or [],
                cultural_callbacks=args.get("cultural_callbacks") or [],
                hot_details_to_watch=args.get("hot_details_to_watch") or [],
                spoiler_watch_p1=args.get("spoiler_watch_p1") or [],
                dossiers_dir=Path(args["dossiers_dir"]) if args.get("dossiers_dir") else None,
            )
            return {"slug": out_path.stem, "path": str(out_path)}
        if name == "picorte_auditar_risco":
            return self.service.risk_audit_clip(
                source_id=args.get("source_id"),
                channel_handle=args.get("channel_handle"),
                clip_id=args.get("clip_id"),
                game_slug=str(args.get("game_slug") or ""),
                title=str(args.get("title") or ""),
                description=str(args.get("description") or ""),
                source_credit=str(args.get("source_credit") or ""),
            )
        if name == "picorte_politicas_jogo":
            return self.service.risk_game_policy(str(args["game_slug"]))
        if name == "picorte_pausar_fonte":
            return self.service.risk_pause_source(
                str(args["source_id"]),
                claim_type=str(args.get("claim_type") or "copyright_claim"),
                details=str(args.get("details") or ""),
                reason=str(args.get("reason") or ""),
            )
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

"""Testes TDD: Cadastro Multi-Streamer, Thumbnail com Identidade do Autor,
Enquadramento 100% Preenchido (sem wide-menu blur) e Central de Publicação Assistida (PublishPayload)."""
from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

import cv2
import numpy as np
import pytest


def test_streamer_registry_resolves_initial_five_and_contact_email():
    from picorte.engine.publish_kit import load_streamer_registry, resolve_streamer

    reg = load_streamer_registry()
    assert reg["channel_brand"]["name"] == "Bomba Clips"
    assert reg["channel_brand"]["contact_email"] == "jffilho618@gmail.com"

    assert resolve_streamer(channel_name="alanzoka")["display_name"] == "ALANZOKA"
    assert resolve_streamer(channel_name="Davi jones")["display_name"] == "DAVY JONES"
    assert resolve_streamer(channel_name="GameplayRJ")["display_name"] == "DAVY JONES"
    assert resolve_streamer(channel_name="LOUD Coringa")["display_name"] == "CORINGA"
    assert resolve_streamer(channel_name="Bistecone")["display_name"] == "BISTECONE"
    assert resolve_streamer(channel_name="BRKsEDU")["display_name"] == "BRKSEDU"

    # Fallback limpo para streamer ainda não cadastrado
    other = resolve_streamer(channel_name="Gaules")
    assert other["display_name"] == "GAULES"
    assert other["slug"] == "gaules"


def test_build_publish_kit_generates_native_ptbr_copy_for_four_platforms_without_podcast():
    from picorte.engine.publish_kit import build_publish_kit

    seg = {
        "id": "001",
        "hook": "alanzoka-30-fps-gta6",
        "proposed_title": "Alanzoka manda a real sobre GTA 6 rodar a 30 FPS",
        "context_banner_2s": "OPINIÃO SINCERA SOBRE 30 FPS!",
        "pinned_comment_debate": "Você aceita GTA 6 a 30 FPS ou só joga a 60?",
        "archetype": "polemica_hottake",
        "tier": "ouro",
        "overall": 10.0,
        "start": 493.8,
        "end": 548.1,
    }
    source_meta = {
        "channel": "alanzoka",
        "title": "BEM VINDO A LEONIDA! - GRAND THEFT AUTO 6 - Parte 1",
        "detected_game": "gta6",
    }

    kit = build_publish_kit(
        seg,
        source_meta=source_meta,
        mp4_path="C:/tmp/001.mp4",
        thumb_path="C:/tmp/001_thumb.png",
    )

    assert kit["streamer"]["display_name"] == "ALANZOKA"
    assert kit["game"] == "GTA 6"
    plats = kit["platforms"]
    assert set(plats.keys()) == {"youtube_shorts", "tiktok", "instagram_reels", "facebook_reels"}

    yt = plats["youtube_shorts"]
    assert "alanzoka" in yt["description"].lower()
    assert "jffilho618@gmail.com" in yt["description"]
    assert "twitch.tv/alanzoka" in yt["description"].lower()
    assert "#podcast" not in yt["description"].lower()
    assert "#gta6" in yt["description"].lower()
    assert yt["pinned_comment"] == "Você aceita GTA 6 a 30 FPS ou só joga a 60?"
    assert len(yt["title"]) <= 95

    tt = plats["tiktok"]
    assert "@alanzoka" in tt["description"].lower()
    assert "#podcast" not in tt["description"].lower()
    assert len(tt["description"]) < len(yt["description"])

    ig = plats["instagram_reels"]
    assert "@alanzoka" in ig["description"].lower()
    assert "Você aceita GTA 6 a 30 FPS" in ig["description"]


def test_thumbnail_9_16_keeps_provided_facecam_stamps_author_and_never_uses_wide_menu_blur(tmp_path: Path):
    from picorte.engine.thumbnail_factory import generate_thumbnail

    # Frame sintético com "menu" cheio de texto nos dois lados (para provar que NÃO ativa wide_menu blur!)
    # e um quadrado colorido no canto superior direito simulando facecam sem rosto detectável por Haar
    frame = np.full((1080, 1920, 3), (35, 110, 45), dtype=np.uint8)
    for row_y in range(180, 920, 52):
        cv2.putText(frame, f"STATUS {row_y}", (90, row_y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (240, 240, 240), 2)
        cv2.putText(frame, f"ATRIBUTO {row_y}", (1100, row_y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (240, 240, 240), 2)
    # Facecam azul brilhante no canto superior esquerdo (onde Haar não encontra rosto)
    frame[20:320, 20:420] = (210, 140, 50)

    out_path = tmp_path / "alanzoka_thumb.png"
    res = generate_thumbnail(
        frame,
        out_path,
        title_text="30 FPS TRAVADO?",
        aspect="9:16",
        vision_preset="low",
        facecam_box=(20, 20, 400, 300),
        streamer_name="ALANZOKA",
        streamer_accent_hex="#E11D2E",
        cutout_runner=lambda img, _m: np.zeros(img.shape[:2], dtype=np.uint8),
    )

    assert res["width"] == 1080
    assert res["height"] == 1920
    assert res["facecam_detected"] is True
    assert res["streamer_name"] == "ALANZOKA"

    img = cv2.imread(str(out_path))
    assert img is not None and img.shape == (1920, 1080, 3)

    # Topo (facecam) herdou a cor azulada da facecam fornecida (canal B > G e B > R)
    top_patch = img[120:260, 300:780]
    assert float(top_patch[:, :, 0].mean()) > float(top_patch[:, :, 2].mean()) + 30.0

    # Base extrema (y=1760..1880) NÃO pode estar escura/borrada de wide_menu: deve manter a cor verde do gameplay!
    bottom_edge = img[1760:1880, 200:880]
    assert float(bottom_edge[:, :, 1].mean()) > 85.0
    assert float(bottom_edge[:, :, 1].mean()) > float(bottom_edge[:, :, 2].mean()) + 25.0


def test_select_best_thumbnail_frame_avoids_blurred_menu_or_flat_sky_when_crisp_gameplay_exists(tmp_path: Path):
    from picorte.engine.thumbnail_factory import _select_best_thumbnail_frame

    # Monta vídeo sintético de 3s: 0-2s céu liso/blur; 2-3s cena nítida de gameplay
    vid = tmp_path / "sample.mp4"
    writer = cv2.VideoWriter(str(vid), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (640, 360))
    flat_frame = np.full((360, 640, 3), (180, 120, 60), dtype=np.uint8)
    crisp_frame = np.full((360, 640, 3), (40, 90, 40), dtype=np.uint8)
    for x in range(80, 520, 40):
        cv2.rectangle(crisp_frame, (x, 60), (x + 25, 300), (230, 220, 80), 2)
    for idx in range(30):
        writer.write(flat_frame if idx < 20 else crisp_frame)
    writer.release()

    chosen, _ = _select_best_thumbnail_frame(
        vid, clip_start_s=0.0, clip_end_s=3.0, facecam_box=(480, 10, 140, 100)
    )
    gray_center = cv2.cvtColor(chosen[60:300, 120:440], cv2.COLOR_BGR2GRAY)
    assert float(cv2.Laplacian(gray_center, cv2.CV_64F).var()) > 30.0


def test_export_daily_bundle_creates_scheduled_pack_with_single_thumb_and_copy_file(tmp_path: Path):
    from picorte.db.connection import Database
    from picorte.db.repositories import PicorteRepositories
    from picorte.engine.publish_kit import export_daily_bundle

    db = Database(f"sqlite:///{(tmp_path / 'bundle.db').as_posix()}")
    db.init_schema()
    src = PicorteRepositories(db).sources.create_source(
        name="ALANZOKA", platform="twitch", channel_handle="@alanzoka", permission_status="liberada")

    pdir = tmp_path / "proj1"
    clips_dir = pdir / "clips"
    clips_dir.mkdir(parents=True)
    (pdir / "project.json").write_text(
        json.dumps({"id": "proj1", "source_meta": {"channel": "alanzoka", "title": "GTA 6 Parte 1", "detected_game": "gta6"},
                    "source_gate": {"source_id": src["id"]}}),
        encoding="utf-8",
    )

    stems = ["001-clip-um", "002-clip-dois", "003-clip-tres", "004-clip-quatro"]
    for idx, stem in enumerate(stems, 1):
        (clips_dir / f"{stem}.mp4").write_bytes(b"fake-mp4-" + str(idx).encode())
        (clips_dir / f"{stem}.png").write_bytes(b"raw-poster-should-not-duplicate")
        (clips_dir / f"{stem}_thumb.png").write_bytes(b"official-thumb-" + str(idx).encode())
        (clips_dir / f"{stem}.meta.json").write_text(
            json.dumps({
                "proposed_title": f"Corte {idx} do Alanzoka no GTA 6",
                "pinned_comment_debate": f"Pergunta {idx}?",
                "score": 10.0 - idx * 0.1,
                "risk_status": "pass",
            }),
            encoding="utf-8",
        )

    bundle_root = tmp_path / "prontos_para_postar"
    result = export_daily_bundle(pdir, out_root=bundle_root, per_day=3, db=db,
                                 cadence_state_path=tmp_path / "cadence.json")

    assert result["count"] == 4
    out_dir = Path(result["bundle_dir"])
    assert out_dir.is_dir()

    mp4s = sorted(p.name for p in out_dir.glob("*.mp4"))
    thumbs = sorted(p.name for p in out_dir.glob("*_thumb.png"))
    txts = sorted(p.name for p in out_dir.glob("*_COPIAR.txt"))
    assert len(mp4s) == 4
    assert len(thumbs) == 4
    assert len(txts) == 4
    # Nenhum poster duplicado fora do _thumb.png
    assert len(list(out_dir.glob("*.png"))) == 4

    # Agenda segura 3/dia: 3 no Dia 1 (12h, 18h, 21h) e 1 no Dia 2 (12h)
    assert mp4s[0].startswith("01_D1_12h_")
    assert mp4s[1].startswith("02_D1_18h_")
    assert mp4s[2].startswith("03_D1_21h_")
    assert mp4s[3].startswith("04_D2_12h_")

    copy_text = (out_dir / txts[0]).read_text(encoding="utf-8")
    assert "YOUTUBE SHORTS" in copy_text
    assert "TIKTOK" in copy_text
    assert "INSTAGRAM REELS" in copy_text
    assert "jffilho618@gmail.com" in copy_text


def test_dashboard_publish_kit_mark_posted_and_export_bundle_endpoints(tmp_path: Path, monkeypatch):
    import dashboard
    from picorte.db.connection import Database
    from picorte.services.studio_service import StudioService

    db_path = tmp_path / "picorte_test.db"
    test_db = Database(f"sqlite:///{db_path.as_posix()}")
    test_db.init_schema()
    monkeypatch.setattr("picorte.db.connection.get_default_db", lambda: test_db)
    monkeypatch.setattr("picorte.services.studio_service.get_default_db", lambda: test_db)

    from picorte.db.repositories import PicorteRepositories

    src = PicorteRepositories(test_db).sources.create_source(
        name="ALANZOKA", platform="twitch", channel_handle="@alanzoka", permission_status="liberada")
    monkeypatch.setattr("picorte.risk_shield.cadence_guard.DEFAULT_CADENCE_STATE_PATH", tmp_path / "cadence.json")

    root = tmp_path / "projects"
    pdir = root / "abc123456789"
    clips_dir = pdir / "clips"
    clips_dir.mkdir(parents=True)
    (pdir / "project.json").write_text(
        json.dumps({
            "id": "abc123456789",
            "created": "2026-11-19T16:00:00Z",
            "source": "https://youtube.com/watch?v=test",
            "status": "complete",
            "stage": "complete",
            "options": {"aspect": "9:16", "layout": "games"},
            "source_meta": {"channel": "alanzoka", "title": "GTA 6 Parte 1", "detected_game": "gta6"},
            "source_gate": {"source_id": src["id"]},
        }),
        encoding="utf-8",
    )
    stem = "001-alanzoka-30fps"
    (clips_dir / f"{stem}.mp4").write_bytes(b"mp4data")
    (clips_dir / f"{stem}_thumb.png").write_bytes(b"thumbdata")
    (clips_dir / f"{stem}.meta.json").write_text(
        json.dumps({
            "proposed_title": "Alanzoka sobre 30 FPS no GTA 6",
            "pinned_comment_debate": "30 ou 60 FPS?",
            "risk_status": "pass",
        }),
        encoding="utf-8",
    )

    server = dashboard.make_server(root, 0)
    port = server.server_port
    token = server.app.token
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        base = f"http://127.0.0.1:{port}"
        with urllib.request.urlopen(f"{base}/api/projects/abc123456789") as r:
            detail = json.loads(r.read().decode("utf-8"))
        assert stem in detail["publish_kits"]
        assert detail["publish_kits"][stem]["streamer"]["display_name"] == "ALANZOKA"

        # Marca como postado no YouTube Shorts
        req = urllib.request.Request(
            f"{base}/api/projects/abc123456789/mark-posted",
            data=json.dumps({
                "clip_stem": stem,
                "platform": "youtube_shorts",
                "external_url": "https://youtube.com/shorts/xyz123",
            }).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Chopify-Token": token},
            method="POST",
        )
        with urllib.request.urlopen(req) as r:
            marked = json.loads(r.read().decode("utf-8"))
        assert marked["ok"] is True
        assert marked["publication"]["platform"] == "youtube_shorts"
        assert marked["publication"]["publish_mode"] == "assisted_manual"
        assert marked["publication"]["external_url"] == "https://youtube.com/shorts/xyz123"

        # Recarrega projeto e confirma que publications vem preenchido
        with urllib.request.urlopen(f"{base}/api/projects/abc123456789") as r:
            detail2 = json.loads(r.read().decode("utf-8"))
        assert "youtube_shorts" in detail2["publications"][stem]

        # Exporta Pacote do Dia
        req2 = urllib.request.Request(
            f"{base}/api/projects/abc123456789/export-bundle",
            data=json.dumps({"out_root": str(tmp_path / "bundles"), "open_folder": False}).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Chopify-Token": token},
            method="POST",
        )
        with urllib.request.urlopen(req2) as r:
            bundle = json.loads(r.read().decode("utf-8"))
        assert bundle["ok"] is True
        assert bundle["count"] == 1
        assert Path(bundle["bundle_dir"]).is_dir()
    finally:
        server.shutdown()
        server.server_close()

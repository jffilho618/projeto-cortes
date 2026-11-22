import json
import time
from datetime import datetime, timedelta, timezone

import httpx

from picorte.capacidades import sondas as S


class _Resp:
    def __init__(self, dados, status=200):
        self._dados, self.status_code = dados, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("x", request=None, response=None)

    def json(self):
        return self._dados


def test_ollama_lista_modelos():
    r = S.sonda_ollama("http://h:11434", get=lambda url, timeout: _Resp(
        {"models": [{"name": "qwen3.5:9b"}, {"name": "nomic-embed-text"}]}))
    assert r.ok and r.dados["modelos"] == ["nomic-embed-text", "qwen3.5:9b"]


def test_ollama_fora_do_ar():
    def falha(url, timeout):
        raise httpx.ConnectError("recusado")

    r = S.sonda_ollama("http://h:11434", get=falha)
    assert r.ok is False and "h:11434" in r.detalhe


def test_ollama_host_sem_esquema_ganha_http(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "0.0.0.0:11434")
    vistos = []
    S.sonda_ollama(get=lambda url, timeout: vistos.append(url) or _Resp({"models": []}))
    assert vistos == ["http://0.0.0.0:11434/api/tags"]


def test_binario_presente_e_ausente():
    assert S.sonda_binario("node", resolver=lambda n: "/usr/bin/node").ok
    assert S.sonda_binario("node", resolver=lambda n: None).ok is False


def test_gpu_com_e_sem_placa():
    assert S.sonda_gpu(probe=lambda: (8188, "RTX 4060 Ti")).dados == {
        "gpu_name": "RTX 4060 Ti", "vram_mib": 8188}
    assert S.sonda_gpu(probe=lambda: (0, "")).ok is False


def test_disco_informa_espaco_livre(tmp_path):
    r = S.sonda_disco(tmp_path, minimo_gib=0.0)
    assert r.ok and r.dados["livre_gib"] > 0


def test_agy_ve_429_recente_no_engine_health(tmp_path):
    proj = tmp_path / "abcdef123456"
    proj.mkdir()
    quando = datetime.now(timezone.utc) - timedelta(hours=2)
    (proj / "engine_health.json").write_text(json.dumps({"editor": {
        "status": "failed", "detail": "agy: 429 RESOURCE_EXHAUSTED",
        "at": quando.isoformat(timespec="seconds")}}), encoding="utf-8")
    r = S.sonda_agy(tmp_path, resolver=lambda n: "C:/agy.cmd" if n == "agy" else None)
    assert r.ok is False
    assert r.dados["presente"] is True and r.dados["ultima_falha"] == quando.isoformat(timespec="seconds")


def test_agy_429_antigo_nao_conta(tmp_path):
    proj = tmp_path / "abcdef123456"
    proj.mkdir()
    velho = datetime.now(timezone.utc) - timedelta(days=3)
    (proj / "engine_health.json").write_text(json.dumps({"editor": {
        "status": "failed", "detail": "429", "at": velho.isoformat()}}), encoding="utf-8")
    r = S.sonda_agy(tmp_path, resolver=lambda n: "agy")
    assert r.ok is True and r.dados["ultima_falha"] is None


def test_agy_429_no_erro_do_projeto(tmp_path):
    proj = tmp_path / "abcdef123456"
    proj.mkdir()
    (proj / "project.json").write_text(json.dumps({
        "error": "Editor-Chefe falhou: gemini 429", "updated": time.time() - 60}), encoding="utf-8")
    r = S.sonda_agy(tmp_path, resolver=lambda n: "agy")
    assert r.ok is False and r.dados["ultima_falha"]


def test_sondas_padrao_tem_todos_os_nomes(tmp_path):
    cache = S.sondas_padrao(tmp_path)
    assert set(cache._sondas) == set(S.NOMES_SONDAS)


def test_agy_falha_sem_429_no_texto_tambem_conta(tmp_path):
    # formato real (bd4a2463b200): o detail é cortado em 400 caracteres e o 429 fica de fora
    proj = tmp_path / "bd4a2463b200"
    proj.mkdir()
    quando = datetime.now(timezone.utc) - timedelta(hours=1)
    (proj / "engine_health.json").write_text(json.dumps({"editor": {
        "status": "failed",
        "detail": "lote 1/2 falhou 2x: CalledProcessError: Command '['C:\\Users\\x\\.gemini\\bin\\agy.exe', '-p'",
        "at": quando.isoformat(timespec="seconds")}}), encoding="utf-8")
    r = S.sonda_agy(tmp_path, resolver=lambda n: "agy")
    assert r.ok is False and r.dados["ultima_falha"] == quando.isoformat(timespec="seconds")


def test_falha_do_ollama_nao_conta_como_falha_do_gemini(tmp_path):
    proj = tmp_path / "ae5f08feaaa0"
    proj.mkdir()
    (proj / "engine_health.json").write_text(json.dumps({"editor": {
        "status": "failed", "detail": "lote 1/2 falhou 2x: TimeoutError: timed out",
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}}), encoding="utf-8")
    (proj / "project.json").write_text(json.dumps({
        "error": "[Editor-Chefe] ollama indisponível (TimeoutError)", "updated": time.time()}),
        encoding="utf-8")
    assert S.sonda_agy(tmp_path, resolver=lambda n: "agy").ok is True

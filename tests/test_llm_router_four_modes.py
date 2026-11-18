"""Teste obrigatório R-07 (AD-4): Roteador de IA de 4 Modos (Ollama / Claude / Gemini / Dupla) e Seletor na UI."""
import json
import unittest


class TestLLMRouterFourModes(unittest.TestCase):
    def _sample_candidates(self):
        return [
            {"start": 10.0, "end": 42.0, "overall": 8.2, "text": "Cara olha esse bug do carro voando no GTA 6!"},
            {"start": 60.0, "end": 95.0, "overall": 7.9, "text": "Meu Deus, eu não acredito que ele acertou aquele tiro."},
            {"start": 120.0, "end": 150.0, "overall": 7.5, "text": "Estou arrumando o inventário aqui rapidinho."},
        ]

    def test_single_modes_ollama_claude_gemini(self):
        from picorte.ai.llm_router import LLMRouter

        calls = []

        def fake_runner(provider: str, model: str | None, system_prompt: str, user_prompt: str) -> str:
            calls.append((provider, model))
            return json.dumps([
                {
                    "index": 0,
                    "adjustment": 0.8,
                    "reason": f"Aprovado via {provider}",
                    "proposed_title": "Bug absurdo do carro voando no GTA 6",
                    "context_banner_2s": "Tentando fugir da polícia a 200km/h",
                    "thumbnail_words": "VOOU NO GTA",
                    "pinned_comment_debate": "Foi bug ou física quebrada?",
                }
            ])

        router = LLMRouter(provider_runner=fake_runner)
        for mode in ("ollama", "claude", "gemini"):
            res = router.rerank_candidates(self._sample_candidates(), ai_mode=mode)
            self.assertEqual(res["llm_mode_used"], mode)
            self.assertEqual(res["candidates"][0]["llm_mode_used"], mode)
            self.assertAlmostEqual(res["candidates"][0]["overall"], 9.0)
            self.assertEqual(res["candidates"][0]["proposed_title"], "Bug absurdo do carro voando no GTA 6")
            self.assertEqual(res["candidates"][0]["context_banner_2s"], "Tentando fugir da polícia a 200km/h")
            self.assertEqual(res["candidates"][0]["pinned_comment_debate"], "Foi bug ou física quebrada?")

        self.assertEqual([c[0] for c in calls], ["ollama", "claude", "gemini"])

    def test_dupla_mode_runs_filter_then_companion(self):
        from picorte.ai.llm_router import LLMRouter

        calls = []

        def fake_runner(provider: str, model: str | None, system_prompt: str, user_prompt: str) -> str:
            calls.append((provider, user_prompt))
            if provider == "ollama":
                # Filtro mantém os 2 primeiros e penaliza o 3º (inventário)
                return json.dumps([
                    {"index": 0, "adjustment": 0.4, "reason": "Reação forte"},
                    {"index": 1, "adjustment": 0.3, "reason": "Tiro impossível"},
                    {"index": 2, "adjustment": -0.9, "reason": "Sem graça"},
                ])
            # Acompanhante (claude) recebe os filtrados e lapida o campeão
            return json.dumps([
                {
                    "index": 0,
                    "adjustment": 0.5,
                    "reason": "Gancho imediato de bug",
                    "proposed_title": "CARRO VOOU DO NADA NO GTA 6!",
                    "context_banner_2s": "Fuga impossível da polícia",
                    "thumbnail_words": "BUG INSANO!",
                    "pinned_comment_debate": "Você já viu isso acontecer?",
                }
            ])

        router = LLMRouter(provider_runner=fake_runner)
        res = router.rerank_candidates(
            self._sample_candidates(),
            ai_mode="dupla",
            filter_provider="ollama",
            companion_provider="claude",
        )
        self.assertEqual([c[0] for c in calls], ["ollama", "claude"])
        self.assertIn("Triagem", calls[1][1])
        self.assertEqual(res["llm_mode_used"], "dupla:ollama->claude")
        self.assertEqual(res["candidates"][0]["llm_mode_used"], "dupla:ollama->claude")
        self.assertEqual(res["candidates"][0]["proposed_title"], "CARRO VOOU DO NADA NO GTA 6!")
        # O candidato 0 recebeu +0.4 no filtro (8.6) e +0.5 no acompanhante -> 9.1
        self.assertAlmostEqual(res["candidates"][0]["overall"], 9.1)

    def test_projects_and_ui_expose_four_ai_modes(self):
        import projects
        from pathlib import Path

        opts = projects.validate_options({
            "ai_mode": "dupla",
            "ai_filter": "ollama",
            "ai_companion": "gemini",
        })
        self.assertEqual(opts["ai_mode"], "dupla")
        self.assertEqual(opts["ai_filter"], "ollama")
        self.assertEqual(opts["ai_companion"], "gemini")

        with self.assertRaises(ValueError):
            projects.validate_options({"ai_mode": "invalid_provider"})

        html = Path("assets/studio/index.html").read_text(encoding="utf-8")
        self.assertIn('name="ai_mode"', html)
        self.assertIn('value="dupla"', html)


if __name__ == "__main__":
    unittest.main()

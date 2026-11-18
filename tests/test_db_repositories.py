"""Testes TDD para o Schema Canônico das 10 Tabelas e Repositórios (Story 2.1 / AD-2)."""
import tempfile
import unittest
from pathlib import Path


class TestDbRepositories(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test_picorte.db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_all_10_canonical_tables_exist_without_workspace_id(self):
        from picorte.db.connection import Database

        db = Database(f"sqlite:///{self.db_path}")
        db.init_schema()
        tables = db.list_tables()
        expected = {
            "sources",
            "publisher_policies",
            "campaigns",
            "videos",
            "clips",
            "publications",
            "metrics_snapshots",
            "claims_events",
            "bandit_state",
            "dataset_samples",
        }
        self.assertTrue(expected.issubset(set(tables)), f"Tabelas faltando: {expected - set(tables)}")
        for tbl in expected:
            cols = db.list_columns(tbl)
            self.assertNotIn("workspace_id", cols, f"Tabela {tbl} não deve ter workspace_id (AD-2)")

    def test_repositories_crud_and_atomic_lifecycle(self):
        from picorte.db.connection import Database
        from picorte.db.repositories import PicorteRepositories

        db = Database(f"sqlite:///{self.db_path}")
        db.init_schema()
        repos = PicorteRepositories(db)

        # 1. Publisher Policy
        pol = repos.policies.upsert_policy(
            publisher="Rockstar Games",
            game_slug="gta-6",
            spoiler_window_days=14,
            forbidden_content_rules=["ending_cutscene", "leaks"],
            has_licensed_radio_music=True,
            violence_check_strict=True,
        )
        self.assertEqual(pol["game_slug"], "gta-6")
        self.assertTrue(pol["has_licensed_radio_music"])

        # 2. Source (starts as desconhecida by default, then updated)
        src = repos.sources.create_source(
            name="Alanzoka",
            platform="twitch",
            channel_handle="alanzoka",
        )
        self.assertEqual(src["permission_status"], "desconhecida")
        src = repos.sources.update_permission(src["id"], "liberada", evidence_url="https://twitch.tv/alanzoka")
        self.assertEqual(src["permission_status"], "liberada")

        # 3. Campaign
        camp = repos.campaigns.create_campaign(
            source_id=src["id"],
            game_slug="gta-6",
            cpm_brl=12.50,
            required_tags=["#gta6", "@alanzoka"],
        )
        self.assertEqual(float(camp["cpm_brl"]), 12.50)

        # 4. Video + Clip (saving llm_mode_used and parent_long_clip_id)
        vid = repos.videos.create_video(
            source_id=src["id"],
            origin_type="vod",
            source_url="https://twitch.tv/videos/12345",
            game_slug="gta-6",
            duration_seconds=3600.0,
            workdir_path="/tmp/work1",
        )
        long_clip = repos.clips.create_clip(
            video_id=vid["id"],
            format_type="long_16_9",
            start_sec=100.0,
            end_sec=340.0,
            score_chat=8.5,
            score_audio=8.0,
            score_visual=9.0,
            score_text=8.8,
            score_overall=8.7,
            ypp_transform_score=85,
            llm_mode_used="dupla:ollama->claude",
            proposed_title="GTA 6 Missão Insana",
        )
        short_clip = repos.clips.create_clip(
            video_id=vid["id"],
            parent_long_clip_id=long_clip["id"],
            format_type="short_9_16",
            start_sec=120.0,
            end_sec=165.0,
            score_chat=9.2,
            score_audio=8.9,
            score_visual=9.4,
            score_text=9.0,
            score_overall=9.1,
            ypp_transform_score=90,
            llm_mode_used="dupla:ollama->claude",
            proposed_title="Olha o que aconteceu no GTA 6 #shorts",
            context_banner_2s="3ª tentativa de passar da polícia",
            pinned_comment_debate="Foi bug ou jogada de mestre no 0:12?",
        )
        self.assertEqual(short_clip["parent_long_clip_id"], long_clip["id"])
        self.assertEqual(short_clip["llm_mode_used"], "dupla:ollama->claude")

        # 5. Publication + Metrics Snapshot + Bandit State
        pub = repos.publications.create_publication(
            clip_id=short_clip["id"],
            platform="youtube_shorts",
            publish_mode="assisted_manual",
            status="fila",
        )
        snap = repos.metrics.record_snapshot(
            publication_id=pub["id"],
            window_label="24h",
            views=45000,
            likes=3800,
            comments=210,
            shares=400,
            avg_view_pct=0.82,
            stayed_to_watch_3s_pct=0.76,
            computed_reward=3.4,
        )
        self.assertEqual(snap["views"], 45000)

        b_state = repos.bandit.upsert_factor("game:gta-6", mu=1.45, sigma_sq=0.25, observations_count=5)
        self.assertAlmostEqual(b_state["mu"], 1.45)


if __name__ == "__main__":
    unittest.main()

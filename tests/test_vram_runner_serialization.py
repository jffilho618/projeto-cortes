"""Teste obrigatório R-06 (AD-3 / AD-11): Serialização de VRAM via filelock e Modo Madrugada."""
from concurrent.futures import ThreadPoolExecutor
import tempfile
import time
import unittest
from pathlib import Path


class TestVRAMRunnerSerialization(unittest.TestCase):
    def test_concurrent_gpu_stages_never_overlap_and_run_cleanup(self):
        from picorte.engine.vram_runner import VRAMRunner

        with tempfile.TemporaryDirectory() as tmp:
            lock_file = Path(tmp) / "gpu.lock"
            events: list[str] = []
            runner = VRAMRunner(
                lock_path=lock_file,
                cleanup_hook=lambda stage: events.append(f"cleanup:{stage}"),
            )

            def stage_work(name: str):
                def _fn():
                    events.append(f"start:{name}")
                    time.sleep(0.06)
                    events.append(f"end:{name}")
                    return f"done:{name}"

                return runner.run_stage(name, _fn)

            with ThreadPoolExecutor(max_workers=2) as pool:
                f1 = pool.submit(stage_work, "whisper")
                time.sleep(0.01)
                f2 = pool.submit(stage_work, "vision")
                self.assertEqual(f1.result(), "done:whisper")
                self.assertEqual(f2.result(), "done:vision")

            # Verifica que o segundo estágio só iniciou DEPOIS do fim e do cleanup do primeiro
            self.assertEqual(
                events,
                [
                    "start:whisper",
                    "end:whisper",
                    "cleanup:whisper",
                    "start:vision",
                    "end:vision",
                    "cleanup:vision",
                ],
            )

    def test_night_mode_window_evaluation(self):
        from picorte.engine.vram_runner import is_in_night_window

        # Janela padrão: 01:00 às 07:00
        self.assertTrue(is_in_night_window(hour=3, start_hour=1, end_hour=7))
        self.assertFalse(is_in_night_window(hour=14, start_hour=1, end_hour=7))
        # Janela cruzando meia-noite: 23:00 às 06:00
        self.assertTrue(is_in_night_window(hour=23, start_hour=23, end_hour=6))
        self.assertTrue(is_in_night_window(hour=2, start_hour=23, end_hour=6))
        self.assertFalse(is_in_night_window(hour=12, start_hour=23, end_hour=6))


if __name__ == "__main__":
    unittest.main()

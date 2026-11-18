"""Testes TDD para detecção automática de perfil de GPU/VRAM (Story 1.1 / AD-3)."""
import unittest
from pathlib import Path


class TestGpuProfile(unittest.TestCase):
    def test_notebook_4gb_profile_uses_small_int8(self):
        from picorte.config import detect_gpu_profile

        profile = detect_gpu_profile(vram_mib=4096, gpu_name="NVIDIA GeForce GTX 1650")
        self.assertEqual(profile["device"], "cuda")
        self.assertEqual(profile["tier"], "notebook_4gb")
        self.assertEqual(profile["whisper_model"], "small")
        self.assertEqual(profile["compute_type"], "int8")
        self.assertEqual(profile["vram_mib"], 4096)

    def test_desktop_8gb_plus_profile_uses_large_v3_turbo(self):
        from picorte.config import detect_gpu_profile

        profile = detect_gpu_profile(vram_mib=8192, gpu_name="NVIDIA GeForce RTX 4060 Ti")
        self.assertEqual(profile["device"], "cuda")
        self.assertEqual(profile["tier"], "desktop_8gb_plus")
        self.assertEqual(profile["whisper_model"], "large-v3-turbo")
        self.assertEqual(profile["compute_type"], "int8_float16")

        profile_12gb = detect_gpu_profile(vram_mib=12288, gpu_name="NVIDIA GeForce RTX 4070 Ti")
        self.assertEqual(profile_12gb["tier"], "desktop_8gb_plus")
        self.assertEqual(profile_12gb["whisper_model"], "large-v3-turbo")

    def test_cpu_fallback_when_no_gpu(self):
        from picorte.config import detect_gpu_profile

        profile = detect_gpu_profile(vram_mib=0, gpu_name="")
        self.assertEqual(profile["device"], "cpu")
        self.assertEqual(profile["tier"], "cpu_only")
        self.assertEqual(profile["whisper_model"], "base")
        self.assertEqual(profile["compute_type"], "int8")

    def test_ensure_cuda_libraries_is_idempotent(self):
        from picorte.engine.cuda import ensure_cuda_libraries

        dirs = ensure_cuda_libraries()
        self.assertIsInstance(dirs, list)

    def test_cross_platform_venv_bin_dir_windows_and_linux(self):
        from picorte.config import get_venv_bin_dir

        win_dir = get_venv_bin_dir(Path("/repo"), platform_name="win32")
        linux_dir = get_venv_bin_dir(Path("/repo"), platform_name="linux")
        self.assertEqual(win_dir.name, "Scripts")
        self.assertEqual(linux_dir.name, "bin")

    def test_dashboard_static_assets_exist(self):
        import dashboard

        for fname in ("index.html", "app.js", "style.css"):
            p = dashboard.STATIC / fname
            self.assertTrue(p.is_file(), f"Arquivo estático ausente: {p}")


if __name__ == "__main__":
    unittest.main()

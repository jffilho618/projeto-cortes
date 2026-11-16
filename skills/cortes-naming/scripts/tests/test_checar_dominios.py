import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from checar_dominios import normalizar, ROTULO_VALIDO


class TestNormalizar(unittest.TestCase):
    def test_acentos_e_espacos(self):
        self.assertEqual(normalizar("Ação Rápida"), "acaorapida")

    def test_mantem_hifen_e_digitos(self):
        self.assertEqual(normalizar("Corte-360"), "corte-360")

    def test_rotulo_invalido(self):
        self.assertIsNone(ROTULO_VALIDO.match("-abc"))
        self.assertIsNotNone(ROTULO_VALIDO.match("abc-1"))


if __name__ == "__main__":
    unittest.main()

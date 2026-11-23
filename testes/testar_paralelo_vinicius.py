"""Testes da parte do Vinicius contra a função comum sequencial."""
import unittest

from comum.grade import criar_grade
from comum.modelo import calcular_intervalo
from comum.probabilidade import calcular_intervalo_probabilistico
from paralelo_threads import rodar_simulacao as rodar_threads
from paralelo_processos import rodar_simulacao as rodar_processos


class TestesParalelo(unittest.TestCase):
    def setUp(self):
        self.linhas, self.colunas, self.geracoes = 12, 13, 6
        self.grade = criar_grade(self.linhas, self.colunas, 0.20, 123)
        self.historico, self.final = self._sequencial()

    def _sequencial(self):
        atual, proxima = bytearray(self.grade), bytearray(len(self.grade))
        historico = []
        for _ in range(self.geracoes):
            historico.append(calcular_intervalo(atual, proxima, self.linhas,
                self.colunas, 0, self.linhas, 2))
            atual, proxima = proxima, atual
        return historico, atual

    def test_threads_correspondem_ao_sequencial(self):
        for n in (1, 2, 4, 7):
            with self.subTest(trabalhadores=n):
                h, final = rodar_threads(self.grade, self.linhas, self.colunas,
                    self.geracoes, 2, n, False)
                self.assertEqual((h, final), (self.historico, self.final))
    def test_processos_correspondem_ao_sequencial(self):
        for n in (1, 2, 4, 7):
            with self.subTest(trabalhadores=n):
                h, final = rodar_processos(self.grade, self.linhas, self.colunas,
                    self.geracoes, 2, n, False)
                self.assertEqual((h, final), (self.historico, self.final))

    def test_probabilidade_independe_da_particao(self):
        saidas = []
        for n in (1, 2, 4, 7):
            h, final = rodar_threads(self.grade, self.linhas, self.colunas,
                self.geracoes, 2, n, False, probabilidade=0.45, semente=777)
            saidas.append((h, final))
        self.assertTrue(all(saida == saidas[0] for saida in saidas))
        h, final = rodar_processos(self.grade, self.linhas, self.colunas,
            self.geracoes, 2, 4, False, probabilidade=0.45, semente=777)
        self.assertEqual((h, final), saidas[0])

    def test_probabilidade_reproduzivel_no_calculo_base(self):
        inicial = bytearray(self.grade)
        a = bytearray(self.linhas * self.colunas)
        c = bytearray(self.linhas * self.colunas)
        ca = calcular_intervalo_probabilistico(inicial, a, self.linhas,
            self.colunas, 0, self.linhas, 2, 0.45, 777, 3)
        cb = calcular_intervalo_probabilistico(inicial, c, self.linhas,
            self.colunas, 0, 5, 2, 0.45, 777, 3)
        cc = calcular_intervalo_probabilistico(inicial, c, self.linhas,
            self.colunas, 5, self.linhas, 2, 0.45, 777, 3)
        self.assertEqual(ca, tuple(x + y for x, y in zip(cb, cc)))
        self.assertEqual(a, c)


if __name__ == "__main__":
    unittest.main()

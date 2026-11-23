"""Testes das melhorias de Willian: bots e estatísticas da propagação.

O teste mais importante é o primeiro: sem bots, a simulação de
`melhorias/bots.py` tem que dar exatamente o mesmo resultado que a versão
sequencial. Assim a melhoria não altera o modelo original, só acrescenta algo
a ele quando é ligada.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from comum.grade import criar_grade
from comum.modelo import ESPALHADOR, IGNORANTE, INATIVO
from melhorias.bots import rodar_simulacao_com_bots, sortear_bots
from melhorias.estatisticas import contar_estados, percentuais_por_geracao, resumir_historico
from sequencial import rodar_simulacao


class TestarBots(unittest.TestCase):

    def test_sem_bots_igual_a_sequencial(self):
        casos = [
            (40, 30, 0.05, 2),
            (25, 25, 0.10, 1),
            (30, 50, 0.20, 3),
        ]
        for linhas, colunas, percentual, limiar in casos:
            with self.subTest(linhas=linhas, colunas=colunas, limiar=limiar):
                grade_inicial = criar_grade(linhas, colunas, percentual, semente=11)
                historico_esperado, grade_esperada = rodar_simulacao(
                    grade_inicial, linhas, colunas, 60, limiar, imprimir=False)
                historico, grade_final, _ = rodar_simulacao_com_bots(
                    grade_inicial, linhas, colunas, 60, limiar, bots=[])
                self.assertEqual(historico, historico_esperado)
                self.assertEqual(grade_final, grade_esperada)

    def test_bots_nunca_deixam_de_espalhar(self):
        linhas, colunas = 40, 40
        grade_inicial = criar_grade(linhas, colunas, 0.05, semente=3)
        bots = sortear_bots(linhas, colunas, 0.02, semente=4)
        _, _, grades = rodar_simulacao_com_bots(
            grade_inicial, linhas, colunas, 30, 2, bots, guardar_grades=True)

        self.assertEqual(len(grades), 31)  # grade inicial + 30 gerações
        for geracao, grade in enumerate(grades):
            with self.subTest(geracao=geracao):
                self.assertTrue(all(grade[indice] == ESPALHADOR for indice in bots))

    def test_contagem_corrigida_confere_com_a_grade(self):
        """A contagem ajustada por `aplicar_bots` tem que bater com uma
        contagem feita direto na grade, célula por célula."""
        linhas, colunas = 35, 45
        grade_inicial = criar_grade(linhas, colunas, 0.03, semente=8)
        bots = sortear_bots(linhas, colunas, 0.01, semente=9)
        historico, _, grades = rodar_simulacao_com_bots(
            grade_inicial, linhas, colunas, 40, 2, bots, guardar_grades=True)

        for geracao, contagem in enumerate(historico, start=1):
            grade = grades[geracao]
            with self.subTest(geracao=geracao):
                self.assertEqual(contagem, (grade.count(IGNORANTE), grade.count(ESPALHADOR), grade.count(INATIVO)))

    def test_sorteio_sem_repeticao(self):
        bots = sortear_bots(50, 50, 0.1, semente=3)
        self.assertEqual(len(bots), 250)
        self.assertEqual(len(set(bots)), 250)
        self.assertEqual(bots, sortear_bots(50, 50, 0.1, semente=3))  # mesma semente, mesmos bots


class TestarEstatisticas(unittest.TestCase):

    def test_resumo_calculado_a_mao(self):
        # 100 pessoas; 10 convencidas na geração 1, 20 na 2, 5 na 3 e nenhuma na 4.
        historico = [(85, 10, 5), (65, 20, 15), (60, 5, 35), (60, 0, 40)]
        resumo = resumir_historico(historico, total_celulas=100)
        self.assertAlmostEqual(resumo["alcance"], 0.40)
        self.assertEqual(resumo["pico_espalhadores"], 20)
        self.assertEqual(resumo["geracao_pico"], 2)
        self.assertEqual(resumo["ultima_geracao_com_novos"], 3)

    def test_bots_ficam_fora_das_pessoas(self):
        # 100 células, 4 delas são bots (sempre contados como espalhadores).
        historico = [(76, 14, 10), (72, 8, 20), (72, 4, 24)]
        resumo = resumir_historico(historico, total_celulas=100, quantidade_bots=4)
        self.assertAlmostEqual(resumo["alcance"], (96 - 72) / 96)
        self.assertEqual(resumo["pico_espalhadores"], 10)
        self.assertEqual(resumo["ultima_geracao_com_novos"], 2)

    def test_contar_estados(self):
        grade = bytearray([IGNORANTE, ESPALHADOR, INATIVO, INATIVO, IGNORANTE, IGNORANTE])
        self.assertEqual(contar_estados(grade), (3, 1, 2))

    def test_percentuais_por_geracao(self):
        ignorantes, espalhadores, inativos = percentuais_por_geracao([(90, 5, 5), (80, 10, 10)], 100)
        self.assertEqual(ignorantes, [90, 80])
        self.assertEqual(espalhadores, [5, 10])
        self.assertEqual(inativos, [5, 10])

        # Com 4 bots: o total passa a ser 96 pessoas e os bots saem dos espalhadores.
        ignorantes, espalhadores, inativos = percentuais_por_geracao([(76, 14, 10)], 100, quantidade_bots=4)
        self.assertAlmostEqual(ignorantes[0], 100 * 76 / 96)
        self.assertAlmostEqual(espalhadores[0], 100 * 10 / 96)
        self.assertAlmostEqual(ignorantes[0] + espalhadores[0] + inativos[0], 100)


if __name__ == "__main__":
    unittest.main()

"""Testes de correção (seção 6 do plano).

As versões paralela e distribuída ainda não existem neste repositório, então
este arquivo testa hoje a propriedade que todas elas vão precisar respeitar:
calcular a grade em faixas de linhas separadas tem que dar exatamente o mesmo
resultado que calcular a grade inteira de uma vez, porque cada trabalhador só
lê a grade atual e só escreve nas próprias linhas (sem sobreposição).

Quando `paralelo_threads.py`, `paralelo_processos.py` e a versão distribuída
existirem, acrescentar aqui testes chamando cada uma com a mesma grade inicial
e semente, e comparando a grade final e o histórico de contagens com os da
sequencial.
"""

import importlib.util
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from comum.grade import criar_grade
from comum.modelo import calcular_intervalo

CAMINHO_ORIGINAL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "original", "FakeNews.py"
)


def carregar_modulo_original(caminho):
    especificacao = importlib.util.spec_from_file_location("fake_news_original", caminho)
    modulo = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(modulo)
    return modulo


def grade_lista_para_bytearray(grade_lista):
    """Converte a grade em lista de listas do original para o bytearray plano
    usado pela refatoração (índice linha * colunas + coluna)."""
    linhas = len(grade_lista)
    colunas = len(grade_lista[0])
    plana = bytearray(linhas * colunas)
    for i in range(linhas):
        for j in range(colunas):
            plana[i * colunas + j] = grade_lista[i][j]
    return plana, linhas, colunas


def calcular_geracao_completa(atual, linhas, colunas, limiar):
    proxima = bytearray(len(atual))
    contagem = calcular_intervalo(atual, proxima, linhas, colunas, 0, linhas, limiar)
    return proxima, contagem


def calcular_geracao_em_faixas(atual, linhas, colunas, limiar, numero_faixas):
    """Calcula a mesma geração dividindo as linhas em `numero_faixas` pedaços,
    do mesmo jeito que os trabalhadores das versões paralela e distribuída."""
    proxima = bytearray(len(atual))
    contagem_total = [0, 0, 0]

    for faixa in range(numero_faixas):
        inicio = faixa * linhas // numero_faixas
        fim = (faixa + 1) * linhas // numero_faixas
        contagem = calcular_intervalo(atual, proxima, linhas, colunas, inicio, fim, limiar)
        for indice in range(3):
            contagem_total[indice] += contagem[indice]

    return proxima, tuple(contagem_total)


class TestarDivisaoPorFaixas(unittest.TestCase):
    """Dividir a grade em faixas de linhas não pode mudar o resultado."""

    def test_varios_tamanhos_e_faixas(self):
        casos = [
            (20, 20, 2, 0.1),
            (37, 15, 3, 0.2),
            (50, 50, 1, 0.05),
        ]

        for linhas, colunas, limiar, percentual in casos:
            grade_inicial = criar_grade(linhas, colunas, percentual, semente=123)

            esperado_proxima, esperado_contagem = calcular_geracao_completa(
                grade_inicial, linhas, colunas, limiar
            )

            for numero_faixas in (1, 2, 4, 7):
                with self.subTest(linhas=linhas, colunas=colunas, numero_faixas=numero_faixas):
                    obtido_proxima, obtido_contagem = calcular_geracao_em_faixas(
                        grade_inicial, linhas, colunas, limiar, numero_faixas
                    )
                    self.assertEqual(obtido_proxima, esperado_proxima)
                    self.assertEqual(obtido_contagem, esperado_contagem)

    def test_varias_geracoes_com_quatro_faixas(self):
        linhas, colunas, limiar = 40, 30, 2
        atual_referencia = criar_grade(linhas, colunas, 0.1, semente=7)
        atual_faixas = bytearray(atual_referencia)

        for _ in range(10):
            atual_referencia, _ = calcular_geracao_completa(atual_referencia, linhas, colunas, limiar)
            atual_faixas, _ = calcular_geracao_em_faixas(atual_faixas, linhas, colunas, limiar, 4)
            self.assertEqual(atual_referencia, atual_faixas)


class TestarContraOriginal(unittest.TestCase):
    """Compara a sequencial refatorada com original/FakeNews.py, quando existir.

    Parte da grade que o próprio original sorteia (os dois usam geradores de
    número aleatório diferentes), e depois roda a mesma regra de transição
    geração por geração nos dois lados, comparando o resultado a cada passo.
    """

    def test_compara_com_original(self):
        if not os.path.exists(CAMINHO_ORIGINAL):
            self.skipTest("original/FakeNews.py ainda não foi adicionado ao repositório.")

        original = carregar_modulo_original(CAMINHO_ORIGINAL)
        limiar = 2

        grade_original = original.criar_grade(
            linhas=30, colunas=25, percentual_espalhadores=0.1, semente=99
        )
        atual, linhas, colunas = grade_lista_para_bytearray(grade_original)

        for geracao in range(1, 16):
            grade_original = original.proxima_geracao(grade_original, limiar)
            proxima = bytearray(len(atual))
            calcular_intervalo(atual, proxima, linhas, colunas, 0, linhas, limiar)
            atual = proxima

            esperado, _, _ = grade_lista_para_bytearray(grade_original)
            with self.subTest(geracao=geracao):
                self.assertEqual(atual, esperado)


if __name__ == "__main__":
    unittest.main()

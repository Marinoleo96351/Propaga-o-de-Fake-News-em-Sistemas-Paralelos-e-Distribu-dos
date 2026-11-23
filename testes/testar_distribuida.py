"""Testes de correção da versão distribuída (seção 6 do plano).

A distribuída troca mensagens de verdade por sockets TCP, então o teste
levanta um coordenador e trabalhadores reais em threads, todos em
`127.0.0.1`, e compara a grade final com o cálculo sequencial puro
(`comum.modelo.calcular_intervalo`, sem early-stop, o mesmo padrão usado em
`testar_correcao.py` e `testar_paralelo_vinicius.py`). O coordenador cria a
própria grade inicial a partir de `percentual`/`semente` (com
`comum.grade.criar_grade`), então o teste usa a mesma função para gerar a
grade de referência.
"""

import socket
import threading
import unittest

from comum.grade import criar_grade
from comum.modelo import calcular_intervalo
from distribuida.coordenador import (
    aguardar_trabalhadores,
    configurar_vizinhos,
    executar_simulacao,
)
from distribuida.protocolo import criar_mensagem, enviar_mensagem
from distribuida.trabalhador import executar_trabalhador


def _porta_livre():
    """Pede ao sistema operacional uma porta TCP livre em 127.0.0.1."""
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind(("127.0.0.1", 0))
    porta = servidor.getsockname()[1]
    servidor.close()
    return porta


def calcular_sequencial(grade_inicial, linhas, colunas, geracoes, limiar):
    """Mesma regra da distribuída: roda `geracoes` gerações sem parar antes."""
    atual = bytearray(grade_inicial)
    proxima = bytearray(len(atual))
    for _ in range(geracoes):
        calcular_intervalo(atual, proxima, linhas, colunas, 0, linhas, limiar)
        atual, proxima = proxima, atual
    return atual


def rodar_distribuida(linhas, colunas, geracoes, percentual, semente, limiar,
                       quantidade_trabalhadores):
    """Levanta um coordenador e `quantidade_trabalhadores` trabalhadores reais,
    todos em threads conectadas por sockets TCP em 127.0.0.1, e devolve a
    grade final montada pelo coordenador."""
    porta_coordenador = _porta_livre()
    portas_vizinho = [_porta_livre() for _ in range(quantidade_trabalhadores)]

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(("127.0.0.1", porta_coordenador))
    servidor.listen(quantidade_trabalhadores)

    erros = []

    def alvo_trabalhador(identificador, porta_vizinho):
        try:
            executar_trabalhador("127.0.0.1", porta_coordenador, identificador, porta_vizinho)
        except Exception as erro:  # repassa para o teste, já que é outra thread
            erros.append(erro)

    threads_trabalhadores = [
        threading.Thread(
            target=alvo_trabalhador,
            args=(identificador, portas_vizinho[identificador - 1]),
            daemon=True,
        )
        for identificador in range(1, quantidade_trabalhadores + 1)
    ]
    for thread in threads_trabalhadores:
        thread.start()

    try:
        trabalhadores = aguardar_trabalhadores(servidor, quantidade_trabalhadores)
        configurar_vizinhos(trabalhadores)
        grade_final = executar_simulacao(
            trabalhadores, linhas, colunas, geracoes, percentual, semente, limiar
        )
    finally:
        for dados in trabalhadores.values():
            try:
                enviar_mensagem(dados["conexao"], criar_mensagem("ENCERRAR"))
            except Exception:
                pass
            dados["conexao"].close()
        servidor.close()
        for thread in threads_trabalhadores:
            thread.join(timeout=5)

    if erros:
        raise erros[0]

    return grade_final


class TestarDistribuidaContraSequencial(unittest.TestCase):
    """A grade final da distribuída tem que ser idêntica à sequencial pura,
    para 1, 2 e 4 trabalhadores, confirmando que dividir em faixas com troca
    de fronteiras entre vizinhos não muda o resultado do modelo."""

    LINHAS, COLUNAS, GERACOES = 20, 15, 6
    PERCENTUAL, SEMENTE, LIMIAR = 0.2, 123, 2

    def test_uma_duas_e_quatro_trabalhadores(self):
        grade_inicial = criar_grade(self.LINHAS, self.COLUNAS, self.PERCENTUAL, self.SEMENTE)
        esperado = calcular_sequencial(
            grade_inicial, self.LINHAS, self.COLUNAS, self.GERACOES, self.LIMIAR
        )

        for quantidade_trabalhadores in (1, 2, 4):
            with self.subTest(trabalhadores=quantidade_trabalhadores):
                obtido = rodar_distribuida(
                    self.LINHAS, self.COLUNAS, self.GERACOES,
                    self.PERCENTUAL, self.SEMENTE, self.LIMIAR,
                    quantidade_trabalhadores,
                )
                self.assertEqual(bytearray(obtido), esperado)


if __name__ == "__main__":
    unittest.main()

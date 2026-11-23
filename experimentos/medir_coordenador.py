"""Coordenador da versão distribuída com medição de tempo, usado nos experimentos.

A versão distribuída (pasta distribuida/) não mede tempo. Este script faz o
mesmo que o main() de distribuida/coordenador.py, reaproveitando as funções de
lá sem alterá-las, e só acrescenta a medição.

O tempo vai do envio dos blocos aos trabalhadores até o recebimento do último
resultado. A espera pelas conexões fica de fora, como nas outras versões, em
que só o laço de gerações é medido.

Normalmente é iniciado por executar_experimentos.py, mas também pode ser usado
à mão (cada trabalhador com experimentos/medir_trabalhador.py):
    python experimentos/medir_coordenador.py --porta 6000 --trabalhadores 2 --linhas 100 --colunas 100
"""

import argparse
import os
import socket
import sys
import time

PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PASTA_PROJETO)

from distribuida.coordenador import aguardar_trabalhadores, configurar_vizinhos, executar_simulacao
from distribuida.protocolo import criar_mensagem, enviar_mensagem


def analisar_argumentos():
    analisador = argparse.ArgumentParser(description="Coordenador distribuído com medição de tempo.")
    analisador.add_argument("--porta", type=int, default=6000)
    analisador.add_argument("--trabalhadores", type=int, default=2)
    analisador.add_argument("--linhas", type=int, default=100)
    analisador.add_argument("--colunas", type=int, default=100)
    analisador.add_argument("--geracoes", type=int, default=30)
    analisador.add_argument("--percentual", type=float, default=0.05)
    analisador.add_argument("--semente", type=int, default=42)
    analisador.add_argument("--limiar", type=int, default=2)
    return analisador.parse_args()


def main():
    argumentos = analisar_argumentos()

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(("127.0.0.1", argumentos.porta))
    servidor.listen(argumentos.trabalhadores)
    # flush=True manda a linha na hora: executar_experimentos.py espera por ela
    # para saber que já pode iniciar os trabalhadores.
    print(f"Coordenador aguardando conexões na porta {argumentos.porta}", flush=True)

    trabalhadores = {}
    try:
        trabalhadores = aguardar_trabalhadores(servidor, argumentos.trabalhadores)
        configurar_vizinhos(trabalhadores)

        inicio = time.perf_counter()
        executar_simulacao(trabalhadores, argumentos.linhas, argumentos.colunas, argumentos.geracoes,
                           argumentos.percentual, argumentos.semente, argumentos.limiar)
        fim = time.perf_counter()
        print(f"Tempo total: {fim - inicio:.6f} s")
    finally:
        for dados in trabalhadores.values():
            try:
                enviar_mensagem(dados["conexao"], criar_mensagem("ENCERRAR"))
            except Exception:
                pass  # o trabalhador pode já ter encerrado a conexão
            dados["conexao"].close()
        servidor.close()


if __name__ == "__main__":
    main()

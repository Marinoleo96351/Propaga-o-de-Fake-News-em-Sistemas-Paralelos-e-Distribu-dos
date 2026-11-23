"""Trabalhador da versão distribuída com medição do tempo de comunicação.

Roda o trabalhador de distribuida/trabalhador.py sem alterar o código dele. A
única diferença: a função trocar_fronteiras, que envia as linhas de fronteira
aos vizinhos e recebe as deles, é trocada por uma versão que mede quanto tempo
se passa dentro dela e chama a original. Esse tempo inclui montar e ler as
mensagens, enviá-las, recebê-las e esperar o vizinho mais lento terminar a
geração anterior.

Normalmente é iniciado por executar_experimentos.py, um processo por trabalhador:
    python experimentos/medir_trabalhador.py --porta 6000 --id 1 --porta-vizinho 6001
"""

import argparse
import os
import sys
import time

PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PASTA_PROJETO)

import distribuida.trabalhador as trabalhador

trocar_fronteiras_original = trabalhador.trocar_fronteiras
tempo_comunicacao = 0.0


def trocar_fronteiras_medindo(vizinhos, identificador, geracao, bloco, colunas):
    global tempo_comunicacao
    inicio = time.perf_counter()
    resultado = trocar_fronteiras_original(vizinhos, identificador, geracao, bloco, colunas)
    tempo_comunicacao += time.perf_counter() - inicio
    return resultado


def analisar_argumentos():
    analisador = argparse.ArgumentParser(description="Trabalhador distribuído com medição da comunicação.")
    analisador.add_argument("--porta", type=int, default=6000, help="Porta do coordenador.")
    analisador.add_argument("--id", type=int, required=True)
    analisador.add_argument("--porta-vizinho", dest="porta_vizinho", type=int, required=True)
    return analisador.parse_args()


def main():
    argumentos = analisar_argumentos()

    # executar_trabalhador procura trocar_fronteiras no próprio módulo a cada
    # geração, então trocar a função ali basta para a versão que mede ser usada.
    trabalhador.trocar_fronteiras = trocar_fronteiras_medindo
    trabalhador.executar_trabalhador("127.0.0.1", argumentos.porta, argumentos.id, argumentos.porta_vizinho)

    print(f"Tempo de comunicação: {tempo_comunicacao:.6f} s")


if __name__ == "__main__":
    main()

"""Trabalhador da versão distribuída com medição de três tempos separados.

Roda o trabalhador de distribuida/trabalhador.py sem alterar o código dele.
Duas funções são trocadas por versões que medem o tempo, e chamam as peças
originais (`criar_mensagem_fronteira`, `enviar_mensagem`, `receber_mensagem`,
`extrair_linha_fronteira`) na mesma ordem da versão real, então o
comportamento não muda:

- `calcular_bloco` (cálculo): tempo gasto calculando a faixa, igual ao da
  versão sequencial.
- `trocar_fronteiras` (comunicação e espera): a troca de bordas tem uma fase
  de **envio** (o trabalhador manda a borda para os vizinhos; conta como
  comunicação) e uma fase de **recebimento** (bloqueado em `receber_mensagem`
  até o vizinho mandar a dele; conta como espera, porque o tempo é dominado
  por esperar o vizinho terminar a própria geração e enviar, não pelo
  tamanho da mensagem).

Os três tempos são somados ao longo de todas as gerações, como pede o
roteiro de experimentos (seção 8.3 do plano do projeto).

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
from distribuida.protocolo import (
    criar_mensagem_fronteira,
    enviar_mensagem,
    receber_mensagem,
    extrair_linha_fronteira,
)

calcular_bloco_original = trabalhador.calcular_bloco

tempo_calculo = 0.0
tempo_comunicacao = 0.0
tempo_espera = 0.0


def calcular_bloco_medindo(*args, **kwargs):
    global tempo_calculo
    inicio = time.perf_counter()
    resultado = calcular_bloco_original(*args, **kwargs)
    tempo_calculo += time.perf_counter() - inicio
    return resultado


def trocar_fronteiras_medindo(vizinhos, identificador, geracao, bloco, colunas):
    """Mesma lógica de distribuida.trabalhador.trocar_fronteiras, com o envio
    e o recebimento cronometrados separadamente."""
    global tempo_comunicacao, tempo_espera

    primeira = bloco[:colunas]
    ultima = bloco[-colunas:]

    inicio = time.perf_counter()
    for id_vizinho, conexao in vizinhos.items():
        linha = primeira if id_vizinho < identificador else ultima
        enviar_mensagem(conexao, criar_mensagem_fronteira(identificador, geracao, linha))
    tempo_comunicacao += time.perf_counter() - inicio

    fronteiras = {}
    inicio = time.perf_counter()
    for id_vizinho, conexao in vizinhos.items():
        mensagem = receber_mensagem(conexao)
        fronteiras[id_vizinho] = extrair_linha_fronteira(mensagem, geracao, colunas)
    tempo_espera += time.perf_counter() - inicio

    esquerda = None
    direita = None
    for id_vizinho, linha in fronteiras.items():
        if id_vizinho < identificador:
            esquerda = linha
        else:
            direita = linha

    return esquerda, direita


def analisar_argumentos():
    analisador = argparse.ArgumentParser(description="Trabalhador distribuído com medição de cálculo, comunicação e espera.")
    analisador.add_argument("--porta", type=int, default=6000, help="Porta do coordenador.")
    analisador.add_argument("--id", type=int, required=True)
    analisador.add_argument("--porta-vizinho", dest="porta_vizinho", type=int, required=True)
    return analisador.parse_args()


def main():
    argumentos = analisar_argumentos()

    # executar_trabalhador procura calcular_bloco e trocar_fronteiras no
    # próprio módulo a cada geração, então trocar as funções ali basta para
    # as versões que medem serem usadas.
    trabalhador.calcular_bloco = calcular_bloco_medindo
    trabalhador.trocar_fronteiras = trocar_fronteiras_medindo
    trabalhador.executar_trabalhador("127.0.0.1", argumentos.porta, argumentos.id, argumentos.porta_vizinho)

    print(f"Tempo de cálculo: {tempo_calculo:.6f} s")
    print(f"Tempo de comunicação: {tempo_comunicacao:.6f} s")
    print(f"Tempo de espera: {tempo_espera:.6f} s")


if __name__ == "__main__":
    main()

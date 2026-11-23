"""Melhoria: bots automatizados.

Um bot é uma conta automática que publica a fake news sem parar. Ao contrário
de uma pessoa, ele nunca deixa de espalhar (nunca vira Inativo).

Na grade, o bot é uma célula no estado Espalhador como qualquer outra. Por isso
a regra de vizinhança de `comum/modelo.py` funciona sem nenhuma mudança: os
vizinhos contam o bot como mais um espalhador. A única diferença acontece no
fim de cada geração: a função de cálculo transforma o bot em Inativo, como
faria com uma pessoa, e `aplicar_bots` o devolve ao estado Espalhador.

Uso, a partir da pasta raiz do projeto:
    python3 melhorias/bots.py --linhas 200 --colunas 200 --percentual-bots 0.005
"""

import argparse
import os
import random
import sys

PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PASTA_PROJETO)

from comum.grade import carregar_grade, criar_grade
from comum.modelo import ESPALHADOR, calcular_intervalo
from melhorias.estatisticas import resumir_historico


def sortear_bots(linhas, colunas, percentual_bots, semente):
    """Sorteia as posições dos bots, sem repetir célula."""
    aleatorio = random.Random(semente)
    total_celulas = linhas * colunas
    quantidade = int(total_celulas * percentual_bots)
    return sorted(aleatorio.sample(range(total_celulas), quantidade))


def aplicar_bots(proxima, bots, contagem):
    """Devolve os bots ao estado Espalhador depois do cálculo da geração.

    Como o bot era Espalhador na geração anterior, `calcular_intervalo` o
    transformou em Inativo e o contou como inativo. Aqui ele volta a ser
    Espalhador e a contagem é corrigida: um inativo a menos e um espalhador a
    mais para cada bot.
    """
    ignorantes, espalhadores, inativos = contagem
    for indice in bots:
        proxima[indice] = ESPALHADOR
    return ignorantes, espalhadores + len(bots), inativos - len(bots)


def rodar_simulacao_com_bots(grade_inicial, linhas, colunas, geracoes, limiar_convencimento,
                             bots, guardar_grades=False):
    """Mesmo laço da versão sequencial, aplicando os bots a cada geração.

    Com a lista `bots` vazia, o resultado é idêntico ao da sequencial
    (conferido em testes/testar_melhorias.py). Devolve o histórico de
    contagens, a grade final e, se `guardar_grades` for verdadeiro, uma cópia
    da grade de cada geração (usada pela animação).
    """
    atual = bytearray(grade_inicial)
    for indice in bots:
        atual[indice] = ESPALHADOR  # os bots já começam espalhando
    proxima = bytearray(len(atual))
    historico = []
    grades = [bytes(atual)] if guardar_grades else []

    for _ in range(geracoes):
        contagem = calcular_intervalo(atual, proxima, linhas, colunas, 0, linhas, limiar_convencimento)
        contagem = aplicar_bots(proxima, bots, contagem)
        historico.append(contagem)
        atual, proxima = proxima, atual
        if guardar_grades:
            grades.append(bytes(atual))

        # Com bots sempre existe espalhador, então a simulação só termina
        # quando chega ao limite de gerações.
        if contagem[1] == 0:
            break

    return historico, atual, grades


def analisar_argumentos():
    analisador = argparse.ArgumentParser(description="Compara a propagação com e sem bots na mesma grade inicial.")
    analisador.add_argument("--linhas", type=int, default=200)
    analisador.add_argument("--colunas", type=int, default=200)
    analisador.add_argument("--geracoes", type=int, default=200)
    analisador.add_argument("--percentual", type=float, default=0.05,
                            help="Percentual inicial de espalhadores (0 a 1).")
    analisador.add_argument("--percentual-bots", dest="percentual_bots", type=float, default=0.005,
                            help="Percentual das células ocupadas por bots (0 a 1).")
    analisador.add_argument("--limiar", type=int, default=2,
                            help="Vizinhos espalhadores necessários para convencer um ignorante.")
    analisador.add_argument("--semente", type=int, default=42)
    analisador.add_argument("--arquivo-grade", dest="arquivo_grade", type=str, default=None,
                            help="Carrega a grade inicial deste arquivo em vez de sortear uma nova.")
    return analisador.parse_args()


def main():
    argumentos = analisar_argumentos()

    if argumentos.arquivo_grade:
        grade_inicial, linhas, colunas = carregar_grade(argumentos.arquivo_grade)
    else:
        linhas, colunas = argumentos.linhas, argumentos.colunas
        grade_inicial = criar_grade(linhas, colunas, argumentos.percentual, argumentos.semente)

    # Semente diferente da usada na grade, para as posições dos bots não
    # repetirem o sorteio dos espalhadores iniciais.
    bots = sortear_bots(linhas, colunas, argumentos.percentual_bots, argumentos.semente + 1)
    total_celulas = linhas * colunas

    historico_sem_bots, _, _ = rodar_simulacao_com_bots(
        grade_inicial, linhas, colunas, argumentos.geracoes, argumentos.limiar, bots=[])
    historico_com_bots, _, _ = rodar_simulacao_com_bots(
        grade_inicial, linhas, colunas, argumentos.geracoes, argumentos.limiar, bots=bots)

    sem_bots = resumir_historico(historico_sem_bots, total_celulas)
    com_bots = resumir_historico(historico_com_bots, total_celulas, len(bots))

    print(f"Grade {linhas}x{colunas}, {argumentos.percentual:.1%} de espalhadores iniciais, "
          f"limiar {argumentos.limiar}, até {argumentos.geracoes} gerações")
    print(f"Bots: {len(bots)} ({len(bots) / total_celulas:.1%} das células), nunca deixam de espalhar\n")
    print(f"{'':<40}{'sem bots':>12}{'com bots':>12}")
    print(f"{'Pessoas alcançadas':<40}{sem_bots['alcance']:>12.1%}{com_bots['alcance']:>12.1%}")
    print(f"{'Pico de pessoas espalhando':<40}{sem_bots['pico_espalhadores']:>12}{com_bots['pico_espalhadores']:>12}")
    print(f"{'Geração do pico':<40}{sem_bots['geracao_pico']:>12}{com_bots['geracao_pico']:>12}")
    print(f"{'Última geração com novos convencidos':<40}"
          f"{sem_bots['ultima_geracao_com_novos']:>12}{com_bots['ultima_geracao_com_novos']:>12}")


if __name__ == "__main__":
    main()

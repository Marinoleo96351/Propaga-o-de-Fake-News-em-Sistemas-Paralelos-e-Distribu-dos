"""Versão sequencial refatorada: base de comparação para a paralela e a distribuída.

Usa duas grades alternadas (sem `deepcopy`) e a mesma função de cálculo
(`comum.modelo.calcular_intervalo`) que as outras versões vão usar, só que
chamada para a grade inteira de uma vez.
"""

import argparse
import time

from comum.grade import carregar_grade, criar_grade, salvar_grade
from comum.modelo import ESPALHADOR, calcular_intervalo


def rodar_simulacao(grade_inicial, linhas, colunas, geracoes, limiar_convencimento,
                     parar_quando_nao_ha_espalhador=True, imprimir=True):
    """Roda a simulação por até `geracoes` gerações.

    Devolve a lista de contagens (ignorantes, espalhadores, inativos) de cada
    geração executada e a grade final.
    """
    atual = bytearray(grade_inicial)
    proxima = bytearray(len(atual))
    historico = []

    for geracao in range(1, geracoes + 1):
        contagem = calcular_intervalo(atual, proxima, linhas, colunas, 0, linhas, limiar_convencimento)
        historico.append(contagem)
        atual, proxima = proxima, atual

        if imprimir:
            ignorantes, espalhadores, inativos = contagem
            print(f"Geração {geracao}: ignorantes={ignorantes} espalhadores={espalhadores} inativos={inativos}")

        if parar_quando_nao_ha_espalhador and contagem[1] == 0:
            break

    return historico, atual


def analisar_argumentos():
    analisador = argparse.ArgumentParser(description="Simulação sequencial de propagação de fake news.")
    analisador.add_argument("--linhas", type=int, default=100)
    analisador.add_argument("--colunas", type=int, default=100)
    analisador.add_argument("--geracoes", type=int, default=50)
    analisador.add_argument("--percentual", type=float, default=0.05,
                             help="Percentual inicial de espalhadores (0 a 1).")
    analisador.add_argument("--limiar", type=int, default=2,
                             help="Vizinhos espalhadores necessários para convencer um ignorante.")
    analisador.add_argument("--semente", type=int, default=42)
    analisador.add_argument("--arquivo-grade", dest="arquivo_grade", type=str, default=None,
                             help="Carrega a grade inicial deste arquivo em vez de sortear uma nova.")
    analisador.add_argument("--salvar-grade", dest="salvar_grade_em", type=str, default=None,
                             help="Salva a grade inicial sorteada neste arquivo, para outras versões usarem.")
    analisador.add_argument("--sem-parada-antecipada", dest="sem_parada_antecipada",
                             action="store_true",
                             help="Roda todas as gerações pedidas, mesmo sem espalhadores restantes.")
    analisador.add_argument("--sem-impressao", dest="sem_impressao", action="store_true",
                             help="Não imprime a contagem a cada geração (usar para medir desempenho).")
    return analisador.parse_args()


def main():
    argumentos = analisar_argumentos()

    if argumentos.arquivo_grade:
        grade_inicial, linhas, colunas = carregar_grade(argumentos.arquivo_grade)
    else:
        linhas, colunas = argumentos.linhas, argumentos.colunas
        grade_inicial = criar_grade(linhas, colunas, argumentos.percentual, argumentos.semente)
        print(f"Espalhadores iniciais sorteados: {grade_inicial.count(ESPALHADOR)}")

    if argumentos.salvar_grade_em:
        salvar_grade(grade_inicial, linhas, colunas, argumentos.salvar_grade_em)

    inicio = time.perf_counter()
    historico, _ = rodar_simulacao(
        grade_inicial, linhas, colunas, argumentos.geracoes, argumentos.limiar,
        parar_quando_nao_ha_espalhador=not argumentos.sem_parada_antecipada,
        imprimir=not argumentos.sem_impressao,
    )
    fim = time.perf_counter()

    print(f"Gerações executadas: {len(historico)}")
    print(f"Tempo total: {fim - inicio:.4f} s")


if __name__ == "__main__":
    main()

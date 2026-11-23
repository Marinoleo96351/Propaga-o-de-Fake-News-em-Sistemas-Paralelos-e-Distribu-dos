"""Melhoria: probabilidade de convencimento.

Na regra original, um vizinho espalhador sempre conta para o limiar de
convencimento. Aqui, cada contato com um vizinho espalhador só convence com
probabilidade `p`: com `p = 1.0` a regra volta a ser a determinística
original (mesmo resultado, útil para comparar).

O sorteio usa o gerador de contador de `comum/probabilidade.py`
(`calcular_intervalo_probabilistico`): o resultado de cada célula depende só
da semente, da geração, da linha, da coluna e do vizinho, nunca de quem
calculou a célula. Por isso dividir a grade em mais ou menos faixas não muda
o resultado final, a propriedade que a versão paralela e a distribuída
precisam para usar a probabilidade sem perder a comparação com a sequencial
(técnica descrita por Salmon et al., 2011).

Uso, a partir da pasta raiz do projeto:
    python3 melhorias/probabilidade.py --linhas 200 --colunas 200
"""

import argparse
import os
import sys

PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PASTA_PROJETO)

from comum.grade import criar_grade
from comum.probabilidade import calcular_intervalo_probabilistico
from melhorias.estatisticas import resumir_historico


def rodar_simulacao_probabilistica(grade_inicial, linhas, colunas, geracoes,
                                    limiar_convencimento, probabilidade, semente,
                                    faixas=1):
    """Roda a simulação probabilística dividindo cada geração em `faixas`
    pedaços de linhas, só para provar que o resultado não depende da divisão
    (o mesmo papel que `trabalhadores` tem nas versões paralela e distribuída).
    """
    atual = bytearray(grade_inicial)
    proxima = bytearray(len(atual))
    historico = []

    for geracao in range(1, geracoes + 1):
        contagem_total = [0, 0, 0]
        for faixa in range(faixas):
            inicio = faixa * linhas // faixas
            fim = (faixa + 1) * linhas // faixas
            contagem = calcular_intervalo_probabilistico(
                atual, proxima, linhas, colunas, inicio, fim,
                limiar_convencimento, probabilidade, semente, geracao,
            )
            for indice in range(3):
                contagem_total[indice] += contagem[indice]

        historico.append(tuple(contagem_total))
        atual, proxima = proxima, atual

        if contagem_total[1] == 0:
            break

    return historico, atual


def analisar_argumentos():
    analisador = argparse.ArgumentParser(
        description="Mede o alcance final da propagação para várias probabilidades de convencimento.")
    analisador.add_argument("--linhas", type=int, default=200)
    analisador.add_argument("--colunas", type=int, default=200)
    analisador.add_argument("--geracoes", type=int, default=200)
    analisador.add_argument("--percentual", type=float, default=0.05,
                             help="Percentual inicial de espalhadores (0 a 1).")
    analisador.add_argument("--limiar", type=int, default=2)
    analisador.add_argument("--semente", type=int, default=42)
    analisador.add_argument("--probabilidades", type=float, nargs="+",
                             default=[0.1, 0.3, 0.5, 1.0])
    return analisador.parse_args()


def main():
    argumentos = analisar_argumentos()
    linhas, colunas = argumentos.linhas, argumentos.colunas
    total_celulas = linhas * colunas
    grade_inicial = criar_grade(linhas, colunas, argumentos.percentual, argumentos.semente)

    print(f"Grade {linhas}x{colunas}, {argumentos.percentual:.1%} de espalhadores iniciais, "
          f"limiar {argumentos.limiar}, até {argumentos.geracoes} gerações\n")
    print(f"{'Probabilidade':<16}{'Alcance final':>14}{'Gerações até parar':>20}")

    for probabilidade in argumentos.probabilidades:
        historico, _ = rodar_simulacao_probabilistica(
            grade_inicial, linhas, colunas, argumentos.geracoes,
            argumentos.limiar, probabilidade, argumentos.semente,
        )
        resumo = resumir_historico(historico, total_celulas)
        rotulo = f"{probabilidade:.1f}" + (" (determinística)" if probabilidade == 1.0 else "")
        print(f"{rotulo:<16}{resumo['alcance']:>14.1%}{len(historico):>20}")

    print("\nConferindo que o resultado não depende da divisão em faixas "
          "(1, 4 e 8 trabalhadores, p = 0.3):")
    referencia = None
    for faixas in (1, 4, 8):
        _, final = rodar_simulacao_probabilistica(
            grade_inicial, linhas, colunas, argumentos.geracoes,
            argumentos.limiar, 0.3, argumentos.semente, faixas=faixas,
        )
        if referencia is None:
            referencia = final
        igual = "sim" if final == referencia else "NÃO (erro!)"
        print(f"  {faixas} faixas: grade final igual à referência? {igual}")


if __name__ == "__main__":
    main()

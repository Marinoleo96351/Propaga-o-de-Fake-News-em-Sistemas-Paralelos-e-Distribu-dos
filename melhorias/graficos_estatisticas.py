"""Melhoria: estatísticas adicionais da propagação, em gráficos e tabela.

A partir de simulações com a mesma grade inicial, gera em melhorias/saidas/:
    curvas_estados.png      percentual de ignorantes, espalhadores e inativos a
                            cada geração, sem bots e com bots, lado a lado;
    alcance_por_bots.png    pessoas alcançadas conforme o percentual de bots,
                            para dois limiares de convencimento;
    estatisticas_bots.csv   tabela com os números usados no segundo gráfico.

Uso, a partir da pasta raiz do projeto (o matplotlib está no .venv):
    .venv/bin/python melhorias/graficos_estatisticas.py
"""

import argparse
import csv
import os
import sys

import matplotlib

matplotlib.use("Agg")  # só grava os arquivos PNG, sem abrir janela
import matplotlib.pyplot as plt

PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PASTA_PROJETO)

from comum.grade import criar_grade
from melhorias.bots import rodar_simulacao_com_bots, sortear_bots
from melhorias.estatisticas import contar_estados, percentuais_por_geracao, resumir_historico

PASTA_SAIDAS = os.path.join(PASTA_PROJETO, "melhorias", "saidas")

PERCENTUAIS_BOTS = [0, 0.001, 0.0025, 0.005, 0.01, 0.02]
LIMIARES = [2, 3]

# Estados com as cores da animação (o inativo num azul mais escuro, para a
# linha aparecer bem sobre o fundo branco).
CORES_ESTADOS = {"Ignorantes": "#898781", "Espalhadores": "#e34948", "Inativos": "#2a78d6"}
ESTILO_LIMIARES = {2: {"cor": "#6250d6", "marcador": "o"}, 3: {"cor": "#eb6834", "marcador": "s"}}
COR_TEXTO_SECUNDARIO = "#52514e"

COLUNAS_CSV = ["limiar", "percentual_bots", "quantidade_bots", "alcance",
               "pico_espalhadores", "geracao_pico", "ultima_geracao_com_novos"]


def simular(grade_inicial, linhas, colunas, geracoes, limiar, bots):
    """Roda a simulação e devolve a contagem de estados de cada geração,
    começando pela grade inicial (geração 0)."""
    historico, _, grades = rodar_simulacao_com_bots(grade_inicial, linhas, colunas, geracoes,
                                                    limiar, bots, guardar_grades=True)
    return [contar_estados(grades[0])] + historico


def estilizar_eixo(eixo):
    eixo.grid(True, color="#e1e0d9", linewidth=0.8)
    eixo.set_axisbelow(True)
    for lado in ("top", "right"):
        eixo.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        eixo.spines[lado].set_color("#c3c2b7")
    eixo.tick_params(colors=COR_TEXTO_SECUNDARIO)


def grafico_curvas(paineis, total_celulas, geracoes, descricao, caminho):
    """Um painel por simulação, com as três curvas em % da população.

    `paineis` é uma lista de (título, contagens, quantidade de bots).
    """
    figura, eixos = plt.subplots(1, len(paineis), figsize=(11, 5), sharex=True, sharey=True,
                                 layout="constrained")
    figura.suptitle("Evolução dos estados da população a cada geração", x=0.01, ha="left",
                    fontsize=14, fontweight="bold")
    figura.supxlabel(descricao, fontsize=9, color=COR_TEXTO_SECUNDARIO)

    for eixo, (titulo, contagens, quantidade_bots) in zip(eixos, paineis):
        ignorantes, espalhadores, inativos = percentuais_por_geracao(contagens, total_celulas, quantidade_bots)
        numeros_geracao = list(range(len(contagens)))
        eixo.plot(numeros_geracao, ignorantes, color=CORES_ESTADOS["Ignorantes"], linewidth=2, label="Ignorantes")
        eixo.plot(numeros_geracao, espalhadores, color=CORES_ESTADOS["Espalhadores"], linewidth=2, label="Espalhadores")
        eixo.plot(numeros_geracao, inativos, color=CORES_ESTADOS["Inativos"], linewidth=2, label="Inativos")

        pico = max(espalhadores)
        geracao_pico = espalhadores.index(pico)
        eixo.annotate(f"pico de espalhadores: {pico:.1f}% (geração {geracao_pico})",
                      (geracao_pico, pico), xytext=(10, 12), textcoords="offset points", fontsize=9)

        # Sem espalhadores a grade não muda mais, e a simulação para antes do limite.
        ultima = numeros_geracao[-1]
        if ultima < geracoes:
            eixo.annotate(f"propagação parou\nna geração {ultima}", (ultima, ignorantes[-1]),
                          xytext=(6, 10), textcoords="offset points", fontsize=9, color=COR_TEXTO_SECUNDARIO)

        alcance = resumir_historico(contagens[1:], total_celulas, quantidade_bots)["alcance"]
        eixo.set_title(f"{titulo}\nPessoas alcançadas ao final: {alcance:.1%}", loc="left", fontsize=11)
        eixo.set_xlabel("Geração", color=COR_TEXTO_SECUNDARIO)
        estilizar_eixo(eixo)

    eixos[0].set_ylabel("População (%)", color=COR_TEXTO_SECUNDARIO)
    eixos[0].set_ylim(0, 100)
    eixos[0].set_xlim(0, geracoes)
    eixos[0].legend(frameon=False, loc="upper right")
    figura.savefig(caminho, dpi=150, facecolor="white")
    plt.close(figura)
    print(f"Gráfico gerado: {caminho}")


def grafico_alcance_por_bots(tabela, descricao, caminho):
    figura, eixo = plt.subplots(figsize=(8, 5), layout="constrained")
    figura.suptitle("Pessoas alcançadas conforme o percentual de bots", x=0.01, ha="left",
                    fontsize=14, fontweight="bold")
    eixo.set_title(descricao, loc="left", fontsize=10, color=COR_TEXTO_SECUNDARIO)

    for limiar in LIMIARES:
        linhas = [linha for linha in tabela if linha["limiar"] == limiar]
        x = [100 * linha["percentual_bots"] for linha in linhas]
        y = [100 * linha["alcance"] for linha in linhas]
        estilo = ESTILO_LIMIARES[limiar]
        eixo.plot(x, y, color=estilo["cor"], marker=estilo["marcador"], markersize=7,
                  markeredgecolor="white", markeredgewidth=1.5, linewidth=2,
                  label=f"Limiar {limiar} (vizinhos espalhadores para convencer)")
        # Só o primeiro e o último valor ficam escritos; o resto está na tabela CSV.
        for indice in (0, -1):
            eixo.annotate(f"{y[indice]:.1f}%", (x[indice], y[indice]), xytext=(0, 9),
                          textcoords="offset points", ha="center", fontsize=9)

    eixo.set_xlabel("Bots (% das células da grade)", color=COR_TEXTO_SECUNDARIO)
    eixo.set_ylabel("Pessoas alcançadas ao final (%)", color=COR_TEXTO_SECUNDARIO)
    eixo.xaxis.set_major_formatter(lambda valor, _: f"{valor:g}%")
    eixo.set_ylim(0, 100)
    eixo.legend(frameon=False, loc="center right")
    estilizar_eixo(eixo)
    figura.savefig(caminho, dpi=150, facecolor="white")
    plt.close(figura)
    print(f"Gráfico gerado: {caminho}")


def salvar_tabela(tabela, caminho):
    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS_CSV)
        escritor.writeheader()
        for linha in tabela:
            escritor.writerow({**linha, "alcance": f"{linha['alcance']:.4f}"})
    print(f"Tabela gravada em {caminho}")


def analisar_argumentos():
    analisador = argparse.ArgumentParser(description="Gera gráficos e tabela de estatísticas da propagação.")
    analisador.add_argument("--linhas", type=int, default=200)
    analisador.add_argument("--colunas", type=int, default=200)
    analisador.add_argument("--geracoes", type=int, default=60)
    analisador.add_argument("--percentual", type=float, default=0.05,
                            help="Percentual inicial de espalhadores (0 a 1).")
    analisador.add_argument("--limiar", type=int, default=2,
                            help="Limiar usado no gráfico de curvas.")
    analisador.add_argument("--percentual-bots", dest="percentual_bots", type=float, default=0.005,
                            help="Percentual de bots no painel 'com bots' do gráfico de curvas.")
    analisador.add_argument("--semente", type=int, default=42)
    return analisador.parse_args()


def main():
    argumentos = analisar_argumentos()
    linhas, colunas, geracoes = argumentos.linhas, argumentos.colunas, argumentos.geracoes
    total_celulas = linhas * colunas
    grade_inicial = criar_grade(linhas, colunas, argumentos.percentual, argumentos.semente)
    os.makedirs(PASTA_SAIDAS, exist_ok=True)

    # Gráfico 1: curvas sem bots e com bots, na mesma grade inicial.
    # Os bots usam a semente da grade + 1, a mesma regra de melhorias/bots.py.
    bots = sortear_bots(linhas, colunas, argumentos.percentual_bots, argumentos.semente + 1)
    paineis = [
        ("Sem bots", simular(grade_inicial, linhas, colunas, geracoes, argumentos.limiar, []), 0),
        (f"Com {len(bots)} bots ({len(bots) / total_celulas:.1%} das células)",
         simular(grade_inicial, linhas, colunas, geracoes, argumentos.limiar, bots), len(bots)),
    ]
    grafico_curvas(paineis, total_celulas, geracoes,
                   f"Grade {linhas}x{colunas} · {argumentos.percentual:.0%} de espalhadores iniciais · "
                   f"limiar {argumentos.limiar} · até {geracoes} gerações",
                   os.path.join(PASTA_SAIDAS, "curvas_estados.png"))

    # Gráfico 2 e tabela: alcance para cada combinação de limiar e percentual de bots.
    tabela = []
    for limiar in LIMIARES:
        for percentual_bots in PERCENTUAIS_BOTS:
            bots = sortear_bots(linhas, colunas, percentual_bots, argumentos.semente + 1)
            contagens = simular(grade_inicial, linhas, colunas, geracoes, limiar, bots)
            resumo = resumir_historico(contagens[1:], total_celulas, len(bots))
            tabela.append({"limiar": limiar, "percentual_bots": percentual_bots,
                           "quantidade_bots": len(bots), **resumo})
            print(f"limiar {limiar} · bots {percentual_bots:>6.2%} ({len(bots):>3}) · "
                  f"alcance {resumo['alcance']:>6.1%} · pico {resumo['pico_espalhadores']:>5} "
                  f"na geração {resumo['geracao_pico']:>2} · última geração com novos "
                  f"{resumo['ultima_geracao_com_novos']:>2}")

    salvar_tabela(tabela, os.path.join(PASTA_SAIDAS, "estatisticas_bots.csv"))
    grafico_alcance_por_bots(tabela,
                             f"Grade {linhas}x{colunas} · {argumentos.percentual:.0%} de espalhadores "
                             f"iniciais · até {geracoes} gerações",
                             os.path.join(PASTA_SAIDAS, "alcance_por_bots.png"))


if __name__ == "__main__":
    main()

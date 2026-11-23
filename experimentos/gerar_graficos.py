"""Lê o CSV de tempos, calcula os indicadores e gera a tabela-resumo e os gráficos.

Para cada configuração (versão + cenário + número de trabalhadores) calcula a
média e o desvio padrão das repetições. Depois, com p = número de trabalhadores:

    speedup     S(p) = T_sequencial / T_versao(p)
    eficiência  E(p) = S(p) / p

T_sequencial é o tempo médio da versão sequencial no mesmo experimento e no
mesmo cenário (tamanho, gerações e percentual). S(p) = p e E(p) = 1 seriam o
caso ideal, em que dobrar os trabalhadores corta o tempo pela metade.

Um gráfico só é gerado se o CSV tiver os dados que ele precisa; caso contrário
o script avisa e segue para o próximo. Nada é estimado ou preenchido.

Uso, a partir da pasta raiz do projeto (o matplotlib está no .venv):
    .venv/bin/python experimentos/gerar_graficos.py --maquina notebook
"""

import argparse
import csv
import os
import statistics
import sys

import matplotlib

matplotlib.use("Agg")  # só grava os arquivos PNG, sem abrir janela
import matplotlib.pyplot as plt

PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_RESULTADOS = os.path.join(PASTA_PROJETO, "experimentos", "resultados")
PASTA_GRAFICOS = os.path.join(PASTA_PROJETO, "experimentos", "graficos")

# Cada versão tem sempre a mesma cor e o mesmo marcador, em todos os gráficos.
# O marcador diferente ajuda quem não distingue bem as cores e na impressão.
ESTILO_VERSOES = {
    "sequencial": {"nome": "Sequencial", "cor": "#52514e", "marcador": "D"},
    "threads": {"nome": "Paralela (threads)", "cor": "#2a78d6", "marcador": "o"},
    "processos": {"nome": "Paralela (processos)", "cor": "#eb6834", "marcador": "s"},
    "distribuida": {"nome": "Distribuída (sockets)", "cor": "#1baf7a", "marcador": "^"},
}
COR_COMUNICACAO = "#eda100"
COR_TEXTO = "#0b0b0b"
COR_TEXTO_SECUNDARIO = "#52514e"
COR_IDEAL = "#898781"
COR_GRADE = "#e1e0d9"
COR_EIXO = "#c3c2b7"

COLUNAS_RESUMO = [
    "experimento", "versao", "linhas", "colunas", "geracoes", "percentual", "trabalhadores",
    "repeticoes", "tempo_medio_s", "desvio_padrao_s", "speedup", "eficiencia",
    "tempo_comunicacao_medio_s", "bytes_enviados_medio",
]


def ler_tempos(caminho):
    """Lê o CSV gerado por executar_experimentos.py, convertendo os números."""
    execucoes = []
    with open(caminho, newline="", encoding="utf-8") as arquivo:
        for linha in csv.DictReader(arquivo):
            execucoes.append({
                "experimento": linha["experimento"],
                "versao": linha["versao"],
                "linhas": int(linha["linhas"]),
                "colunas": int(linha["colunas"]),
                "geracoes": int(linha["geracoes"]),
                "percentual": float(linha["percentual"]),
                "trabalhadores": int(linha["trabalhadores"]),
                "tempo_s": float(linha["tempo_s"]),
                # Só a versão distribuída preenche estas duas colunas.
                "tempo_comunicacao_s": float(linha["tempo_comunicacao_s"]) if linha["tempo_comunicacao_s"] else None,
                "bytes_enviados": int(linha["bytes_enviados"]) if linha["bytes_enviados"] else None,
            })
    return execucoes


def chave_do_cenario(execucao):
    """Identifica o cenário, sem a versão nem o número de trabalhadores."""
    return (execucao["experimento"], execucao["linhas"], execucao["colunas"],
            execucao["geracoes"], execucao["percentual"])


def media_ou_vazio(valores):
    valores = [valor for valor in valores if valor is not None]
    return statistics.mean(valores) if valores else None


def calcular_speedup(tempo_sequencial, tempo_versao):
    return tempo_sequencial / tempo_versao


def calcular_eficiencia(speedup, trabalhadores):
    return speedup / trabalhadores


def montar_resumo(execucoes):
    """Agrupa as repetições de cada configuração e calcula média, desvio
    padrão, speedup e eficiência. Devolve uma linha por configuração."""
    grupos = {}
    for execucao in execucoes:
        chave = chave_do_cenario(execucao) + (execucao["versao"], execucao["trabalhadores"])
        grupos.setdefault(chave, []).append(execucao)

    # Tempo médio da sequencial em cada cenário: é a base do speedup.
    tempo_sequencial = {}
    for chave, repeticoes in grupos.items():
        if chave[5] == "sequencial":
            tempo_sequencial[chave[:5]] = statistics.mean(r["tempo_s"] for r in repeticoes)

    resumo = []
    for chave, repeticoes in grupos.items():
        experimento, linhas, colunas, geracoes, percentual, versao, trabalhadores = chave
        tempos = [r["tempo_s"] for r in repeticoes]
        tempo_medio = statistics.mean(tempos)
        # O desvio padrão precisa de pelo menos duas medições.
        desvio = statistics.stdev(tempos) if len(tempos) > 1 else 0.0

        speedup = eficiencia = None
        if chave[:5] in tempo_sequencial:
            speedup = calcular_speedup(tempo_sequencial[chave[:5]], tempo_medio)
            eficiencia = calcular_eficiencia(speedup, trabalhadores)

        resumo.append({
            "experimento": experimento, "versao": versao, "linhas": linhas, "colunas": colunas,
            "geracoes": geracoes, "percentual": percentual, "trabalhadores": trabalhadores,
            "repeticoes": len(tempos), "tempo_medio_s": tempo_medio, "desvio_padrao_s": desvio,
            "speedup": speedup, "eficiencia": eficiencia,
            "tempo_comunicacao_medio_s": media_ou_vazio(r["tempo_comunicacao_s"] for r in repeticoes),
            "bytes_enviados_medio": media_ou_vazio(r["bytes_enviados"] for r in repeticoes),
        })
    return resumo


def formatar(valor, casas=4):
    if valor is None:
        return ""
    if isinstance(valor, float):
        return f"{valor:.{casas}f}"
    return str(valor)


def salvar_resumo(resumo, caminho):
    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS_RESUMO)
        escritor.writeheader()
        for linha in resumo:
            escritor.writerow({coluna: formatar(linha[coluna]) for coluna in COLUNAS_RESUMO})


def imprimir_resumo(resumo):
    print(f"{'experimento':<13} {'versao':<11} {'grade':>9} {'ger':>4} {'perc':>5} {'trab':>4} "
          f"{'rep':>3} {'tempo (s)':>10} {'desvio':>8} {'speedup':>8} {'eficiência':>10}")
    for linha in resumo:
        speedup = f"{linha['speedup']:.2f}" if linha["speedup"] is not None else "-"
        eficiencia = f"{linha['eficiencia']:.0%}" if linha["eficiencia"] is not None else "-"
        print(f"{linha['experimento']:<13} {linha['versao']:<11} "
              f"{str(linha['linhas']) + 'x' + str(linha['colunas']):>9} {linha['geracoes']:>4} "
              f"{linha['percentual']:>5.0%} {linha['trabalhadores']:>4} {linha['repeticoes']:>3} "
              f"{linha['tempo_medio_s']:>10.4f} {linha['desvio_padrao_s']:>8.4f} "
              f"{speedup:>8} {eficiencia:>10}")


def filtrar(resumo, experimento, versao, ordenar_por):
    linhas = [l for l in resumo if l["experimento"] == experimento and l["versao"] == versao]
    return sorted(linhas, key=lambda linha: linha[ordenar_por])


def descrever_cenario(linha, experimento):
    """Descreve os parâmetros que ficam fixos no experimento (o que varia já
    aparece no eixo x) e quantas repetições entraram na média."""
    partes = []
    if experimento != "tamanho":
        partes.append(f"Grade {linha['linhas']}x{linha['colunas']}")
    if experimento != "geracoes":
        partes.append(f"{linha['geracoes']} gerações")
    if experimento != "percentual":
        partes.append(f"{linha['percentual']:.0%} de espalhadores iniciais")
    return ", ".join(partes) + f" · média de {linha['repeticoes']} repetições"


def novo_grafico(titulo, subtitulo, rotulo_x, rotulo_y):
    """Cria a figura com o estilo comum a todos os gráficos: título, subtítulo
    com o cenário, eixos nomeados com unidade e grade discreta."""
    figura, eixo = plt.subplots(figsize=(8, 5), layout="constrained")
    figura.suptitle(titulo, x=0.01, ha="left", fontsize=14, fontweight="bold", color=COR_TEXTO)
    eixo.set_title(subtitulo, loc="left", fontsize=10, color=COR_TEXTO_SECUNDARIO)
    eixo.set_xlabel(rotulo_x, color=COR_TEXTO_SECUNDARIO)
    eixo.set_ylabel(rotulo_y, color=COR_TEXTO_SECUNDARIO)
    eixo.margins(y=0.1)  # folga para o ponto mais alto não encostar na borda
    eixo.grid(True, color=COR_GRADE, linewidth=0.8)
    eixo.set_axisbelow(True)
    for lado in ("top", "right"):
        eixo.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        eixo.spines[lado].set_color(COR_EIXO)
    eixo.tick_params(colors=COR_TEXTO_SECUNDARIO)
    return figura, eixo


def desenhar_linha(eixo, versao, valores_x, valores_y, desvios=None):
    estilo = ESTILO_VERSOES[versao]
    eixo.errorbar(valores_x, valores_y, yerr=desvios, label=estilo["nome"], color=estilo["cor"],
                  marker=estilo["marcador"], markersize=7, markeredgecolor="white",
                  markeredgewidth=1.5, linewidth=2, capsize=3)


def salvar_grafico(figura, nome_arquivo):
    caminho = os.path.join(PASTA_GRAFICOS, nome_arquivo)
    figura.savefig(caminho, dpi=150, facecolor="white")
    plt.close(figura)
    print(f"Gráfico gerado: {caminho}")


def versoes_paralelas_com_dados(resumo, experimento):
    return [versao for versao in ESTILO_VERSOES
            if versao != "sequencial" and filtrar(resumo, experimento, versao, "trabalhadores")]


def grafico_tempo_por_trabalhadores(resumo):
    versoes = versoes_paralelas_com_dados(resumo, "trabalhadores")
    sequencial = filtrar(resumo, "trabalhadores", "sequencial", "trabalhadores")
    if not versoes or not sequencial:
        print("Pulando tempo_por_trabalhadores.png: faltam medições da sequencial ou de versões paralelas.")
        return

    referencia = sequencial[0]
    figura, eixo = novo_grafico("Tempo de execução por número de trabalhadores",
                                descrever_cenario(referencia, "trabalhadores") +
                                "\nBarras verticais = desvio padrão",
                                "Número de trabalhadores (threads, processos ou nós)",
                                "Tempo de execução (s)")
    for versao in versoes:
        linhas = filtrar(resumo, "trabalhadores", versao, "trabalhadores")
        desenhar_linha(eixo, versao, [l["trabalhadores"] for l in linhas],
                       [l["tempo_medio_s"] for l in linhas], [l["desvio_padrao_s"] for l in linhas])

    # A sequencial não depende do número de trabalhadores: vira uma linha de referência.
    estilo = ESTILO_VERSOES["sequencial"]
    eixo.axhline(referencia["tempo_medio_s"], color=estilo["cor"], linewidth=1.5,
                 label=f"{estilo['nome']} ({referencia['tempo_medio_s']:.2f} s)")

    todos_trabalhadores = sorted({l["trabalhadores"] for l in resumo if l["experimento"] == "trabalhadores"})
    eixo.set_xticks(todos_trabalhadores)
    eixo.set_ylim(bottom=0)
    eixo.legend(frameon=False)
    salvar_grafico(figura, "tempo_por_trabalhadores.png")


def rotular_ultimo_ponto(eixo, x, y, texto):
    eixo.annotate(texto, (x, y), xytext=(8, 0), textcoords="offset points",
                  va="center", fontsize=9, color=COR_TEXTO)


def grafico_speedup(resumo):
    versoes = versoes_paralelas_com_dados(resumo, "trabalhadores")
    if not versoes or not filtrar(resumo, "trabalhadores", "sequencial", "trabalhadores"):
        print("Pulando speedup.png: faltam medições da sequencial ou de versões paralelas.")
        return

    referencia = filtrar(resumo, "trabalhadores", versoes[0], "trabalhadores")[0]
    figura, eixo = novo_grafico("Speedup em relação à versão sequencial",
                                descrever_cenario(referencia, "trabalhadores") +
                                "\nS(p) = T_sequencial / T(p)",
                                "Número de trabalhadores (p)", "Speedup S(p)")
    todos_trabalhadores = sorted({l["trabalhadores"] for l in resumo if l["experimento"] == "trabalhadores"})
    eixo.plot(todos_trabalhadores, todos_trabalhadores, color=COR_IDEAL, linewidth=1.5,
              linestyle="--", label="Ideal: S(p) = p")

    for versao in versoes:
        linhas = filtrar(resumo, "trabalhadores", versao, "trabalhadores")
        x = [l["trabalhadores"] for l in linhas]
        y = [l["speedup"] for l in linhas]
        desenhar_linha(eixo, versao, x, y)
        rotular_ultimo_ponto(eixo, x[-1], y[-1], f"{y[-1]:.2f}x")

    eixo.set_xticks(todos_trabalhadores)
    eixo.set_ylim(bottom=0)
    eixo.legend(frameon=False, loc="upper left")
    salvar_grafico(figura, "speedup.png")


def grafico_eficiencia(resumo):
    versoes = versoes_paralelas_com_dados(resumo, "trabalhadores")
    if not versoes or not filtrar(resumo, "trabalhadores", "sequencial", "trabalhadores"):
        print("Pulando eficiencia.png: faltam medições da sequencial ou de versões paralelas.")
        return

    referencia = filtrar(resumo, "trabalhadores", versoes[0], "trabalhadores")[0]
    figura, eixo = novo_grafico("Eficiência do uso dos trabalhadores",
                                descrever_cenario(referencia, "trabalhadores") +
                                "\nE(p) = S(p) / p",
                                "Número de trabalhadores (p)", "Eficiência E(p) (%)")
    eixo.axhline(100, color=COR_IDEAL, linewidth=1.5, linestyle="--", label="Ideal: 100%")

    for versao in versoes:
        linhas = filtrar(resumo, "trabalhadores", versao, "trabalhadores")
        x = [l["trabalhadores"] for l in linhas]
        y = [l["eficiencia"] * 100 for l in linhas]
        desenhar_linha(eixo, versao, x, y)
        rotular_ultimo_ponto(eixo, x[-1], y[-1], f"{y[-1]:.0f}%")

    todos_trabalhadores = sorted({l["trabalhadores"] for l in resumo if l["experimento"] == "trabalhadores"})
    eixo.set_xticks(todos_trabalhadores)
    eixo.set_ylim(bottom=0)
    eixo.legend(frameon=False)
    salvar_grafico(figura, "eficiencia.png")


def grafico_tempo_por_parametro(resumo, experimento, titulo, rotulo_x, valor_x, texto_x, nome_arquivo):
    """Tempo de cada versão conforme um parâmetro do cenário varia.

    `valor_x(linha)` diz onde o ponto fica no eixo x e `texto_x(linha)` o
    rótulo daquele ponto (por exemplo, "500x500" no lugar de 250000 células).
    """
    versoes = [versao for versao in ESTILO_VERSOES if filtrar(resumo, experimento, versao, "linhas")]
    if not versoes:
        print(f"Pulando {nome_arquivo}: não há medições do experimento '{experimento}'.")
        return

    linhas_experimento = [l for l in resumo if l["experimento"] == experimento]
    trabalhadores_paralelos = sorted({l["trabalhadores"] for l in linhas_experimento if l["versao"] != "sequencial"})
    subtitulo = descrever_cenario(linhas_experimento[0], experimento) + "\nBarras verticais = desvio padrão"
    if trabalhadores_paralelos:
        subtitulo += f" · {', '.join(map(str, trabalhadores_paralelos))} trabalhadores nas versões paralelas"
    figura, eixo = novo_grafico(titulo, subtitulo, rotulo_x, "Tempo de execução (s)")

    for versao in versoes:
        linhas = sorted(filtrar(resumo, experimento, versao, "linhas"), key=valor_x)
        desenhar_linha(eixo, versao, [valor_x(l) for l in linhas],
                       [l["tempo_medio_s"] for l in linhas], [l["desvio_padrao_s"] for l in linhas])

    pontos = sorted({(valor_x(l), texto_x(l)) for l in linhas_experimento})
    eixo.set_xticks([valor for valor, _ in pontos], [texto for _, texto in pontos])
    eixo.set_ylim(bottom=0)
    eixo.legend(frameon=False)
    salvar_grafico(figura, nome_arquivo)


def grafico_comunicacao(resumo):
    """Divide o tempo da versão distribuída em cálculo e comunicação.

    Usa o tempo de comunicação medido pela própria versão distribuída. Se ela
    não informar esse tempo, mostra a diferença T_distribuída - T_processos
    para o mesmo número de trabalhadores, deixando claro no título que é uma
    estimativa (as duas versões fazem o mesmo cálculo; o que muda é a troca de
    mensagens por socket).
    """
    distribuida = filtrar(resumo, "trabalhadores", "distribuida", "trabalhadores")
    if not distribuida:
        print("Pulando comunicacao.png: não há medições da versão distribuída.")
        return

    referencia = distribuida[0]
    trabalhadores = [l["trabalhadores"] for l in distribuida]
    posicoes = range(len(trabalhadores))

    if all(l["tempo_comunicacao_medio_s"] is not None for l in distribuida):
        comunicacao = [l["tempo_comunicacao_medio_s"] for l in distribuida]
        calculo = [l["tempo_medio_s"] - c for l, c in zip(distribuida, comunicacao)]
        figura, eixo = novo_grafico("Custo de comunicação na versão distribuída",
                                    descrever_cenario(referencia, "trabalhadores") +
                                    "\nComunicação = média, entre os trabalhadores, do tempo gasto trocando fronteiras",
                                    "Número de trabalhadores (p)", "Tempo de execução (s)")
        # A borda branca deixa um espaço entre as duas partes da barra.
        eixo.bar(posicoes, calculo, width=0.5, color=ESTILO_VERSOES["distribuida"]["cor"],
                 edgecolor="white", linewidth=1.5, label="Cálculo e demais etapas")
        eixo.bar(posicoes, comunicacao, width=0.5, bottom=calculo, color=COR_COMUNICACAO,
                 edgecolor="white", linewidth=1.5, label="Comunicação (envio, recepção e espera)")
        for posicao, linha, c in zip(posicoes, distribuida, comunicacao):
            eixo.annotate(f"{c / linha['tempo_medio_s']:.0%} comunicação", (posicao, linha["tempo_medio_s"]),
                          xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9, color=COR_TEXTO)
    else:
        processos = {l["trabalhadores"]: l for l in filtrar(resumo, "trabalhadores", "processos", "trabalhadores")}
        if not all(p in processos for p in trabalhadores):
            print("Pulando comunicacao.png: a distribuída não informou o tempo de comunicação "
                  "e não há medições de processos para comparar.")
            return
        diferenca = [l["tempo_medio_s"] - processos[l["trabalhadores"]]["tempo_medio_s"] for l in distribuida]
        figura, eixo = novo_grafico("Estimativa do custo de comunicação na versão distribuída",
                                    descrever_cenario(referencia, "trabalhadores") +
                                    "\nEstimativa = T_distribuída(p) - T_processos(p)",
                                    "Número de trabalhadores (p)", "Tempo extra da distribuída (s)")
        eixo.bar(posicoes, diferenca, width=0.5, color=COR_COMUNICACAO, label="T_distribuída - T_processos")
        eixo.axhline(0, color=COR_EIXO, linewidth=1)

    eixo.set_xticks(list(posicoes), [str(p) for p in trabalhadores])
    eixo.legend(frameon=False)
    salvar_grafico(figura, "comunicacao.png")


def analisar_argumentos():
    analisador = argparse.ArgumentParser(description="Gera a tabela-resumo e os gráficos a partir do CSV de tempos.")
    analisador.add_argument("--maquina", default="local",
                            help="Mesmo nome usado em executar_experimentos.py.")
    return analisador.parse_args()


def main():
    argumentos = analisar_argumentos()
    caminho_tempos = os.path.join(PASTA_RESULTADOS, f"tempos_{argumentos.maquina}.csv")
    if not os.path.exists(caminho_tempos):
        sys.exit(f"{caminho_tempos} não existe. Rode antes experimentos/executar_experimentos.py.")

    resumo = montar_resumo(ler_tempos(caminho_tempos))
    caminho_resumo = os.path.join(PASTA_RESULTADOS, f"resumo_{argumentos.maquina}.csv")
    salvar_resumo(resumo, caminho_resumo)
    imprimir_resumo(resumo)
    print(f"\nTabela-resumo gravada em {caminho_resumo}\n")

    os.makedirs(PASTA_GRAFICOS, exist_ok=True)
    grafico_tempo_por_trabalhadores(resumo)
    grafico_speedup(resumo)
    grafico_eficiencia(resumo)
    grafico_tempo_por_parametro(
        resumo, "tamanho", "Tempo de execução por tamanho da grade", "Tamanho da grade (células)",
        valor_x=lambda l: l["linhas"] * l["colunas"],
        texto_x=lambda l: f"{l['linhas']}x{l['colunas']}",
        nome_arquivo="tempo_por_tamanho.png")
    grafico_tempo_por_parametro(
        resumo, "geracoes", "Tempo de execução por número de gerações", "Número de gerações",
        valor_x=lambda l: l["geracoes"], texto_x=lambda l: str(l["geracoes"]),
        nome_arquivo="tempo_por_geracoes.png")
    grafico_tempo_por_parametro(
        resumo, "percentual", "Tempo de execução por percentual inicial de espalhadores",
        "Espalhadores na grade inicial (%)",
        valor_x=lambda l: l["percentual"] * 100, texto_x=lambda l: f"{l['percentual']:.0%}",
        nome_arquivo="tempo_por_percentual.png")
    grafico_comunicacao(resumo)


if __name__ == "__main__":
    main()

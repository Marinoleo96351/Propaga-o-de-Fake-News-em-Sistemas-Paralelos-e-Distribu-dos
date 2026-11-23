"""Melhoria: visualização animada da propagação da fake news.

Roda a simulação numa grade pequena, guarda a grade de cada geração e monta
uma animação com o matplotlib: cada célula é um quadradinho colorido pelo
estado da pessoa. O cálculo é o mesmo das outras versões
(`comum.modelo.calcular_intervalo`, chamado por `rodar_simulacao_com_bots`);
a animação só desenha o resultado.

Uso, a partir da pasta raiz do projeto (o matplotlib está no .venv):
    .venv/bin/python melhorias/animacao.py                          # salva melhorias/saidas/propagacao.gif
    .venv/bin/python melhorias/animacao.py --percentual-bots 0.005 --saida melhorias/saidas/propagacao_bots.gif
    .venv/bin/python melhorias/animacao.py --mostrar                # abre uma janela (demonstração ao vivo)
"""

import argparse
import os
import sys

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PASTA_PROJETO)

from comum.grade import carregar_grade, criar_grade
from comum.modelo import ESPALHADOR, IGNORANTE, INATIVO
from melhorias.bots import rodar_simulacao_com_bots, sortear_bots

# Na simulação o bot é um Espalhador comum; o valor 3 existe só no desenho,
# para o bot aparecer com uma cor própria.
BOT_NO_DESENHO = 3

# Cores na ordem dos valores 0, 1, 2 e 3 da grade desenhada.
CORES = ["#f0efec", "#e34948", "#86b6ef", "#0b0b0b"]
NOMES = ["Ignorante", "Espalhador", "Inativo", "Bot"]

QUADROS_POR_SEGUNDO = 5


def montar_imagem(grade, linhas, colunas, bots):
    """Converte a grade (um bytearray) em uma lista de linhas para o imshow."""
    valores = list(grade)
    for indice in bots:
        valores[indice] = BOT_NO_DESENHO
    return [valores[linha * colunas:(linha + 1) * colunas] for linha in range(linhas)]


def descrever_geracao(numero, grade, quantidade_bots):
    pessoas = len(grade) - quantidade_bots
    ignorantes = grade.count(IGNORANTE)
    espalhadores = grade.count(ESPALHADOR) - quantidade_bots
    inativos = grade.count(INATIVO)
    titulo = "Grade inicial" if numero == 0 else f"Geração {numero}"
    return (f"{titulo}\nIgnorantes {ignorantes / pessoas:.0%} · espalhadores {espalhadores / pessoas:.0%} · "
            f"inativos {inativos / pessoas:.0%}")


def criar_animacao(grades, linhas, colunas, bots, descricao_cenario):
    figura, eixo = plt.subplots(figsize=(6, 6.8), layout="constrained")
    figura.suptitle("Propagação da fake news", fontsize=14, fontweight="bold")
    eixo.set_xticks([])
    eixo.set_yticks([])

    mapa_de_cores = ListedColormap(CORES)
    imagem = eixo.imshow(montar_imagem(grades[0], linhas, colunas, bots), cmap=mapa_de_cores,
                         vmin=0, vmax=len(CORES) - 1, interpolation="nearest")

    quantidade_de_estados = 4 if bots else 3
    legenda = [Patch(facecolor=CORES[i], edgecolor="#c3c2b7", label=NOMES[i])
               for i in range(quantidade_de_estados)]
    eixo.legend(handles=legenda, loc="upper center", bbox_to_anchor=(0.5, -0.02),
                ncol=quantidade_de_estados, frameon=False)
    eixo.set_xlabel(descricao_cenario, labelpad=30, color="#52514e", fontsize=9)

    def atualizar(numero):
        imagem.set_data(montar_imagem(grades[numero], linhas, colunas, bots))
        eixo.set_title(descrever_geracao(numero, grades[numero], len(bots)), fontsize=10)
        return [imagem]

    # O último quadro se repete por 2 segundos, para o estado final ficar
    # visível antes de a animação recomeçar.
    ultimo = len(grades) - 1
    quadros = list(range(len(grades))) + [ultimo] * (2 * QUADROS_POR_SEGUNDO)

    atualizar(0)
    animacao = FuncAnimation(figura, atualizar, frames=quadros, interval=1000 // QUADROS_POR_SEGUNDO)
    return figura, animacao


def analisar_argumentos():
    analisador = argparse.ArgumentParser(description="Gera uma animação da propagação da fake news.")
    analisador.add_argument("--linhas", type=int, default=100)
    analisador.add_argument("--colunas", type=int, default=100)
    analisador.add_argument("--geracoes", type=int, default=60)
    analisador.add_argument("--percentual", type=float, default=0.05,
                            help="Percentual inicial de espalhadores (0 a 1).")
    analisador.add_argument("--percentual-bots", dest="percentual_bots", type=float, default=0.0,
                            help="Percentual das células ocupadas por bots (0 = modelo original).")
    analisador.add_argument("--limiar", type=int, default=2,
                            help="Vizinhos espalhadores necessários para convencer um ignorante.")
    analisador.add_argument("--semente", type=int, default=42)
    analisador.add_argument("--arquivo-grade", dest="arquivo_grade", type=str, default=None,
                            help="Carrega a grade inicial deste arquivo em vez de sortear uma nova.")
    analisador.add_argument("--saida", default=os.path.join(PASTA_PROJETO, "melhorias", "saidas", "propagacao.gif"),
                            help="Arquivo GIF a ser gravado.")
    analisador.add_argument("--mostrar", action="store_true",
                            help="Abre a animação numa janela em vez de gravar o GIF.")
    return analisador.parse_args()


def main():
    argumentos = analisar_argumentos()

    if argumentos.arquivo_grade:
        grade_inicial, linhas, colunas = carregar_grade(argumentos.arquivo_grade)
    else:
        linhas, colunas = argumentos.linhas, argumentos.colunas
        grade_inicial = criar_grade(linhas, colunas, argumentos.percentual, argumentos.semente)

    bots = []
    if argumentos.percentual_bots > 0:
        # Mesma regra de melhorias/bots.py: semente da grade + 1.
        bots = sortear_bots(linhas, colunas, argumentos.percentual_bots, argumentos.semente + 1)

    _, _, grades = rodar_simulacao_com_bots(grade_inicial, linhas, colunas, argumentos.geracoes,
                                            argumentos.limiar, bots, guardar_grades=True)

    descricao = (f"Grade {linhas}x{colunas} · {argumentos.percentual:.0%} de espalhadores iniciais · "
                 f"limiar {argumentos.limiar}")
    if bots:
        descricao += f" · {len(bots)} bots"
    figura, animacao = criar_animacao(grades, linhas, colunas, bots, descricao)

    if argumentos.mostrar:
        plt.show()
    else:
        os.makedirs(os.path.dirname(os.path.abspath(argumentos.saida)), exist_ok=True)
        animacao.save(argumentos.saida, writer=PillowWriter(fps=QUADROS_POR_SEGUNDO))
        plt.close(figura)
        print(f"{len(grades) - 1} gerações animadas em {argumentos.saida}")


if __name__ == "__main__":
    main()

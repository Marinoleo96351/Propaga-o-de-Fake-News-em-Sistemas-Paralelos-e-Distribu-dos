"""Compara threads e processos na mesma máquina e grava medições em CSV."""
import argparse
import csv
import statistics
import sys
import time
from pathlib import Path

# Permite executar o arquivo diretamente a partir da pasta do projeto.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comum.grade import criar_grade
from paralelo_processos import rodar_simulacao as rodar_processos
from paralelo_threads import rodar_simulacao as rodar_threads


def medir(metodo, trabalhadores, grade, linhas, colunas, geracoes, limiar,
          probabilidade, semente):
    inicio = time.perf_counter()
    if metodo == "threads":
        rodar_threads(grade, linhas, colunas, geracoes, limiar,
                      trabalhadores, False, probabilidade, semente)
    else:
        rodar_processos(grade, linhas, colunas, geracoes, limiar,
                        trabalhadores, False, probabilidade=probabilidade,
                        semente=semente)
    return time.perf_counter() - inicio


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linhas", type=int, default=100)
    parser.add_argument("--colunas", type=int, default=100)
    parser.add_argument("--geracoes", type=int, default=20)
    parser.add_argument("--percentual", type=float, default=0.05)
    parser.add_argument("--limiar", type=int, default=2)
    parser.add_argument("--probabilidade", type=float, default=1.0)
    parser.add_argument("--semente", type=int, default=42)
    parser.add_argument("--repeticoes", type=int, default=3)
    parser.add_argument("--trabalhadores", type=int, nargs="+", default=[1, 2, 4])
    parser.add_argument("--saida", default="experimentos/tempos_paralelismo.csv")
    args = parser.parse_args()

    if args.repeticoes < 1 or any(n < 1 for n in args.trabalhadores):
        parser.error("repeticoes e trabalhadores precisam ser positivos")
    if 1 not in args.trabalhadores:
        parser.error("inclua 1 em --trabalhadores para calcular o speedup base")
    if not 0.0 <= args.probabilidade <= 1.0:
        parser.error("probabilidade precisa estar entre 0 e 1")

    grade = criar_grade(args.linhas, args.colunas, args.percentual, args.semente)
    resultados = []
    for metodo in ("threads", "processos"):
        for trabalhadores in args.trabalhadores:
            for repeticao in range(1, args.repeticoes + 1):
                duracao = medir(metodo, trabalhadores, grade, args.linhas,
                                args.colunas, args.geracoes, args.limiar,
                                args.probabilidade, args.semente)
                resultados.append({
                    "metodo": metodo,
                    "trabalhadores": trabalhadores,
                    "repeticao": repeticao,
                    "tempo_s": duracao,
                })

    medianas = {}
    for metodo in ("threads", "processos"):
        for trabalhadores in args.trabalhadores:
            tempos = [r["tempo_s"] for r in resultados
                      if r["metodo"] == metodo and r["trabalhadores"] == trabalhadores]
            medianas[(metodo, trabalhadores)] = statistics.median(tempos)

    campos = ("metodo", "trabalhadores", "repeticao", "tempo_s",
              "mediana_s", "speedup_vs_1", "eficiencia")
    with open(args.saida, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        for resultado in resultados:
            metodo = resultado["metodo"]
            trabalhadores = resultado["trabalhadores"]
            mediana = medianas[(metodo, trabalhadores)]
            base = medianas[(metodo, 1)]
            escritor.writerow({
                **resultado,
                "mediana_s": f"{mediana:.6f}",
                "speedup_vs_1": f"{base / mediana:.4f}",
                "eficiencia": f"{base / mediana / trabalhadores:.4f}",
                "tempo_s": f"{resultado['tempo_s']:.6f}",
            })

    print(f"Medições gravadas em {args.saida}")
    for metodo in ("threads", "processos"):
        base = medianas[(metodo, 1)]
        for trabalhadores in args.trabalhadores:
            mediana = medianas[(metodo, trabalhadores)]
            print(f"{metodo:9} {trabalhadores:2} trabalhador(es): "
                  f"mediana={mediana:.4f}s speedup={base / mediana:.2f}x "
                  f"eficiência={base / mediana / trabalhadores:.2f}")


if __name__ == "__main__":
    main()


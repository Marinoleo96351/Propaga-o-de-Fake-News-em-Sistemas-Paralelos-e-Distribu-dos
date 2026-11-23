"""Versão paralela com threads. Uso: python paralelo_threads.py --ajuda"""
import argparse
import threading
import time

from comum.grade import carregar_grade, criar_grade, salvar_grade
from comum.modelo import ESPALHADOR, calcular_intervalo
from comum.probabilidade import calcular_intervalo_probabilistico


def faixas_de_linhas(linhas, trabalhadores):
    return [(i * linhas // trabalhadores, (i + 1) * linhas // trabalhadores)
            for i in range(trabalhadores)]


def rodar_simulacao(grade_inicial, linhas, colunas, geracoes, limiar_convencimento,
                     trabalhadores=2, parar_quando_nao_ha_espalhador=True,
                     probabilidade=1.0, semente=42):
    if trabalhadores < 1:
        raise ValueError("trabalhadores precisa ser pelo menos 1")
    if geracoes < 0 or linhas < 1 or colunas < 1:
        raise ValueError("dimensões precisam ser positivas e geracoes não pode ser negativa")
    if len(grade_inicial) != linhas * colunas:
        raise ValueError("dimensões não correspondem ao tamanho da grade")
    if not 0.0 <= probabilidade <= 1.0:
        raise ValueError("probabilidade precisa estar entre 0 e 1")
    if geracoes == 0:
        return [], bytearray(grade_inicial)
    buffers = [bytearray(grade_inicial), bytearray(len(grade_inicial))]
    faixas = faixas_de_linhas(linhas, trabalhadores)
    resultados = [(0, 0, 0)] * trabalhadores
    barreira = threading.Barrier(trabalhadores)
    geracao = [0]
    terminou = [False]
    historico = []

    def trabalhador(indice):
        inicio, fim = faixas[indice]
        while True:
            atual = buffers[geracao[0] % 2]
            proxima = buffers[1 - geracao[0] % 2]
            if probabilidade == 1.0:
                resultados[indice] = calcular_intervalo(
                    atual, proxima, linhas, colunas, inicio, fim, limiar_convencimento
                )
            else:
                resultados[indice] = calcular_intervalo_probabilistico(
                    atual, proxima, linhas, colunas, inicio, fim,
                    limiar_convencimento, probabilidade, semente, geracao[0] + 1
                )
            barreira.wait()
            if indice == 0:
                geracao[0] += 1
                historico.append(tuple(sum(parte[e] for parte in resultados) for e in range(3)))
                terminou[0] = geracao[0] >= geracoes or (
                    parar_quando_nao_ha_espalhador and historico[-1][1] == 0
                )
            barreira.wait()
            if terminou[0]:
                break

    threads = [threading.Thread(target=trabalhador, args=(i,), name=f"thread-{i}")
               for i in range(trabalhadores)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return historico, bytearray(buffers[len(historico) % 2])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--linhas", type=int, default=100)
    p.add_argument("--colunas", type=int, default=100)
    p.add_argument("--geracoes", type=int, default=50)
    p.add_argument("--percentual", type=float, default=0.05)
    p.add_argument("--limiar", type=int, default=2)
    p.add_argument("--semente", type=int, default=42)
    p.add_argument("--probabilidade", type=float, default=1.0,
                   help="Chance de cada contato espalhador convencer (0 a 1).")
    p.add_argument("--trabalhadores", type=int, default=2)
    p.add_argument("--arquivo-grade")
    p.add_argument("--salvar-grade")
    p.add_argument("--sem-parada-antecipada", action="store_true")
    p.add_argument("--sem-impressao", action="store_true")
    a = p.parse_args()
    if a.arquivo_grade:
        grade, linhas, colunas = carregar_grade(a.arquivo_grade)
    else:
        linhas, colunas = a.linhas, a.colunas
        grade = criar_grade(linhas, colunas, a.percentual, a.semente)
        if not a.sem_impressao:
            print(f"Espalhadores iniciais: {grade.count(ESPALHADOR)}")
    if a.salvar_grade:
        salvar_grade(grade, linhas, colunas, a.salvar_grade)
    inicio = time.perf_counter()
    historico, _ = rodar_simulacao(grade, linhas, colunas, a.geracoes, a.limiar,
        a.trabalhadores, not a.sem_parada_antecipada, a.probabilidade, a.semente)
    duracao = time.perf_counter() - inicio
    if not a.sem_impressao:
        for i, c in enumerate(historico, 1):
            print(f"Geração {i}: ignorantes={c[0]} espalhadores={c[1]} inativos={c[2]}")
    print(f"Gerações executadas: {len(historico)}")
    print(f"Tempo total: {duracao:.6f} s")


if __name__ == "__main__":
    main()

"""Versão com multiprocessing e grades em memória compartilhada.

Os processos são criados uma vez e reutilizados em todas as gerações.
"""
import argparse
import multiprocessing as mp
from multiprocessing import shared_memory
import time

from comum.grade import carregar_grade, criar_grade, salvar_grade
from comum.modelo import ESPALHADOR, calcular_intervalo
from comum.probabilidade import calcular_intervalo_probabilistico


def faixas_de_linhas(linhas, trabalhadores):
    return [(i * linhas // trabalhadores, (i + 1) * linhas // trabalhadores)
            for i in range(trabalhadores)]


def _trabalhador(nome_a, nome_b, linhas, colunas, geracoes, limiar, faixa,
                 indice, trabalhadores, contagens, barreira, parar_antecipado,
                 probabilidade, semente):
    mem_a = shared_memory.SharedMemory(name=nome_a)
    mem_b = shared_memory.SharedMemory(name=nome_b)
    try:
        a = memoryview(mem_a.buf)[:linhas * colunas]
        b = memoryview(mem_b.buf)[:linhas * colunas]
        inicio, fim = faixa
        for geracao in range(geracoes):
            origem, destino = (a, b) if geracao % 2 == 0 else (b, a)
            if probabilidade == 1.0:
                contagem = calcular_intervalo(origem, destino, linhas, colunas,
                                               inicio, fim, limiar)
            else:
                contagem = calcular_intervalo_probabilistico(
                    origem, destino, linhas, colunas, inicio, fim, limiar,
                    probabilidade, semente, geracao + 1
                )
            base = geracao * trabalhadores * 3 + indice * 3
            contagens[base:base + 3] = contagem
            # Barreira de geração: todos terminaram de escrever antes da redução.
            barreira.wait()
            total_espalhadores = sum(
                contagens[geracao * trabalhadores * 3 + p * 3 + 1]
                for p in range(trabalhadores)
            )
            if parar_antecipado and total_espalhadores == 0:
                break
    finally:
        a.release()
        b.release()
        mem_a.close()
        mem_b.close()


def rodar_simulacao(grade_inicial, linhas, colunas, geracoes, limiar_convencimento,
                     trabalhadores=2, parar_quando_nao_ha_espalhador=True,
                     metodo="spawn", probabilidade=1.0, semente=42):
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
    ctx = mp.get_context(metodo)
    mem_a = shared_memory.SharedMemory(create=True, size=len(grade_inicial))
    mem_b = shared_memory.SharedMemory(create=True, size=len(grade_inicial))
    mem_a.buf[:len(grade_inicial)] = grade_inicial
    contagens = ctx.Array("Q", max(1, geracoes * trabalhadores * 3), lock=False)
    barreira = ctx.Barrier(trabalhadores)
    processos = []
    try:
        faixas = faixas_de_linhas(linhas, trabalhadores)
        for i, faixa in enumerate(faixas):
            processo = ctx.Process(
                target=_trabalhador,
                args=(mem_a.name, mem_b.name, linhas, colunas, geracoes,
                      limiar_convencimento, faixa, i, trabalhadores,
                      contagens, barreira, parar_quando_nao_ha_espalhador,
                      probabilidade, semente),
                name=f"processo-{i}",
            )
            processo.start()
            processos.append(processo)
        for processo in processos:
            processo.join()
        falhas = [(p.name, p.exitcode) for p in processos if p.exitcode != 0]
        if falhas:
            raise RuntimeError(f"Falha em processos trabalhadores: {falhas}")
        historico = []
        for g in range(geracoes):
            base = g * trabalhadores * 3
            total = tuple(sum(contagens[base + p * 3 + e]
                              for p in range(trabalhadores)) for e in range(3))
            historico.append(total)
            if parar_quando_nao_ha_espalhador and total[1] == 0:
                break
        memoria_final = mem_b if len(historico) % 2 else mem_a
        final = bytearray(memoria_final.buf[:len(grade_inicial)])
        return historico, final
    finally:
        for processo in processos:
            if processo.is_alive():
                processo.terminate()
                processo.join()
        mem_a.close()
        mem_a.unlink()
        mem_b.close()
        mem_b.unlink()


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
        a.trabalhadores, not a.sem_parada_antecipada,
        probabilidade=a.probabilidade, semente=a.semente)
    duracao = time.perf_counter() - inicio
    if not a.sem_impressao:
        for i, c in enumerate(historico, 1):
            print(f"Geração {i}: ignorantes={c[0]} espalhadores={c[1]} inativos={c[2]}")
    print(f"Gerações executadas: {len(historico)}")
    print(f"Tempo total: {duracao:.6f} s")


if __name__ == "__main__":
    mp.freeze_support()
    main()

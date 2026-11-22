"""Criação, gravação e leitura da grade inicial da simulação.

A grade é um `bytearray` único (1 byte por célula), com índice
`linha * colunas + coluna`. Salvar e carregar de arquivo garante que todas as
versões (sequencial, paralela e distribuída) partam exatamente da mesma grade.
"""

import random
import struct

from comum.modelo import ESPALHADOR, IGNORANTE

_CABECALHO = struct.Struct("!II")  # linhas, colunas


def criar_grade(linhas, colunas, percentual_inicial, semente):
    """Cria uma grade com `percentual_inicial` de espalhadores sorteados.

    Usa `semente` fixa para que a mesma chamada sempre gere a mesma grade.
    O sorteio pode cair duas vezes na mesma célula, então o número real de
    espalhadores pode ser menor que `linhas * colunas * percentual_inicial`.
    """
    aleatorio = random.Random(semente)
    total_celulas = linhas * colunas
    grade = bytearray([IGNORANTE]) * total_celulas

    quantidade_espalhadores = int(total_celulas * percentual_inicial)
    for _ in range(quantidade_espalhadores):
        indice = aleatorio.randrange(total_celulas)
        grade[indice] = ESPALHADOR

    return grade


def salvar_grade(grade, linhas, colunas, caminho):
    """Grava a grade em arquivo: cabeçalho (linhas, colunas) seguido dos bytes."""
    with open(caminho, "wb") as arquivo:
        arquivo.write(_CABECALHO.pack(linhas, colunas))
        arquivo.write(grade)


def carregar_grade(caminho):
    """Lê uma grade salva por `salvar_grade`. Devolve (grade, linhas, colunas)."""
    with open(caminho, "rb") as arquivo:
        linhas, colunas = _CABECALHO.unpack(arquivo.read(_CABECALHO.size))
        grade = bytearray(arquivo.read(linhas * colunas))
    return grade, linhas, colunas

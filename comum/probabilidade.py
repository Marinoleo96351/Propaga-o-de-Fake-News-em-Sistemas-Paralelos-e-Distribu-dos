"""Regra probabilística reproduzível, independente do trabalhador responsável."""
from comum.modelo import IGNORANTE, ESPALHADOR, INATIVO, DESLOCAMENTOS_VIZINHANCA

_MASK = (1 << 64) - 1


def _mix64(valor):
    valor = (valor + 0x9E3779B97F4A7C15) & _MASK
    valor = ((valor ^ (valor >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
    valor = ((valor ^ (valor >> 27)) * 0x94D049BB133111EB) & _MASK
    return valor ^ (valor >> 31)


def _sorteio_64(semente, geracao, linha, coluna, vizinho):
    """Hash de contador: a mesma célula e contato sempre têm o mesmo sorteio."""
    x = _mix64(semente & _MASK)
    for valor in (geracao, linha, coluna, vizinho):
        x = _mix64(x ^ _mix64(valor & _MASK))
    return x


def calcular_intervalo_probabilistico(atual, proxima, linhas, colunas, inicio, fim,
                                       limiar_convencimento, probabilidade,
                                       semente, geracao):
    if not 0.0 <= probabilidade <= 1.0:
        raise ValueError("probabilidade precisa estar entre 0 e 1")
    limiar = int(probabilidade * (1 << 64))
    ignorantes = espalhadores = inativos = 0
    for linha in range(inicio, fim):
        base = linha * colunas
        for coluna in range(colunas):
            indice = base + coluna
            estado = atual[indice]
            if estado == IGNORANTE:
                convincentes = 0
                for numero, (dl, dc) in enumerate(DESLOCAMENTOS_VIZINHANCA):
                    vl, vc = linha + dl, coluna + dc
                    if 0 <= vl < linhas and 0 <= vc < colunas and \
                            atual[vl * colunas + vc] == ESPALHADOR:
                        if _sorteio_64(semente, geracao, linha, coluna, numero) < limiar:
                            convincentes += 1
                novo = ESPALHADOR if convincentes >= limiar_convencimento else IGNORANTE
            else:
                novo = INATIVO
            proxima[indice] = novo
            if novo == IGNORANTE:
                ignorantes += 1
            elif novo == ESPALHADOR:
                espalhadores += 1
            else:
                inativos += 1
    return ignorantes, espalhadores, inativos

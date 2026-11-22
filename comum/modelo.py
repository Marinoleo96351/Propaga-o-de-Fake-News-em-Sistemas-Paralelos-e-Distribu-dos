"""Regras do modelo de propagação de fake news (autômato celular).

Estados: 0 = Ignorante, 1 = Espalhador, 2 = Inativo.
Vizinhança de Moore (8 vizinhos); as bordas não dão a volta, então uma célula
da borda simplesmente tem menos vizinhos.

Esta é a única função de cálculo do projeto: a sequencial, a paralela (threads
e processos) e a distribuída chamam exatamente esta função, cada uma passando
o intervalo de linhas que lhe cabe.
"""

IGNORANTE = 0
ESPALHADOR = 1
INATIVO = 2

DESLOCAMENTOS_VIZINHANCA = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1), (0, 1),
    (1, -1), (1, 0), (1, 1),
)


def contar_vizinhos_espalhadores(atual, linhas, colunas, linha, coluna):
    """Conta vizinhos no estado Espalhador na vizinhança de Moore de uma célula."""
    total = 0
    for deslocamento_linha, deslocamento_coluna in DESLOCAMENTOS_VIZINHANCA:
        vizinho_linha = linha + deslocamento_linha
        vizinho_coluna = coluna + deslocamento_coluna
        if 0 <= vizinho_linha < linhas and 0 <= vizinho_coluna < colunas:
            if atual[vizinho_linha * colunas + vizinho_coluna] == ESPALHADOR:
                total += 1
    return total


def calcular_intervalo(atual, proxima, linhas, colunas, inicio, fim, limiar_convencimento):
    """Calcula a próxima geração para as linhas [inicio, fim) da grade `atual`.

    Lê somente de `atual` e escreve somente em `proxima`, nas linhas do
    intervalo recebido. Quando cada trabalhador recebe um intervalo que não
    se sobrepõe ao dos outros, não há condição de corrida.

    Devolve a contagem de cada estado (ignorantes, espalhadores, inativos)
    entre as linhas calculadas, para a redução feita depois pelo coordenador
    do cálculo (processo principal ou coordenador da versão distribuída).
    """
    contagem_ignorantes = 0
    contagem_espalhadores = 0
    contagem_inativos = 0

    for linha in range(inicio, fim):
        base = linha * colunas
        for coluna in range(colunas):
            indice = base + coluna
            estado = atual[indice]

            if estado == IGNORANTE:
                vizinhos_espalhadores = contar_vizinhos_espalhadores(
                    atual, linhas, colunas, linha, coluna
                )
                novo_estado = ESPALHADOR if vizinhos_espalhadores >= limiar_convencimento else IGNORANTE
            else:
                # Espalhador espalha por uma única geração e vira Inativo;
                # Inativo continua Inativo. O novo valor é o mesmo nos dois casos.
                novo_estado = INATIVO

            proxima[indice] = novo_estado

            if novo_estado == IGNORANTE:
                contagem_ignorantes += 1
            elif novo_estado == ESPALHADOR:
                contagem_espalhadores += 1
            else:
                contagem_inativos += 1

    return contagem_ignorantes, contagem_espalhadores, contagem_inativos

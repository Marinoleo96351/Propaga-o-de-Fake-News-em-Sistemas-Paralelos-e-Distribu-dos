"""Estatísticas da propagação calculadas a partir do histórico de contagens.

O histórico é a lista de (ignorantes, espalhadores, inativos) de cada geração,
o mesmo formato devolvido por `rodar_simulacao` da versão sequencial.
"""

from comum.modelo import ESPALHADOR, IGNORANTE, INATIVO


def resumir_historico(historico, total_celulas, quantidade_bots=0):
    """Resume a propagação em quatro números.

    Bots não são pessoas: ficam fora do total da população e não entram na
    contagem de espalhadores. Como no modelo uma pessoa espalha por uma única
    geração, os espalhadores de uma geração são exatamente as pessoas
    convencidas naquela geração.
    """
    total_pessoas = total_celulas - quantidade_bots
    ignorantes_finais = historico[-1][0]
    pessoas_espalhando = [espalhadores - quantidade_bots for _, espalhadores, _ in historico]

    pico = max(pessoas_espalhando)
    ultima_geracao_com_novos = 0
    for geracao, quantidade in enumerate(pessoas_espalhando, start=1):
        if quantidade > 0:
            ultima_geracao_com_novos = geracao

    return {
        "alcance": (total_pessoas - ignorantes_finais) / total_pessoas,
        "pico_espalhadores": pico,
        "geracao_pico": pessoas_espalhando.index(pico) + 1,
        "ultima_geracao_com_novos": ultima_geracao_com_novos,
    }


def contar_estados(grade):
    """Conta (ignorantes, espalhadores, inativos) direto na grade."""
    return grade.count(IGNORANTE), grade.count(ESPALHADOR), grade.count(INATIVO)


def percentuais_por_geracao(contagens, total_celulas, quantidade_bots=0):
    """Converte as contagens de cada geração em percentuais da população.

    Devolve três listas (ignorantes, espalhadores, inativos), em %. Os bots
    saem do total e dos espalhadores, como em `resumir_historico`.
    """
    total_pessoas = total_celulas - quantidade_bots
    ignorantes = [100 * i / total_pessoas for i, _, _ in contagens]
    espalhadores = [100 * (e - quantidade_bots) / total_pessoas for _, e, _ in contagens]
    inativos = [100 * n / total_pessoas for _, _, n in contagens]
    return ignorantes, espalhadores, inativos


"""Processo trabalhador da simulação distribuída."""

import argparse
import socket

from comum.modelo import calcular_intervalo
from distribuida.protocolo import (
    criar_mensagem,
    enviar_mensagem,
    receber_mensagem,
    codificar_grade,
    decodificar_grade,
)


def processar_tarefa(mensagem):
    """Calcula o intervalo recebido, utilizando linhas de fronteira."""

    colunas = mensagem["colunas"]
    linhas_locais = mensagem["linhas_locais"]
    inicio_local = mensagem["inicio_local"]
    fim_local = mensagem["fim_local"]

    inicio = mensagem["inicio"]
    fim = mensagem["fim"]
    limiar = mensagem["limiar"]

    grade_atual = decodificar_grade(mensagem["grade"])

    if len(grade_atual) != linhas_locais * colunas:
        raise ValueError("Tamanho da grade local incompatível.")

    if not (0 <= inicio_local < fim_local <= linhas_locais):
        raise ValueError("Intervalo local inválido.")

    grade_proxima = bytearray(linhas_locais * colunas)

    contagem = calcular_intervalo(
        grade_atual,
        grade_proxima,
        linhas_locais,
        colunas,
        inicio_local,
        fim_local,
        limiar,
    )

    resultado = bytearray()

    for linha in range(inicio_local, fim_local):
        inicio_linha = linha * colunas
        fim_linha = inicio_linha + colunas
        resultado.extend(grade_proxima[inicio_linha:fim_linha])

    return criar_mensagem(
        "RESULTADO",
        trabalhador=mensagem["trabalhador"],
        inicio=inicio,
        fim=fim,
        grade=codificar_grade(resultado),
        contagem=list(contagem),
    )


def executar_trabalhador(host, porta, identificador):
    """Conecta ao coordenador e aguarda tarefas."""

    with socket.create_connection((host, porta)) as conexao:
        enviar_mensagem(
            conexao,
            criar_mensagem(
                "REGISTRO",
                trabalhador=identificador,
            ),
        )

        while True:
            mensagem = receber_mensagem(conexao)

            if mensagem["tipo"] == "ENCERRAR":
                print(f"Trabalhador {identificador} encerrado.")
                break

            if mensagem["tipo"] != "TAREFA":
                raise ValueError("Tipo de mensagem inesperado.")

            resultado = processar_tarefa(mensagem)
            enviar_mensagem(conexao, resultado)

            print(
                f"Trabalhador {identificador}: "
                f"linhas {resultado['inicio']} até "
                f"{resultado['fim'] - 1} calculadas."
            )


def main():
    parser = argparse.ArgumentParser(
        description="Trabalhador da simulação distribuída."
    )

    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--porta", type=int, default=5000)
    parser.add_argument("--id", type=int, required=True)

    argumentos = parser.parse_args()

    executar_trabalhador(
        argumentos.host,
        argumentos.porta,
        argumentos.id,
    )


if __name__ == "__main__":
    main()

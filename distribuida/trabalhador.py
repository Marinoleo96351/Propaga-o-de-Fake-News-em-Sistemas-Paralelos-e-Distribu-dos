
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
    criar_mensagem_fronteira,
    extrair_linha_fronteira,
)


def iniciar_servidor(host, porta):
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((host, porta))
    servidor.listen(2)
    return servidor


def trocar_fronteiras(vizinhos, identificador, geracao, bloco, colunas):
    primeira = bloco[:colunas]
    ultima = bloco[-colunas:]

    for id_vizinho, conexao in vizinhos.items():
        linha = primeira if id_vizinho < identificador else ultima

        enviar_mensagem(
            conexao,
            criar_mensagem_fronteira(
                identificador,
                geracao,
                linha,
            ),
        )

    fronteiras = {}

    for id_vizinho, conexao in vizinhos.items():
        mensagem = receber_mensagem(conexao)

        fronteiras[id_vizinho] = extrair_linha_fronteira(
            mensagem,
            geracao,
            colunas,
        )

    esquerda = None
    direita = None

    for id_vizinho, linha in fronteiras.items():
        if id_vizinho < identificador:
            esquerda = linha
        else:
            direita = linha

    return esquerda, direita


def calcular_bloco(bloco, esquerda, direita, linhas, colunas, limiar):
    grade = bytearray()

    if esquerda is not None:
        grade.extend(esquerda)

    grade.extend(bloco)

    if direita is not None:
        grade.extend(direita)

    linhas_locais = len(grade) // colunas
    inicio = 1 if esquerda is not None else 0
    fim = inicio + linhas

    proxima = bytearray(len(grade))

    contagem = calcular_intervalo(
        grade,
        proxima,
        linhas_locais,
        colunas,
        inicio,
        fim,
        limiar,
    )

    resultado = bytearray()

    for linha in range(inicio, fim):
        inicio_linha = linha * colunas
        resultado.extend(proxima[inicio_linha:inicio_linha + colunas])

    return resultado, contagem


def executar_trabalhador(host, porta, identificador, porta_vizinho):
    servidor = iniciar_servidor(host, porta_vizinho)
    vizinhos = {}

    try:
        with socket.create_connection((host, porta)) as coordenador:
            enviar_mensagem(
                coordenador,
                criar_mensagem(
                    "REGISTRO",
                    trabalhador=identificador,
                    porta_vizinho=porta_vizinho,
                ),
            )

            configuracao = receber_mensagem(coordenador)

            if configuracao["tipo"] != "CONFIGURACAO":
                raise ValueError("Configuração inválida.")

            vizinhos_ids = configuracao["vizinhos"]
            portas = configuracao["portas"]

            # Conecta aos trabalhadores com ID maior.
            for id_vizinho in vizinhos_ids:
                if id_vizinho > identificador:
                    conexao = socket.create_connection(
                        (host, portas[str(id_vizinho)])
                    )

                    enviar_mensagem(
                        conexao,
                        criar_mensagem(
                            "VIZINHO",
                            trabalhador=identificador,
                        ),
                    )

                    vizinhos[id_vizinho] = conexao

            # Aceita conexões dos trabalhadores com ID menor.
            quantidade_esperada = sum(
                1 for id_vizinho in vizinhos_ids
                if id_vizinho < identificador
            )

            for _ in range(quantidade_esperada):
                conexao, _ = servidor.accept()
                mensagem = receber_mensagem(conexao)

                if mensagem["tipo"] != "VIZINHO":
                    conexao.close()
                    raise ValueError("Conexão de vizinho inválida.")

                id_vizinho = mensagem["trabalhador"]
                vizinhos[id_vizinho] = conexao

            while True:
                mensagem = receber_mensagem(coordenador)

                if mensagem["tipo"] == "ENCERRAR":
                    break

                if mensagem["tipo"] != "TAREFA":
                    raise ValueError("Tipo de mensagem inesperado.")

                colunas = mensagem["colunas"]
                linhas = mensagem["linhas"]
                geracoes = mensagem["geracoes"]
                limiar = mensagem["limiar"]

                bloco = decodificar_grade(mensagem["grade"])

                if len(bloco) != linhas * colunas:
                    raise ValueError("Tamanho do bloco incompatível.")

                contagem_total = [0, 0, 0]

                for geracao in range(1, geracoes + 1):
                    esquerda, direita = trocar_fronteiras(
                        vizinhos,
                        identificador,
                        geracao,
                        bloco,
                        colunas,
                    )

                    bloco, contagem = calcular_bloco(
                        bloco,
                        esquerda,
                        direita,
                        linhas,
                        colunas,
                        limiar,
                    )

                    for i in range(3):
                        contagem_total[i] += contagem[i]

                enviar_mensagem(
                    coordenador,
                    criar_mensagem(
                        "RESULTADO",
                        trabalhador=identificador,
                        grade=codificar_grade(bloco),
                        contagem=contagem_total,
                    ),
                )

    finally:
        for conexao in vizinhos.values():
            conexao.close()

        servidor.close()


def main():
    parser = argparse.ArgumentParser(
        description="Trabalhador da simulação distribuída."
    )

    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--porta", type=int, default=5000)
    parser.add_argument("--porta-vizinho", type=int, required=True)
    parser.add_argument("--id", type=int, required=True)

    args = parser.parse_args()

    executar_trabalhador(
        args.host,
        args.porta,
        args.id,
        args.porta_vizinho,
    )


if __name__ == "__main__":
    main()

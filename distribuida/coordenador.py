
"""Coordenador da simulação distribuída."""

import argparse
import socket

from comum.grade import criar_grade, salvar_grade
from distribuida.protocolo import (
    criar_mensagem,
    enviar_mensagem,
    receber_mensagem,
    codificar_grade,
    decodificar_grade,
)


def dividir_intervalos(linhas, quantidade_trabalhadores):
    if quantidade_trabalhadores < 1 or quantidade_trabalhadores > linhas:
        raise ValueError("Quantidade de trabalhadores inválida.")

    intervalos = []
    base = linhas // quantidade_trabalhadores
    resto = linhas % quantidade_trabalhadores
    inicio = 0

    for i in range(quantidade_trabalhadores):
        quantidade = base + (1 if i < resto else 0)
        fim = inicio + quantidade
        intervalos.append((inicio, fim))
        inicio = fim

    return intervalos


def aguardar_trabalhadores(servidor, quantidade):
    trabalhadores = {}

    print(f"Aguardando {quantidade} trabalhadores...")

    while len(trabalhadores) < quantidade:
        conexao, endereco = servidor.accept()

        try:
            mensagem = receber_mensagem(conexao)

            if mensagem["tipo"] != "REGISTRO":
                raise ValueError("Registro inválido.")

            identificador = mensagem["trabalhador"]
            porta_vizinho = mensagem["porta_vizinho"]

            if (
                type(identificador) is not int
                or identificador < 1
                or identificador > quantidade
            ):
                raise ValueError("Identificador inválido.")

            if identificador in trabalhadores:
                raise ValueError("Trabalhador duplicado.")

            if type(porta_vizinho) is not int or not 1 <= porta_vizinho <= 65535:
                raise ValueError("Porta de vizinho inválida.")

            trabalhadores[identificador] = {
                "conexao": conexao,
                "porta": porta_vizinho,
                "endereco": endereco[0],
            }

            print(f"Trabalhador {identificador} conectado.")

        except Exception:
            conexao.close()
            raise

    if sorted(trabalhadores) != list(range(1, quantidade + 1)):
        raise ValueError("IDs dos trabalhadores inválidos.")

    return trabalhadores


def configurar_vizinhos(trabalhadores):
    portas = {
        str(identificador): dados["porta"]
        for identificador, dados in trabalhadores.items()
    }

    quantidade = len(trabalhadores)

    for identificador, dados in trabalhadores.items():
        vizinhos = []

        if identificador > 1:
            vizinhos.append(identificador - 1)

        if identificador < quantidade:
            vizinhos.append(identificador + 1)

        enviar_mensagem(
            dados["conexao"],
            criar_mensagem(
                "CONFIGURACAO",
                vizinhos=vizinhos,
                portas=portas,
            ),
        )


def executar_simulacao(
    trabalhadores,
    linhas,
    colunas,
    geracoes,
    percentual,
    semente,
    limiar,
):
    intervalos = dividir_intervalos(linhas, len(trabalhadores))

    grade = criar_grade(
        linhas,
        colunas,
        percentual,
        semente,
    )

    print("\nSimulação iniciada!")

    for identificador, dados in trabalhadores.items():
        inicio, fim = intervalos[identificador - 1]

        bloco = grade[inicio * colunas:fim * colunas]

        enviar_mensagem(
            dados["conexao"],
            criar_mensagem(
                "TAREFA",
                linhas=fim - inicio,
                colunas=colunas,
                geracoes=geracoes,
                limiar=limiar,
                grade=codificar_grade(bloco),
            ),
        )

    grade_final = bytearray(linhas * colunas)
    contagem_total = [0, 0, 0]

    for identificador, dados in trabalhadores.items():
        resultado = receber_mensagem(dados["conexao"])

        if resultado["tipo"] != "RESULTADO":
            raise ValueError("Resultado inesperado.")

        if resultado["trabalhador"] != identificador:
            raise ValueError("Resultado de trabalhador incorreto.")

        inicio, fim = intervalos[identificador - 1]
        parte = decodificar_grade(resultado["grade"])

        tamanho_esperado = (fim - inicio) * colunas

        if len(parte) != tamanho_esperado:
            raise ValueError("Tamanho do resultado incorreto.")

        grade_final[inicio * colunas:fim * colunas] = parte

        contagem = resultado["contagem"]

        if not isinstance(contagem, list) or len(contagem) != 3:
            raise ValueError("Contagem inválida.")

        for i in range(3):
            contagem_total[i] += contagem[i]

    if sum(contagem_total) != linhas * colunas * geracoes:
        raise ValueError("Contagem acumulada inválida.")

    print(
        f"Resultado final: "
        f"Ignorantes={grade_final.count(0)}, "
        f"Espalhadores={grade_final.count(1)}, "
        f"Inativos={grade_final.count(2)}"
    )

    return grade_final


def main():
    parser = argparse.ArgumentParser(
        description="Coordenador da simulação distribuída."
    )

    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--porta", type=int, default=5000)
    parser.add_argument("--linhas", type=int, default=20)
    parser.add_argument("--colunas", type=int, default=20)
    parser.add_argument("--geracoes", type=int, default=5)
    parser.add_argument("--trabalhadores", type=int, default=2)
    parser.add_argument("--percentual", type=float, default=0.10)
    parser.add_argument("--semente", type=int, default=42)
    parser.add_argument("--limiar", type=int, default=2)
    parser.add_argument("--saida", default="grade_distribuida.bin")

    args = parser.parse_args()

    if args.linhas < 1 or args.colunas < 1:
        parser.error("Linhas e colunas devem ser positivas.")

    if args.geracoes < 0:
        parser.error("Gerações não pode ser negativo.")

    if not 0 <= args.percentual <= 1:
        parser.error("Percentual deve estar entre 0 e 1.")

    if not 0 <= args.limiar <= 8:
        parser.error("Limiar deve estar entre 0 e 8.")

    if not 1 <= args.trabalhadores <= args.linhas:
        parser.error("Quantidade de trabalhadores inválida.")

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    trabalhadores = {}

    try:
        servidor.bind((args.host, args.porta))
        servidor.listen(args.trabalhadores)

        print(
            f"Coordenador aguardando conexões em "
            f"{args.host}:{args.porta}"
        )

        trabalhadores = aguardar_trabalhadores(
            servidor,
            args.trabalhadores,
        )

        configurar_vizinhos(trabalhadores)

        grade_final = executar_simulacao(
            trabalhadores,
            args.linhas,
            args.colunas,
            args.geracoes,
            args.percentual,
            args.semente,
            args.limiar,
        )

        salvar_grade(
            grade_final,
            args.linhas,
            args.colunas,
            args.saida,
        )

        print(f"\nGrade final salva em: {args.saida}")

    except KeyboardInterrupt:
        print("\nSimulação interrompida.")

    finally:
        for dados in trabalhadores.values():
            conexao = dados["conexao"]

            try:
                enviar_mensagem(
                    conexao,
                    criar_mensagem("ENCERRAR"),
                )
            except Exception:
                pass

            conexao.close()

        servidor.close()


if __name__ == "__main__":
    main()

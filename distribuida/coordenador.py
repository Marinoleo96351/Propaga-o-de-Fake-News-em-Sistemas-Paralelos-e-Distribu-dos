
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
    """Divide as linhas da grade entre os trabalhadores."""

    if quantidade_trabalhadores < 1:
        raise ValueError("É necessário pelo menos um trabalhador.")

    if quantidade_trabalhadores > linhas:
        raise ValueError("Não pode haver mais trabalhadores que linhas.")

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
    """Aceita e registra as conexões dos trabalhadores."""

    trabalhadores = {}

    print(f"Aguardando {quantidade} trabalhadores...")

    while len(trabalhadores) < quantidade:
        conexao, endereco = servidor.accept()

        try:
            mensagem = receber_mensagem(conexao)

            if mensagem["tipo"] != "REGISTRO":
                raise ValueError("Mensagem de registro inválida.")

            identificador = mensagem["trabalhador"]

            if not isinstance(identificador, int) or identificador < 1:
                raise ValueError("Identificador de trabalhador inválido.")

            if identificador in trabalhadores:
                raise ValueError("Trabalhador já registrado.")

            trabalhadores[identificador] = conexao

            print(
                f"Trabalhador {identificador} conectado: {endereco}"
            )

        except Exception:
            conexao.close()
            raise

    identificadores = sorted(trabalhadores.keys())

    if identificadores != list(range(1, quantidade + 1)):
        raise ValueError("Os IDs dos trabalhadores devem começar em 1 e ser consecutivos.")

    return trabalhadores


def executar_geracao(
    trabalhadores,
    grade,
    linhas,
    colunas,
    limiar,
):
    """Distribui blocos com linhas de fronteira e reúne os resultados."""

    intervalos = dividir_intervalos(linhas, len(trabalhadores))

    grade_proxima = bytearray(linhas * colunas)
    contagem_total = [0, 0, 0]

    # Envia para cada trabalhador seu bloco e as linhas de fronteira.
    for identificador, conexao in trabalhadores.items():
        inicio, fim = intervalos[identificador - 1]

        inicio_bloco = max(0, inicio - 1)
        fim_bloco = min(linhas, fim + 1)

        bloco = bytearray(
            grade[
                inicio_bloco * colunas:
                fim_bloco * colunas
            ]
        )

        inicio_local = inicio - inicio_bloco
        fim_local = inicio_local + (fim - inicio)

        tarefa = criar_mensagem(
            "TAREFA",
            trabalhador=identificador,
            linhas_locais=fim_bloco - inicio_bloco,
            colunas=colunas,
            inicio_local=inicio_local,
            fim_local=fim_local,
            inicio=inicio,
            fim=fim,
            limiar=limiar,
            grade=codificar_grade(bloco),
        )

        enviar_mensagem(conexao, tarefa)

    # Recebe os resultados e monta a próxima geração.
    for identificador, conexao in trabalhadores.items():
        resultado = receber_mensagem(conexao)

        if resultado["tipo"] != "RESULTADO":
            raise ValueError("Resultado inesperado.")

        if resultado["trabalhador"] != identificador:
            raise ValueError("Resultado de trabalhador incorreto.")

        inicio, fim = intervalos[identificador - 1]

        if resultado["inicio"] != inicio or resultado["fim"] != fim:
            raise ValueError("Intervalo recebido incorreto.")

        parte_grade = decodificar_grade(resultado["grade"])

        tamanho_esperado = (fim - inicio) * colunas

        if len(parte_grade) != tamanho_esperado:
            raise ValueError("Tamanho da grade recebida incorreto.")

        inicio_grade = inicio * colunas
        fim_grade = fim * colunas

        grade_proxima[inicio_grade:fim_grade] = parte_grade

        contagem = resultado["contagem"]

        if not isinstance(contagem, list) or len(contagem) != 3:
            raise ValueError("Contagem de estados inválida.")

        if any(type(valor) is not int or valor < 0 for valor in contagem):
            raise ValueError("Valores da contagem inválidos.")

        for i in range(3):
            contagem_total[i] += contagem[i]

    if sum(contagem_total) != linhas * colunas:
        raise ValueError("A contagem total de células está incorreta.")

    return grade_proxima, contagem_total


def executar_simulacao(
    trabalhadores,
    linhas,
    colunas,
    geracoes,
    percentual,
    semente,
    limiar,
):
    """Executa todas as gerações da simulação."""

    grade = criar_grade(
        linhas,
        colunas,
        percentual,
        semente,
    )

    print("\nSimulação iniciada!")

    for geracao in range(1, geracoes + 1):
        grade, contagem = executar_geracao(
            trabalhadores,
            grade,
            linhas,
            colunas,
            limiar,
        )

        print(
            f"Geração {geracao}: "
            f"Ignorantes={contagem[0]}, "
            f"Espalhadores={contagem[1]}, "
            f"Inativos={contagem[2]}"
        )

    return grade


def main():
    parser = argparse.ArgumentParser(
        description="Coordenador da simulação distribuída."
    )

    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--porta", type=int, default=5000)
    parser.add_argument("--linhas", type=int, default=20)
    parser.add_argument("--colunas", type=int, default=20)
    parser.add_argument("--geracoes", type=int, default=10)
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
        parser.error("O percentual deve estar entre 0 e 1.")

    if args.limiar < 0 or args.limiar > 8:
        parser.error("O limiar deve estar entre 0 e 8.")

    if args.trabalhadores < 1 or args.trabalhadores > args.linhas:
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
        for conexao in trabalhadores.values():
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

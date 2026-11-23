
"""Protocolo de comunicação entre coordenador e trabalhadores.

As mensagens são enviadas usando sockets TCP.
Cada mensagem possui:
1. Um cabeçalho de 4 bytes indicando o tamanho.
2. O conteúdo da mensagem em formato JSON.

Grades são codificadas em Base64 para permitir o envio de bytes.
"""

import base64
import json
import socket
import struct


TAMANHO_CABECALHO = struct.Struct("!I")
TAMANHO_MAXIMO_MENSAGEM = 256 * 1024 * 1024


class ErroProtocolo(Exception):
    """Erro durante o envio ou recebimento de mensagens."""
    pass


def criar_mensagem(tipo, **dados):
    """Cria uma mensagem padronizada."""
    if not isinstance(tipo, str) or not tipo:
        raise ValueError("O tipo da mensagem deve ser um texto válido.")

    return {
        "tipo": tipo,
        **dados
    }


def enviar_mensagem(conexao, mensagem):
    """Envia uma mensagem JSON pelo socket TCP."""
    if not isinstance(mensagem, dict):
        raise ErroProtocolo("A mensagem precisa ser um dicionário.")

    if not isinstance(mensagem.get("tipo"), str):
        raise ErroProtocolo("A mensagem precisa possuir um tipo válido.")

    try:
        conteudo = json.dumps(
            mensagem,
            ensure_ascii=False
        ).encode("utf-8")
    except (TypeError, ValueError) as erro:
        raise ErroProtocolo(
            "Não foi possível converter a mensagem para JSON."
        ) from erro

    tamanho = len(conteudo)

    if tamanho == 0 or tamanho > TAMANHO_MAXIMO_MENSAGEM:
        raise ErroProtocolo("Tamanho de mensagem inválido.")

    cabecalho = TAMANHO_CABECALHO.pack(tamanho)

    try:
        conexao.sendall(cabecalho + conteudo)
    except OSError as erro:
        raise ErroProtocolo("Falha ao enviar mensagem.") from erro


def receber_exatamente(conexao, quantidade):
    """Recebe exatamente a quantidade de bytes solicitada."""
    dados = bytearray()

    while len(dados) < quantidade:
        try:
            parte = conexao.recv(quantidade - len(dados))
        except OSError as erro:
            raise ErroProtocolo("Falha ao receber dados.") from erro

        if not parte:
            raise ErroProtocolo(
                "A conexão foi encerrada inesperadamente."
            )

        dados.extend(parte)

    return bytes(dados)


def receber_mensagem(conexao):
    """Recebe uma mensagem completa pelo socket TCP."""
    cabecalho = receber_exatamente(
        conexao,
        TAMANHO_CABECALHO.size
    )

    tamanho = TAMANHO_CABECALHO.unpack(cabecalho)[0]

    if tamanho == 0 or tamanho > TAMANHO_MAXIMO_MENSAGEM:
        raise ErroProtocolo("Tamanho de mensagem inválido.")

    conteudo = receber_exatamente(conexao, tamanho)

    try:
        mensagem = json.loads(conteudo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ErroProtocolo(
            "Mensagem recebida não é um JSON válido."
        ) from erro

    if not isinstance(mensagem, dict):
        raise ErroProtocolo(
            "A mensagem recebida não é um objeto válido."
        )

    if not isinstance(mensagem.get("tipo"), str):
        raise ErroProtocolo(
            "A mensagem recebida não possui um tipo válido."
        )

    return mensagem


def codificar_grade(grade):
    """Converte uma grade de bytes para Base64."""
    return base64.b64encode(bytes(grade)).decode("ascii")


def decodificar_grade(dados):
    """Converte uma representação Base64 para bytearray."""
    try:
        return bytearray(
            base64.b64decode(dados, validate=True)
        )
    except (ValueError, TypeError) as erro:
        raise ErroProtocolo(
            "Não foi possível decodificar a grade."
        ) from erro


def criar_mensagem_fronteira(trabalhador, geracao, linha):
    """Cria uma mensagem para compartilhar uma linha de fronteira."""
    return criar_mensagem(
        "FRONTEIRA",
        trabalhador=trabalhador,
        geracao=geracao,
        linha=codificar_grade(linha)
    )


def extrair_linha_fronteira(mensagem, geracao, colunas):
    """Valida e extrai uma linha recebida de outro trabalhador."""
    if mensagem.get("tipo") != "FRONTEIRA":
        raise ErroProtocolo("Mensagem de fronteira inválida.")

    if mensagem.get("geracao") != geracao:
        raise ErroProtocolo("Geração da fronteira incompatível.")

    linha = decodificar_grade(mensagem.get("linha"))

    if len(linha) != colunas:
        raise ErroProtocolo("Tamanho da linha de fronteira incorreto.")

    return linha

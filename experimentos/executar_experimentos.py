"""Executa os experimentos de desempenho e grava os tempos medidos em CSV.

Cada versão (sequencial, threads, processos e distribuída) roda como um
programa separado, partindo da mesma grade inicial. O tempo é lido da linha
"Tempo total: X s" que cada programa imprime ao terminar; este script não mede
tempo por conta própria. A versão distribuída roda com os scripts
medir_coordenador.py e medir_trabalhador.py, que reaproveitam o código da
pasta distribuida/ e acrescentam a medição do tempo total e da comunicação.

Cada experimento varia um fator por vez em torno de um cenário base, como pede
o enunciado: número de trabalhadores, tamanho da matriz, número de gerações e
percentual inicial de espalhadores.

Uso, a partir da pasta raiz do projeto:
    python3 experimentos/executar_experimentos.py --maquina notebook --repeticoes 5
"""

import argparse
import csv
import datetime
import os
import platform
import statistics
import subprocess
import sys

PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PASTA_PROJETO)

from comum.grade import criar_grade, salvar_grade

PASTA_RESULTADOS = os.path.join(PASTA_PROJETO, "experimentos", "resultados")
PASTA_GRADES = os.path.join(PASTA_PROJETO, "experimentos", "grades")

# Cenário base: cada experimento muda só um destes valores por vez.
TAMANHO_BASE = 500  # grade quadrada: linhas = colunas
GERACOES_BASE = 30
PERCENTUAL_BASE = 0.05
TRABALHADORES_BASE = 4
LIMIAR = 2
SEMENTE = 42

LISTA_TRABALHADORES = [1, 2, 4, 8]
LISTA_TAMANHOS = [250, 500, 1000]
LISTA_GERACOES = [10, 30, 60]
LISTA_PERCENTUAIS = [0.01, 0.05, 0.20]

# Versão -> (arquivo do programa, opção que recebe o número de trabalhadores).
# A distribuída não usa montar_comando: ela é iniciada por executar_distribuida.
VERSOES = {
    "sequencial": ("sequencial.py", None),
    "threads": ("paralelo_threads.py", "--trabalhadores"),
    "processos": ("paralelo_processos.py", "--trabalhadores"),
    "distribuida": ("experimentos/medir_coordenador.py", "--trabalhadores"),
}

# Cada execução distribuída usa um bloco de portas diferente (coordenador na
# primeira, trabalhadores nas seguintes), para não depender de a porta da
# execução anterior já ter sido liberada pelo sistema operacional.
PORTA_INICIAL = 6000
# Se um processo travar (por exemplo, um trabalhador que não conseguiu
# conectar), o script desiste depois deste tempo em vez de esperar para sempre.
TEMPO_LIMITE_SEGUNDOS = 600

COLUNAS_CSV = [
    "experimento", "versao", "linhas", "colunas", "geracoes", "percentual", "limiar",
    "trabalhadores", "repeticao", "tempo_s", "tempo_comunicacao_s", "bytes_enviados",
    "python", "data_hora",
]


def montar_cenarios():
    """Lista os cenários de cada experimento, variando um fator por vez."""
    cenarios = []

    for trabalhadores in LISTA_TRABALHADORES:
        cenarios.append({"experimento": "trabalhadores", "tamanho": TAMANHO_BASE,
                         "geracoes": GERACOES_BASE, "percentual": PERCENTUAL_BASE,
                         "trabalhadores": trabalhadores})
    for tamanho in LISTA_TAMANHOS:
        cenarios.append({"experimento": "tamanho", "tamanho": tamanho,
                         "geracoes": GERACOES_BASE, "percentual": PERCENTUAL_BASE,
                         "trabalhadores": TRABALHADORES_BASE})
    for geracoes in LISTA_GERACOES:
        cenarios.append({"experimento": "geracoes", "tamanho": TAMANHO_BASE,
                         "geracoes": geracoes, "percentual": PERCENTUAL_BASE,
                         "trabalhadores": TRABALHADORES_BASE})
    for percentual in LISTA_PERCENTUAIS:
        cenarios.append({"experimento": "percentual", "tamanho": TAMANHO_BASE,
                         "geracoes": GERACOES_BASE, "percentual": percentual,
                         "trabalhadores": TRABALHADORES_BASE})

    return cenarios


def montar_execucoes(versoes):
    """Combina cada cenário com cada versão.

    A sequencial não usa trabalhadores, então ela entra com trabalhadores = 1
    e uma vez só por cenário (no experimento "trabalhadores" ela seria
    repetida quatro vezes com o mesmo comando).
    """
    execucoes = []
    for cenario in montar_cenarios():
        for versao in versoes:
            if versao == "sequencial":
                execucao = dict(cenario, versao=versao, trabalhadores=1)
            else:
                execucao = dict(cenario, versao=versao)

            if execucao not in execucoes:
                execucoes.append(execucao)
    return execucoes


def caminho_da_grade(tamanho, percentual):
    return os.path.join(PASTA_GRADES, f"grade_{tamanho}x{tamanho}_p{percentual}.grade")


def preparar_grades(execucoes):
    """Cria uma grade inicial para cada par (tamanho, percentual) usado.

    Todas as versões e repetições de um cenário leem o mesmo arquivo, então
    partem exatamente da mesma população inicial.
    """
    os.makedirs(PASTA_GRADES, exist_ok=True)
    for execucao in execucoes:
        tamanho, percentual = execucao["tamanho"], execucao["percentual"]
        caminho = caminho_da_grade(tamanho, percentual)
        if not os.path.exists(caminho):
            grade = criar_grade(tamanho, tamanho, percentual, SEMENTE)
            salvar_grade(grade, tamanho, tamanho, caminho)


def montar_comando(execucao):
    arquivo, opcao_trabalhadores = VERSOES[execucao["versao"]]
    comando = [
        sys.executable, arquivo,
        "--arquivo-grade", caminho_da_grade(execucao["tamanho"], execucao["percentual"]),
        "--geracoes", str(execucao["geracoes"]),
        "--limiar", str(LIMIAR),
        "--sem-parada-antecipada",
        "--sem-impressao",
    ]
    if opcao_trabalhadores:
        comando += [opcao_trabalhadores, str(execucao["trabalhadores"])]
    return comando


def ler_valor(saida, rotulo):
    """Procura na saída do programa a linha "rotulo: valor ..." e devolve o
    valor como texto, ou "" se o programa não imprimiu essa linha."""
    for linha in saida.splitlines():
        if linha.startswith(rotulo + ":"):
            return linha.split(":", 1)[1].split()[0]
    return ""


def executar(comando):
    """Roda o programa e devolve o que ele imprimiu. Para tudo se der erro,
    para nunca gravar no CSV uma medição que não aconteceu."""
    resultado = subprocess.run(comando, cwd=PASTA_PROJETO, capture_output=True, text=True)
    if resultado.returncode != 0:
        sys.exit(f"Erro ao executar: {' '.join(comando)}\n{resultado.stderr}")
    return resultado.stdout


def executar_distribuida(execucao, porta):
    """Roda a versão distribuída na própria máquina: o coordenador primeiro e,
    quando ele avisa que está esperando conexões, um processo por trabalhador.

    A versão distribuída cria a grade inicial com criar_grade e a mesma
    semente, então parte exatamente da mesma grade dos arquivos .grade.
    Devolve o tempo total (do coordenador) e o tempo médio de comunicação
    entre os trabalhadores, como texto.
    """
    trabalhadores = execucao["trabalhadores"]
    comando_coordenador = [
        sys.executable, "experimentos/medir_coordenador.py",
        "--porta", str(porta),
        "--trabalhadores", str(trabalhadores),
        "--linhas", str(execucao["tamanho"]),
        "--colunas", str(execucao["tamanho"]),
        "--geracoes", str(execucao["geracoes"]),
        "--percentual", str(execucao["percentual"]),
        "--semente", str(SEMENTE),
        "--limiar", str(LIMIAR),
    ]
    coordenador = subprocess.Popen(comando_coordenador, cwd=PASTA_PROJETO, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    primeira_linha = coordenador.stdout.readline()
    if "aguardando" not in primeira_linha:
        coordenador.kill()
        sys.exit(f"O coordenador não iniciou:\n{coordenador.stderr.read()}")

    processos = []
    for identificador in range(1, trabalhadores + 1):
        comando = [sys.executable, "experimentos/medir_trabalhador.py", "--porta", str(porta),
                   "--id", str(identificador), "--porta-vizinho", str(porta + identificador)]
        processos.append(subprocess.Popen(comando, cwd=PASTA_PROJETO, text=True,
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE))

    try:
        saida_coordenador, erro_coordenador = coordenador.communicate(timeout=TEMPO_LIMITE_SEGUNDOS)
        saidas = [processo.communicate(timeout=TEMPO_LIMITE_SEGUNDOS) for processo in processos]
    except subprocess.TimeoutExpired:
        for processo in [coordenador] + processos:
            processo.kill()
        sys.exit(f"A versão distribuída não terminou em {TEMPO_LIMITE_SEGUNDOS} s.")

    if coordenador.returncode != 0:
        sys.exit(f"Erro no coordenador:\n{erro_coordenador}")
    for processo, (_, erro) in zip(processos, saidas):
        if processo.returncode != 0:
            sys.exit(f"Erro em um trabalhador:\n{erro}")

    tempos_comunicacao = [float(ler_valor(saida, "Tempo de comunicação")) for saida, _ in saidas]
    return ler_valor(saida_coordenador, "Tempo total"), f"{statistics.mean(tempos_comunicacao):.6f}"


def medir(execucao, numero):
    """Faz uma medição e devolve (tempo total, tempo de comunicação, bytes
    enviados), como texto; os dois últimos ficam vazios quando a versão não
    os informa."""
    if execucao["versao"] == "distribuida":
        tempo, comunicacao = executar_distribuida(execucao, PORTA_INICIAL + (numero % 100) * 10)
        return tempo, comunicacao, ""

    saida = executar(montar_comando(execucao))
    return (ler_valor(saida, "Tempo total"), ler_valor(saida, "Tempo de comunicação"),
            ler_valor(saida, "Bytes enviados"))


def ler_processador():
    try:
        with open("/proc/cpuinfo") as arquivo:
            for linha in arquivo:
                if linha.startswith("model name"):
                    return linha.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "não identificado (preencher manualmente)"


def contar_nucleos_fisicos():
    """Conta pares (processador físico, núcleo) distintos em /proc/cpuinfo.
    Fora do Linux esse arquivo não existe e o valor deve ser preenchido à mão."""
    try:
        nucleos = set()
        processador_fisico = ""
        with open("/proc/cpuinfo") as arquivo:
            for linha in arquivo:
                if linha.startswith("physical id"):
                    processador_fisico = linha.split(":", 1)[1].strip()
                elif linha.startswith("core id"):
                    nucleos.add((processador_fisico, linha.split(":", 1)[1].strip()))
        if nucleos:
            return str(len(nucleos))
    except OSError:
        pass
    return "não identificado (preencher manualmente)"


def ler_memoria_ram():
    try:
        with open("/proc/meminfo") as arquivo:
            for linha in arquivo:
                if linha.startswith("MemTotal"):
                    quilobytes = int(linha.split()[1])
                    return f"{quilobytes / 1024 / 1024:.1f} GiB"
    except OSError:
        pass
    return "não identificada (preencher manualmente)"


def ler_sistema_operacional():
    try:
        return f"{platform.freedesktop_os_release()['PRETTY_NAME']} ({platform.platform()})"
    except (OSError, AttributeError, KeyError):
        return platform.platform()


def salvar_ambiente(caminho, repeticoes, versoes):
    """Grava a configuração experimental pedida no enunciado."""
    linhas = [
        f"Data: {datetime.datetime.now().isoformat(timespec='seconds')}",
        f"Processador: {ler_processador()}",
        f"Núcleos físicos: {contar_nucleos_fisicos()}",
        f"Núcleos lógicos: {os.cpu_count()}",
        f"Memória RAM: {ler_memoria_ram()}",
        f"Sistema operacional: {ler_sistema_operacional()}",
        f"Linguagem: Python {platform.python_version()} ({platform.python_implementation()})",
        f"Interpretador: {sys.executable}",
        f"Versões medidas: {', '.join(versoes)}",
        f"Repetições por cenário: {repeticoes}",
        f"Cenário base: {TAMANHO_BASE}x{TAMANHO_BASE}, {GERACOES_BASE} gerações, "
        f"{PERCENTUAL_BASE:.0%} de espalhadores, limiar {LIMIAR}, semente {SEMENTE}",
        f"Trabalhadores: {LISTA_TRABALHADORES}",
        f"Tamanhos: {LISTA_TAMANHOS}",
        f"Gerações: {LISTA_GERACOES}",
        f"Percentuais: {LISTA_PERCENTUAIS}",
    ]
    with open(caminho, "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(linhas) + "\n")


def analisar_argumentos():
    analisador = argparse.ArgumentParser(description="Executa os experimentos de desempenho e grava os tempos em CSV.")
    analisador.add_argument("--maquina", default="local",
                            help="Nome curto da máquina, usado no nome dos arquivos de resultado.")
    analisador.add_argument("--repeticoes", type=int, default=5,
                            help="Quantas vezes cada execução é repetida.")
    analisador.add_argument("--versoes", nargs="+", choices=list(VERSOES), default=list(VERSOES),
                            help="Versões a medir (padrão: todas as que existirem).")
    return analisador.parse_args()


def main():
    argumentos = analisar_argumentos()

    versoes = []
    for versao in argumentos.versoes:
        arquivo = VERSOES[versao][0]
        if os.path.exists(os.path.join(PASTA_PROJETO, arquivo)):
            versoes.append(versao)
        else:
            print(f"Aviso: {arquivo} não existe, a versão '{versao}' será pulada.")
    if not versoes:
        sys.exit("Nenhuma versão disponível para medir.")

    os.makedirs(PASTA_RESULTADOS, exist_ok=True)
    caminho_csv = os.path.join(PASTA_RESULTADOS, f"tempos_{argumentos.maquina}.csv")
    caminho_ambiente = os.path.join(PASTA_RESULTADOS, f"ambiente_{argumentos.maquina}.txt")

    # Medições reais levam tempo para refazer, então não sobrescrevemos sem querer.
    if os.path.exists(caminho_csv):
        sys.exit(f"{caminho_csv} já existe. Apague o arquivo ou use outro --maquina.")

    execucoes = montar_execucoes(versoes)
    preparar_grades(execucoes)
    salvar_ambiente(caminho_ambiente, argumentos.repeticoes, versoes)

    total = len(execucoes) * argumentos.repeticoes
    feitas = 0

    with open(caminho_csv, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS_CSV)
        escritor.writeheader()

        # As versões se alternam dentro de cada repetição: se a máquina esquentar
        # ou mudar de frequência no meio, o efeito se espalha por todas as versões.
        for repeticao in range(1, argumentos.repeticoes + 1):
            for execucao in execucoes:
                tempo, comunicacao, bytes_enviados = medir(execucao, feitas)
                if not tempo:
                    sys.exit(f"A versão '{execucao['versao']}' não imprimiu a linha 'Tempo total'.")

                escritor.writerow({
                    "experimento": execucao["experimento"],
                    "versao": execucao["versao"],
                    "linhas": execucao["tamanho"],
                    "colunas": execucao["tamanho"],
                    "geracoes": execucao["geracoes"],
                    "percentual": execucao["percentual"],
                    "limiar": LIMIAR,
                    "trabalhadores": execucao["trabalhadores"],
                    "repeticao": repeticao,
                    "tempo_s": tempo,
                    "tempo_comunicacao_s": comunicacao,
                    "bytes_enviados": bytes_enviados,
                    "python": platform.python_version(),
                    "data_hora": datetime.datetime.now().isoformat(timespec="seconds"),
                })
                # Grava a linha no disco na hora: se a execução for interrompida,
                # o que já foi medido não se perde.
                arquivo.flush()

                feitas += 1
                print(f"[{feitas}/{total}] {execucao['experimento']:<13} {execucao['versao']:<10} "
                      f"{execucao['tamanho']}x{execucao['tamanho']} ger={execucao['geracoes']} "
                      f"perc={execucao['percentual']} trab={execucao['trabalhadores']} "
                      f"rep={repeticao} -> {tempo} s")

    print(f"Resultados gravados em {caminho_csv}")
    print(f"Configuração da máquina em {caminho_ambiente}")


if __name__ == "__main__":
    main()


# Propagação de Fake News em Sistemas Paralelos e Distribuídos

Trabalho da disciplina de Sistemas Distribuídos (ES45A.2026_02.ES51), UTFPR Cornélio Procópio.

Simulação de propagação de fake news como um autômato celular, implementada em versão sequencial, paralela (`threading` e `multiprocessing`) e distribuída (`socket`), usando a biblioteca padrão do Python no cálculo.

## Integrantes

- Leonardo Marino Scarparo Silva (RA 2707012)
- Vinicius Luiz Andretta Ferracini (RA 2707110)
- Arthur Henrique de Melo Almeida (RA 2706920)
- Willian Kiyoshi Onuki (RA 2151456)

## Modelo

Cada célula da grade representa uma pessoa em um de três estados:

- **0 — Ignorante**: ainda não recebeu a informação.
- **1 — Espalhador**: recebeu e está espalhando.
- **2 — Inativo**: já espalhou e parou.

A cada geração, considerando a vizinhança de Moore (8 vizinhos, sem voltar pela borda):

- Um Ignorante vira Espalhador se tiver pelo menos `limiar_convencimento` vizinhos espalhadores.
- Um Espalhador vira Inativo na geração seguinte.
- Um Inativo permanece Inativo.

## Como rodar

Requer Python 3.12 ou mais novo, sem dependências externas para o cálculo. A biblioteca `matplotlib`, presente em `requirements.txt`, é utilizada somente para os gráficos dos experimentos.

### Versão sequencial

```bash
python sequencial.py --linhas 100 --colunas 100 --geracoes 50 --percentual 0.05 --limiar 2
```

Opções principais:

- `--limiar`: quantidade de vizinhos espalhadores necessária para convencer um ignorante.
- `--sem-parada-antecipada`: executa todas as gerações.
- `--sem-impressao`: desativa a impressão de resultados por geração.
- `--salvar-grade arquivo.grade`: salva a grade inicial.
- `--arquivo-grade arquivo.grade`: carrega uma grade inicial de um arquivo.

### Versões paralelas locais

As duas versões paralelas aceitam as mesmas opções principais da versão sequencial,
incluindo `--arquivo-grade`, `--salvar-grade`, `--limiar`, `--semente`,
`--probabilidade` e `--trabalhadores`.

```bash
python paralelo_threads.py --linhas 100 --colunas 100 --geracoes 50 --limiar 2 --trabalhadores 4
python paralelo_processos.py --linhas 100 --colunas 100 --geracoes 50 --limiar 2 --trabalhadores 4
```

Para comparar as versões partindo da mesma entrada, salve uma grade com a
sequencial e passe o arquivo às duas versões paralelas. Use
`--sem-parada-antecipada --sem-impressao` para executar um número fixo de
gerações e reduzir o custo de saída no terminal.

`paralelo_threads.py` reparte faixas de linhas entre threads e sincroniza cada
geração com uma barreira. Como o cálculo é Python puro, o GIL pode limitar o
ganho de desempenho das threads. `paralelo_processos.py` mantém processos
trabalhadores ativos durante a simulação e compartilha os dois buffers da grade
com `multiprocessing.shared_memory`, evitando copiar a grade por pickle a cada
geração.

O argumento opcional `--probabilidade` define a chance de cada contato com um
espalhador convencer uma célula ignorante (padrão `1.0`, que reproduz a regra
determinística). No modo probabilístico, `--semente` torna o resultado
reproduzível e independente da quantidade de trabalhadores.

### Experimento de threads e processos

Execute o benchmark na mesma máquina e com a mesma entrada para comparar o
efeito do GIL com o custo de criação e sincronização dos processos:

```bash
python experimentos/comparar_paralelismo.py --linhas 100 --colunas 100 --geracoes 20 --repeticoes 3 --trabalhadores 1 2 4
```

O script roda as duas implementações com cada quantidade de trabalhadores,
mede cada execução com `time.perf_counter()` e grava os tempos individuais,
medianas, speedup e eficiência em `experimentos/tempos_paralelismo.csv`. Ele
usa a mesma grade e semente para cada configuração; não inclui tempos
estimados. Execute o benchmark na máquina da apresentação e use os valores
gerados no CSV para os gráficos e slides.

Referências técnicas: [threading e GIL](https://docs.python.org/3.14/library/threading.html),
[memória compartilhada](https://docs.python.org/3.14/library/multiprocessing.shared_memory.html)
e [`time.perf_counter`](https://docs.python.org/3.14/library/time.html#time.perf_counter).

### Versão distribuída

A versão distribuída utiliza comunicação TCP com sockets. O coordenador divide a grade em blocos de linhas e envia cada bloco para um trabalhador. Durante a simulação, os trabalhadores trocam diretamente as linhas de fronteira com seus vizinhos para calcular as gerações corretamente.

Para executar localmente, abra terminais separados.

**Terminal 1 — Coordenador:**

```bash
python -m distribuida.coordenador --trabalhadores 2 --linhas 20 --colunas 20 --geracoes 5
```

**Terminal 2 — Trabalhador 1:**

```bash
python -m distribuida.trabalhador --id 1 --porta-vizinho 5001
```

**Terminal 3 — Trabalhador 2:**

```bash
python -m distribuida.trabalhador --id 2 --porta-vizinho 5002
```

Inicie primeiro o coordenador e depois os trabalhadores.

É possível alterar a quantidade de trabalhadores. Por exemplo, para quatro trabalhadores, utilize `--trabalhadores 4` no coordenador e inicie os processos com IDs de 1 a 4, cada um usando uma porta diferente.

A grade final é salva no arquivo `grade_distribuida.bin`.

## Testes

Para executar os testes automatizados:

```bash
python -m unittest discover -v
```

Os testes `testes/testar_paralelo_vinicius.py` comparam threads e processos à
função sequencial comum e verificam que a probabilidade não muda quando o
número de faixas é alterado.

Também é possível verificar a compilação dos arquivos Python:

```bash
python -m py_compile sequencial.py paralelo_threads.py paralelo_processos.py comum/*.py distribuida/*.py experimentos/*.py
```

Os testes verificam se a divisão da grade em faixas de linhas mantém o mesmo resultado do cálculo da grade inteira e se a versão refatorada preserva o comportamento do código original fornecido pelo professor (`original/FakeNews.py`).

Além disso, foram realizados testes de comparação entre as versões sequencial e distribuída, utilizando dois e quatro trabalhadores, verificando que as grades finais são idênticas.

## Estrutura

```text
comum/
├── __init__.py
├── modelo.py
├── grade.py
└── probabilidade.py

distribuida/
├── __init__.py
├── protocolo.py
├── coordenador.py
└── trabalhador.py

testes/
├── __init__.py
├── testar_correcao.py
└── testar_paralelo_vinicius.py

experimentos/
└── comparar_paralelismo.py

original/
└── FakeNews.py

sequencial.py
paralelo_threads.py
paralelo_processos.py
experimentos/comparar_paralelismo.py
README.md
requirements.txt
.gitignore
```

## Melhoria 1 — Grade em `bytearray` e duas grades alternadas

**O que é.** O código original cria uma nova grade a cada geração com `deepcopy(grade)` e depois sobrescreve as células que mudaram. A refatoração usa a grade como um único `bytearray` (1 byte por célula, índice `linha * colunas + coluna`) e mantém duas grades que trocam de papel a cada geração (`atual, proxima = proxima, atual`), eliminando a cópia.

**Por que foi feita.** `deepcopy` em uma lista de listas percorre e recria cada sublista recursivamente, o que é caro em Python puro, além de não ser necessário: basta ter dois buffers e alternar entre eles.

**Como foi implementada.** `comum/modelo.py` define a função única de cálculo (`calcular_intervalo`), usada pelas versões do projeto. Ela lê de um `bytearray` e escreve em outro. `sequencial.py` cria os dois buffers uma única vez e só troca os papéis entre gerações.

**Impacto medido.** Comparando `original/FakeNews.py` com a versão refatorada, nas mesmas condições (30 gerações fixas, sem parada antecipada, sem impressão, 5% de espalhadores iniciais, limiar 2, `time.perf_counter()`, Python 3.14.5):

| Grade | Original (ms/geração) | Refatorado (ms/geração) | Speedup |
| --- | --- | --- | --- |
| 300 x 300 | 85,26 | 76,96 | 1,11x |
| 500 x 500 | 250,07 | 225,05 | 1,11x |
| 1000 x 1000 | 1012,78 | 918,23 | 1,10x |

O ganho medido (cerca de 10%) é bem menor do que estimativas informais iniciais, e a diferença é explicada principalmente pelo custo do próprio `deepcopy`. Medido isoladamente, ele leva cerca de 8,8 ms por chamada em uma grade 300 x 300 e escala com o número de células. A contagem de vizinhos (vizinhança de Moore) continua sendo o principal custo do cálculo em Python puro.

## Contribuição individual — Leonardo Marino Scarparo Silva

Responsável pela base do projeto, sobre a qual as demais versões são construídas:

- **`comum/modelo.py`**: definição dos três estados e da função `calcular_intervalo`, que calcula a próxima geração para um intervalo de linhas de uma grade `bytearray` e devolve a contagem de cada estado nesse intervalo.
- **`comum/grade.py`**: criação da grade inicial com semente fixa (`criar_grade`) e gravação/leitura em arquivo (`salvar_grade`/`carregar_grade`).
- **`sequencial.py`**: versão sequencial refatorada, com duas grades alternadas em vez de `deepcopy`, contagem de estados feita durante o cálculo e opções de linha de comando para configurar a simulação.
- **`testes/testar_correcao.py`**: testes automatizados que comparam a refatoração com o código original e verificam se a divisão do cálculo em faixas de linhas preserva o resultado.
- **Melhoria 1** (`bytearray` e duas grades alternadas): implementação e medição de desempenho descritas na seção acima.
- Organização inicial do repositório (estrutura de pastas, `.gitignore`, `requirements.txt`) e abertura do primeiro Pull Request (`sequencial` → `main`).

## Contribuição individual — Vinicius Luiz Andretta Ferracini

- **`paralelo_threads.py`**: divide a grade em faixas de linhas para threads e sincroniza cada geração com uma barreira.
- **`paralelo_processos.py`**: mantém processos trabalhadores e dois buffers de grade em `multiprocessing.shared_memory`.
- **`comum/probabilidade.py`**: aplica chance de convencimento com sorteio determinístico por geração e célula, mantendo os resultados reproduzíveis entre partições.
- **`testes/testar_paralelo_vinicius.py`**: compara os resultados das versões paralelas com o cálculo sequencial comum e verifica consistência entre faixas.
- **`experimentos/comparar_paralelismo.py`**: mede tempos de threads e processos e grava tempos, medianas, speedup e eficiência em CSV para análise do efeito do GIL.
- **Melhorias**: comparação entre threads e processos e probabilidade de convencimento configurável.

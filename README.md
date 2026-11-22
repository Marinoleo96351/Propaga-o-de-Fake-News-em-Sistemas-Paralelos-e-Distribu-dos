# Propagação de Fake News em Sistemas Paralelos e Distribuídos

Trabalho da disciplina de Sistemas Distribuídos (ES45A.2026_02.ES51), UTFPR Cornélio Procópio.

Simulação de propagação de fake news como um autômato celular, implementada em versão
sequencial, paralela (`threading` e `multiprocessing`) e distribuída (`socket`), usando
só a biblioteca padrão do Python no cálculo.

## Integrantes

- Leonardo Marino Scarparo Silva (RA 2707012)
- Vinicius Luiz Andretta Ferracini (RA 2707110)
- Arthur Henrique de Melo Almeida (RA 2706920)
- Willian Kiyoshi Onuki (RA 2151456)

## Modelo

Cada célula da grade é uma pessoa em um de três estados:

- **0 — Ignorante**: ainda não recebeu a informação.
- **1 — Espalhador**: recebeu e está espalhando.
- **2 — Inativo**: já espalhou e parou.

A cada geração, considerando a vizinhança de Moore (8 vizinhos, sem voltar pela borda):

- um Ignorante vira Espalhador se tiver pelo menos `limiar_convencimento` vizinhos espalhadores;
- um Espalhador vira Inativo na geração seguinte;
- um Inativo permanece Inativo.

## Como rodar

Requer Python 3.12 ou mais novo, sem dependências externas para o cálculo
(`matplotlib`, em `requirements.txt`, é usado só para os gráficos dos experimentos).

```bash
python sequencial.py --linhas 100 --colunas 100 --geracoes 50 --percentual 0.05 --limiar 2
```

Opções principais: `--limiar` (vizinhos espalhadores para convencer um ignorante),
`--sem-parada-antecipada` e `--sem-impressao` (para medir desempenho),
`--salvar-grade arquivo.grade` e `--arquivo-grade arquivo.grade` (para todas as
versões partirem da mesma grade inicial).

## Testes

```bash
python -m unittest testes.testar_correcao -v
```

Os testes garantem duas coisas: (1) dividir a grade em faixas de linhas, como vão
fazer as versões paralela e distribuída, dá exatamente o mesmo resultado que calcular
a grade inteira de uma vez; (2) a versão refatorada produz, geração por geração, a
mesma grade que o código original fornecido (`original/FakeNews.py`).

## Estrutura

```
comum/
├── modelo.py     estados e a função de cálculo usada por todas as versões
└── grade.py      criação, gravação e leitura da grade inicial
sequencial.py      versão sequencial refatorada (base de comparação)
testes/
└── testar_correcao.py   compara a refatoração com o original e testa a divisão em faixas
original/
└── FakeNews.py    código fornecido pelo professor, sem alterações
```

As versões paralela (`threading`/`multiprocessing`) e distribuída (`socket`) serão
adicionadas em branches próprias e integradas aqui depois de revisadas.

## Melhoria 1 — grade em `bytearray` e duas grades alternadas (sem `deepcopy`)

**O que é.** O código original cria uma nova grade a cada geração com
`deepcopy(grade)` e depois sobrescreve as células que mudaram. A refatoração usa a
grade como um único `bytearray` (1 byte por célula, índice `linha * colunas + coluna`)
e mantém duas grades que trocam de papel a cada geração (`atual, proxima = proxima, atual`),
eliminando a cópia.

**Por que foi feita.** `deepcopy` em uma lista de listas percorre e recria cada
sublista recursivamente, o que é caro em Python puro, além de não ser necessário:
basta ter dois buffers e alternar entre eles.

**Como foi implementada.** `comum/modelo.py` define a função única de cálculo
(`calcular_intervalo`), usada por todas as versões do projeto, que lê de um
`bytearray` e escreve em outro. `sequencial.py` cria os dois buffers uma única vez
e só troca os papéis entre gerações.

**Impacto medido.** Comparando `original/FakeNews.py` com a versão refatorada, nas
mesmas condições (30 gerações fixas, sem parada antecipada, sem impressão,
5% de espalhadores iniciais, limiar 2, `time.perf_counter()`, Python 3.14.5):

| Grade | Original (ms/geração) | Refatorado (ms/geração) | Speedup |
| --- | --- | --- | --- |
| 300 x 300 | 85,26 | 76,96 | 1,11x |
| 500 x 500 | 250,07 | 225,05 | 1,11x |
| 1000 x 1000 | 1012,78 | 918,23 | 1,10x |

O ganho medido (cerca de 10%) é bem menor do que estimativas informais iniciais, e a
diferença é totalmente explicada pelo custo do próprio `deepcopy`: medido isoladamente,
ele leva cerca de 8,8 ms por chamada em uma grade 300 x 300, e escala com o número de
células — praticamente o mesmo valor da diferença observada entre as duas versões. A
contagem de vizinhos (vizinhança de Moore) é o verdadeiro gargalo do cálculo em Python
puro e custa o mesmo nas duas versões, por isso o ganho desta melhoria isolada é
modesto; o valor real dela é remover uma operação sem necessidade antes de aplicar as
otimizações seguintes (memória compartilhada entre processos, halos na distribuída),
que dependem de a grade já estar num único `bytearray`.

## Contribuição individual — Leonardo Marino Scarparo Silva

Responsável pela base do projeto, sobre a qual as demais versões são construídas:

- **`comum/modelo.py`**: definição dos três estados e da função `calcular_intervalo`,
  que calcula a próxima geração para um intervalo de linhas de uma grade `bytearray` e
  devolve a contagem de cada estado nesse intervalo. É a mesma função reaproveitada
  pelas versões sequencial, paralela e distribuída — só muda o intervalo de linhas
  que cada uma passa, o que garante que todas sigam exatamente a mesma regra.
- **`comum/grade.py`**: criação da grade inicial com semente fixa
  (`criar_grade`), e gravação/leitura em arquivo (`salvar_grade`/`carregar_grade`),
  para que todas as versões possam partir da mesma grade quando necessário.
- **`sequencial.py`**: versão sequencial refatorada, com duas grades alternadas em
  vez de `deepcopy`, contagem de estados feita dentro do próprio laço de cálculo (sem
  percorrer a grade de novo), e opções de linha de comando (`argparse`) para tamanho,
  número de gerações, percentual inicial, limiar de convencimento, além de desligar a
  parada antecipada e a impressão por geração — necessário para medir desempenho sem
  contaminar o tempo medido.
- **`testes/testar_correcao.py`**: dois testes automatizados. O primeiro gera uma
  grade e compara o resultado de calcular todas as linhas de uma vez com o resultado
  de calcular as mesmas linhas divididas em várias faixas (1, 2, 4 e 7 faixas, em
  vários tamanhos de grade e por várias gerações em sequência), confirmando que a
  divisão de trabalho por linhas não altera o resultado — a propriedade que sustenta a
  ausência de condição de corrida nas versões paralela e distribuída. O segundo
  carrega `original/FakeNews.py` dinamicamente e compara, geração por geração, a grade
  calculada pelo código original com a calculada pela função refatorada, confirmando
  que a refatoração preserva exatamente o comportamento do modelo original.
- **Melhoria 1** (`bytearray` e duas grades alternadas): implementação e medição de
  desempenho descritas na seção acima.
- Organização inicial do repositório (estrutura de pastas, `.gitignore`,
  `requirements.txt`) e abertura do primeiro Pull Request (`sequencial` → `main`).

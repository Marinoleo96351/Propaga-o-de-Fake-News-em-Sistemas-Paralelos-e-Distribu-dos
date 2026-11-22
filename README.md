# Propagação de Fake News em Sistemas Paralelos e Distribuídos

Trabalho da matéria de Sistemas Distribuídos (UTFPR Cornélio Procópio). O plano completo
do projeto está em `.claude/PLANO_DO_PROJETO (2).md`.

## Como rodar

Requer Python 3.12 ou mais novo, sem dependências externas para o cálculo
(`matplotlib` é usado só para os gráficos dos experimentos).

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

## Estrutura

- `comum/modelo.py` — estados e a função de cálculo usada por todas as versões.
- `comum/grade.py` — criação, gravação e leitura da grade inicial.
- `sequencial.py` — versão sequencial refatorada (base de comparação).
- `testes/testar_correcao.py` — garante que dividir a grade em faixas não muda o resultado.
- `original/` — coloque aqui o `FakeNews.py` fornecido pelo professor, sem alterações.

As versões paralela (`threading`/`multiprocessing`) e distribuída (`socket`) ainda
serão adicionadas, cada uma em sua branch, conforme a seção 9 do plano.

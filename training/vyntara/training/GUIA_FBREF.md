# Guia FBref — captar xG sem API paga

O FBref tem xG de graça, mas **bloqueia robôs**. Por isso o fluxo é separado do
robô diário: você roda a captação **no seu PC** e comita o resultado.

## Fluxo
```
[Seu PC] python fetch_fbref.py  ->  fbref_data.json  ->  commit no GitHub
                                                              |
[Robô diário / pipeline] LE o fbref_data.json  ->  features de xG no modelo
```

## Passo a passo (no SEU PC)
1. Instale a lib:
   ```
   pip install soccerdata pandas
   ```
2. Entre na pasta e rode:
   ```
   cd training
   python fetch_fbref.py
   ```
3. O script imprime **as colunas** e **os nomes dos times** que o FBref retornou.
   - Confira se os nomes batem com o `fbref_teams.json`. Onde aparecer
     `??? NAO MAPEADO`, corrija o nome no `fbref_teams.json` (tem que ser IGUAL
     ao que o FBref mostra) e rode de novo.
4. No fim gera o `fbref_data.json` (jogos com xG, já com os IDs da API-Football).
5. **Comite** o `fbref_data.json` (e o `fbref_teams.json` ajustado) no repo `vyntara-model`,
   dentro de `training/`.

## Ligar no modelo (próxima fase)
- Depois que o `fbref_data.json` estiver certo, a gente pluga o **xG rolante** como
  features do ML (xG feito/sofrido nos últimos jogos) e mede no backtest se melhora.
- O flag `"useFbref": true` no `config.json` ativa isso (deixe `false` até validarmos).

## Verdades honestas
- **FBref bloqueia datacenter** (GitHub Actions). Por isso roda no seu PC. Se mesmo
  no PC bloquear, o `soccerdata` tem cache e espera entre requisições — rode de novo
  mais tarde.
- **soccerdata pode não cobrir o Brasil por padrão.** Se der erro de liga, rode:
  ```
  python -c "import soccerdata as sd; print(sd.FBref.available_leagues())"
  ```
  e me mande a lista — eu ajusto o código da liga no `fetch_fbref.py`.
- É uma **v1 pra calibrar**: rode, me mande o que ele imprimir (colunas + times +
  qualquer erro), e eu acerto o parser/mapeamento pra bater com o que o FBref
  realmente devolve.

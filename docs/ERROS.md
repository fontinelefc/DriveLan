# Registro de erros e soluções

Este arquivo guarda os erros relevantes encontrados durante a construção do DriveLan e como foram
resolvidos, para que não se repitam. Registre aqui todo erro que tenha custado investigação, que
possa voltar a acontecer ou que revele uma armadilha do ambiente, da stack ou do FSD.

Como usar:

- adicione cada novo registro **no topo** da lista (mais recente primeiro);
- use a data no formato `AAAA-MM-DD`;
- nunca registre PINs, tokens, chaves, conteúdo de arquivos ou caminhos locais da máquina;
- se a solução exigir mudar o FSD, registre aqui e avise o usuário antes de alterar o FSD.

Modelo:

```text
## <data> - <título curto do erro>

- Sintoma:
- Causa:
- Solução aplicada:
- Como evitar no futuro:
```

---

## 2026-11-24 - Avisos do ruff com nomes em português e `noqa` de regra desligada

- Sintoma: `ruff check` acusou `N818` nas exceções `NomeInvalido` e `CaminhoInvalido` (falta o
  sufixo "Error") e `RUF100` ("unused noqa") em `# noqa: PLW0603` e `# noqa: DTZ001`.
- Causa: o `N818` exige nomes de exceção em inglês. O `RUF100` marca como inútil todo `noqa` de
  regra que não está habilitada no `pyproject.toml` (as famílias `PL` e `DTZ` não estão em
  `select`).
- Solução aplicada: `N818` acrescentado ao `ignore` do ruff, com comentário (o projeto usa nomes
  em português). Os `noqa` de regras desligadas foram removidos.
- Como evitar no futuro: só escrever `# noqa: <regra>` para regras do `select` do `pyproject.toml`
  (E, W, F, I, B, UP, N, S, SIM, RUF). Exceções novas podem ter nomes em português, sem
  "Error".

## 2026-11-17 - `uv sync` falhou por falta do README.md

- Sintoma: `uv sync` parou com "failed to open file `README.md`" ao construir o pacote `drivelan`.
- Causa: o `pyproject.toml` declara `readme = "README.md"` e o backend `uv_build` exige que o
  arquivo exista para montar os metadados do pacote.
- Solução aplicada: criação do `README.md` na raiz antes de rodar `uv sync` novamente.
- Como evitar no futuro: todo arquivo referenciado no `pyproject.toml` (`readme`, `license-files`)
  precisa existir no repositório; não removê-los.

## 2026-11-17 - Python 3.12 ausente no Fedora de desenvolvimento

- Sintoma: só havia Python 3.14 no sistema, sem `python3.12`, `pip` ou `uv`; o FSD exige Python 3.12.
- Causa: o Fedora atual traz uma versão mais nova do Python por padrão.
- Solução aplicada: instalação do uv no usuário pelo instalador oficial e `uv python install 3.12`;
  o projeto fixa a versão em `.python-version` e `requires-python = ">=3.12,<3.13"`.
- Como evitar no futuro: sempre usar `uv run ...` (nunca o `python3` do sistema) para rodar
  ferramentas e testes do projeto.

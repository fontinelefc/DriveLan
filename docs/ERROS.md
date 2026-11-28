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

## 2026-11-27 - Middleware do aiohttp falhou com "unexpected keyword argument 'handler'"

- Sintoma: todo pedido ao canal local respondia `500 Server got itself in trouble` (página do
  próprio aiohttp, fora do formato 23.6) e o terminal mostrava `TypeError: identificar() got an
  unexpected keyword argument 'handler'`.
- Causa: o aiohttp 3.14 chama os middlewares com `middleware(request, handler=...)`, por nome. O
  parâmetro tinha sido chamado `manipulador`.
- Solução aplicada: os middlewares em `servico/api/local/aplicacao.py` usam exatamente
  `(pedido, handler)`; o primeiro parâmetro pode ter qualquer nome.
- Como evitar no futuro: em middlewares `@web.middleware`, manter o nome `handler` no segundo
  parâmetro (exceção à regra de nomes em português). Os testes de `tests/servico/test_api_local.py`
  passam pelos middlewares e pegam o problema.

## 2026-11-27 - `assert` de plataforma, ruff (S101/E402) e mypy sem pywin32 no Linux

- Sintoma: `ruff` acusou `S101` e `E402` nos módulos só do Windows; `mypy` acusou
  `Module "...windows_pipe" has no attribute "ServidorPipe"` e falta de tipos do `psutil`.
- Causa: os módulos `plataforma/windows*.py` começam com `assert sys.platform == "win32"` para o
  mypy não analisá-los no Linux (onde o pywin32 não existe); por isso os imports vêm depois do
  `assert`. Um import desses módulos fora de um `if sys.platform == "win32":` não é entendido como
  inalcançável. O `psutil` não publica tipos.
- Solução aplicada: `# noqa: S101` no `assert` de plataforma, `E402` liberado só para
  `src/drivelan/servico/plataforma/windows*.py` no `pyproject.toml`, imports de módulos do Windows
  sempre dentro de `if sys.platform == "win32":` e override do mypy com `ignore_missing_imports`
  para os módulos do pywin32 e para o `psutil`, sem adicionar `types-pywin32`/`types-psutil`
  (dependências novas). Fora desses casos, o código do pacote não usa `assert` (S101): usa
  `RuntimeError` explícito.
- Como evitar no futuro: código novo só do Windows vai para `plataforma/windows*.py` e é importado
  dentro de `if sys.platform == "win32":`; valores vindos do `psutil` são convertidos (`float(...)`,
  `int(...)`) antes de devolver.

## 2026-11-27 - `sqlite3.complete_statement` não detecta comando sintaticamente incompleto

- Sintoma: o teste que esperava `MigracaoInvalida` para um script terminado em
  `CREATE TABLE u (b` não recebeu a exceção.
- Causa: `complete_statement` só verifica se o texto termina em `;` fora de textos, comentários e
  corpos de gatilho (`BEGIN ... END`). Um parêntese aberto com `;` no fim é considerado "completo";
  o erro de sintaxe só aparece ao executar.
- Solução aplicada: a divisão de comandos recusa apenas gatilho ou texto sem fechamento; erros de
  sintaxe são tratados na execução, dentro da transação da migration (`FalhaMigracao`, nada fica
  aplicado). O teste passou a cobrir os dois casos separadamente.
- Como evitar no futuro: não usar `complete_statement` como validador de sintaxe; validar uma
  migration nova rodando `uv run pytest tests/servico/test_migracoes.py tests/servico/test_esquema_0001.py`.

## 2026-11-24 - Pasta raiz dos logs criada com 0755 em vez de 0700

- Sintoma: o teste de permissões do log falhou: a pasta do mês ficou com 0700, mas a pasta raiz dos
  logs ficou com 0755.
- Causa: `criar_diretorio_privado` usa `mkdir(parents=True)`, que cria as pastas intermediárias com
  o modo padrão (umask); só a última pasta recebe 0700 pelo `chmod`.
- Solução aplicada: `LogErros` cria a raiz e a pasta do mês com duas chamadas separadas a
  `criar_diretorio_privado`.
- Como evitar no futuro: quando várias pastas da cadeia precisarem ser privadas (dados, certificado,
  logs), chamar `criar_diretorio_privado` para cada uma, da mais externa para a mais interna. Nota:
  a função também reaplica 0700 numa pasta que já existe, então tirar a permissão de escrita da
  pasta não serve para simular falha de gravação nos testes (use falha simulada com `monkeypatch`).

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

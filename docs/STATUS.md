# Status do projeto DriveLan

**Última atualização:** 27/11/2026 — Fase 5 (serviço mínimo)
**Fase atual:** Fase 5 concluída no Linux, **aguardando o critério de saída da seção 15.5.1 na VM
Windows 11** · a Fase 6 só começa depois dessa validação

## Estado atual

A base do repositório está pronta: Python 3.12.16 gerenciado pelo uv, dependências da seção 3.2
do FSD instaladas e fixadas no `uv.lock`, estrutura de pastas e módulos-esqueleto da seção 5.5,
ferramentas de qualidade configuradas e passando, licença GPLv3, fontes embutidas, logo oficial,
folha QSS com os tokens oficiais e documentação viva.

Na Fase 2 foi implementado o código compartilhado em `src/drivelan/comum/` (RN-68, caminhos
do protocolo, diretórios por plataforma, protocolo e i18n). Na Fase 3, a leitura e gravação do
`drivelan.toml` (`servico/configuracao.py`) e o log de erros com contingência e retenção
(`servico/log_erros.py`). Na Fase 4, o banco SQLite (`servico/dados/banco.py`), o executor de
migrations (`servico/dados/migracoes.py`) e a `0001_inicial.sql` completa. Na Fase 5, o
`drivelan-service` passou a subir de verdade (`--console`, `--dados`, `--migrar`), na ordem da
seção 6.1, com agendador e canal local seguro (socket Unix com `SO_PEERCRED`; named pipe próprio no
Windows, ainda não executado numa VM). O app (`drivelan`) continua como esqueleto (Fase 6).

Validação da Fase 1 (17/11/2026):

- `uv run ruff check .` → sem problemas
- `uv run ruff format --check .` → 54 arquivos formatados
- `uv run mypy` (estrito) → sem problemas em 47 arquivos
- `uv run pytest` → 39 testes passando
- Qt carrega em modo offscreen e registra as famílias Inter e JetBrains Mono embutidas

Versões principais fixadas: PySide6 6.8.3, aiohttp 3.14.5, zeroconf 0.154.0, cryptography 50.0.2,
argon2-cffi 25.1.0, psutil 7.2.2, watchdog 7.1.0, Send2Trash 2.2.0, tomli-w 1.2.0.

## Fases

| # | Fase | Situação |
|---|---|---|
| 1 | Preparação do repositório | ✅ Concluída |
| 2 | Módulos comuns | ✅ Concluída |
| 3 | Configuração e log de erros | ✅ Concluída |
| 4 | Banco e migrations | ✅ Concluída |
| 5 | Serviço mínimo (com critério de saída da seção 15.5.1) | 🟡 Concluída no Linux; critério 15.5.1 pendente na VM |
| 6 | App mínimo | Bloqueada até o critério 15.5.1 |
| 7 | Contas e sessão | Pendente |
| 8 | Administrador | Pendente |
| 9 | Auditoria | Pendente |
| 10 | Rede local | Pendente |
| 11 | Identidade e TLS | Pendente |
| 12 | Descoberta | Pendente |
| 13 | Criação e gestão básica de pastas | Pendente |
| 14 | Entrada de clientes | Pendente |
| 15 | Navegação e operações | Pendente |
| 16 | Transferências | Pendente |
| 17 | Arrastar e soltar | Pendente |
| 18 | Lixeira | Pendente |
| 19 | Gestão de usuários | Pendente |
| 20 | Encerramento | Pendente |
| 21 | Edição | Pendente |
| 22 | Servidor offline | Pendente |
| 23 | Notificações e bandeja | Pendente |
| 24 | Sair da pasta | Pendente |
| 25 | Revisão de segurança | Pendente |
| 26 | Revisão de qualidade | Pendente |
| 27 | Empacotamento e instalador | Pendente |
| 28 | Piloto em laboratório | Pendente |

O checklist detalhado de cada fase está em `docs/PLANO.md`; marque os itens lá e resuma aqui.

## Checklist da Fase 1 — Preparação do repositório ✅

- [x] `pyproject.toml` (metadados, dependências, pontos de entrada, ruff, mypy, pytest)
- [x] `uv.lock` e `.python-version` (3.12)
- [x] Estrutura e módulos-esqueleto da seção 5.5
- [x] ruff, mypy e pytest passando
- [x] `LICENSE` (GPLv3 oficial)
- [x] Fontes Inter (Regular, Medium, SemiBold, Bold) e JetBrains Mono (Regular, Medium, Bold) com OFL
- [x] Logo oficial em `recursos/icones/drivelan-logo.jpg`
- [x] `recursos/estilo/drivelan.qss` com o bloco TOKENS da paleta do FSD 12.1
- [x] `recursos/traducoes/drivelan_pt_BR.ts`
- [x] `.gitignore` e repositório Git inicializado (branch `main`, sem commits)
- [x] `README.md`, `CLAUDE.md`, `docs/PLANO.md`, `docs/STATUS.md`, `docs/ERROS.md`

## Checklist da Fase 2 — Módulos comuns ✅ (24/11/2026)

- [x] `comum/nomes.py`: RN-68 completa (caracteres proibidos e de controle, nomes reservados com
  ou sem extensão, ponto ou espaço no final, vazio, `.`/`..`, `.drivelan` na raiz, 255 caracteres
  após NFC), comparação NFC + `casefold`, motivos traduzíveis para "Nome inválido: <motivo>."
- [x] Nome adaptado na cópia conforme o SO de destino (FSD 21.9), nomes de duplicidade
  `nome (N).ext` e de conflito `nome (conflito usuario N).ext` (FSD 21.8), com limite de 255
- [x] `comum/caminhos.py`: `CaminhoProtocolo`, formato do FSD 21.4 item 1, `validar_caminho_novo`
  (NFC, RN-68, 1.024 caracteres) e conversão de/para caminhos do SO
- [x] `comum/diretorios.py`: locais da seção 5.6 (Windows e Linux), modo de desenvolvimento
  `--dados <pasta>` (tudo dentro da pasta; socket `<pasta>/local.sock` ou, se o caminho passar de
  100 bytes, `$XDG_RUNTIME_DIR/drivelan-dev-<hash>.sock`; pipe `drivelan-servico-dev-<hash>` no
  Windows), pasta do usuário e `criar_diretorio_privado` (0700)
- [x] `comum/protocolo.py`: constantes (versão, prefixos, porta, cabeçalhos, limites), `CodigoErro`
  com status HTTP da tabela 23.6, mensagens fixas do FSD, mensagem de erro interno com código,
  `ErroProtocolo`, `TipoEvento`/`MensagemEvento` (23.5) e datas ISO UTC com milissegundos
- [x] `comum/i18n.py`: `QT_TRANSLATE_NOOP`, `traduzir`, `formatar`, `instalar_tradutor` (sem Qt)
- [x] Testes em `tests/comum/` (289 casos novos; Unicode, maiúsculas, reservados, `..`, `\`,
  letras de unidade, caminhos de Windows calculados no Linux)

Arquivos principais: `src/drivelan/comum/{nomes,caminhos,diretorios,protocolo,i18n}.py`,
`tests/comum/test_*.py`, `pyproject.toml` (ruff passa a ignorar `N818`, porque as exceções usam
nomes em português, como `NomeInvalido`).

Validação da Fase 2 (24/11/2026):

- `uv run ruff check .` → sem problemas
- `uv run ruff format --check .` → 63 arquivos formatados
- `uv run mypy` (estrito) → sem problemas em 47 arquivos
- `uv run pytest` → 328 testes passando
- `pyside6-lupdate` (no scratchpad, sem alterar o `.ts`) → extrai os 17 textos marcados nos
  contextos `Nomes` e `Protocolo`

Decisões desta fase:

- Os textos dos motivos de nome inválido não estão no FSD; foram propostos no plano e aprovados
  pelo usuário.
- O formato do caminho (`validar_caminho_protocolo`) não aplica NFC, para manter localizáveis os
  itens já existentes com nomes fora da regra; a NFC entra em `validar_caminho_novo` (criar ou
  renomear).
- Ficaram para as próximas fases: os itens 2 a 6 da seção 21.4 no servidor (Fase 15), o código de
  log de 8 caracteres (Fase 3), o cliente do canal local (Fase 5) e o nome de pasta compartilhada
  de 1 a 64 caracteres (Fase 13).

## Checklist da Fase 3 — Configuração e log de erros ✅ (24/11/2026)

- [x] `servico/configuracao.py`: `Configuracao` com os padrões da seção 20.2, `carregar_configuracao`
  (ausente → criado com o modelo comentado do FSD, em modo 0600 e pasta 0700; ilegível → padrões,
  `AVISO` e nunca sobrescrito; valor inválido → padrão da chave e `AVISO`, sem repetir o valor),
  validação de `log.ativo` (booleano), `rede.porta` (inteiro 1024–65535, recusando `true`) e
  `rede.interface` (texto sem caracteres de controle)
- [x] `gravar_valores` e `gravar_atomico`: temporário na mesma pasta (0600), `fsync`, `os.replace`,
  `fsync` da pasta; preserva as demais chaves e seções; recusa arquivo ilegível
  (`ConfiguracaoIlegivel`); em falha o original fica intacto e o temporário é removido
- [x] `MonitorConfiguracao`: carga inicial e verificação do `mtime` no máximo a cada 60 s, aplicando
  `log.ativo` ao log e registrando os avisos (o agendador que chama `verificar` é da Fase 5)
- [x] `servico/log_erros.py`: `LogErros` com linhas no formato da seção 19.1.2 (hora local com fuso
  e milissegundos), níveis `ERRO`/`CRITICO`/`AVISO`, pilha indentada, escape de quebras de linha e
  `|`, arquivo `<logs>/AAAA-MM/AAAA-MM-DD.log` escolhido pela data do evento (rotação diária),
  modos 0600/0700 e trava para uso por várias threads
- [x] Liga/desliga (`definir_ativo`); desligado não grava nem guarda nada
- [x] Contingência: buffer de 500 eventos, saída de erro padrão, nova tentativa após 60 s ou por
  `tentar_novamente()`, despejo em ordem no arquivo de cada dia, sem duplicar em falha parcial;
  `estado_contingencia()` para o aviso da aba Logs de erros (Fase 8)
- [x] `erro_inesperado` gera e devolve o código de 8 hexadecimais maiúsculos (para
  `mensagem_erro_interno`), gravado no contexto `codigo=`
- [x] Segredos: valores de chaves de contexto com `pin`, `token`, `chave`, `senha`, `sessao`,
  `segredo` ou `conteudo` no nome viram `[omitido]`; a pilha não inclui variáveis locais
- [x] `aplicar_retencao(pasta, hoje)`: apaga só arquivos no padrão do log com data anterior a 3 meses
  (fim de mês ajustado) e remove pastas de mês vazias
- [x] Sem `.env`; nenhuma dependência nova

Arquivos principais: `src/drivelan/servico/configuracao.py`, `src/drivelan/servico/log_erros.py`,
`tests/servico/test_configuracao.py`, `tests/servico/test_log_erros.py`, `docs/PLANO.md`.

Validação da Fase 3 (24/11/2026):

- `uv run ruff check .` → sem problemas
- `uv run ruff format --check .` → 65 arquivos formatados
- `uv run mypy` (estrito) → sem problemas em 47 arquivos
- `uv run pytest` → 420 testes passando (92 novos em `tests/servico/`)
- Teste manual em `.dev/fase3` (apagado depois): arquivo criado com os padrões, erro inesperado com
  código e `pin=[omitido]`, `AVISO` para porta inválida e para arquivo ilegível, que foi preservado

Decisões desta fase:

- O arquivo criado do zero usa o modelo comentado da seção 20.2; gravações posteriores pelo
  `tomli-w` preservam as chaves, mas não os comentários (limitação da biblioteca).
- A verificação de que a placa de `rede.interface` existe fica para a Fase 10 (rede local); nesta
  fase o valor só é validado como texto.
- Textos dos avisos de configuração e da mensagem de contingência na saída de erro não estão no
  FSD; são mensagens técnicas do log (não aparecem ao usuário).
- Ficaram para as próximas fases: chamada periódica do monitor, da contingência e da retenção pelo
  agendador e a ordem de inicialização (Fase 5); a contingência do app em `log-contingencia/` e a
  rota `POST /local/v1/app/erros` (Fases 5 e 6, com o canal local); a aba Logs de erros (Fase 8).

## Checklist da Fase 4 — Banco e migrations ✅ (27/11/2026)

- [x] `dados/banco.py`: `abrir_conexao` com os PRAGMAs da seção 11.1 (`foreign_keys`, `WAL`,
  `synchronous = NORMAL`, `busy_timeout = 5000`) em toda conexão, controle explícito de transação
  e conexão somente leitura (`mode=ro`); pasta de dados 0700 e arquivo do banco 0600
- [x] `transacao`: `BEGIN IMMEDIATE` → `COMMIT`, `ROLLBACK` em qualquer exceção
- [x] `BancoDados`: **uma única conexão de escrita numa thread dedicada** e uma segunda conexão
  somente leitura em outra thread; `abrir` executa as migrations antes de liberar o banco; API
  assíncrona (`escrever`, `gravar_em_transacao`, `ler`) e síncrona (`*_sincrono`); `fechar`
  idempotente
- [x] `dados/migracoes.py`: leitura com `importlib.resources`, nomes `NNNN_descricao.sql` em
  ordem numérica, checksum SHA-256, conferência das já aplicadas (`MigracaoAlterada`,
  `MigracaoDesconhecida`: `ERRO` no log e nada é executado), cópia `drivelan.db.antes-NNNN` pela API
  de backup do SQLite (0600, só as 3 mais recentes), uma transação por migration com o registro
  em `schema_migracoes` na mesma transação (`FalhaMigracao` desfaz só a que falhou)
- [x] `0001_inicial.sql`: as 19 tabelas da seção 11.2 com campos, `CHECK`, chaves e ações
  (`CASCADE`/`RESTRICT`), 31 índices (8 parciais, inclusive `(ocorrido_em DESC, id DESC)`), FTS5
  `auditoria_busca` com `trigram` (conteúdo externo) e gatilhos de inclusão e exclusão; linha
  única de `admin_controle`
- [x] Alternativa sem `trigram`: o bloco FTS fica entre marcadores e é pulado quando
  `suporta_trigram` é falso; `busca_fts_disponivel` indica se a consulta usa FTS ou `LIKE`
- [x] Testes: execução duplicada, migration alterada e desconhecida, cópia de segurança e
  retenção de 3 cópias, falha no meio, divisão de comandos, banco sem `trigram`, conjunto exato
  de tabelas e índices, `CHECK`s, índices únicos parciais, FKs e busca FTS (inclusive cascata)

Arquivos principais: `src/drivelan/servico/dados/banco.py`, `src/drivelan/servico/dados/migracoes.py`,
`src/drivelan/servico/dados/migracoes/0001_inicial.sql` (o `.gitkeep` da pasta foi removido),
`tests/servico/test_banco.py`, `tests/servico/test_migracoes.py`,
`tests/servico/test_esquema_0001.py`, `docs/PLANO.md`.

Validação da Fase 4 (27/11/2026):

- `uv run ruff check .` → sem problemas
- `uv run ruff format --check .` → 68 arquivos formatados
- `uv run mypy` (estrito) → sem problemas em 47 arquivos
- `uv run pytest` → 492 testes passando (72 novos)
- Teste manual em `.dev/fase4` (apagado depois): banco criado do zero com 24 tabelas (19 + FTS e
  suas tabelas internas) e 31 índices; segunda abertura não reaplicou nada; arquivo com modo 0600
- `uv build --wheel` (no scratchpad): o `0001_inicial.sql` vai no pacote
- SQLite do ambiente: 3.53.1, com FTS5 e `trigram`

Decisões desta fase (aprovadas no plano):

- `schema_migracoes` é criada pela própria `0001`; sem ela o banco é novo e tudo está pendente.
- Banco novo não recebe cópia de segurança (não há dados); banco já migrado sempre recebe antes
  da primeira pendente, uma cópia por execução.
- `CHECK`s derivados do texto do FSD, sem campos novos: indicadores 0/1, contadores `>= 0`,
  `erros_no_ciclo` de 0 a 4, `motivo_remocao` na lista do FSD, `detalhes` em JSON válido, ator
  `usuario` exige identidade, portas de 1 a 65535.
- A linha de `instalacao` não é criada pela migration (depende do certificado e da chave, Fases 8
  e 11). A consulta de auditoria com FTS ou `LIKE` é da Fase 9; o comando `--migrar` e a nova
  tentativa a cada 30 s, da Fase 5.

## Checklist da Fase 5 — Serviço mínimo 🟡 (27/11/2026)

- [x] `servico/__main__.py`: `--console` (primeiro plano, log também no terminal), `--dados <pasta>`
  e `--migrar` (aplica as migrations e sai; sem `--dados` exige root/administrador, FSD 24.8)
- [x] `servico/inicializacao.py`: as 10 etapas da seção 6.1 em ordem (1 log, 2 configuração,
  3 banco, 8 canal local e 10 agendador implementadas; 4, 5, 6, 7 e 9 aparecem como marcadores das
  Fases 11, 20, 13, 11 e 12); etapas impeditivas (3 e 8) tentam de novo a cada 30 s sem encerrar;
  a parada interrompe a espera; fechamento na ordem agendador → canal → banco
- [x] Laço `asyncio`, pool de 4 threads de disco (executor padrão do laço), `SIGTERM`/`SIGINT` no
  Linux e Ctrl+C no Windows
- [x] `tarefas/agendador.py`: tarefas "a cada N s" e "diariamente às HH:MM" (com execução na
  inicialização); funções síncronas no pool de disco; falha registrada no log sem derrubar nada
- [x] `tarefas/basicas.py`: verificação do `drivelan.toml` (60 s), nova tentativa da contingência do
  log (60 s) e retenção dos logs (03:00 e na inicialização)
- [x] Canal local no Linux (`plataforma/linux.py`): `SO_PEERCRED` (UID e PID) e horário de criação
  do processo; socket antigo removido só se for socket e ninguém responder; outra instância →
  `CanalEmUso`; socket 0666 em produção (`/run/drivelan` 0755) e 0600 em desenvolvimento
- [x] Canal local no Windows (`plataforma/windows_pipe.py` e `windows.py`): `CreateNamedPipe` com
  `PIPE_ACCESS_DUPLEX | FILE_FLAG_OVERLAPPED` (e `FILE_FLAG_FIRST_PIPE_INSTANCE` na primeira),
  `PIPE_REJECT_REMOTE_CLIENTS`, SDDL da seção 15.5.1, instâncias ilimitadas com uma sempre
  aguardando, PID por `GetNamedPipeClientProcessId` e SID pelo token **antes** de qualquer pedido,
  transporte do proactor atendido pelo `aiohttp.web.Server` — **escrito e compilado, mas ainda não
  executado** (não há Windows neste ambiente)
- [x] `api/local/`: middlewares de identidade (uma vez por conexão; sem identidade → 403
  `acesso_negado` e log) e de erros 23.6 (404 `nao_encontrado`; 405, corpo malformado ou > 64 KB →
  400 `requisicao_invalida`; exceção → 500 `erro_interno` com `codigo_log`, sem detalhes técnicos);
  `GET /local/v1/estado`; `GET /local/v1/eventos` (WebSocket mínimo, ping de 30 s, só identidade do
  SO); JSON em UTF-8
- [x] Diagnóstico só em `--console`: uma linha por conexão (`usuario_so` e `pid`) na saída do
  terminal, nunca no arquivo de log (decisão do usuário)
- [x] `comum/canal_local.py`: `UnixConnector`/`NamedPipeConnector`, `ClienteCanalLocal`
  (`obter_estado`, `abrir_eventos`, `pedir_json`), `ErroCanalLocal` (formato 23.6) e
  `ServicoIndisponivel`
- [x] `LogErros` ganhou o parâmetro `espelho` (log também no terminal em `--console`)
- [x] Duas instâncias com `--dados` e `rede.porta` diferentes rodando juntas (teste de integração)
- [ ] **Critério de saída da seção 15.5.1 numa VM Windows 11 com o serviço como LocalSystem**
  (roteiro abaixo) — pendência do usuário; bloqueia a Fase 6

Arquivos principais: `src/drivelan/servico/{__main__,inicializacao,log_erros}.py`,
`src/drivelan/servico/api/local/{aplicacao,estado,eventos,servidor}.py`,
`src/drivelan/servico/tarefas/{agendador,basicas}.py`,
`src/drivelan/servico/plataforma/{__init__,linux,windows,windows_pipe}.py`,
`src/drivelan/comum/{canal_local,protocolo}.py`, `pyproject.toml`, `uv.lock`, testes em
`tests/servico/`, `tests/comum/`, `tests/integracao/` e `tests/test_estrutura.py`, `docs/PLANO.md`,
`docs/ERROS.md`.

Validação da Fase 5 no Fedora (27/11/2026):

- `uv run ruff check .` → sem problemas
- `uv run ruff format --check .` → 83 arquivos formatados
- `uv run mypy` (estrito) → sem problemas em 53 arquivos (os módulos do Windows não são analisados
  no Linux)
- `uv run pytest` → 562 testes passando (70 novos) e 5 pulados (os do Windows); repetido 3 vezes
  sem falhas
- Teste manual em `.dev/` (apagado depois): `--console` sobe e mostra o socket; `curl
  --unix-socket` em `/local/v1/estado` devolve `pronto: true`, aparece a linha de diagnóstico com o
  UID e o PID, rota inexistente → 404 e `POST` no estado → 400, ambos no formato 23.6; duas
  instâncias em pastas diferentes sobem juntas; uma terceira na mesma pasta registra a falha
  impeditiva da etapa 8 e espera 30 s; `SIGTERM` encerra e remove o socket; `--migrar --dados`
  sai com 0 e `--migrar` sem root sai com 2

Decisões desta fase (aprovadas no plano):

- Sem `--console`, o processo roda em primeiro plano (como o systemd espera). O registro como
  serviço do Windows e a unidade systemd ficam para a Fase 27. Na VM, o LocalSystem é obtido por
  uma tarefa agendada como SYSTEM.
- `--migrar` com `--dados` (desenvolvimento) não exige administrador.
- `usuario_so` usa o formato de `so_dono`/`so_usuario`: o UID em texto (Linux) ou o SID (Windows).
- Mensagem dos códigos sem texto próprio no FSD (`nao_encontrado`, `requisicao_invalida`): a
  genérica da seção 19.1.4 (`mensagem_generica()` em `comum/protocolo.py`).
- `aiohttp` passou a exigir `>=3.14` (uso de `web.RequestKey`; versão fixada continua 3.14.5).
  Nenhuma dependência nova.
- Ficaram para as próximas fases: `POST /local/v1/app/erros` e a contingência do app (Fase 6);
  sessões de conta e o fim da sessão pelo WebSocket fechado > 60 s (Fase 7).

### Roteiro do critério 15.5.1 na VM Windows 11 (a fazer pelo usuário)

Pré-requisitos: VM Windows 11 em rede ponte; Git e uv instalados; uma conta de **usuário comum**
(sem administrador) e uma de administrador; o serviço "Servidor" (LanmanServer) ativo, para o teste
pelo caminho de rede.

1. Como usuário comum, clonar o repositório (ex.: `C:\DriveLan`), rodar `uv sync` e depois
   `uv run pytest tests/integracao/test_canal_local_windows.py -v`. Esperado: 5 testes passando
   (HTTP e WebSocket pelo pipe, SID e PID identificados, caminho de rede recusado, segunda
   instância do pipe recusada).
2. Num terminal de **administrador**, subir o serviço como LocalSystem com uma tarefa agendada:

   ```bat
   mkdir C:\DriveLanDev
   schtasks /create /tn DriveLanFase5 /sc once /st 00:00 /ru SYSTEM /f /tr "cmd /c C:\DriveLan\.venv\Scripts\drivelan-service.exe --console --dados C:\DriveLanDev > C:\DriveLanDev-console.txt 2>&1"
   schtasks /run /tn DriveLanFase5
   ```

   Conferir em `C:\DriveLanDev-console.txt` as linhas `canal local em \\.\pipe\drivelan-servico-dev-...`
   e `pronto.`.
3. Como **usuário comum**, em `C:\DriveLan`:

   ```bat
   set DRIVELAN_TESTE_PIPE_DADOS=C:\DriveLanDev
   uv run pytest tests/integracao/test_canal_local_windows.py -v -s
   ```

   Esperado: HTTP e WebSocket passam; o teste mostra "SID deste processo: S-1-5-21-... | PID: N".
   Em `C:\DriveLanDev-console.txt` deve aparecer `conexão local aceita | usuario_so=<mesmo SID>
   pid=<PID>` (o PID é o do processo `python` do pytest, mostrado na linha do teste); o teste do
   caminho de rede precisa passar (acesso recusado).
4. Outro computador: de uma segunda máquina da rede, tentar abrir
   `\\<nome-da-VM>\pipe\drivelan-servico-dev-<hash>` (ex.: no PowerShell de outro Windows,
   `[System.IO.File]::Open("\\<VM>\pipe\<nome>", "Open")`, ou no Fedora `smbclient //<VM>/IPC$ -U
   <usuario>` seguido de `open <nome>`). Esperado: recusado.
5. Parar e remover: `schtasks /end /tn DriveLanFase5` e `schtasks /delete /tn DriveLanFase5 /f`;
   apagar `C:\DriveLanDev` e `C:\DriveLanDev-console.txt`.

Se algum passo falhar, guarde a saída e o arquivo do console e abra um chat para corrigir antes da
Fase 6. Pelo FSD, o pipe não pode ser trocado por TCP local sem revisar o FSD. Se o problema for o
transporte do proactor, a alternativa prevista é a ponte com uma thread por conexão.

## Versionamento

O versionamento (commit e push) é feito pelo próprio usuário. Commit da Fase 1 registrado:
`c94c021 initial commit for DriveLAN project`. Commit da Fase 2:
`ea4b280 Coding started - Phase 2: common modules` (14 arquivos), enviado ao GitHub
(`main` sincronizado com `origin/main`, conferido em 24/11/2026).

Fase 3 (24/11/2026, branch `develop`): entrega pronta para versionar, conferida com `git status`,
sem segredos, banco ou logs. Arquivos: `src/drivelan/servico/configuracao.py`,
`src/drivelan/servico/log_erros.py`, `tests/servico/test_configuracao.py`,
`tests/servico/test_log_erros.py`, `docs/PLANO.md`, `docs/STATUS.md` e `docs/ERROS.md`.
Mensagem sugerida: `Fase 3: configuração (drivelan.toml) e log de erros com contingência e
retenção`. Registrada pelo usuário como `7c27480 Config (drivelan.toml) and error logs`.

Fase 4 (27/11/2026, branch `develop`): entrega pronta para versionar, conferida com `git status`,
sem banco, cópias ou logs. Arquivos: `src/drivelan/servico/dados/banco.py`,
`src/drivelan/servico/dados/migracoes.py`, `src/drivelan/servico/dados/migracoes/0001_inicial.sql`,
remoção de `src/drivelan/servico/dados/migracoes/.gitkeep`, `tests/servico/test_banco.py`,
`tests/servico/test_migracoes.py`, `tests/servico/test_esquema_0001.py`, `docs/PLANO.md`,
`docs/STATUS.md` e `docs/ERROS.md`. Mensagem sugerida:
`Fase 4: banco SQLite e migrations (0001_inicial completa)`. Registrada pelo usuário como
`272ebbd SQLite database and migrations (0001_initial completed)`.

Fase 5 (27/11/2026, branch `develop`): entrega pronta para versionar, conferida com `git status`,
sem banco, logs, sockets ou `.dev/`. Arquivos alterados e novos listados no checklist da Fase 5.
Mensagem sugerida: `Fase 5: serviço mínimo e canal local seguro (Linux validado; pipe do Windows
aguardando VM)`.

## Observações e pendências conhecidas

- O uv foi instalado no usuário (pasta `.local/bin` da home). Se o comando `uv` não for
  encontrado no terminal, adicione essa pasta ao `PATH` do shell.
- A adaptação da logo para os formatos de cada uso (`.ico`, ícone `.desktop`, bandeja) fica para a
  Fase 6 (ícone da janela) e a Fase 27 (instalador), conforme `docs/INSUMOS.md`.
- O carregador da QSS (substituição dos tokens) é implementado na Fase 6.
- O Windows ainda não foi preparado como ambiente de teste (VM Windows 11 em modo ponte). Ele é
  obrigatório para fechar a Fase 5 (roteiro do critério 15.5.1 acima).

## Próximo passo recomendado

1. Versionar a Fase 5.
2. Preparar a VM Windows 11 e executar o **roteiro do critério 15.5.1** (checklist da Fase 5).
3. Com o critério cumprido, marcar a Fase 5 como ✅ e o item correspondente no `docs/PLANO.md`. Depois
   disso, iniciar a **Fase 6 — App mínimo** num chat novo: `drivelan --servico-local`, instância única,
   fontes, QSS com tokens, barra de título própria, `PonteAssincrona` (usando
   `comum/canal_local.ClienteCanalLocal`) e tela "serviço indisponível". Se o critério falhar, corrigir
   o pipe antes de tudo (registrar em `docs/ERROS.md`).

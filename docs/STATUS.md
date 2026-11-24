# Status do projeto DriveLan

**Última atualização:** 24/11/2026 — Fase 3 (configuração e log de erros)
**Fase atual:** Fase 3 concluída · próxima: **Fase 4 — Banco e migrations**

## Estado atual

A base do repositório está pronta: Python 3.12.16 gerenciado pelo uv, dependências da seção 3.2
do FSD instaladas e fixadas no `uv.lock`, estrutura de pastas e módulos-esqueleto da seção 5.5,
ferramentas de qualidade configuradas e passando, licença GPLv3, fontes embutidas, logo oficial,
folha QSS com os tokens oficiais e documentação viva.

Na Fase 2 foi implementado o código compartilhado em `src/drivelan/comum/` (RN-68, caminhos
do protocolo, diretórios por plataforma, protocolo e i18n). Na Fase 3, a leitura e gravação do
`drivelan.toml` (`servico/configuracao.py`) e o log de erros com contingência e retenção
(`servico/log_erros.py`). Os demais módulos continuam como esqueletos; os dois pontos de entrada
só imprimem um aviso.

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
| 4 | Banco e migrations | ⏳ Próxima |
| 5 | Serviço mínimo (com critério de saída da seção 15.5.1) | Pendente |
| 6 | App mínimo | Pendente |
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
retenção`.

## Observações e pendências conhecidas

- O uv foi instalado no usuário (pasta `.local/bin` da home). Se o comando `uv` não for
  encontrado no terminal, adicione essa pasta ao `PATH` do shell.
- A adaptação da logo para os formatos de cada uso (`.ico`, ícone `.desktop`, bandeja) fica para a
  Fase 6 (ícone da janela) e a Fase 27 (instalador), conforme `docs/INSUMOS.md`.
- O carregador da QSS (substituição dos tokens) é implementado na Fase 6.
- O Windows ainda não foi preparado como ambiente de teste (VM Windows 11 em modo ponte); ele é
  obrigatório no fim da Fase 5.

## Próximo passo recomendado

Depois de versionar a Fase 3, iniciar a **Fase 4 — Banco e migrations** em um chat novo:
`dados/banco.py` (conexão de escrita única em thread dedicada, conexão somente leitura, PRAGMAs da
seção 11.1), executor de migrations com `schema_migracoes`, checksum e cópia de segurança, e a
`0001_inicial.sql` completa da seção 11.2. Erros de migration usam o `LogErros` desta fase.

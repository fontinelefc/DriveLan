# Status do projeto DriveLan

**Última atualização:** 24/11/2026 — Fase 2 (módulos comuns)
**Fase atual:** Fase 2 concluída · próxima: **Fase 3 — Configuração e log de erros**

## Estado atual

A base do repositório está pronta: Python 3.12.16 gerenciado pelo uv, dependências da seção 3.2
do FSD instaladas e fixadas no `uv.lock`, estrutura de pastas e módulos-esqueleto da seção 5.5,
ferramentas de qualidade configuradas e passando, licença GPLv3, fontes embutidas, logo oficial,
folha QSS com os tokens oficiais e documentação viva.

Na Fase 2 foi implementado o código compartilhado em `src/drivelan/comum/` (RN-68, caminhos
do protocolo, diretórios por plataforma, protocolo e i18n). Os demais módulos continuam como
esqueletos; os dois pontos de entrada só imprimem um aviso.

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
| 3 | Configuração e log de erros | ⏳ Próxima |
| 4 | Banco e migrations | Pendente |
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

## Versionamento

O versionamento (commit e push) é feito pelo próprio usuário. Commit da Fase 1 registrado:
`c94c021 initial commit for DriveLAN project`. Commit da Fase 2: **aguardando o usuário**
(mensagem sugerida: `Fase 2: módulos comuns (RN-68, caminhos, diretórios, protocolo, i18n)`).

## Observações e pendências conhecidas

- O uv foi instalado no usuário (pasta `.local/bin` da home). Se o comando `uv` não for
  encontrado no terminal, adicione essa pasta ao `PATH` do shell.
- A adaptação da logo para os formatos de cada uso (`.ico`, ícone `.desktop`, bandeja) fica para a
  Fase 6 (ícone da janela) e a Fase 27 (instalador), conforme `docs/INSUMOS.md`.
- O carregador da QSS (substituição dos tokens) é implementado na Fase 6.
- O Windows ainda não foi preparado como ambiente de teste (VM Windows 11 em modo ponte); ele é
  obrigatório no fim da Fase 5.

## Próximo passo recomendado

Depois de versionar a Fase 2, iniciar a **Fase 3 — Configuração e log de erros** em um chat novo:
`drivelan.toml` com `tomllib`/`tomli-w` (padrões, validação, gravação atômica), log diário em
`<logs>/AAAA-MM/AAAA-MM-DD.log`, contingência, código curto de 8 caracteres e retenção de 3 meses.
Ela usa `comum/diretorios.py` (campos `configuracao` e `logs`).

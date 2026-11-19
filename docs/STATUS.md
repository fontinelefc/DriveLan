# Status do projeto DriveLan

**Última atualização:** 17/11/2026 — preparação do terreno (Fase 1)
**Fase atual:** Fase 1 concluída · próxima: **Fase 2 — Módulos comuns**

## Estado atual

A base do repositório está pronta: Python 3.12.16 gerenciado pelo uv, dependências da seção 3.2
do FSD instaladas e fixadas no `uv.lock`, estrutura de pastas e módulos-esqueleto da seção 5.5,
ferramentas de qualidade configuradas e passando, licença GPLv3, fontes embutidas, logo oficial,
folha QSS com os tokens oficiais e documentação viva.

Nenhuma funcionalidade de negócio foi implementada. Os módulos em `src/drivelan/` contêm apenas
docstrings que indicam a fase responsável; os dois pontos de entrada só imprimem um aviso.

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
| 2 | Módulos comuns | ⏳ Próxima |
| 3 | Configuração e log de erros | Pendente |
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

## Observações e pendências conhecidas

- O uv foi instalado no usuário (pasta `.local/bin` da home). Se o comando `uv` não for
  encontrado no terminal, adicione essa pasta ao `PATH` do shell.
- O repositório Git foi inicializado, mas **nenhum commit foi feito**. Sugestão: revisar os arquivos
  e fazer o commit inicial.
- A adaptação da logo para os formatos de cada uso (`.ico`, ícone `.desktop`, bandeja) fica para a
  Fase 6 (ícone da janela) e a Fase 27 (instalador), conforme `docs/INSUMOS.md`.
- O carregador da QSS (substituição dos tokens) é implementado na Fase 6.
- O Windows ainda não foi preparado como ambiente de teste (VM Windows 11 em modo ponte); ele é
  obrigatório no fim da Fase 5.

## Próximo passo recomendado

Iniciar a **Fase 2 — Módulos comuns** em um chat novo: regra de nomes RN-68, caminhos do
protocolo, diretórios por plataforma, códigos de erro e i18n, com testes unitários extensos.

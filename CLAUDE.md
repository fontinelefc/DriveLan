# CLAUDE.md — contexto do projeto DriveLan

## Idioma

Responder **sempre em português do Brasil**: mensagens, comentários, docstrings, textos da
interface, nomes de módulos e de funções (o código já segue esse padrão).

## Protocolo dos arquivos vivos

```text
Antes de iniciar qualquer trabalho:
1. Ler `docs/FSD.md`.
2. Ler `docs/DESIGN.md`.
3. Ler `docs/INSUMOS.md`.
4. Ler `docs/PLANO.md`.
5. Ler `docs/STATUS.md`.
6. Ler `docs/ERROS.md`.

Use sempre caminhos relativos à raiz do projeto.
Não transformar estes caminhos em links absolutos.
Não usar links `file:///`.
Não registrar caminhos locais da máquina atual dentro do `CLAUDE.md`.

Ao terminar qualquer trabalho:
1. Atualizar `docs/STATUS.md`.
2. Registrar erros e soluções em `docs/ERROS.md`, se houver.
3. Informar ao usuário o que foi feito.
4. Informar como testar ou validar a entrega.
```

- `docs/FSD.md` é a fonte de verdade de comportamento, regras, dados, protocolo e segurança.
  Em divergência visual, prevalece a seção 12.1 do FSD sobre o `docs/DESIGN.md`.
- `docs/code.html`, `docs/screen.png` e `docs/Captura de tela de 2026-11-13 18-38-14.png` são
  **só referência de composição visual**. Não implementar textos, fluxos, CDNs, caminhos SMB,
  "Visualizar PIN", recuperação de PIN nem nada que contrarie o FSD (FSD seção 2).
- Os arquivos da raiz `PRD_DriveLan.md`, `DECISOES_TECNICAS.md` e o `.txt` de exploração são
  histórico das etapas anteriores; o FSD já os consolida.
- Construir **uma fase do `docs/PLANO.md` por vez**, na ordem. Não adiantar funcionalidades.

## O que é o sistema

DriveLan: app **desktop** (Windows 10/11 64 bits e Linux, Fedora como referência) para criar,
encontrar e usar pastas compartilhadas na LAN, sem nuvem, sem SMB e **sem acesso por navegador**.
Licença GPLv3. Não é um sistema web: não existem PHP, MySQL, servidor web público, pasta pública,
XAMPP ou hospedagem.

Dois processos por computador (FSD 5.2):

- `drivelan-service`: serviço do SO (LocalSystem / root), sem interface. Única parte que acessa o
  banco e a rede. Hospeda as pastas, aplica as regras, grava auditoria e logs.
- `drivelan`: app de janela + bandeja, um por sessão do usuário do SO. Única parte que lê e grava
  no disco do usuário (cópias, pasta de edição, pendências, Lixeira do SO). Nunca abre conexões de
  rede e nunca acessa o banco.

## Stack (FSD 3) — não trocar nem acrescentar sem revisar o FSD

| Item | Definição |
|---|---|
| Linguagem | Python **3.12** (mesma versão em todos os pacotes) |
| Interface | PySide6 **6.8.x** (Qt Widgets), estilizada pela folha QSS central |
| Banco | SQLite (`sqlite3`), gravado só pelo serviço, FTS5 na auditoria |
| Rede | HTTP + WebSocket sobre **TLS** (aiohttp), porta TCP fixa (padrão 47820) |
| Descoberta | mDNS/DNS-SD (zeroconf) + broadcast UDP de reserva + adição manual |
| Canal local | HTTP/WebSocket sobre socket Unix (Linux) ou named pipe próprio (Windows, FSD 15.5.1) |
| Outras libs | cryptography, argon2-cffi, psutil, watchdog, Send2Trash, tomli-w, pywin32 (só Windows) |
| Dev | uv, pytest, pytest-qt, pytest-asyncio, ruff, mypy |
| Padrão | Organização inspirada em MVC (FSD 5.4) |

Toda dependência nova precisa de licença compatível com GPLv3 **e** de aprovação do usuário.

### Restrições técnicas (FSD 3.4 e 1.6)

- Proibido: serviços externos, CDNs, telemetria, atualização automática, comunicação fora da LAN.
- Proibido acessar o banco a partir do app `drivelan`.
- Proibido executar rede ou disco na thread da interface (a janela nunca trava).
- Proibido arquivo `.env`. Configuração técnica só no `drivelan.toml` (FSD 20.2), sem credenciais.
- Só IPv4 na v1.
- Fontes e ícones embutidos; nada é baixado em tempo de execução.
- Não existe "sincronização contínua": termos como "sync" no material de design são só visuais.

## Ambientes (FSD 4)

- **Desenvolvimento:** Fedora, Python 3.12 via uv (`.venv` na raiz), VS Code, Git. Os processos
  rodam sem instalação:
  - `uv run drivelan-service --console --dados .dev/<nome>` (a partir da Fase 5);
  - `uv run drivelan --servico-local <caminho-do-socket>` (a partir da Fase 6);
  - duas instâncias do serviço com pastas de dados e portas diferentes simulam dono e cliente.
- **Testes:** pytest no Linux e no Windows; VM Windows 11 em rede **ponte (bridge)** na mesma LAN.
- **Homologação:** piloto em laboratório com Windows 11 e Windows 10 (FSD 26.3).
- **Produção:** GitHub Releases com `.exe` (Windows), `.rpm` e `.deb` (Linux), requisitos da
  seção 4.5. A ferramenta de empacotamento é escolhida na Fase 27.

## Estrutura de pastas (FSD 5.5)

```text
pyproject.toml / uv.lock / .python-version   metadados, dependências fixadas, Python 3.12
LICENSE                                      GPLv3
docs/                                        documentação (NÃO é pasta pública do sistema)
src/drivelan/
  comum/        código compartilhado (nomes, caminhos, protocolo, canal local, diretórios, i18n)
  servico/      drivelan-service
    api/local/  rotas do canal local      api/rede/  rotas do protocolo entre instalações
    regras/     casos de uso (única camada que decide o que é permitido)
    dados/      banco.py, migracoes.py, migracoes/*.sql, repositorios/
    rede/ arquivos/ tarefas/ plataforma/
  app/          drivelan
    controladores/ modelos/ telas/ componentes/ edicao/ transferencias/
recursos/       estilo/drivelan.qss, fontes/ (Inter, JetBrains Mono, OFL), icones/, traducoes/
empacotamento/  windows/, linux/   (Fase 27)
tests/          servico/, app/, integracao/
```

Regras da estrutura:

- `servico/` e `app/` **não importam um ao outro** (há teste automático); compartilham só por `comum/`.
- MVC: telas (`app/telas/`, `app/componentes/`) não acessam banco, rede, canal local nem disco e não
  têm regras; controllers falam com o serviço pelo canal local via `PonteAssincrona`; no serviço,
  `api/` valida e delega, `regras/` decide, `dados/` só faz SQL.
- Não existem `logs/`, `config/`, `public/`, `htdocs/` ou `www/` no repositório. Banco,
  certificado, configuração e logs ficam nos diretórios do sistema da seção 5.6 (ou em `.dev/`
  durante o desenvolvimento, ignorado pelo Git).
- O banco é criado e alterado **somente por migrations** numeradas em
  `src/drivelan/servico/dados/migracoes/` (`0001_inicial.sql`, `0002_<descricao>.sql`…).
  Nunca editar uma migration já aplicada: criar uma nova.

## Comandos principais

```bash
uv sync                        # instalar/atualizar o ambiente (.venv) a partir do uv.lock
uv add <pacote>                # só com aprovação do usuário e licença compatível com GPLv3
uv run ruff check .            # lint
uv run ruff format .           # formatar (use --check para só verificar)
uv run mypy                    # tipagem estrita do pacote drivelan
uv run pytest                  # todos os testes
uv run drivelan-service        # ponto de entrada do serviço
uv run drivelan                # ponto de entrada do app
uv run drivelan-service --migrar   # executar migrations (a partir das Fases 4/5)
```

Antes de dar uma fase por concluída: ruff, formatação, mypy e pytest sem erros.

## Regras de segurança (FSD 15, 16, 19, 21, 24)

**Banco e dados**
- SQL sempre com parâmetros (`?`/nomeados); nunca montar SQL com f-string ou concatenação de entrada.
- Gravações em mais de uma tabela numa única transação.
- Banco, certificado e chave privada só na pasta de dados protegida (0700 / SYSTEM+Administradores).

**Credenciais**
- PINs (4 e 6 dígitos) e chave de segurança só como hash **Argon2id** (64 MiB, 3 iterações,
  paralelismo 1, sal de 16 bytes), calculado fora do laço `asyncio`.
- Tokens de acesso: `secrets.token_urlsafe(32)`; no servidor só o SHA-256. Sessões só em memória.
- Login com nome inexistente responde igual a conta real (contador fictício, hash fictício).
- Bloqueios por tentativas persistidos: conta (5), PIN de pasta (5 por instalação e IP, 15 min),
  chave (5 por ciclo, crescente).
- A chave de segurança é lida pela entrada padrão (`--definir-chave`), nunca por argumento.
- PINs, tokens, chave e conteúdo de arquivos **nunca** em logs, auditoria, mensagens ou eventos.

**Canal local**
- Identificar o usuário do SO e o PID de cada conexão (`SO_PEERCRED` / `GetNamedPipeClientProcessId`).
- Sessão vinculada à conta + usuário do SO + processo; recusar token de outro usuário ou processo.
- Named pipe com o SDDL da seção 15.5.1 e `PIPE_REJECT_REMOTE_CLIENTS`. Não trocar por TCP local.
- Rotas de gestão, contas e administração existem **só** no canal local, nunca na rede.

**Rede**
- TLS 1.2+ em toda conexão; confiança no primeiro uso pela impressão digital (RN-67), sem
  "confiar mesmo assim".
- Toda rota verifica sessão, papel e token na camada `regras/` (FSD 16.2); a interface nunca é a
  única barreira. Respostas `401 sessao_invalida` e `403 acesso_negado`.
- Limites: JSON ≤ 64 KB, ≤ 20 sessões de transporte por IP, ≤ 10 pedidos de PIN/min por IP,
  mensagens UDP ≤ 1 KB.
- O servidor só lê e grava dentro das pastas compartilhadas e nunca serve instalação, banco,
  configuração ou logs.

**Arquivos**
- Validar todo caminho recebido (FSD 21.4): relativo com `/`, sem `..`, `\`, letra de unidade,
  links, junções ou pontos de montagem; resolvido dentro da raiz; `.drivelan` inacessível.
- Regra única de nomes RN-68 em criação, renomeação, envio e movimentação.
- Recebimentos em `.drivelan/tmp/` e movimentação atômica; nunca sobrescrever em silêncio.
- Arquivos só são abertos pelo programa padrão a pedido explícito do usuário.
- Instalador e migrations nunca apagam arquivos das pastas compartilhadas.

**Erros e logs**
- O usuário nunca vê pilha, caminhos internos ou mensagens técnicas: mensagem genérica com
  código de 8 caracteres gravado no log (FSD 19.1.4).
- Logs em pasta acessível só ao serviço e aos administradores do SO; nunca servidos pela rede.
- Validar entradas no serviço (formato e faixa, FSD 14.2), mesmo que o app já valide.

## Boas práticas

- Código claro, funções pequenas, nomes descritivos em português, tipagem completa (mypy estrito).
- Comentários e docstrings úteis em português, citando a seção ou regra do FSD quando ajudar
  (ex.: `# RN-20`, `FSD 13.14`).
- Sem duplicação desnecessária; reutilizar `comum/` e os componentes de interface.
- Testes junto com cada regra de negócio, repositório, validação e rota.
- Nada fora do escopo do FSD (seção 7). Na dúvida, perguntar ao usuário.
- Mensagens e textos exatamente como definidos no FSD.

## Interface

- Seguir `docs/DESIGN.md` **com as correções da seção 12.1 do FSD**: paleta do texto descritivo
  (tokens YAML do DESIGN.md descartados), raios de 12px (cartões/painéis) e 8px (botões/campos),
  pílula em chips, sem `backdrop-filter`, selos "Pasta local" (#8B5CF6) e "Pasta da rede" (#22D3EE).
- Cores, fontes e raios **só** em `recursos/estilo/drivelan.qss`, pelos tokens do bloco TOKENS.
  Nenhum widget define cores no código.
- Inter em toda a interface; JetBrains Mono para IPs, identificadores, impressões digitais, PINs e
  a janela do administrador. Fontes carregadas de `recursos/fontes/`.
- Todos os textos em português e marcados para tradução (`self.tr()` / `QCoreApplication.translate`).
- Janela mínima 800 × 600, inicial 1200 × 800, barra de título própria de 38px.
- Estados de lista: carregando, vazio, erro e serviço indisponível (FSD 12.2).

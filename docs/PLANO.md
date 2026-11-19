# Plano de construção do DriveLan v1

> Fonte: `docs/FSD.md`, principalmente a seção 25 (organização sugerida da implementação) e a
> seção 26 (critérios de aceitação). As 28 fases abaixo seguem **a mesma numeração e ordem** das
> etapas da seção 25. Cada fase é pequena, termina com algo funcionando e testado, e só começa
> quando as dependências indicadas estiverem prontas.
>
> Regras que valem para todas as fases:
>
> - nada fora do escopo do FSD (seção 7 lista o que **não** entra na v1);
> - separação MVC e de processos da seção 5 (rede só no serviço, disco do usuário só no app,
>   `servico/` e `app/` só compartilham código por `comum/`);
> - nenhuma operação de rede ou disco na thread da interface;
> - textos da interface em português, marcados para tradução;
> - toda fase termina com `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` e
>   `uv run pytest` sem erros, e com `docs/STATUS.md` atualizado.

---

## Fase 1 — Preparação do repositório

**Objetivo:** criar a base do projeto, com dependências fixadas, a estrutura de pastas da seção 5.5
e as ferramentas de qualidade rodando (FSD 25, etapa 1).

**Checklist**

- [x] `pyproject.toml` com metadados, dependências da seção 3.2 e pontos de entrada `drivelan-service` e `drivelan`
- [x] Python 3.12 e dependências fixadas em `uv.lock`; `.python-version`
- [x] Estrutura de pastas e módulos-esqueleto da seção 5.5 (sem lógica)
- [x] ruff, mypy (estrito) e pytest configurados e passando
- [x] `LICENSE` com o texto oficial da GPLv3
- [x] Fontes Inter e JetBrains Mono (OFL) em `recursos/fontes/`
- [x] Logo oficial copiada para `recursos/icones/` (insumo marcado como usado em `docs/INSUMOS.md`)
- [x] Folha QSS central com os tokens oficiais (FSD 12.1) e arquivo `.ts` de tradução
- [x] `.gitignore` protegendo banco, certificados, logs e dados de desenvolvimento
- [x] `README.md`, `CLAUDE.md`, `docs/PLANO.md`, `docs/STATUS.md`, `docs/ERROS.md`

**Critérios de pronto:** `uv sync` instala tudo; ruff, mypy e pytest passam; os dois pontos de
entrada executam; teste automático confirma que `servico/` e `app/` não se importam.

**Áreas alteradas:** raiz do repositório, `src/drivelan/`, `recursos/`, `empacotamento/`, `tests/`, `docs/`.

---

## Fase 2 — Módulos comuns

**Objetivo:** implementar o código compartilhado entre serviço e app (FSD 25, etapa 2).

**Checklist**

- [ ] Regra única de nomes RN-68 (`comum/nomes.py`): caracteres proibidos, nomes reservados, ponto/espaço final, `.drivelan` na raiz, 255/1.024 caracteres, NFC, comparação sem maiúsculas
- [ ] Nome adaptado na cópia para o computador (RN-68) e nomes gerados de duplicidade e conflito (FSD 21.8)
- [ ] Caminhos do protocolo (`comum/caminhos.py`): validação de formato relativo com `/` (FSD 21.4, item 1) e conversão para o SO
- [ ] Diretórios do sistema por plataforma (`comum/diretorios.py`, FSD 5.6), com pasta de dados alternativa para desenvolvimento
- [ ] Códigos de erro, formato de erro e versão do protocolo (`comum/protocolo.py`, FSD 23.6)
- [ ] Base de textos traduzíveis (`comum/i18n.py`)
- [ ] Testes unitários extensos (Unicode, maiúsculas, nomes reservados com extensão, `..`, `\`, letras de unidade)

**Critérios de pronto:** cobertura de todos os casos da RN-68 e da seção 21.4 (item 1) em testes, rodando em Linux.

**Áreas:** `src/drivelan/comum/`, `tests/servico/` ou `tests/comum/`.

**Dependências:** Fase 1.

---

## Fase 3 — Configuração e log de erros

**Objetivo:** ler e gravar o `drivelan.toml` e registrar erros em arquivos diários (FSD 25, etapa 3).

**Checklist**

- [ ] Leitura com `tomllib` e valores padrão (`log.ativo`, `rede.interface`, `rede.porta`), validação e fallback (FSD 20.2)
- [ ] Gravação atômica com `tomli-w`, preservando as demais chaves; arquivo ausente é criado; ilegível não é sobrescrito
- [ ] Log em `<logs>/AAAA-MM/AAAA-MM-DD.log`, formato e níveis da seção 19.1.2
- [ ] Liga/desliga por `log.ativo`, com verificação da data de modificação a cada 60 s
- [ ] Contingência: buffer de 500 eventos, saída de erro padrão, nova tentativa a cada 60 s (FSD 19.1.5)
- [ ] Código curto de 8 caracteres para erros inesperados (FSD 19.1.4)
- [ ] Retenção de 3 meses (função usada depois pelo agendador)
- [ ] Garantia de que PINs, tokens e chave nunca são registrados
- [ ] Sem `.env`

**Critérios de pronto:** testes cobrindo padrões, valores inválidos, gravação atômica, rotação diária, contingência e retenção.

**Áreas:** `src/drivelan/servico/configuracao.py`, `src/drivelan/servico/log_erros.py`, `tests/servico/`.

**Dependências:** Fase 2 (diretórios).

---

## Fase 4 — Banco e migrations

**Objetivo:** criar o banco SQLite completo, somente por migrations (FSD 25, etapa 4).

**Checklist**

- [ ] `dados/banco.py`: conexão de escrita única em thread dedicada, conexão somente leitura, PRAGMAs da seção 11.1, transações
- [ ] `dados/migracoes.py`: `schema_migracoes`, ordem numérica, checksum SHA-256, cópia `drivelan.db.antes-<versao>` (3 mais recentes), uma transação por migration
- [ ] `0001_inicial.sql` com **todas** as tabelas, campos, `CHECK`, chaves, índices (inclusive parciais), FTS5 `auditoria_busca` com `trigram` e gatilhos da seção 11.2; linha única de `admin_controle`
- [ ] Alternativa `LIKE` quando o SQLite não suportar `trigram`
- [ ] Testes: execução duplicada, migration alterada (para sem corromper), cópia de segurança, constraints e índices únicos parciais

**Critérios de pronto:** banco criado do zero em pasta temporária com todas as estruturas; testes de integridade passando.

**Áreas:** `src/drivelan/servico/dados/`, `src/drivelan/servico/dados/migracoes/`, `tests/servico/`.

**Dependências:** Fases 2 e 3.

---

## Fase 5 — Serviço mínimo

**Objetivo:** `drivelan-service --console` iniciando na ordem da seção 6.1 e canal local seguro (FSD 25, etapa 5).

**Checklist**

- [ ] Opções de linha de comando: `--console`, `--dados`, `--migrar` (demais comandos protegidos ficam nas fases que os usam)
- [ ] Ordem de inicialização da seção 6.1, com nova tentativa a cada 30 s em falha impeditiva, sem encerrar
- [ ] Laço `asyncio` principal, pool de threads para disco, esqueleto do agendador
- [ ] Canal local no Linux: socket Unix `/run/drivelan/local.sock` (ou caminho de desenvolvimento), `SO_PEERCRED` (UID e PID)
- [ ] Canal local no Windows: servidor próprio do named pipe (`plataforma/windows_pipe.py`, FSD 15.5.1) com SDDL, `PIPE_REJECT_REMOTE_CLIENTS`, SID e PID do cliente, `aiohttp.web.Server`
- [ ] Rota `GET /local/v1/estado` e formato de erro da seção 23.6
- [ ] Cliente do canal local em `comum/canal_local.py` (`UnixConnector` / `NamedPipeConnector`)
- [ ] Duas instâncias com pastas de dados e portas diferentes na mesma máquina

**Critérios de pronto:** serviço sobe em modo console no Fedora; teste automatizado do canal local; **critério de saída obrigatório da seção 15.5.1** cumprido numa VM Windows 11 com o serviço como LocalSystem. Se não for atingido, a implementação para e o FSD é revisado (não substituir por TCP local).

**Áreas:** `src/drivelan/servico/__main__.py`, `inicializacao.py`, `api/local/`, `tarefas/`, `plataforma/`, `src/drivelan/comum/canal_local.py`, `tests/servico/`, `tests/integracao/`.

**Dependências:** Fases 3 e 4. **Bloqueia a Fase 6.**

---

## Fase 6 — App mínimo

**Objetivo:** janela base do app, com visual oficial e comunicação assíncrona com o serviço (FSD 25, etapa 6).

**Checklist**

- [ ] `drivelan --servico-local <caminho>` para desenvolvimento
- [ ] Instância única por usuário do SO (`QLocalServer` `drivelan-app-<SID ou UID>`, FSD 5.2)
- [ ] Carga das fontes embutidas com `QFontDatabase.addApplicationFont`
- [ ] Carregador da folha QSS central com substituição dos tokens (`recursos/estilo/drivelan.qss`)
- [ ] Barra de título própria de 38 px (FSD 12.1): botões 46 × 38, `startSystemMove`/`startSystemResize`; no Windows, `WM_NCHITTEST` (Snap Layouts) e cantos arredondados via DWM
- [ ] Janela mínima 800 × 600, inicial 1200 × 800; barra lateral 240/64 px; área para painel direito de 320 px
- [ ] `PonteAssincrona` (laço `asyncio` em thread própria, resultados por sinais Qt)
- [ ] Tela "serviço indisponível" com nova tentativa a cada 5 s (FSD 12.2)
- [ ] Estados comuns de lista (carregando, vazio, erro) como componentes
- [ ] Ícone do app a partir de `recursos/icones/drivelan-logo.jpg` (adaptação de formatos decidida aqui ou na Fase 27)
- [ ] Testes com pytest-qt

**Critérios de pronto:** app abre, conecta ao serviço de desenvolvimento, nunca trava; sem cores definidas no código dos widgets.

**Áreas:** `src/drivelan/app/` (`__main__.py`, `ponte_assincrona.py`, `componentes/`, `telas/`, `controladores/`), `recursos/estilo/`, `tests/app/`.

**Dependências:** Fase 5 (incluindo o critério da seção 15.5.1).

---

## Fase 7 — Contas e sessão

**Objetivo:** cadastro, login e ciclo de vida da sessão local (FSD 6.2, 12.3, 12.4, 13.1–13.7, 15).

**Checklist**

- [ ] Regras e repositórios de conta e identidade; Argon2id (64 MiB, 3 iterações, paralelismo 1) fora do laço principal
- [ ] Rotas `/local/v1/contas`, `/sessao`, `/sessao/desbloquear`, `/conta/pin`, `/conta/nome`, `/conta`
- [ ] Token de sessão vinculado à conta, ao usuário do SO e ao processo (PID + horário de criação); expiração pelo WebSocket local fechado > 60 s
- [ ] Login com nome inexistente indistinguível (contador fictício em memória, hash fictício)
- [ ] Bloqueio após 5 erros (fluxo 13.4) numa transação; uma sessão por conta (FSD 14.4)
- [ ] Troca obrigatória de PIN temporário; alterar nome (com histórico) e PIN; excluir conta
- [ ] Telas de login, cadastro, troca obrigatória e desbloqueio com PIN segmentado (DESIGN.md)
- [ ] Fechar a janela mantém a sessão; reabrir exige PIN (FSD 15.3)
- [ ] Auditoria dos eventos de conta (gravação simples; consulta na Fase 9)

**Critérios de pronto:** critérios funcionais de "Cadastro e login" (FSD 26.2) cobertos em testes e verificados no app.

**Áreas:** `servico/regras/`, `servico/dados/repositorios/`, `servico/api/local/`, `app/telas/`, `app/controladores/`, `app/componentes/`.

**Dependências:** Fases 4, 5 e 6.

---

## Fase 8 — Administrador

**Objetivo:** chave de segurança e janela de administração (FSD 6.11, 12.15, 12.16, 13.25, 15.6).

**Checklist**

- [ ] `drivelan-service --definir-chave` (lê da entrada padrão, 12 a 128 caracteres, guarda só o hash)
- [ ] Shift + F12 em todas as janelas (`QShortcut` de aplicação), inclusive no login
- [ ] Janela terminal 520 × 220, sempre em primeiro plano, sem eco de caracteres
- [ ] Bloqueio crescente RN-58 (`admin_controle`), auditoria sem o conteúdo digitado
- [ ] Sessão de administrador vinculada ao usuário do SO e ao processo
- [ ] Aba **Logs de erros**: meses/dias, leitura em blocos de 1.000 linhas, busca progressiva, limpeza (dia, mês, todos), aviso de log desligado e de contingência
- [ ] Aba **Resgate de usuários**: PIN temporário, reativação de conta, pastas e acessos (RN-52)
- [ ] Aba **Auditoria das pastas** (estrutura; consulta completa na Fase 9)

**Critérios de pronto:** critérios funcionais de "Administrador" e "Logs de erros" (FSD 26.2), exceto os que dependem de pastas.

**Áreas:** `servico/__main__.py`, `servico/regras/`, `servico/api/local/`, `app/telas/`, `app/controladores/`.

**Dependências:** Fases 3 e 7.

---

## Fase 9 — Auditoria

**Objetivo:** registro e consulta completa da auditoria (FSD 9.3, 17, 22.2).

**Checklist**

- [ ] Serviço único de registro com os códigos da seção 17.2 e sem segredos
- [ ] Consulta com escopo aplicado antes dos filtros (dono / administrador), filtros por período, usuário, ação e busca (FTS5 ou `LIKE`)
- [ ] Paginação por cursor, 100 registros; exibição `nome_atual@host (nome_anterior)`
- [ ] Retenção: 12 meses; pastas apagadas após 1 mês; limpeza de identidades sem referência
- [ ] Componente de consulta reutilizável (aba do administrador agora; aba do dono na Fase 13)
- [ ] Teste de desempenho com 12 meses simulados (< 1 s por página)

**Critérios de pronto:** critérios funcionais de "Auditoria" (FSD 26.2) cobertos para eventos de conta e de administração.

**Áreas:** `servico/regras/`, `servico/dados/repositorios/`, `servico/tarefas/`, `app/telas/`, `app/modelos/`.

**Dependências:** Fases 4, 7 e 8.

---

## Fase 10 — Rede local

**Objetivo:** identificar a placa e a rede e permitir a troca de placa (FSD 6.3, 6.3.1, 13.27).

**Checklist**

- [ ] Placa principal pela rota padrão (socket UDP para `192.0.2.1`), fallback por IPv4 privado
- [ ] Endereço e CIDR por `psutil`; nome da rede por `netsh` (Windows) e `nmcli` / `/sys/class/net` (Linux)
- [ ] Detecção de VPN e placas sempre ignoradas
- [ ] Reavaliação a cada 30 s e na mudança de endereço
- [ ] Rotas `/local/v1/rede`, `/rede/placas`, `/rede/placa`; gravação de `rede.interface`
- [ ] Cabeçalho do dashboard com a rede; tela Configurações do app (placa, versão, porta)

**Critérios de pronto:** dashboard mostra rede, IP e faixa; troca de placa funciona; VPN marcada "VPN — ignorada por padrão".

**Áreas:** `servico/rede/interfaces.py`, `servico/api/local/`, `app/telas/`, `app/controladores/`.

**Dependências:** Fases 3, 6 e 7.

---

## Fase 11 — Identidade e TLS

**Objetivo:** identidade criptográfica da instalação e sessões de transporte seguras (FSD 23.4, 24.2).

**Checklist**

- [ ] Certificado ECDSA P-256 autoassinado (20 anos) e chave privada em `<dados>/certificado/`; `instalacao_id` = SHA-256 do DER
- [ ] `--regenerar-identidade`
- [ ] Servidor TLS (1.2+, preferência 1.3) na porta configurada, rotas `/v1/servidor`, `/v1/sessao/desafio`, `/v1/sessao`
- [ ] Desafio assinado, sessão de transporte de 12 h vinculada ao IP, criação/atualização de identidade e troca de nome
- [ ] Cliente remoto com `aiohttp.Fingerprint`; confiança no primeiro uso e "Identidade alterada" (RN-67)
- [ ] Limites da seção 24.9 (64 KB de JSON, 20 sessões por IP)

**Critérios de pronto:** teste de integração com dois serviços locais estabelecendo sessão de transporte; identidade trocada é bloqueada.

**Áreas:** `servico/rede/tls.py`, `servico/rede/cliente_remoto.py`, `servico/api/rede/`, `tests/integracao/`.

**Dependências:** Fases 4 e 5.

---

## Fase 12 — Descoberta

**Objetivo:** encontrar servidores DriveLan na LAN (FSD 13.9, 23.2).

**Checklist**

- [ ] Anúncio `_drivelan._tcp.local.` com TXT `v`, `id`, `h`, só na placa escolhida, convivendo com o Avahi
- [ ] Broadcast UDP de reserva com limite de 10 respostas/s por IP e descarte de mensagens inválidas
- [ ] Adição e remoção de servidor manual (`/local/v1/servidores`, FSD 12.7, 13.28)
- [ ] `GET /v1/pastas` e `GET /local/v1/rede/pastas` com atualizações incrementais; offline após 90 s
- [ ] Detecção de identificador duplicado (computador clonado) com `AVISO` no log
- [ ] Tela "Pastas da rede" (lista completa) e resumo no dashboard; modal "Adicionar servidor"

**Critérios de pronto:** duas instâncias se descobrem por mDNS e por broadcast separadamente; adição manual funciona.

**Áreas:** `servico/rede/anuncio_mdns.py`, `servico/rede/broadcast.py`, `servico/api/`, `app/telas/`, `app/modelos/`.

**Dependências:** Fases 10 e 11.

---

## Fase 13 — Criação e gestão básica de pastas

**Objetivo:** o dono cria e configura pastas compartilhadas (FSD 6.5, 12.8, 12.11, 13.8, 13.19).

**Checklist**

- [ ] Sugestão de local (RN-14), validação de locais proibidos (RN-15, FSD 21.5), limite (RN-19, RN-20)
- [ ] App cria o diretório com as permissões do usuário; serviço revalida dono e vazio; área `.drivelan/` (FSD 21.3)
- [ ] PIN de 6 dígitos sugerido por gerador criptográfico, sem sequências óbvias
- [ ] Contador de espaço (`bytes_conteudo`, `bytes_lixeira`) e recálculo em segundo plano
- [ ] Rotas de pasta do dono (sugestão, validar local, criar, listar, detalhes, PIN, limite)
- [ ] "Minhas pastas" no dashboard, assistente "Criar pasta" com resumo do PIN
- [ ] Janela "Configurações da pasta": aba Geral e aba Auditoria (componente da Fase 9)
- [ ] Pastas locais de outras contas na lista da rede (FSD 5.2.1)

**Critérios de pronto:** critérios funcionais de "Criação e gestão de pastas" (FSD 26.2).

**Áreas:** `servico/regras/`, `servico/arquivos/validacao.py`, `servico/arquivos/espaco.py`, `servico/api/local/`, `app/telas/`.

**Dependências:** Fases 9, 10 e 12.

---

## Fase 14 — Entrada de clientes

**Objetivo:** clientes entram nas pastas com PIN e permanecem conectados (FSD 6.6, 12.6, 13.10, 13.11).

**Checklist**

- [ ] `POST /v1/pastas/{uuid}/entrar` com a ordem de verificação do fluxo 13.10; token `secrets.token_urlsafe(32)` (hash no servidor)
- [ ] Bloqueio temporário de PIN por instalação e IP (RN-27), limite de 10 pedidos/min por IP
- [ ] Acessos de cliente (`cliente_acesso`) e servidores conhecidos; caso local entre contas (FSD 5.2.1)
- [ ] WebSocket de eventos (`/v1/eventos`): `assinar`, `assinatura_resultado`, ping de 30 s / 90 s
- [ ] Reconexão com espera crescente e ao reaparecer na descoberta
- [ ] Estados da conexão (FSD 12.6) persistidos; "Pastas que acesso" no dashboard; modal "Entrar com PIN"
- [ ] `/local/v1/acessos` (listar, entrar, sair/remover da lista)
- [ ] Notificações ao dono: entrada e bloqueio (entregues na Fase 23; eventos emitidos aqui)

**Critérios de pronto:** critérios funcionais de "Acesso de clientes" (FSD 26.2) entre duas instâncias.

**Áreas:** `servico/regras/`, `servico/api/rede/`, `servico/api/local/`, `servico/rede/cliente_remoto.py`, `app/`.

**Dependências:** Fases 11, 12 e 13.

---

## Fase 15 — Navegação e operações

**Objetivo:** navegar e operar o conteúdo das pastas (FSD 12.9, 13.12, 21.4).

**Checklist**

- [ ] Validação de caminhos no servidor (FSD 21.4, itens 2 a 6): resolução, links, junções, pontos de montagem, `.drivelan`
- [ ] Listagem paginada (200), versão `<mtime_ns>-<tamanho>`, nomes incompatíveis com alerta
- [ ] Subpasta, renomear, mover, excluir (para a lixeira da pasta), com bloqueio por edição e por encerramento
- [ ] Permissões de arquivos criados (FSD 24.7) em `servico/arquivos/permissoes.py`
- [ ] Idempotência por `X-DriveLan-Pedido` (FSD 23.7)
- [ ] Rotas de conteúdo na rede e no canal local (`propria` e `acesso/{id}`), adaptador local (FSD 5.2.1)
- [ ] Navegador da pasta com trilha, carregamento sob demanda e menu de contexto
- [ ] Testes de segurança de caminhos (`..`, links, junções, nomes reservados, Unicode)

**Critérios de pronto:** operações funcionam para dono e cliente; testes de fuga de pasta passam.

**Áreas:** `servico/arquivos/`, `servico/regras/`, `servico/api/`, `app/telas/`, `app/modelos/`.

**Dependências:** Fase 14.

---

## Fase 16 — Transferências

**Objetivo:** enviar e copiar arquivos com progresso e controle de espaço (FSD 6.7, 12.10, 13.13, 21.6–21.9).

**Checklist**

- [ ] Verificação prévia (`envios/verificar`): encerramento, nomes, limite, disco do dono + 100 MiB
- [ ] Envio em fluxo para `.drivelan/tmp/` e movimentação atômica; reservas em memória; interrupção por limite ou disco
- [ ] Download em fluxo com `ETag`; app grava em `temp/` e renomeia ao final; nome adaptado (RN-68)
- [ ] Streaming no canal local em blocos de 256 KB; `transferencia_progresso` a cada 250 ms; cancelar = fechar a conexão
- [ ] Nome repetido: "Substituir", "Manter os dois", "Pular" e "Aplicar a todos"
- [ ] Painel de transferências (320 px) e "Limpar concluídas"
- [ ] Eventos de aviso de 90% e de disco do dono cheio

**Critérios de pronto:** critérios funcionais de "Transferências" (exceto arrastar e soltar) e de "Limite" (FSD 26.2).

**Áreas:** `servico/regras/`, `servico/api/`, `app/transferencias/`, `app/telas/`.

**Dependências:** Fase 15.

---

## Fase 17 — Arrastar e soltar

**Objetivo:** arrastar e soltar nos dois sentidos e entre subpastas (FSD 21.10, RN-64).

**Checklist**

- [ ] Soltar arquivos e pastas do explorador no navegador da pasta (fluxo 13.13)
- [ ] Arrastar para fora com entrega sob demanda (`QMimeData.retrieveData`), progresso e cancelamento
- [ ] Arrastar entre subpastas = mover

**Critérios de pronto:** funciona no Fedora (Wayland e X11) e no Windows 11.

**Áreas:** `app/transferencias/`, `app/telas/`.

**Dependências:** Fase 16.

---

## Fase 18 — Lixeira

**Objetivo:** lixeira da pasta completa (FSD 13.17, RN-31 a RN-33).

**Checklist**

- [ ] Restaurar (pastas intermediárias, "nome (2)"), esvaziar com confirmação, expiração de 30 dias
- [ ] Contagem no limite (`bytes_lixeira`)
- [ ] Aba Lixeira nas configurações da pasta, com dias restantes e total ocupado

**Critérios de pronto:** critérios de lixeira da seção 26.2.

**Áreas:** `servico/regras/`, `servico/tarefas/`, `servico/api/local/`, `app/telas/`.

**Dependências:** Fase 15.

---

## Fase 19 — Gestão de usuários

**Objetivo:** o dono controla quem acessa (FSD 13.18, RN-24, RN-25, RN-59).

**Checklist**

- [ ] Lista de usuários com "Conectado agora" ou "Último acesso em"
- [ ] "Apenas desconectar" e "Remover e bloquear" com envio de `acesso_revogado` e liberação de travas
- [ ] Lista de bloqueados e desbloqueio
- [ ] Abas Usuários e Bloqueados

**Critérios de pronto:** critérios de "Remoção e bloqueio" (FSD 26.2).

**Áreas:** `servico/regras/`, `servico/api/local/`, `app/telas/`.

**Dependências:** Fase 14.

---

## Fase 20 — Encerramento

**Objetivo:** desativar, apagar, reativar e prazos (FSD 13.20–13.22, RN-34 a RN-40, RN-57, RN-60).

**Checklist**

- [ ] Encerrar imediatamente ou com prazo (5 min a 7 dias, padrão 1 h); somente leitura durante o prazo
- [ ] Contagem regressiva baseada nos segundos do servidor; eventos `encerramento_*`, `pasta_desativada`, `pasta_encerrada`
- [ ] Cancelar e alterar prazo; reativar com "Restaurar acessos" ou "Exigir PIN"
- [ ] Apagar com nome digitado; envio à Lixeira do SO pelo app do `so_dono` com Send2Trash (`/local/v1/lixeira-so/...`)
- [ ] Execução de encerramentos vencidos na inicialização e pelo agendador (a cada minuto)
- [ ] Aba Encerramento e diálogos da seção 12.13

**Critérios de pronto:** critérios de "Encerramento" (FSD 26.2).

**Áreas:** `servico/regras/`, `servico/tarefas/`, `servico/api/`, `app/telas/`, `app/controladores/`.

**Dependências:** Fases 14, 15 e 19.

---

## Fase 21 — Edição

**Objetivo:** abrir e editar no programa padrão com controle de conflito (FSD 6.8, 13.14, 13.15, RN-45 a RN-47, RN-66).

**Checklist**

- [ ] Travas de edição (`/v1/pastas/{uuid}/edicoes`), sinal de presença a cada 60 s, liberação após 10 min sem sinal
- [ ] Pasta de edição do usuário, `QDesktopServices.openUrl`, monitor watchdog com espera de 2 s, filtros de temporários
- [ ] Envio com `If-Match`; cópia de conflito com troca de trava numa única operação
- [ ] "Salvar edição", detecção de fechamento (arquivo travado no Windows, arquivos de trava `~$` / `.~lock`)
- [ ] Abrir somente leitura
- [ ] Edição ativa persistida e retomada após queda do app
- [ ] Liberação manual pelo dono (aba Em edição)

**Critérios de pronto:** critérios de "Edição e conflitos" (FSD 26.2), exceto servidor offline.

**Áreas:** `app/edicao/`, `servico/regras/`, `servico/api/`, `app/telas/`.

**Dependências:** Fases 15 e 16.

---

## Fase 22 — Servidor offline

**Objetivo:** guardar alterações com o servidor offline e enviar depois (FSD 13.16, RN-65).

**Checklist**

- [ ] Alteração pendente em `pendentes/` e em `cliente_alteracao_pendente` (filtrada pelo usuário do SO)
- [ ] Substituição da cópia pendente em novos salvamentos
- [ ] Envio automático ao reconectar, idempotente pela versão base, com conflito (RN-47)
- [ ] Mensagem "Servidor offline. Sua alteração foi guardada neste computador."

**Critérios de pronto:** critério "Servidor offline" de "Edição e conflitos" (FSD 26.2).

**Áreas:** `app/edicao/`, `servico/regras/`, `servico/api/local/`.

**Dependências:** Fase 21.

---

## Fase 23 — Notificações e bandeja

**Objetivo:** entregar as notificações da seção 12.14 e o menu da bandeja (FSD 6.9, 12.14, 12.17, RN-69).

**Checklist**

- [ ] Balões `QSystemTrayIcon.showMessage` e avisos na janela, só com sessão ativa e sem acúmulo
- [ ] Todos os eventos da tabela 12.14, e nenhum outro
- [ ] Menu da bandeja: "Abrir DriveLan", "Criar pasta…", "Transferências", "Configurações", "Sair do DriveLan"
- [ ] Modo sem bandeja (fechar minimiza; "Sair do DriveLan" no menu da conta)

**Critérios de pronto:** critérios de "Notificações" (FSD 26.2).

**Áreas:** `app/notificacoes.py`, `app/bandeja.py`, `servico/api/local/` (eventos).

**Dependências:** Fases 14 a 22 (eventos já emitidos).

---

## Fase 24 — Sair da pasta

**Objetivo:** saída do cliente com opção de cópia (FSD 13.23, RN-30).

**Checklist**

- [ ] Diálogo "Copiar para uma pasta…", "Sair sem copiar", "Cancelar"
- [ ] Cópia da árvore completa com nomes adaptados e nome repetido (FSD 21.9, prefixo `\\?\` no Windows)
- [ ] Aviso e descarte de alterações pendentes; `POST /v1/pastas/{uuid}/sair`; liberação de travas

**Critérios de pronto:** critérios de "Saída do cliente" e de "Interoperabilidade" relativos a nomes (FSD 26.2).

**Áreas:** `app/transferencias/`, `app/telas/`, `servico/regras/`.

**Dependências:** Fases 16 e 22.

---

## Fase 25 — Revisão de segurança

**Objetivo:** executar a revisão da seção 24.10 do FSD.

**Checklist**

- [ ] Validação de caminhos (`..`, links, junções, nomes reservados, Unicode)
- [ ] Canal local com sessão de outro usuário do SO e de outro processo
- [ ] TLS e mudança de identidade
- [ ] Nenhum segredo em logs, auditoria, mensagens ou eventos
- [ ] Permissões das pastas do sistema em Windows e Linux

**Critérios de pronto:** todos os itens verificados e falhas corrigidas, com registro em `docs/ERROS.md`.

**Dependências:** Fases 1 a 24.

---

## Fase 26 — Revisão de qualidade

**Objetivo:** consolidar testes, textos e desempenho (FSD 25, etapa 26).

**Checklist**

- [ ] Cobertura de testes das regras de negócio
- [ ] Testes de integração com dois serviços
- [ ] Revisão de textos e traduções (`.ts` atualizado com `pyside6-lupdate`)
- [ ] Desempenho da auditoria com 12 meses simulados
- [ ] Conferência da lista de critérios técnicos (FSD 26.1)

**Dependências:** Fase 25.

---

## Fase 27 — Empacotamento e instalador

**Objetivo:** gerar `.exe`, `.rpm` e `.deb` atendendo à seção 4.5 do FSD.

**Checklist**

- [ ] Escolher a ferramenta de empacotamento e de instalador (FSD 27, item 1) — **decisão do usuário nesta fase**
- [ ] Serviço do Windows (LocalSystem) e unidade systemd `drivelan.service` (root), com SELinux verificado
- [ ] Início automático do app em todas as sessões (`/etc/xdg/autostart/drivelan.desktop`)
- [ ] Definição da chave na instalação; geração de certificado e identidade
- [ ] Regras de firewall (Windows Defender, firewalld, ufw) e `--configurar-firewall`
- [ ] Reinstalação com "Manter dados e trocar apenas a chave" (padrão); desinstalação sem apagar pastas
- [ ] Ícones do app nos formatos de cada plataforma a partir da logo oficial
- [ ] Arquivos `.qm` compilados no pacote

**Áreas:** `empacotamento/windows/`, `empacotamento/linux/`.

**Dependências:** Fase 26.

---

## Fase 28 — Piloto em laboratório

**Objetivo:** executar a lista de verificação da seção 26.3 do FSD.

**Checklist**

- [ ] Todos os itens da seção 26.3 (Windows 10 e 11, Fedora com SELinux, firewalls, Avahi, Wayland/X11, 10+ clientes, interoperabilidade nos dois sentidos)
- [ ] Pontos dependentes do ambiente (FSD 27, item 2) validados; falhas registradas numa revisão do FSD

**Dependências:** Fase 27.

# DOCUMENTO DE ESPECIFICAÇÃO FUNCIONAL (FSD)

**Sistema:** DriveLan — Compartilhamento de pastas na rede local
**Versão do documento:** 1.2 (revisada após validação)
**Data:** novembro de 2026
**Local no projeto:** `docs/FSD.md`
**Licença do sistema:** GPLv3

> Este documento é a especificação completa e autossuficiente da primeira versão (v1) do DriveLan. Junto com o `docs/DESIGN.md`, ele contém tudo o que é necessário para implementar o sistema. Quando o `docs/DESIGN.md` divergir deste FSD, prevalecem as correções visuais registradas na seção 12.1.

---

## 1. Visão Geral

### 1.1 Nome do sistema

**DriveLan**. O projeto se chamava anteriormente Fontinele Rede-Files; esse nome não deve aparecer na interface, nos pacotes nem no código.

### 1.2 Objetivo principal

Permitir que qualquer pessoa crie, encontre e use pastas compartilhadas na rede local (LAN) de forma simples, segura e controlada, sem conhecimento técnico de redes, sem serviços de nuvem e sem depender do compartilhamento nativo do Windows (SMB).

### 1.3 Resumo do funcionamento

O DriveLan é um aplicativo desktop instalado em cada computador participante, para **Windows e Linux**. Cada instalação é formada por dois processos:

- **`drivelan-service`**: serviço do sistema operacional, sem interface, que inicia com o computador e funciona independentemente de quem está logado. Ele hospeda as pastas compartilhadas, guarda os dados, conversa com a rede, aplica as regras de negócio, executa tarefas periódicas e grava a auditoria e os logs.
- **`drivelan`**: aplicativo de janela com ícone na bandeja do sistema, executado em cada sessão de usuário do sistema operacional. Ele exibe as telas, faz o login das contas do DriveLan, mostra notificações, abre arquivos no programa padrão, acompanha a edição e lê e grava arquivos no disco do usuário.

O mesmo aplicativo é usado de três formas:

- **Dono de pasta (modo servidor):** cria uma pasta compartilhada no próprio computador, define um PIN de 6 dígitos e um limite de tamanho, e controla quem entra.
- **Cliente:** vê as pastas do DriveLan disponíveis na rede, entra nelas com o PIN e trabalha com os arquivos (copiar, abrir, editar, renomear, mover e excluir).
- **Híbrido:** é dono de uma ou mais pastas e, ao mesmo tempo, cliente de pastas de outras pessoas.

Recursos centrais: contas locais com PIN de 4 dígitos, descoberta automática das pastas (com adição manual de servidor), dashboard, controle de clientes (desconectar e bloquear), transferências com progresso, edição no programa padrão com controle de conflito, lixeira da pasta, encerramento com prazo, notificações, auditoria, logs de erros e um administrador local de último recurso, liberado por uma chave de segurança digitada numa janela aberta com **Shift + F12**.

### 1.4 Público usuário

- Ambientes corporativos e pequenos escritórios.
- Laboratórios de informática e salas de aula (cenário de origem: o professor compartilha material e os alunos acessam).
- Administradores de rede e analistas de TI que precisam de uma alternativa simples ao SMB.

### 1.5 Contexto de uso

- Funciona **somente na rede local**, sem internet e sem nuvem.
- O app instalado é obrigatório; **não existe acesso por navegador**.
- Código aberto sob **GPLv3**, gratuito e sem fins lucrativos.
- Interface em **português do Brasil**, com todos os textos preparados para tradução desde a v1.
- Compatibilidade total entre Windows e Linux nos dois sentidos: uma pasta hospedada em Linux é usada por clientes Windows e vice-versa, com todas as funcionalidades.

### 1.6 Observações relevantes para implementação

- O DriveLan **não é um sistema web**. Não existem PHP, MySQL, servidor web público, pasta pública de hospedagem, XAMPP ou hospedagem compartilhada. A comunicação HTTP e WebSocket existe apenas como protocolo interno entre instalações do DriveLan, sempre sob TLS.
- Toda operação de rede e de disco deve ser assíncrona ou executada fora da thread da interface. A janela nunca pode travar.
- Nenhum recurso pode depender do sistema operacional do servidor ou do cliente.
- Termos visuais como "sync", "peer-to-peer" e "Syncing" usados no material de design são apenas linguagem visual. **Não existe sincronização contínua** no DriveLan.
- O sistema não possui telemetria, atualização automática nem qualquer comunicação fora da LAN.

---

## 2. Documentos do Projeto para Implementação

A IA codificadora deve usar apenas os seguintes documentos:

| Documento | Papel |
|---|---|
| `docs/FSD.md` | Especificação funcional e técnica completa: escopo, regras, dados, protocolo, telas, fluxos, segurança e critérios de aceitação. |
| `docs/DESIGN.md` | Referência visual: cores, tipografia, espaçamentos, formas e componentes. Deve ser aplicado com as correções da seção 12.1 deste FSD. |
| `docs/code.html`, `docs/screen.png`, `docs/Captura de tela de 2026-11-13 18-38-14.png` | Referência **apenas de composição visual** das telas (layout geral, estrutura de cabeçalho e navegação, disposição de cartões de pasta e de campos de login) — material anterior a esta versão do FSD, usado só como inspiração de diagramação. Qualquer conteúdo, fluxo, texto, nome de campo, caminho de exemplo ou tecnologia presente nesses arquivos que contrarie este FSD ou o `docs/DESIGN.md` (por exemplo: carregamento de fontes/ícones por CDN, caminhos no estilo `\\computador\pasta`, botão "Solicitar", PIN "memorizado" ou "sincronizado", opção "Visualizar PIN", link de recuperação de PIN, textos em inglês) **não deve ser implementado**. Em qualquer divergência, prevalece o texto deste FSD. |

Este FSD já consolida todas as decisões funcionais e técnicas necessárias. Além dos arquivos de referência visual acima, nenhum outro documento ou conversa é necessário para implementar o sistema.

---

## 3. Stack Definida

### 3.1 Linguagem e plataforma

| Item | Decisão |
|---|---|
| Linguagem | **Python 3.12** (última correção disponível da série 3.12 no momento do build; a mesma versão em todos os pacotes) |
| Interface | **PySide6 6.8.x (Qt Widgets)**, estilizada por uma folha de estilo **QSS** central |
| Banco de dados | **SQLite** (módulo `sqlite3` da biblioteca padrão), gravado somente pelo serviço, com FTS5 para busca textual da auditoria |
| Comunicação de rede | HTTP e WebSocket sobre **TLS**, numa única porta TCP fixa e configurável |
| Descoberta | **mDNS/DNS-SD** como método principal e **broadcast UDP** como reserva, além da adição manual |
| Canal local app ↔ serviço | HTTP e WebSocket sobre **socket Unix** (Linux) ou **named pipe** (Windows), restritos ao próprio computador; no Windows, o servidor do pipe é implementação própria do DriveLan (seção 15.5.1) |
| Sistemas suportados | Windows 10 e 11 (64 bits) e Linux (Fedora como referência; distribuições com `.deb` e `.rpm`). O Windows 10 é verificado no piloto (seção 26.3) |
| Padrão arquitetural | Organização inspirada em **MVC** (seção 5.4) |

### 3.2 Bibliotecas e licenças

Todas as dependências foram escolhidas com licença compatível com a GPLv3. Nenhuma dependência nova pode ser adicionada sem conferir a licença.

| Biblioteca | Uso | Licença | Onde |
|---|---|---|---|
| PySide6 | Interface, bandeja, atalhos, tradução (Qt Linguist) | LGPLv3 | app |
| aiohttp | Servidor e cliente HTTP e WebSocket, canal local e protocolo de rede | Apache-2.0 | serviço e app |
| zeroconf (python-zeroconf) | Anúncio e descoberta mDNS/DNS-SD | LGPL-2.1 ou posterior | serviço |
| cryptography | Geração do certificado e da chave da instalação, assinatura de desafios | Apache-2.0 / BSD | serviço |
| argon2-cffi | Hash Argon2id de PINs e da chave de segurança | MIT | serviço |
| psutil | Placas de rede, endereços, discos e espaço livre | BSD-3 | serviço e app |
| watchdog | Detecção de salvamentos e de arquivos de trava na pasta de edição | Apache-2.0 | app |
| Send2Trash | Envio da pasta apagada para a Lixeira do sistema operacional | BSD-3 | app |
| tomli-w | Gravação do arquivo de configuração TOML (a leitura usa `tomllib`, da biblioteca padrão) | MIT | serviço |
| pywin32 | Serviço do Windows, servidor do named pipe com descritor de segurança próprio (seção 15.5.1), identidade do cliente do named pipe, teste de arquivo travado, ajustes da janela (seção 12.1) | PSF-2.0 | serviço e app (só Windows) |

Ferramentas de desenvolvimento (não distribuídas): pytest e pytest-qt (MIT), pytest-asyncio (Apache-2.0), ruff (MIT) e mypy (MIT).

### 3.3 Recursos embutidos

- Fontes **Inter** e **JetBrains Mono** embutidas no app (licença OFL), carregadas com `QFontDatabase.addApplicationFont` na inicialização. O sistema nunca depende de fontes instaladas no computador.
- Ícones em SVG embutidos no pacote. Nenhum recurso é baixado da internet.
- Arquivos de tradução Qt (`.ts` no repositório, `.qm` no pacote). O português é o único idioma da v1.

### 3.4 Restrições técnicas

- Proibido usar serviços externos, CDNs, telemetria ou atualização automática.
- Proibido acessar o banco de dados a partir do app `drivelan`. Todo dado passa pelo canal local com o serviço.
- Proibido executar operações de rede ou de disco na thread da interface.
- Proibido usar arquivo `.env`. A configuração técnica fica no arquivo descrito na seção 20.2, que não contém credenciais.
- Suporte a **IPv4** na v1 (descoberta, anúncio e conexões). IPv6 não faz parte da v1.

---

## 4. Ambientes do Projeto

### 4.1 Desenvolvimento local

- Fedora, Python 3.12 em ambiente virtual (`venv` ou `uv`), VS Code e Git.
- Os dois processos podem rodar em modo de desenvolvimento sem instalação:
  - `drivelan-service --console --dados <pasta-temporária>`: roda o serviço em primeiro plano, com pasta de dados alternativa, log no terminal e sem registro como serviço do sistema.
  - `drivelan --servico-local <caminho-do-socket>`: abre o app apontando para o serviço de desenvolvimento.
- É possível rodar duas instâncias do serviço na mesma máquina, com pastas de dados e portas diferentes, para testar dono e cliente.

### 4.2 Testes locais

- Máquina virtual Windows 11 com placa de rede em **modo ponte (bridge)**, para que a VM e o Fedora estejam na mesma LAN e a descoberta por mDNS e broadcast funcione.
- Testes automatizados (pytest) cobrindo regras de negócio, repositórios, validação de nomes e caminhos, protocolo e migrations, executados no Linux e no Windows.

### 4.3 Homologação

Antes de cada versão, piloto em laboratório real com computadores Windows 11 e ao menos um computador Windows 10, seguindo a lista de verificação da seção 26.3.

### 4.4 Produção

- Publicação no **GitHub Releases**.
- Instalador `.exe` para Windows e pacotes `.rpm` e `.deb` para Linux.
- A ferramenta de empacotamento e o gerador do instalador são escolhidos na etapa 27 da organização da implementação (seção 25), desde que atendam aos requisitos da seção 4.5.

### 4.5 Requisitos do instalador e do deploy

O instalador e os pacotes devem:

1. Instalar os binários num diretório de programas protegido contra escrita por usuários comuns.
2. Registrar o `drivelan-service` como serviço do sistema com início automático (serviço do Windows executado como LocalSystem; unidade systemd `drivelan.service` executada como root no Linux).
3. Registrar o app `drivelan` para iniciar em todas as sessões de usuário (Windows: entrada de inicialização para todos os usuários; Linux: `/etc/xdg/autostart/drivelan.desktop`).
4. Pedir ao técnico a **chave de segurança** do computador (com confirmação) e gravá-la pelo comando protegido `drivelan-service --definir-chave`, que lê a chave pela entrada padrão e guarda apenas o hash (seção 15.6).
5. Gerar o certificado e a identidade da instalação, se ainda não existirem (seção 24.2).
6. Criar as regras de firewall:
   - Windows Defender Firewall: entrada TCP e UDP na porta do DriveLan e UDP 5353 (mDNS), restritas ao executável do serviço e ao escopo "sub-rede local", em todos os perfis de rede;
   - Linux: definição de serviço `drivelan` no `firewalld` (TCP e UDP na porta do DriveLan, mais o serviço `mdns`), ativada na zona padrão; perfil de aplicativo equivalente no `ufw` quando ele estiver em uso.
7. Na **reinstalação**, perguntar se os dados devem ser mantidos, com **"Manter dados e trocar apenas a chave"** marcada por padrão. A outra opção, "Apagar dados do DriveLan", remove banco, certificado e logs.
8. **Nunca apagar os arquivos das pastas compartilhadas**, em nenhuma opção de instalação, reinstalação ou desinstalação.
9. No Linux, conviver com o Avahi já ativo na porta 5353, sem desativá-lo.
10. Oferecer o comando protegido `drivelan-service --regenerar-identidade`, que gera novo certificado e novo identificador da instalação, mantendo contas, pastas e auditoria.

**Computadores clonados por imagem de disco:** a imagem deve ser gerada antes da instalação do DriveLan. Se o DriveLan já estiver na imagem, o TI deve executar `drivelan-service --regenerar-identidade` em cada computador clonado, porque computadores com a mesma identidade quebram o bloqueio por computador (RN-27) e a confiança no primeiro uso (RN-67). Clientes que acessavam pastas do computador antes da regeneração verão "Identidade alterada" (RN-67) e precisarão entrar de novo com o PIN.

Se a porta for alterada no arquivo de configuração, as regras de firewall devem ser atualizadas pelo comando protegido `drivelan-service --configurar-firewall`, executado como administrador do sistema operacional.

---

## 5. Arquitetura do Sistema

### 5.1 Diretório do projeto

A raiz de referência deste FSD é o **`[Diretório do Projeto - Repositório]`**: a pasta do projeto versionada no Git. Ela pode estar em qualquer local da máquina de desenvolvimento (por exemplo, `~/projetos/drivelan/`).

Como o DriveLan é um aplicativo desktop, não existe pasta pública de servidor web. Nomes como `htdocs`, `www`, `public_html` ou `public` **não se aplicam** e não devem ser usados na estrutura. O repositório gera pacotes instaláveis; os arquivos instalados ficam nos diretórios do sistema descritos na seção 5.6.

O equivalente, no DriveLan, à regra "pastas internas não podem ser acessadas pelo navegador" é:

- o servidor de rede expõe **apenas** as rotas definidas na seção 23.3 e nunca serve arquivos do diretório de instalação, do banco, da configuração ou dos logs;
- o servidor de rede só lê e grava dentro das pastas compartilhadas, após a validação de caminhos da seção 21.4;
- a pasta de dados, a configuração e os logs ficam em diretórios do sistema protegidos contra leitura e escrita por usuários comuns;
- as rotas de gestão de pastas, contas e administração existem **apenas no canal local** e nunca são expostas na rede.

### 5.2 Visão dos processos

```
Computador A (dono)                               Computador B (cliente)
┌──────────────────────────┐                      ┌──────────────────────────┐
│ drivelan (sessão do SO)  │                      │ drivelan (sessão do SO)  │
│  telas, bandeja, edição  │                      │  telas, bandeja, edição  │
└───────────┬──────────────┘                      └───────────┬──────────────┘
            │ canal local (socket Unix / named pipe)          │ canal local
┌───────────┴──────────────┐   HTTP + WebSocket   ┌───────────┴──────────────┐
│ drivelan-service         │◄──── sobre TLS ─────►│ drivelan-service         │
│  SQLite, regras, rede,   │   porta TCP 47820    │  SQLite, regras, rede,   │
│  auditoria, logs, tarefas│   mDNS + UDP 47820   │  auditoria, logs, tarefas│
└──────────────────────────┘                      └──────────────────────────┘
```

Regras de responsabilidade:

- **Toda comunicação de rede é feita pelo serviço.** Isso mantém a chave da instalação e os tokens de acesso protegidos no serviço, fora do alcance dos usuários do computador. O app nunca abre conexões de rede.
- **Toda leitura e gravação no disco do usuário é feita pelo app**, com as permissões do próprio usuário do sistema operacional: arquivos copiados para o computador, arrastar e soltar, pasta de edição, alterações guardadas com o servidor offline e envio para a Lixeira do sistema. O serviço nunca grava em locais escolhidos pelo usuário fora das pastas compartilhadas.
- Nas transferências, o app envia ou recebe o conteúdo do arquivo pelo canal local, em fluxo contínuo (streaming), e o serviço repassa para o servidor remoto ou para a pasta local.
- Quando o dono trabalha com o conteúdo da própria pasta, o serviço atende diretamente, sem passar pela rede, aplicando exatamente as mesmas regras de um cliente remoto (edição, conflito, lixeira, auditoria e somente leitura durante encerramento).
- Quando um usuário é cliente de uma pasta hospedada no mesmo computador por outra conta, o serviço trata o acesso como de um cliente, com PIN, token e todas as regras, mas sem tráfego de rede (seção 5.2.1).
- **Instância única do app:** existe no máximo um processo `drivelan` por usuário do SO. Na inicialização, o app tenta conectar a um `QLocalServer` de nome exclusivo por usuário do SO (`drivelan-app-<SID ou UID>`); se já houver instância, envia a ela o pedido "mostrar janela" e encerra. A instância existente traz a janela para frente (com a tela de desbloqueio, se houver sessão em segundo plano).

#### 5.2.1 Cliente de pasta hospedada no mesmo computador

Uma conta pode ser cliente de uma pasta que outra conta hospeda no mesmo computador. Esse caso segue as regras de um cliente remoto, com as diferenças abaixo:

- **Servidor conhecido local:** a própria instalação é registrada em `cliente_servidor_conhecido` com `local = 1`, `instalacao_id` igual ao desta instalação e endereço e porta nulos. O registro é criado na primeira vez que uma conta entra numa pasta local de outra conta.
- **Lista de pastas da rede:** além do resultado da descoberta, o serviço inclui as pastas `ativa` e `em_encerramento` hospedadas neste computador cujo dono seja outra conta. Status e situação de acesso são calculados direto no banco. Pastas do próprio computador nunca são buscadas por mDNS, broadcast ou TLS.
- **Entrada com PIN:** `POST /local/v1/acessos` para uma pasta local chama diretamente a regra de entrada do lado servidor, com as mesmas verificações e na mesma ordem do fluxo 13.10. A identidade (`instalacao_id` local + UUID da conta) é criada ou atualizada na mesma transação, como no passo 3 da seção 23.4, sem desafio, pois a conta já foi autenticada pela sessão local. O bloqueio temporário de PIN usa `tipo_chave = 'instalacao'` com o identificador local; não há registro por IP.
- **Token:** gerado e guardado como num acesso remoto (hash em `acesso`, valor em `cliente_acesso`).
- **Operações de conteúdo:** as rotas `/local/v1/conteudo/acesso/{id}/...` cujo servidor conhecido é local são despachadas por um adaptador interno para as mesmas regras do lado servidor, sem HTTP e sem TLS. O adaptador aplica todas as verificações das rotas de rede da seção 16.2 (token, acesso ativo, situação da pasta, bloqueio pelo dono e caminho).
- **Eventos:** as mensagens da seção 23.5 são entregues ao lado cliente por uma fila interna e convertidas em eventos do WebSocket local para o app da conta cliente.
- **Não se aplicam:** a confiança no primeiro uso (RN-67), pois é a mesma instalação, e as alterações pendentes, pois o serviço local está sempre disponível.

### 5.3 Organização interna do serviço

O serviço roda sobre um laço `asyncio` principal.

- O acesso ao SQLite é feito por **uma única conexão de escrita**, executada numa thread dedicada. Leituras pesadas (auditoria) usam uma segunda conexão somente leitura.
- Operações de disco (cópia, cálculo de tamanho, movimentação para a lixeira) rodam num pool de threads.
- Um agendador interno executa as tarefas periódicas da seção 6.1.

### 5.4 Aplicação do MVC

| Camada | Onde fica | Responsabilidade | Proibições |
|---|---|---|---|
| **Model** | `src/drivelan/servico/` (dados, regras, rede, tarefas) e `src/drivelan/app/modelos/` | Acesso ao SQLite por repositórios, regras de negócio (limites, bloqueios, lixeira, encerramentos, conflitos, auditoria), protocolo de rede e sistema de arquivos. No app, os modelos são `QAbstractItemModel` e estruturas de estado alimentados pelo canal local. | Não conhecem telas nem widgets. |
| **View** | `src/drivelan/app/telas/` e `src/drivelan/app/componentes/` | Widgets Qt, diálogos e componentes visuais, estilizados pela folha QSS central. Apenas exibem dados e emitem sinais de ação. | Não acessam o banco, a rede, o canal local nem o disco. Não contêm regras de negócio. |
| **Controller** | `src/drivelan/app/controladores/` | Recebem as ações das telas, chamam o canal local com o serviço (cliente assíncrono), tratam respostas e erros e decidem o que a tela exibe. | Não montam widgets complexos nem gravam diretamente no banco. |

No serviço, a mesma separação é mantida em três níveis:

- **`api/`** (equivalente ao controller do serviço): recebe pedidos HTTP e WebSocket do canal local e da rede, valida a entrada, identifica quem chama e delega para as regras.
- **`regras/`** (casos de uso): implementa as regras de negócio. É a única camada que decide o que é permitido.
- **`dados/`**: repositórios SQL e migrations. Não contém regras de negócio.

Fluxo típico de uma ação:

1. A tela emite um sinal (por exemplo, o clique em "Remover e bloquear").
2. O controller chama o cliente do canal local, numa thread assíncrona separada da interface.
3. O serviço autentica a sessão local, valida a entrada e executa a regra.
4. A regra grava pelos repositórios, registra a auditoria e emite eventos.
5. O controller recebe a resposta ou o erro e atualiza o modelo; a tela é redesenhada.

**Ponte entre Qt e asyncio no app:** o app mantém um laço `asyncio` numa thread própria (classe `PonteAssincrona`). Os controllers enviam corrotinas para essa thread e recebem os resultados por sinais Qt. Os eventos que chegam pelo WebSocket local são convertidos em sinais Qt.

### 5.5 Estrutura de diretórios do projeto

```
[Diretório do Projeto - Repositório]/
├── pyproject.toml                  # metadados, dependências e pontos de entrada
├── uv.lock / requirements*.txt     # versões fixadas das dependências
├── LICENSE                         # GPLv3
├── README.md
├── docs/
│   ├── FSD.md
│   └── DESIGN.md
├── src/drivelan/
│   ├── comum/                      # código compartilhado entre serviço e app
│   │   ├── nomes.py                # regra única de nomes de arquivos e pastas
│   │   ├── caminhos.py             # conversão de caminhos do protocolo
│   │   ├── protocolo.py            # tipos de mensagens, códigos de erro, versões
│   │   ├── canal_local.py          # endereços e cliente do canal local
│   │   ├── diretorios.py           # pastas do sistema por plataforma
│   │   └── i18n.py                 # textos de mensagens marcados para tradução
│   ├── servico/
│   │   ├── __main__.py             # ponto de entrada drivelan-service
│   │   ├── inicializacao.py        # ordem de partida do serviço (seção 6.1)
│   │   ├── configuracao.py         # leitura e gravação do drivelan.toml
│   │   ├── log_erros.py            # log diário em arquivo e contingência
│   │   ├── api/
│   │   │   ├── local/              # rotas do canal local (app ↔ serviço)
│   │   │   └── rede/               # rotas do protocolo entre instalações
│   │   ├── regras/                 # contas, sessões, pastas, acessos, bloqueios,
│   │   │                           # lixeira, encerramento, edição, transferências,
│   │   │                           # auditoria, administração, cliente remoto
│   │   ├── dados/
│   │   │   ├── banco.py            # conexão, PRAGMAs, transações
│   │   │   ├── migracoes.py        # executor de migrations
│   │   │   ├── migracoes/          # 0001_inicial.sql, 0002_..., ...
│   │   │   └── repositorios/       # um repositório por tabela ou agregado
│   │   ├── rede/
│   │   │   ├── interfaces.py       # placa principal, VPN, nome da rede
│   │   │   ├── anuncio_mdns.py     # anúncio e descoberta mDNS
│   │   │   ├── broadcast.py        # descoberta de reserva por UDP
│   │   │   ├── tls.py              # certificado, identidade e impressão digital
│   │   │   └── cliente_remoto.py   # conexões com outros servidores
│   │   ├── arquivos/
│   │   │   ├── validacao.py        # caminhos seguros e locais proibidos
│   │   │   ├── espaco.py           # contador de espaço ocupado e espaço livre
│   │   │   └── permissoes.py       # dono e ACL dos arquivos criados (por SO)
│   │   ├── tarefas/                # agendador e tarefas periódicas
│   │   └── plataforma/             # windows.py e linux.py (serviço, identidade do
│   │                               # cliente do canal local, firewall)
│   └── app/
│       ├── __main__.py             # ponto de entrada drivelan
│       ├── ponte_assincrona.py
│       ├── controladores/
│       ├── modelos/
│       ├── telas/
│       ├── componentes/            # barra de título, chips, cartões, PIN segmentado
│       ├── edicao/                 # pasta de edição, monitor de salvamento e trava
│       ├── transferencias/         # fila, progresso, nome repetido, arrastar e soltar
│       ├── bandeja.py
│       └── notificacoes.py
├── recursos/
│   ├── estilo/drivelan.qss         # folha de estilo central com os tokens visuais
│   ├── fontes/                     # Inter e JetBrains Mono (OFL)
│   ├── icones/                     # SVG
│   └── traducoes/                  # drivelan_pt_BR.ts
├── empacotamento/
│   ├── windows/                    # script do instalador, serviço, firewall
│   └── linux/                      # spec do rpm, controle do deb, unidade systemd,
│                                   # firewalld, ufw, autostart
└── tests/
    ├── servico/
    ├── app/
    └── integracao/                 # dois serviços conversando localmente
```

Regras sobre a estrutura:

- `servico/` e `app/` não importam um ao outro. Só podem compartilhar código por meio de `comum/`.
- As migrations ficam em `src/drivelan/servico/dados/migracoes/`. São empacotadas como arquivos somente leitura no diretório de instalação e executadas apenas pelo serviço (seção 11.3).
- Não existem pastas `logs/` ou `config/` no repositório. Logs, banco e configuração são criados nos diretórios do sistema da seção 5.6.

### 5.6 Diretórios usados na instalação

| Conteúdo | Windows | Linux | Permissões |
|---|---|---|---|
| Programa | `C:\Program Files\DriveLan\` | `/usr/lib/drivelan/` e executáveis em `/usr/bin/` | Somente leitura para usuários comuns |
| Dados do serviço (banco, certificado) | `C:\ProgramData\DriveLan\dados\` | `/var/lib/drivelan/` | Acesso exclusivo de SYSTEM e Administradores (Windows) ou `root`, modo `0700` (Linux) |
| Configuração | `C:\ProgramData\DriveLan\config\drivelan.toml` | `/etc/drivelan/drivelan.toml` | Escrita só pelo serviço e por administradores do SO; sem leitura para usuários comuns |
| Logs de erros | `C:\ProgramData\DriveLan\logs\` | `/var/log/drivelan/` | Acesso exclusivo do serviço e de administradores do SO |
| Canal local | named pipe `\\.\pipe\drivelan-servico` | `/run/drivelan/local.sock` | Conexão permitida a usuários locais autenticados; conexões remotas recusadas (no Windows, descritor de segurança da seção 15.5.1) |
| Dados do usuário (app) | `%LOCALAPPDATA%\DriveLan\` | `~/.local/share/drivelan/` (modo `0700`) | Somente o próprio usuário do SO |

A pasta de dados do usuário contém: `edicao/` (pasta de edição), `pendentes/` (alterações guardadas com o servidor offline), `temp/` (arquivos temporários de transferência e de arrastar para fora) e `log-contingencia/` (seção 19.1.5).

---

## 6. Escopo Funcional da Primeira Versão

As regras citadas como **RN-xx** estão definidas na seção 14.

### 6.1 Módulo Serviço do sistema

| Funcionalidade | Descrição |
|---|---|
| **Inicialização com o computador** | Objetivo: manter as pastas disponíveis sempre que o computador estiver ligado, independentemente de quem esteja logado e com a janela fechada (RN-26, RN-40). Usuários: nenhum diretamente. Resultado: pastas ativas anunciadas na rede após o boot. |
| **Canal local com o app** | Atende os apps das sessões de usuário, com identificação do usuário do SO e sessão do DriveLan (seção 15.5). |
| **Tarefas periódicas** | A cada minuto: encerramentos com prazo vencido; liberação de arquivos em edição sem sinal há 10 minutos. Diariamente às 03:00 e na inicialização: limpeza da lixeira com mais de 30 dias; retenção da auditoria (12 meses e 1 mês para pastas apagadas); retenção dos logs (3 meses); recálculo do espaço ocupado das pastas. |

Ordem de inicialização: (1) log de erros; (2) leitura da configuração, com valores padrão se ausente ou inválida; (3) abertura do banco e execução das migrations; (4) verificação do certificado e da identidade; (5) execução de encerramentos vencidos durante o desligamento; (6) recálculo do espaço ocupado em segundo plano; (7) servidor TLS na porta configurada; (8) canal local; (9) anúncio mDNS e resposta a broadcast; (10) agendador. Falha em qualquer etapa é registrada no log e, quando for impeditiva (por exemplo, porta ocupada), o serviço tenta novamente a cada 30 segundos, sem encerrar.

### 6.2 Módulo Contas

| Funcionalidade | Objetivo e ações | Usuários | Resultado | Regras |
|---|---|---|---|---|
| Cadastro | Criar conta com nome e PIN de 4 dígitos | Qualquer pessoa no computador | Conta ativa criada | RN-01 a RN-03 |
| Login | Entrar com nome e PIN sempre que a janela for aberta | Usuário | Sessão do DriveLan iniciada e dashboard exibido | RN-04 |
| Bloqueio por erros | Desativar a conta após 5 erros seguidos | Sistema | Conta e pastas desativadas, acessos de cliente suspensos, arquivos preservados | RN-05 a RN-07 |
| Troca obrigatória de PIN temporário | Exigir novo PIN após resgate | Usuário | Uso liberado só após a troca | RN-10 |
| Alterar nome | Trocar o próprio nome | Usuário | Nome novo, histórico preservado | RN-08 |
| Alterar PIN | Trocar o próprio PIN, informando o atual | Usuário | PIN novo | — |
| Excluir conta | Remover a própria conta | Usuário | Conta excluída, identidade preservada para a auditoria | RN-09 |
| Sair da conta | Encerrar a sessão do DriveLan | Usuário | Volta à tela de login | RN-04 |

Dependências: todas as demais funções exigem sessão ativa, exceto a janela do administrador.

### 6.3 Módulo Rede

| Funcionalidade | Objetivo e ações | Resultado | Regras |
|---|---|---|---|
| Identificação da rede | Mostrar nome da rede (SSID ou "Rede cabeada"), IP e faixa (CIDR) | Informação visível no dashboard | RN-11 |
| Escolha da placa de rede | Trocar a placa usada, em Configurações do app | Configuração salva e anúncio refeito na nova placa | RN-11 |
| Descoberta automática | Encontrar servidores DriveLan por mDNS e broadcast | Lista de pastas da rede atualizada continuamente | RN-12 |
| Adição manual de servidor | Informar IP ou nome do computador e, opcionalmente, a porta | Servidor consultado e suas pastas exibidas | — |
| Remoção de servidor manual | Remover um servidor adicionado manualmente, em Configurações do app | Servidor deixa de ser consultado; pastas dele com acesso continuam como acessos de cliente | — |
| Confiança no primeiro acesso | Registrar a identidade do servidor no primeiro uso e bloquear se ela mudar | Proteção contra servidor falso | RN-67 |

#### 6.3.1 Métodos de detecção da rede

| Informação | Windows | Linux |
|---|---|---|
| Placa principal (modo automático) | Placa que contém o endereço de origem da rota padrão, obtido abrindo um socket UDP "conectado" a `192.0.2.1` (nenhum pacote é enviado) e lendo o endereço local. Sem rota padrão: primeira placa ativa com IPv4 privado (10/8, 172.16/12, 192.168/16) que não seja VPN | Mesmo método |
| Endereço e faixa | `psutil.net_if_addrs()` (IPv4 e máscara), exibidos como IP e CIDR | Mesmo método |
| Tipo e nome da rede | Saída de `netsh wlan show interfaces` para a placa escolhida: se for sem fio, mostra o SSID; caso contrário, "Rede cabeada" | `nmcli -t -f DEVICE,TYPE,CONNECTION device` e `nmcli -t -f ACTIVE,SSID dev wifi`; sem NetworkManager, usa `/sys/class/net/<placa>/wireless` para decidir entre sem fio e cabeada |
| Falha ao obter o nome | "Rede sem fio" (se a placa for sem fio) ou "Rede cabeada" | Mesmo comportamento |
| Placas VPN (ignoradas por padrão) | Descrição ou nome contendo `TAP-Windows`, `WireGuard`, `OpenVPN`, `Wintun`, `AnyConnect`, `FortiClient`, `PPP` ou `VPN` | Nomes iniciados por `tun`, `tap`, `wg`, `ppp`, `vpn`, `ipsec` ou `tailscale`, ou tipo `tun`/`wireguard` no `nmcli` |
| Placas sempre ignoradas | Loopback e adaptadores sem IPv4 | `lo`, `docker*`, `virbr*`, `veth*`, `br-*` e adaptadores sem IPv4 |

No Windows 11 24H2 ou superior, o `netsh wlan` só informa o SSID quando os serviços de localização estão ativos. Sem eles, o comando falha ou omite o SSID e o dashboard mostra "Rede sem fio". Esse é o comportamento esperado: não é erro, não vai para o log e o DriveLan não pede nem ativa a localização.

As placas VPN aparecem na lista de Configurações do app marcadas como "VPN — ignorada por padrão" e podem ser escolhidas manualmente. O serviço reavalia a placa a cada 30 segundos e quando o endereço muda, refazendo anúncio e descoberta.

### 6.4 Módulo Dashboard e bandeja

O dashboard é a tela principal após o login e exibe: conta logada, nome do computador, rede atual, pastas das quais o usuário é dono, pastas que acessa como cliente, todas as pastas da rede, acesso às configurações de pasta e às configurações de usuário. O ícone da bandeja oferece acesso rápido: abrir o DriveLan, criar pasta, transferências em andamento, configurações e sair do DriveLan (encerra a sessão e fecha o app até o próximo login no sistema operacional).

### 6.5 Módulo Gestão de pastas pelo dono

| Funcionalidade | Ações | Resultado | Regras |
|---|---|---|---|
| Criar pasta | Nome, local, PIN e limite | Pasta nova criada e anunciada; auditoria | RN-13 a RN-17, RN-19, RN-20 |
| Trocar PIN | Novo PIN de 6 dígitos | Novos acessos exigem o PIN novo; conectados continuam | RN-18 |
| Alterar limite | Novo limite | Limite salvo dentro das faixas permitidas | RN-20, RN-23 |
| Ver usuários | Lista de quem tem acesso e quem está conectado | — | — |
| Remover usuário | "Apenas desconectar" ou "Remover e bloquear" | Acesso revogado; bloqueio opcional | RN-24, RN-25, RN-59 |
| Lista de bloqueados | Ver e desbloquear | Usuário volta a poder entrar com PIN | RN-25 |
| Lixeira | Ver, restaurar itens, esvaziar | — | RN-31 a RN-33 |
| Auditoria da pasta | Consultar com filtros | — | RN-41 a RN-44 |
| Desativar | Imediato ou com prazo | Clientes perdem acesso; arquivos ficam | RN-34 a RN-38 |
| Reativar | Restaurar acessos ou exigir PIN | Pasta volta a ser anunciada | RN-57 |
| Apagar | Imediato ou com prazo, digitando o nome | Arquivos vão para a Lixeira do SO | RN-34 a RN-39 |
| Cancelar ou alterar encerramento | Durante o prazo | Pasta volta ao normal ou novo horário final | RN-60 |
| Liberar arquivo em edição | Escolher arquivo na lista de arquivos em edição | Trava removida; auditoria | RN-66 |
| Trabalhar com o conteúdo | Mesmas operações de um cliente | — | RN-45 a RN-47, RN-62 a RN-65 |

### 6.6 Módulo Uso pelo cliente

| Funcionalidade | Ações | Resultado | Regras |
|---|---|---|---|
| Entrar numa pasta | Digitar PIN de 6 dígitos | Acesso concedido ao usuário naquele computador | RN-25, RN-27, RN-29 |
| Várias pastas | Conectar a várias pastas ao mesmo tempo | — | — |
| Acesso permanente e reconexão | Reconectar automaticamente após login ou volta do servidor | — | RN-28, RN-29 |
| Estado da conexão | Exibir conectado, reconectando, offline, em encerramento, desativada, encerrada ou acesso revogado | — | seção 12.6 |
| Operações com arquivos | Navegar, copiar para dentro e para fora, criar subpasta, renomear, mover dentro da pasta, excluir | — | RN-21, RN-31, RN-56, RN-68 |
| Sair da pasta | Copiar antes de sair, sair sem copiar ou cancelar | Acesso removido; auditoria | RN-30 |

### 6.7 Módulo Transferências

Barra de progresso por arquivo e geral, cancelamento com descarte do arquivo incompleto, escolha para nome repetido ("Substituir", "Manter os dois", "Pular", com "Aplicar a todos") e arrastar e soltar nos dois sentidos (RN-62 a RN-64). As transferências em andamento existem só em memória e são perdidas se o app ou o serviço for fechado; não há retomada.

### 6.8 Módulo Edição

Abertura no programa padrão, envio automático de cada salvamento, aviso "arquivo em edição", botão "Salvar edição" (envia a versão pendente e encerra a edição), detecção de fechamento por arquivos de trava, abertura somente leitura, cópia de conflito e alterações guardadas com o servidor offline (RN-45 a RN-47, RN-65, RN-66).

### 6.9 Módulo Notificações

Notificações do sistema operacional (balões da bandeja) e avisos dentro da janela, apenas para os eventos da seção 12.14 (RN-69). Alterações comuns em arquivos nunca geram notificação.

### 6.10 Módulo Auditoria

Registro dos eventos da RN-41, com consulta por dono (próprias pastas) e administrador (todas as pastas do computador), filtros e retenção (RN-41 a RN-44, RN-61).

### 6.11 Módulo Administração do sistema

Janela no estilo terminal aberta por Shift + F12, com bloqueio crescente (RN-58); janela de administração com as abas **Logs de erros**, **Auditoria das pastas** e **Resgate de usuários** (RN-48 a RN-55).

### 6.12 Módulo Logs de erros

Gravação em arquivo diário, organização por mês e ano, liga e desliga por configuração, consulta e limpeza pelo administrador, retenção fixa de 3 meses (RN-54, RN-55).

### 6.13 Módulo Instalação e reinstalação

Definição da chave, manutenção dos dados na reinstalação, preservação dos arquivos das pastas, registro do serviço e firewall (seção 4.5).

---

## 7. Fora de Escopo

Os itens abaixo **não** fazem parte da v1 e não devem ser implementados, nem parcialmente.

| Item | Motivo |
|---|---|
| Unidade virtual no explorador (ex.: `Z:`) | Muito trabalhosa e dependente do sistema operacional. Na v1, o acesso é pela janela do DriveLan. |
| Permissões diferentes por usuário (ex.: somente leitura) | Todos os clientes têm o mesmo poder sobre o conteúdo. |
| Modo "professor publica / aluno entrega" | Depende de permissões por usuário. |
| Pastas ocultas | Adiado. |
| Bloqueio de cópia pelo dono | Pouco eficaz, pois o cliente já copia durante o uso. |
| Retomada de transferências interrompidas | Trabalhoso. |
| Busca de arquivos dentro da pasta | Recurso de conforto adiado. |
| Histórico de versões de arquivos | Exige espaço e regras de retenção. |
| Transferência de posse de pasta | Adiado. |
| Acesso offline às pastas e sincronização contínua | Outro tipo de produto. A única exceção é a alteração guardada com o servidor offline (RN-65). |
| Edição simultânea em tempo real | Exige mesclagem; na v1 há aviso de edição e cópia de conflito. |
| Descoberta através de roteadores ou VLANs | Outros segmentos usam adição manual. |
| Acesso fora da LAN (internet ou VPN) | Foge do propósito e aumenta riscos. Placas VPN são ignoradas por padrão. |
| Interface web, macOS e celular | Plataformas da v1: Windows e Linux. |
| Active Directory, LDAP e serviços de nuvem | Complexos demais para a v1. |
| Administração remota e poderes extras do administrador | O administrador atua só no computador local e só com os recursos da seção 6.11. |
| Atalho global ou outro meio de abrir a janela do administrador | Só Shift + F12 com uma janela do DriveLan em foco. |
| Log de segurança separado | Os eventos de segurança ficam na auditoria. |
| Notificação de alterações comuns em arquivos | Ficam apenas na auditoria. |
| Recuperação de PIN pelo próprio usuário | Só o administrador resolve. |
| APIs públicas, webhooks e integrações externas | Existe apenas o protocolo interno do DriveLan. |
| Exportações (CSV, PDF, Excel) e relatórios gerenciais, gráficos ou indicadores | Existem apenas as consultas da seção 22. |
| Telemetria e atualização automática | Não aprovadas. |
| IPv6 | Não necessário para a v1. |

---

## 8. Perfis de Usuário e Permissões

Existe **um único tipo de conta**. "Dono" e "cliente" são **papéis contextuais**, definidos por pasta. O **administrador do sistema** não é uma conta: é um acesso temporário liberado pela chave de segurança do computador. Não há RBAC configurável.

### 8.1 Usuário (conta comum)

- **Descrição:** pessoa com conta local no computador, identificada na rede como `nome@host`.
- **Permissões:** criar conta, fazer login, alterar o próprio nome e PIN, excluir a própria conta, ver o dashboard e as pastas da rede, adicionar servidor manualmente, escolher a placa de rede, criar pastas (tornando-se dono) e entrar em pastas (tornando-se cliente).
- **Restrições:** vê e gerencia apenas a própria conta, as próprias pastas e os próprios acessos.
- **Ações bloqueadas:** ver ou alterar contas, pastas ou acessos de outros usuários do computador; recuperar o próprio PIN; ver logs de erros.

### 8.2 Dono da pasta

- **Descrição:** usuário que criou a pasta no próprio computador.
- **Permissões:** todas as da seção 6.5 sobre as pastas que criou e sobre o conteúdo delas.
- **Ações bloqueadas:** compartilhar uma pasta já existente; usar locais proibidos; limite abaixo do ocupado ou acima do máximo da RN-20; ver a auditoria de pastas de outros donos; consultar a auditoria das próprias pastas depois de apagadas.

### 8.3 Cliente

- **Descrição:** usuário que entrou numa pasta de outra conta (no mesmo computador ou em outro) com o PIN.
- **Permissões:** ler, abrir, editar, copiar, criar subpastas, renomear, mover e excluir o conteúdo; sair da pasta com opção de cópia.
- **Ações bloqueadas:** gerenciar a pasta (PIN, limite, usuários, bloqueados, encerramento); restaurar ou esvaziar a lixeira; ver a auditoria; entrar estando bloqueado; alterar conteúdo durante o prazo de encerramento; enviar além do limite.

### 8.4 Administrador do sistema

- **Descrição:** técnico de TI que conhece a chave de segurança daquele computador.
- **Permissões:** consultar e limpar logs de erros; consultar a auditoria de todas as pastas do computador, inclusive pastas apagadas há até 1 mês; definir PIN temporário para qualquer conta do computador, reativando-a.
- **Ações bloqueadas:** ver ou alterar a chave; abrir o conteúdo das pastas; apagar, desativar ou alterar pastas; desativar contas; atuar em outros computadores.

### 8.5 Matriz de permissões

| Ação | Usuário | Dono (própria pasta) | Cliente (pasta de outro) | Administrador |
|---|:-:|:-:|:-:|:-:|
| Criar conta, login, alterar nome e PIN, excluir a própria conta | ✓ | ✓ | ✓ | — |
| Ver dashboard e pastas da rede; adicionar e remover servidor manual; escolher placa | ✓ | ✓ | ✓ | — |
| Sair da conta | ✓ | ✓ | ✓ | — |
| Criar pasta compartilhada | ✓ | ✓ | ✓ | — |
| Trocar PIN e limite da pasta; ver o uso do limite | — | ✓ | — | — |
| Ver usuários, remover, bloquear e desbloquear | — | ✓ | — | — |
| Ver lixeira, restaurar e esvaziar | — | ✓ | — | — |
| Ver auditoria da pasta ativa ou desativada | — | ✓ | — | ✓ |
| Ver auditoria de pasta apagada (até 1 mês) | — | — | — | ✓ |
| Desativar, reativar, apagar, cancelar ou alterar encerramento | — | ✓ | — | — |
| Liberar manualmente arquivo em edição | — | ✓ | — | — |
| Navegar, copiar para o computador, abrir somente leitura | — | ✓ | ✓ (inclusive durante o encerramento) | — |
| Abrir para editar, enviar, criar subpasta, renomear, mover, excluir conteúdo | — | ✓ | ✓ (fora do prazo de encerramento) | — |
| "Salvar edição" e liberar a própria trava de edição | — | ✓ | ✓ | — |
| Entrar na pasta com PIN e sair da pasta | — | — | ✓ | — |
| Abrir a janela da chave com Shift + F12 (qualquer pessoa no computador; só avança com a chave correta) | ✓ | ✓ | ✓ | ✓ |
| Consultar e limpar logs de erros | — | — | — | ✓ |
| Definir PIN temporário e reativar conta | — | — | — | ✓ |

---

## 9. Recursos Estruturais do Sistema

### 9.1 Autenticação

- **Objetivo:** identificar quem usa o app e quem faz cada alteração.
- **Onde se aplica:** conta local (nome + PIN de 4 dígitos), acesso a pastas (PIN de 6 dígitos, trocado por um token de acesso), administrador (chave de segurança), sessão local entre app e serviço e sessão de transporte entre instalações.
- **Comportamento esperado:** detalhado na seção 15.
- **Cuidados:** PINs e chave guardados com Argon2id; bloqueios por tentativas; banco legível só pelo serviço; tokens guardados apenas como hash no servidor.
- **Validação:** login com PIN errado conta tentativa; 5 erros bloqueiam; token inválido é recusado.

### 9.2 Controle de acesso por papéis fixos

- **Objetivo:** garantir que cada pessoa só faça o que o papel permite.
- **Onde se aplica:** toda rota do canal local e do protocolo de rede.
- **Comportamento:** a camada `regras/` verifica o papel a cada pedido (seção 16). A interface esconde o que não é permitido, mas a decisão final é sempre do serviço.
- **Validação:** pedidos forjados ao canal local ou à rede para ações sem permissão são recusados com `acesso_negado`.

### 9.3 Auditoria

- **Objetivo:** registrar quem fez o quê, quando e em qual pasta.
- **Onde se aplica:** eventos da RN-41, gravados pelo serviço do computador que hospeda a pasta (ou onde ocorreu a ação de conta e de administração).
- **Comportamento:** seção 17. Retenção de 12 meses; pastas apagadas ficam consultáveis por 1 mês, só pelo administrador.
- **Cuidados:** nunca registrar leituras, downloads, PINs, tokens ou o conteúdo digitado na chave.

### 9.4 Exclusão lógica (equivalente ao soft delete)

- **Objetivo:** evitar perda acidental e manter a auditoria coerente.
- **Onde se aplica:** lixeira da pasta (30 dias), desativação reversível de contas e pastas, conta excluída com identidade preservada, pasta apagada mantida no banco por 1 mês para a auditoria (arquivos enviados à Lixeira do SO).
- **Comportamento:** seção 18.

### 9.5 Log de erros

- **Objetivo:** diagnosticar falhas.
- **Onde se aplica:** serviço e app (o app envia seus erros ao serviço pelo canal local).
- **Comportamento:** somente em arquivos diários, organizados por mês e ano; liga e desliga pela configuração; retenção fixa de 3 meses; contingência quando a gravação falha (seção 19).

### 9.6 Log de segurança

Não existe log de segurança separado. Os eventos de segurança (erros de PIN, bloqueios, tentativas na chave, remoções, desbloqueios, trocas de PIN, ações do administrador, reativação de contas) ficam na **auditoria**.

### 9.7 Configurações globais

Arquivo `drivelan.toml` com: log ligado ou desligado, placa de rede escolhida e porta TCP (seção 20).

### 9.8 Uploads e anexos

Não há upload no sentido de sistema web. A **transferência de arquivos entre computadores** é a função central do produto e está especificada na seção 21.

### 9.9 Exportações, APIs e integrações externas

Não fazem parte da v1. Existe apenas o protocolo interno entre instalações do DriveLan (seção 23).

---

## 10. Entidades do Sistema

### 10.1 Entidades do lado servidor (pastas hospedadas neste computador)

| Entidade | Finalidade | Principais informações | Relacionamentos | Regras e permissões | Exclusão lógica | Auditoria |
|---|---|---|---|---|---|---|
| **Instalação** | Identidade deste computador | Identificador da instalação, nome do computador, certificado, hash da chave de segurança | Única por computador | Criada pela instalação; nunca editada pelo app | Não | Não |
| **Conta** | Usuário local | UUID, nome, PIN (hash), situação, PIN temporário, erros seguidos | Possui identidade; é dona de pastas; tem acessos de cliente | Criada por qualquer pessoa; editada só pelo titular; reativada pelo administrador | Desativada (reversível) ou excluída (identidade preservada) | Bloqueio, troca de nome e PIN, exclusão e reativação |
| **Identidade** | Representa um usuário `nome@host` na auditoria, local ou remoto | Identificador da instalação, UUID da conta, host, nome atual e nome anterior | Referenciada por auditoria, acessos, bloqueios, lixeira e edições | Atualizada quando o usuário muda de nome | Nunca apagada enquanto houver auditoria que a referencie | — |
| **Pasta** | Pasta compartilhada | UUID, nome, caminho, dono, PIN (hash), limite, espaço ocupado, situação | Pertence a uma conta; tem acessos, bloqueios, lixeira, edições, encerramentos e auditoria | Gerida só pelo dono | Desativada (reversível); apagada (registro mantido 1 mês) | Sim |
| **Encerramento programado** | Prazo de desativação ou exclusão | Tipo, horário de início e final, situação | Pertence a uma pasta | Só o dono cria, altera ou cancela | Histórico mantido | Sim |
| **Acesso** | Usuário com acesso a uma pasta | Identidade, token (hash), situação, datas, conexão atual | Pasta × identidade | Criado ao aceitar o PIN; revogado pelo dono ou por regras | Situação `removido` | Entrada, saída e remoção |
| **Bloqueio pelo dono** | Impedir a entrada de uma identidade | Identidade, datas | Pasta × identidade | Só o dono bloqueia e desbloqueia | Situação `desbloqueado` | Sim |
| **Bloqueio temporário de PIN** | Bloquear por 15 minutos após 5 erros | Instalação ou IP, contagem, bloqueado até | Pasta | Automático | Expira sozinho | Bloqueio |
| **Item da lixeira** | Item excluído recuperável | Caminho original, tamanho, quem excluiu, quando, local de armazenamento, situação | Pasta, identidade | Só o dono restaura ou esvazia | Situações finais | Exclusão, restauração, esvaziamento |
| **Arquivo em edição** | Trava de edição | Caminho, identidade, instalação, versão base, último sinal | Pasta, identidade | Criada ao abrir para editar; liberada ao fechar, por falta de sinal ou pelo dono | Removida ao liberar | Liberações |
| **Registro de auditoria** | Evento auditado | Pasta, identidade ou tipo de ator, ação, caminhos, detalhes, data | Pasta, identidade | Somente inclusão; nunca editado | Removido só pela retenção | — |
| **Controle da chave de segurança** | Bloqueio crescente da janela do administrador | Erros no ciclo, ciclos, bloqueado até | Único por computador | Automático | Não | Erros e bloqueios |

### 10.2 Entidades do lado cliente (guardadas pelo serviço deste computador para as contas locais)

| Entidade | Finalidade | Principais informações | Relacionamentos | Regras |
|---|---|---|---|---|
| **Servidor manual** | Servidor adicionado pelo usuário | Endereço (IP ou nome), porta | Pertence a uma conta | Só o titular vê, adiciona e remove |
| **Servidor conhecido** | Confiança no primeiro uso | Identificador da instalação remota (impressão digital do certificado), host, último endereço, indicação de instalação local | Único por computador | Registrado no primeiro contato; nunca substituído silenciosamente; inclui a própria instalação para acessos locais (seção 5.2.1) |
| **Acesso de cliente** | Pasta remota acessada pela conta | Instalação e pasta remotas, nome da pasta, rótulo do dono, token, situação | Conta × pasta remota | Usado na reconexão automática; suspenso no bloqueio da conta; mantém os estados revogado, encerrada e desativada até o usuário remover da lista ou sair da pasta |
| **Alteração pendente** | Salvamento feito com o servidor offline | Acesso de cliente, caminho remoto, versão base, local do arquivo no disco do usuário | Pertence a um acesso de cliente | Enviada automaticamente quando o servidor volta |
| **Edição ativa** | Arquivo aberto para edição pela conta, para retomar a edição após fechamento ou queda do app | Acesso de cliente (ou pasta própria), caminho, trava, versão base, arquivo local, usuário do SO | Pertence a um acesso de cliente ou a uma pasta própria | Criada ao abrir para editar; removida ao fim da edição; convertida em alteração pendente quando a trava não vale mais |

As **transferências em andamento** e as **sessões** existem apenas em memória e não são entidades persistidas.

---

## 11. Modelo de Dados Proposto

### 11.1 Convenções

- Banco SQLite único em `<dados do serviço>/drivelan.db`.
- PRAGMAs na abertura de toda conexão: `foreign_keys = ON`, `journal_mode = WAL`, `synchronous = NORMAL`, `busy_timeout = 5000`.
- Chave primária `id INTEGER PRIMARY KEY` em todas as tabelas. Entidades expostas na rede ou entre processos têm também `uuid TEXT` (UUID v4) único.
- Datas em `TEXT` no formato ISO 8601 em UTC com milissegundos (ex.: `2026-11-12T13:45:10.123Z`). A interface converte para o horário local do computador. O horário de referência é sempre o relógio do computador que hospeda a pasta.
- Situações em `TEXT` com `CHECK` listando os valores permitidos.
- Nomes normalizados (`*_normalizado`) = nome em Unicode NFC convertido com `casefold()`, usados em índices únicos para tratar maiúsculas e minúsculas como iguais.
- Campos de auditoria de linha: `criado_em` e `atualizado_em` em todas as tabelas mutáveis.

### 11.2 Tabelas

#### `schema_migracoes`
| Campo | Tipo | Observação |
|---|---|---|
| versao | INTEGER PK | Número da migration |
| nome | TEXT NOT NULL | Nome do arquivo |
| checksum | TEXT NOT NULL | SHA-256 do conteúdo aplicado |
| aplicada_em | TEXT NOT NULL | — |

#### `instalacao` (linha única, `id = 1`)
| Campo | Tipo | Observação |
|---|---|---|
| id | INTEGER PK | `CHECK (id = 1)` |
| instalacao_id | TEXT NOT NULL UNIQUE | Impressão digital SHA-256 (hexadecimal) do certificado DER |
| host_nome | TEXT NOT NULL | Nome do computador, atualizado na inicialização |
| chave_admin_hash | TEXT NOT NULL | Hash Argon2id da chave de segurança |
| versao_app | TEXT NOT NULL | — |
| criado_em, atualizado_em | TEXT NOT NULL | — |

O certificado e a chave privada ficam em arquivos em `<dados do serviço>/certificado/`, com as mesmas permissões restritas da pasta de dados.

#### `admin_controle` (linha única, `id = 1`)
| Campo | Tipo | Observação |
|---|---|---|
| erros_no_ciclo | INTEGER NOT NULL DEFAULT 0 | 0 a 4 |
| ciclos_bloqueio | INTEGER NOT NULL DEFAULT 0 | Quantos bloqueios já ocorreram desde o último acesso correto |
| bloqueado_ate | TEXT NULL | — |
| atualizado_em | TEXT NOT NULL | — |

#### `identidade`
| Campo | Tipo | Observação |
|---|---|---|
| id | INTEGER PK | — |
| instalacao_id | TEXT NOT NULL | Instalação da conta (a local, para contas deste computador) |
| conta_uuid | TEXT NOT NULL | UUID da conta na instalação de origem |
| host_nome | TEXT NOT NULL | — |
| nome_atual | TEXT NOT NULL | — |
| nome_anterior | TEXT NULL | Exibido entre parênteses na auditoria |
| criado_em, atualizado_em | TEXT NOT NULL | — |

Índices: `UNIQUE (instalacao_id, conta_uuid)`.

#### `identidade_nome_historico`
`id`, `identidade_id` (FK → identidade, ON DELETE CASCADE), `nome_anterior`, `nome_novo`, `alterado_em`. Índice: `(identidade_id, alterado_em)`.

#### `conta`
| Campo | Tipo | Observação |
|---|---|---|
| id | INTEGER PK | — |
| uuid | TEXT NOT NULL UNIQUE | — |
| identidade_id | INTEGER NOT NULL UNIQUE | FK → identidade |
| nome | TEXT NOT NULL | — |
| nome_normalizado | TEXT NOT NULL | — |
| pin_hash | TEXT NOT NULL | Argon2id |
| situacao | TEXT NOT NULL | `CHECK IN ('ativa','desativada','excluida')` |
| pin_temporario | INTEGER NOT NULL DEFAULT 0 | 1 = troca obrigatória no próximo login |
| erros_pin | INTEGER NOT NULL DEFAULT 0 | Erros seguidos no login |
| desativada_em, excluida_em | TEXT NULL | — |
| criado_em, atualizado_em | TEXT NOT NULL | — |

Índices: `UNIQUE (nome_normalizado) WHERE situacao <> 'excluida'` (permite reutilizar o nome de uma conta excluída); `(situacao)`.

Ao excluir a conta: `situacao = 'excluida'`, `pin_hash` substituído por valor inutilizável, `erros_pin = 0`. A linha e a identidade permanecem.

`conta.nome` e `identidade.nome_atual` guardam o mesmo valor para contas locais e são sempre atualizados na mesma transação (cadastro e troca de nome).

#### `pasta`
| Campo | Tipo | Observação |
|---|---|---|
| id | INTEGER PK | — |
| uuid | TEXT NOT NULL UNIQUE | Identificador da pasta no protocolo |
| conta_dono_id | INTEGER NOT NULL | FK → conta (ON DELETE RESTRICT) |
| nome | TEXT NOT NULL | — |
| nome_normalizado | TEXT NOT NULL | — |
| caminho | TEXT NOT NULL | Caminho absoluto no formato do SO |
| caminho_normalizado | TEXT NOT NULL | Caminho absoluto resolvido; no Windows, com `casefold()` |
| so_dono | TEXT NOT NULL | SID (Windows) ou UID (Linux) do usuário do SO que criou a pasta |
| pin_hash | TEXT NOT NULL | Argon2id |
| limite_bytes | INTEGER NOT NULL | `CHECK (limite_bytes > 0)` |
| bytes_conteudo | INTEGER NOT NULL DEFAULT 0 | Espaço do conteúdo visível |
| bytes_lixeira | INTEGER NOT NULL DEFAULT 0 | Espaço da lixeira da pasta |
| situacao | TEXT NOT NULL | `CHECK IN ('ativa','em_encerramento','desativada','apagada')` |
| desativada_por_bloqueio | INTEGER NOT NULL DEFAULT 0 | 1 = desativada pelo bloqueio da conta (RN-06), reativada no resgate (RN-52) |
| aviso_90_enviado | INTEGER NOT NULL DEFAULT 0 | Evita repetir o aviso de 90% até o uso cair abaixo de 90% |
| lixeira_so_pendente | INTEGER NOT NULL DEFAULT 0 | 1 = pasta apagada aguardando o envio dos arquivos à Lixeira do SO |
| desativada_em | TEXT NULL | Data da última desativação (zerada na reativação) |
| apagada_em | TEXT NULL | Início da contagem de 1 mês da auditoria |
| criado_em, atualizado_em | TEXT NOT NULL | — |

Índices: `UNIQUE (nome_normalizado) WHERE situacao <> 'apagada'`; `UNIQUE (caminho_normalizado) WHERE situacao <> 'apagada'`; `(conta_dono_id, situacao)`; `(situacao, apagada_em)`; `(lixeira_so_pendente, so_dono)`.

Espaço ocupado da pasta = `bytes_conteudo + bytes_lixeira`.

#### `pasta_encerramento`
| Campo | Tipo | Observação |
|---|---|---|
| id | INTEGER PK | — |
| pasta_id | INTEGER NOT NULL | FK → pasta (ON DELETE CASCADE) |
| tipo | TEXT NOT NULL | `CHECK IN ('desativar','apagar')` |
| iniciado_em | TEXT NOT NULL | — |
| termina_em | TEXT NOT NULL | — |
| situacao | TEXT NOT NULL | `CHECK IN ('programado','concluido','cancelado')` |
| criado_em, atualizado_em | TEXT NOT NULL | — |

Índices: `UNIQUE (pasta_id) WHERE situacao = 'programado'` (no máximo um encerramento programado por pasta); `(situacao, termina_em)`.

#### `acesso`
| Campo | Tipo | Observação |
|---|---|---|
| id | INTEGER PK | — |
| pasta_id | INTEGER NOT NULL | FK → pasta (ON DELETE CASCADE) |
| identidade_id | INTEGER NOT NULL | FK → identidade |
| token_hash | TEXT NOT NULL UNIQUE | SHA-256 do token |
| situacao | TEXT NOT NULL | `CHECK IN ('ativo','removido')` |
| motivo_remocao | TEXT NULL | `desconectado`, `bloqueado`, `saiu`, `pin_exigido_na_reativacao`, `conta_excluida` |
| concedido_em | TEXT NOT NULL | — |
| ultima_conexao_em | TEXT NULL | — |
| removido_em | TEXT NULL | — |
| criado_em, atualizado_em | TEXT NOT NULL | — |

Índices: `UNIQUE (pasta_id, identidade_id) WHERE situacao = 'ativo'`; `(pasta_id, situacao)`.

A informação "conectado agora" vem das conexões WebSocket abertas, mantidas em memória pelo serviço.

#### `bloqueio_dono`
`id`, `pasta_id` (FK, CASCADE), `identidade_id` (FK), `situacao` (`CHECK IN ('ativo','desbloqueado')`), `bloqueado_em`, `desbloqueado_em`, `criado_em`, `atualizado_em`. Índices: `UNIQUE (pasta_id, identidade_id) WHERE situacao = 'ativo'`; `(pasta_id, situacao)`.

#### `bloqueio_pin_pasta`
| Campo | Tipo | Observação |
|---|---|---|
| id | INTEGER PK | — |
| pasta_id | INTEGER NOT NULL | FK → pasta (CASCADE) |
| tipo_chave | TEXT NOT NULL | `CHECK IN ('instalacao','ip')` |
| valor_chave | TEXT NOT NULL | Identificador da instalação ou endereço IP |
| erros | INTEGER NOT NULL DEFAULT 0 | — |
| bloqueado_ate | TEXT NULL | — |
| ultimo_erro_em | TEXT NOT NULL | — |
| criado_em, atualizado_em | TEXT NOT NULL | — |

Índice: `UNIQUE (pasta_id, tipo_chave, valor_chave)`. Linhas sem bloqueio vigente e sem erro há mais de 24 horas são removidas pela tarefa diária.

#### `lixeira_item`
| Campo | Tipo | Observação |
|---|---|---|
| id | INTEGER PK | — |
| uuid | TEXT NOT NULL UNIQUE | Nome do item dentro da área da lixeira |
| pasta_id | INTEGER NOT NULL | FK → pasta (CASCADE) |
| caminho_original | TEXT NOT NULL | Caminho relativo no formato do protocolo |
| tipo | TEXT NOT NULL | `CHECK IN ('arquivo','pasta')` |
| tamanho_bytes | INTEGER NOT NULL | — |
| excluido_por_identidade_id | INTEGER NOT NULL | FK → identidade |
| excluido_em | TEXT NOT NULL | — |
| situacao | TEXT NOT NULL | `CHECK IN ('na_lixeira','restaurado','esvaziado','expirado')` |
| finalizado_em | TEXT NULL | — |
| criado_em, atualizado_em | TEXT NOT NULL | — |

Índices: `(pasta_id, situacao, excluido_em)`; `(situacao, excluido_em)` para a limpeza de 30 dias; `(situacao, finalizado_em)` para remover linhas finalizadas há mais de 12 meses. Linhas finalizadas são removidas junto com a pasta ou após 12 meses.

#### `arquivo_em_edicao`
| Campo | Tipo | Observação |
|---|---|---|
| id | INTEGER PK | — |
| uuid | TEXT NOT NULL UNIQUE | Identificador da trava |
| pasta_id | INTEGER NOT NULL | FK → pasta (CASCADE) |
| caminho | TEXT NOT NULL | Relativo, formato do protocolo |
| caminho_normalizado | TEXT NOT NULL | — |
| identidade_id | INTEGER NOT NULL | FK → identidade |
| instalacao_id | TEXT NOT NULL | Computador de quem edita |
| versao_base | TEXT NOT NULL | Versão do arquivo quando a edição começou |
| iniciado_em | TEXT NOT NULL | — |
| ultimo_sinal_em | TEXT NOT NULL | — |
| criado_em, atualizado_em | TEXT NOT NULL | — |

Índices: `UNIQUE (pasta_id, caminho_normalizado)`; `(ultimo_sinal_em)`.

#### `auditoria`
| Campo | Tipo | Observação |
|---|---|---|
| id | INTEGER PK | — |
| pasta_id | INTEGER NULL | FK → pasta (ON DELETE CASCADE); nulo para eventos de conta e de administração |
| pasta_nome | TEXT NULL | Nome da pasta no momento do evento |
| ator_tipo | TEXT NOT NULL | `CHECK IN ('usuario','administrador','sistema','computador')` |
| identidade_id | INTEGER NULL | FK → identidade; obrigatório quando `ator_tipo = 'usuario'` |
| ator_rotulo | TEXT NULL | Para `computador`: host e instalação de quem errou o PIN; para `administrador`: "Administrador do sistema" |
| acao | TEXT NOT NULL | Código da seção 17.2 |
| alvo_caminho | TEXT NULL | Item afetado |
| alvo_caminho_novo | TEXT NULL | Destino em renomeações e movimentações |
| detalhes | TEXT NULL | JSON com dados complementares (nunca PINs, tokens ou chave) |
| ocorrido_em | TEXT NOT NULL | — |

Índices:
- `(ocorrido_em DESC, id DESC)` para a listagem geral do administrador;
- `(pasta_id, ocorrido_em DESC, id DESC)` para a auditoria de uma pasta;
- `(identidade_id, ocorrido_em DESC)` para o filtro por usuário;
- `(acao, ocorrido_em DESC)` para o filtro por tipo de ação;
- `(pasta_id, identidade_id)` para montar a lista de usuários do filtro de uma pasta (`SELECT DISTINCT`).

Busca por nome de arquivo ou pasta: tabela virtual **FTS5** `auditoria_busca` com tokenizador `trigram`, indexando `alvo_caminho`, `alvo_caminho_novo` e `pasta_nome`, sincronizada por gatilhos de inclusão e exclusão. Se o SQLite em uso não suportar `trigram`, a busca usa `LIKE` restrito pelos demais filtros e pelo período.

#### `cliente_servidor_manual`
`id`, `conta_id` (FK → conta, CASCADE), `endereco` (IP ou nome), `porta` (INTEGER, `CHECK BETWEEN 1 AND 65535`), `criado_em`, `atualizado_em`. Índice: `UNIQUE (conta_id, endereco, porta)`.

#### `cliente_servidor_conhecido`
`id`, `instalacao_id` (TEXT UNIQUE), `host_nome`, `ultimo_endereco` (NULL para a instalação local), `ultima_porta` (NULL para a instalação local), `local` (INTEGER NOT NULL DEFAULT 0; 1 = esta própria instalação, seção 5.2.1), `primeiro_contato_em`, `ultimo_contato_em`, `criado_em`, `atualizado_em`. Índices: `(host_nome)`; `UNIQUE (local) WHERE local = 1`.

#### `cliente_acesso`
| Campo | Tipo | Observação |
|---|---|---|
| id | INTEGER PK | — |
| conta_id | INTEGER NOT NULL | FK → conta (CASCADE) |
| servidor_conhecido_id | INTEGER NOT NULL | FK → cliente_servidor_conhecido |
| pasta_uuid | TEXT NOT NULL | UUID da pasta no servidor |
| pasta_nome | TEXT NOT NULL | Último nome conhecido |
| dono_rotulo | TEXT NOT NULL | `dono@host` |
| token | TEXT NOT NULL | Token de acesso (legível só pelo serviço) |
| situacao | TEXT NOT NULL | `CHECK IN ('ativo','suspenso','identidade_alterada','revogado','desativada','encerrada')` |
| concedido_em, ultima_conexao_em | TEXT | — |
| criado_em, atualizado_em | TEXT NOT NULL | — |

Índices: `UNIQUE (conta_id, servidor_conhecido_id, pasta_uuid)`; `(conta_id, situacao)`.

Uso das situações:
- `ativo`: reconecta automaticamente;
- `suspenso`: conta bloqueada (RN-06); volta a `ativo` no resgate (RN-52);
- `identidade_alterada`: RN-67; nenhuma conexão é tentada;
- `desativada`: o servidor respondeu `pasta_desativada`; o serviço continua tentando reconectar e volta a `ativo` quando a pasta for reativada com restauração (ou passa a `revogado` se for exigido PIN);
- `revogado`: o servidor respondeu `token_invalido` ou enviou `acesso_revogado`;
- `encerrada`: o servidor respondeu `pasta_encerrada` ou a pasta não existe mais.

A linha só é apagada quando o usuário escolhe "Remover da lista" (situações `revogado` e `encerrada`) ou "Sair da pasta" (qualquer situação). Assim, os estados continuam visíveis mesmo após reiniciar o app ou o computador. Se o usuário entrar de novo com PIN numa pasta em `revogado`, a mesma linha é reaproveitada com o novo token e volta a `ativo`.

#### `cliente_alteracao_pendente`
| Campo | Tipo | Observação |
|---|---|---|
| id | INTEGER PK | — |
| cliente_acesso_id | INTEGER NOT NULL | FK → cliente_acesso (CASCADE) |
| caminho_remoto | TEXT NOT NULL | — |
| versao_base | TEXT NOT NULL | — |
| arquivo_local | TEXT NOT NULL | Caminho do arquivo em `pendentes/` na pasta de dados do usuário |
| so_usuario | TEXT NOT NULL | SID ou UID do usuário do SO dono do arquivo local |
| guardada_em | TEXT NOT NULL | — |
| tentativas | INTEGER NOT NULL DEFAULT 0 | — |
| ultimo_erro | TEXT NULL | Código do último erro |
| criado_em, atualizado_em | TEXT NOT NULL | — |

Índices: `UNIQUE (cliente_acesso_id, caminho_remoto)`; `(so_usuario)`.

Alterações pendentes só existem para pastas de outros computadores: a pasta própria do dono e as pastas de outras contas do mesmo computador (seção 5.2.1) são atendidas pelo serviço local, que está sempre disponível para o app.

#### `cliente_edicao_ativa`
| Campo | Tipo | Observação |
|---|---|---|
| id | INTEGER PK | — |
| conta_id | INTEGER NOT NULL | FK → conta (CASCADE) |
| cliente_acesso_id | INTEGER NULL | FK → cliente_acesso (CASCADE); para pasta remota |
| pasta_id | INTEGER NULL | FK → pasta (CASCADE); para pasta própria |
| caminho_remoto | TEXT NOT NULL | Caminho do arquivo na pasta |
| trava_uuid | TEXT NOT NULL | Identificador da trava no servidor |
| versao_base | TEXT NOT NULL | Última versão confirmada pelo servidor |
| local_mtime_envio | INTEGER NULL | Data de modificação (ns) do arquivo local no último envio aceito |
| local_tamanho_envio | INTEGER NULL | Tamanho do arquivo local no último envio aceito |
| arquivo_local | TEXT NOT NULL | Caminho na pasta `edicao/` do usuário |
| so_usuario | TEXT NOT NULL | SID ou UID do usuário do SO |
| iniciada_em | TEXT NOT NULL | — |
| criado_em, atualizado_em | TEXT NOT NULL | — |

Constraints: `CHECK` exigindo exatamente um entre `cliente_acesso_id` e `pasta_id`. Índices: `UNIQUE (conta_id, cliente_acesso_id, caminho_remoto)`; `UNIQUE (conta_id, pasta_id, caminho_remoto)`; `(so_usuario)`.

A linha é criada quando a trava é obtida, tem `versao_base` atualizada a cada envio aceito e é removida no fim da edição. As regras de retomada estão no fluxo 13.14.

### 11.3 Estratégia de migrations

- A estrutura do banco é criada e atualizada **somente por migrations**. Ninguém cria tabelas manualmente.
- Cada migration é um arquivo SQL numerado em `src/drivelan/servico/dados/migracoes/` (ex.: `0001_inicial.sql`, `0002_<descricao>.sql`), contendo tabelas, campos, chaves, índices, constraints, gatilhos e dados iniciais obrigatórios (apenas as linhas únicas `admin_controle` e, quando aplicável, ajustes de dados).
- A tabela `schema_migracoes` registra as versões aplicadas. O executor:
  1. lê as migrations empacotadas em ordem numérica;
  2. ignora as já registradas e confere o `checksum`; se uma migration já aplicada foi alterada, registra erro no log e para (o serviço continua tentando a cada 30 segundos sem corromper dados);
  3. antes de aplicar qualquer migration pendente, copia o banco para `drivelan.db.antes-<versao>` (mantém apenas as 3 cópias mais recentes);
  4. aplica cada migration numa transação própria e registra a versão na mesma transação.
- **Execução controlada:** as migrations rodam apenas (a) automaticamente na inicialização do serviço ou (b) pelo comando `drivelan-service --migrar`, que exige privilégio de administrador do SO. Não existe rota no canal local nem na rede para executar migrations.
- As migrations ficam no diretório do programa, somente leitura para usuários comuns. O banco fica na pasta de dados protegida.
- Migrations nunca apagam arquivos das pastas compartilhadas.
- A migration `0001_inicial.sql` cria todas as tabelas, índices, a tabela FTS5 e os gatilhos desta seção.

### 11.4 Integridade e desempenho

- Toda gravação que envolve mais de uma tabela (ex.: bloqueio de conta, reativação, exclusão de item com auditoria) acontece numa única transação.
- O contador `bytes_conteudo` e `bytes_lixeira` é atualizado na mesma transação de cada operação e recalculado por varredura em segundo plano na inicialização e diariamente, para corrigir mudanças feitas direto no disco. O envio de arquivos nunca percorre a pasta inteira.
- A auditoria é paginada por cursor (`ocorrido_em`, `id`), 100 registros por página.
- `VACUUM` não é executado automaticamente; `PRAGMA optimize` roda na tarefa diária.

---

## 12. Módulos e Telas

### 12.1 Diretrizes visuais e correções ao `docs/DESIGN.md`

A aparência segue o `docs/DESIGN.md`, aplicado com as correções abaixo, que prevalecem sobre o texto original:

- **Paleta oficial:** a do texto descritivo. Fundos `#0E1024` (base), `#181B3A` (painéis), `#22264C` (elevado e hover); borda `#2A2E5C`; destaques `#3D6BFF` (primária), `#8B5CF6` (secundária, itens locais), `#22D3EE` (terciária, itens da rede e foco); gradiente de 135° de `#3D6BFF` para `#8B5CF6` nos botões primários; texto `#F1F3FF` e `#A3A8D6`; status `#22C55E` (online), `#64748B` (offline), `#F59E0B` (atenção), `#F43F5E` (erro e bloqueio). Os tokens de cor do cabeçalho YAML do `DESIGN.md` são descartados.
- **Arredondamentos:** 12px em cartões e painéis; 8px em botões e campos; pílula em selos e chips.
- **Desfoque de fundo:** não usar `backdrop-filter`. Atrás de modais, usar fundo escuro semitransparente (`rgba(5, 7, 18, 0.6)`). A sombra de modal pode ser simulada com `QGraphicsDropShadowEffect` apenas no diálogo.
- **Selos em português:** "Pasta local" (ícone `#8B5CF6`) e "Pasta da rede" (ícone `#22D3EE`).
- **Chip âmbar** (`#F59E0B`): representa "Reconectando", "Em edição" e "Em encerramento". Não existe estado "sincronizando".
- **Textos da interface:** todos em português e marcados para tradução (`self.tr()` / `QCoreApplication.translate`).
- **Tipografia:** Inter para toda a interface; JetBrains Mono para IPs, identificadores, impressões digitais, PINs e a janela do administrador.
- **Folha QSS central:** `recursos/estilo/drivelan.qss`, com os tokens como variáveis substituídas na carga. Nenhum widget define cores no código.
- **Janela:** mínimo 800 × 600, tamanho inicial 1200 × 800. Barra de título própria de 38px (minimizar, maximizar, fechar; botões de 46 × 38; fechar com hover `#F43F5E`), arrastada com `QWindow.startSystemMove()` para funcionar também no Wayland, e redimensionada pelas bordas com `QWindow.startSystemResize()`. No Windows, a janela trata `WM_NCHITTEST` em `nativeEvent`, devolvendo `HTMAXBUTTON` sobre o botão maximizar (para exibir os Snap Layouts do Windows 11), `HTCAPTION` na área de arrasto e os códigos de borda para redimensionar; os cantos arredondados do sistema são mantidos com `DwmSetWindowAttribute` (`DWMWA_WINDOW_CORNER_PREFERENCE`). Barra lateral de 240px, recolhível para 64px; painel de detalhes opcional à direita de 320px.

Os componentes (botões primário, secundário e fantasma; PIN segmentado; cartões de pasta; alertas; chips de status) seguem as especificações do `docs/DESIGN.md`. Este FSD define apenas comportamento e conteúdo.

### 12.2 Estrutura geral da janela

- **Barra lateral:** Início (dashboard), Minhas pastas, Pastas que acesso, Pastas da rede, Transferências; no rodapé, Configurações de usuário e Configurações do app.
- **Cabeçalho do dashboard:** conta logada, nome do computador, rede atual (nome, IP e faixa).
- **Área central:** conteúdo da seção escolhida.
- **Faixa de avisos:** abaixo do cabeçalho, para avisos persistentes (ex.: contagem regressiva de encerramento, arquivo em edição, servidor offline).
- **Mensagens de resultado:** avisos temporários (toast) de 4 segundos no canto inferior direito para sucesso; erros ficam até serem fechados.

Estados comuns a todas as listas: **carregando** (indicador e texto "Carregando…"), **vazio** (texto explicativo e ação sugerida), **erro** (alerta vermelho com "Tentar novamente") e **serviço indisponível** (tela "O serviço do DriveLan não está respondendo. Aguarde alguns instantes ou reinicie o computador." com nova tentativa automática a cada 5 segundos).

### 12.3 Tela de login e cadastro

- **Usuários:** qualquer pessoa no computador.
- **Login:** campo "Nome de usuário", PIN segmentado de 4 dígitos, botão "Entrar", link "Criar conta". Shift + F12 disponível.
- **Cadastro:** "Nome de usuário", "PIN (4 dígitos)", "Confirmar PIN", botão "Criar conta", link "Voltar".
- **Mensagens:**
  - "Nome de usuário ou PIN incorreto. Tentativas restantes: N." (N de 4 a 1);
  - "Conta bloqueada após 5 tentativas incorretas. Procure o Administrador do Aplicativo para redefinir seu PIN.";
  - "Este nome já está em uso neste computador.";
  - "O PIN deve ter exatamente 4 números.";
  - "Os PINs não conferem.";
  - "Conta criada com sucesso. Faça login para continuar."
- **Estados:** botão desativado durante o envio; PIN com animação de tremor em erro.

### 12.4 Troca obrigatória de PIN e tela de desbloqueio

- **Troca obrigatória:** aparece após login com PIN temporário. Campos "Novo PIN" e "Confirmar novo PIN". O novo PIN não pode ser igual ao temporário ("Escolha um PIN diferente do temporário."). Não há como pular nem acessar o dashboard antes.
- **Desbloqueio:** ao reabrir a janela com uma sessão em segundo plano (seção 15.3), mostra o nome da conta, PIN de 4 dígitos, botão "Entrar" e link "Entrar com outra conta" (encerra a sessão atual e volta ao login). Erros contam para o bloqueio de 5 tentativas.

### 12.5 Dashboard

- **Usuários:** conta logada.
- **Conteúdo:**
  - cabeçalho com conta, computador e rede (ex.: "Rede: Wi-Fi Escola · 192.168.0.25 · 192.168.0.0/24"; ou "Rede cabeada"; ou "Sem rede" em vermelho);
  - **Minhas pastas:** cartões com selo "Pasta local", nome, caminho, uso do limite (barra e "3,2 GB de 10 GB"), usuários conectados, situação (Ativa, Em encerramento com tempo restante, Desativada) e ícone de configurações da pasta;
  - **Pastas que acesso:** cartões com selo "Pasta da rede", nome, `dono@host`, chip de estado da conexão (seção 12.6) e ação "Abrir";
  - **Pastas da rede:** lista resumida das 5 primeiras com link "Ver todas";
  - botões "Criar pasta" (primário) e "Adicionar servidor" (secundário).
- **Estados vazios:** "Você ainda não criou pastas." com botão "Criar pasta"; "Você ainda não acessa pastas de outras pessoas."; "Nenhuma pasta encontrada na rede. Se você sabe o endereço do computador, use Adicionar servidor."

### 12.6 Estados da conexão de uma pasta acessada

| Estado | Chip | Significado | Ação disponível |
|---|---|---|---|
| Conectado | Verde "Conectado" | WebSocket ativo e acesso válido | Abrir |
| Reconectando | Âmbar "Reconectando" | Tentativa de reconexão em andamento | — |
| Offline | Cinza "Offline" | Servidor não encontrado | Sair da pasta (sem cópia) |
| Em encerramento | Âmbar "Em encerramento · 00:45:12" | Prazo de encerramento ativo; somente leitura | Abrir (somente cópia) |
| Desativada | Cinza "Desativada pelo dono" | Pasta desativada; o acesso volta se o dono reativar com restauração | Sair da pasta |
| Encerrada | Vermelho "Pasta encerrada" | Pasta apagada ou inexistente | Remover da lista |
| Acesso revogado | Vermelho "Acesso revogado" | Removido ou bloqueado pelo dono, ou PIN exigido na reativação | Remover da lista; entrar novamente com PIN quando permitido |
| Identidade alterada | Vermelho "Identidade alterada" | O servidor apresentou outra identidade de segurança (RN-67) | Ver detalhes; sair da pasta |
| Suspenso | — | Não aparece: só ocorre com a conta desativada, quando não há login | — |

Reconexão: tentativas com espera crescente (2 s, 5 s, 10 s, 30 s e depois a cada 60 s) e imediatamente quando o servidor reaparece na descoberta.

### 12.7 Pastas da rede, adicionar servidor e entrar com PIN

- **Lista completa de pastas da rede:** colunas Nome, Dono (`dono@host`), Computador (IP em JetBrains Mono), Status (Online, Offline, Em encerramento) e Situação de acesso ("Tem acesso", "Bloqueado", "Precisa do PIN"). Ordenação por nome. Exemplo de linha: "Financeiro — maria@ADM-PC02 — Online — Precisa do PIN".
- Pastas hospedadas no próprio computador e de outras contas também aparecem. As pastas da própria conta aparecem em "Minhas pastas", não nesta lista.
- **Adicionar servidor (modal):** campos "IP ou nome do computador" e "Porta" (preenchida com a porta padrão). Botão "Adicionar". Mensagens: "Servidor adicionado. N pastas encontradas.", "Não foi possível conectar a esse endereço. Verifique o IP, a porta e se o DriveLan está instalado nele.", "Esse servidor já está na sua lista." Servidores manuais aparecem em Configurações do app, com opção "Remover".
- **Entrar com PIN (modal):** título com nome da pasta e `dono@host`, PIN segmentado de 6 dígitos, botão "Entrar". Mensagens:
  - "PIN incorreto. Tentativas restantes: N.";
  - "Muitas tentativas incorretas. Este computador poderá tentar novamente às HH:MM.";
  - "Você foi bloqueado pelo dono desta pasta.";
  - "Esta pasta está desativada no momento.";
  - "Acesso liberado." (o modal fecha e o navegador da pasta abre).

### 12.8 Criar pasta compartilhada (assistente em um passo)

- **Campos:**
  - **Nome da pasta** (obrigatório);
  - **Local:** sugerido no disco com mais espaço livre, com botão "Escolher outro local…" (seletor de diretório). Mostra o caminho final (local + nome);
  - **PIN da pasta:** 6 dígitos sugeridos aleatoriamente, editáveis, com botão "Gerar outro";
  - **Limite de tamanho:** valor e unidade (MB ou GB), sugerido em 10% do espaço livre do disco escolhido, com texto auxiliar "Espaço livre: 412 GB · máximo permitido: 329,6 GB".
- **Botões:** "Criar pasta" (primário), "Cancelar".
- **Mensagens:** "Já existe uma pasta compartilhada com esse nome neste computador.", "Este local não pode ser usado: <motivo>.", "O limite deve ser maior que zero e no máximo 80% do espaço livre (X).", "Pasta criada e compartilhada na rede." Ao concluir, mostra um resumo com nome, local e PIN, com aviso "Anote o PIN: ele não poderá ser visto novamente."

Motivos de local proibido (exibidos ao usuário): "raiz de disco", "pasta do sistema ou de programas", "pasta principal do seu perfil (use uma subpasta, como Documentos)", "dentro de outra pasta compartilhada", "contém uma pasta compartilhada", "unidade removível", "unidade de rede", "você não tem permissão de gravação neste local".

### 12.9 Navegador da pasta

- **Usuários:** dono e clientes com acesso.
- **Cabeçalho:** nome da pasta, `dono@host`, selo local ou da rede, chip de estado, uso do limite (só para o dono), botões "Configurações da pasta" (só dono) e "Sair da pasta" (só cliente).
- **Trilha de navegação** (breadcrumb) e botão "Voltar".
- **Tabela:** ícone, Nome, Tamanho, Modificado em, indicador de "Em edição por nome@host" (chip âmbar) e ícone de alerta para nome incompatível (RN-68, com dica explicando como o item será copiado).
- **Ações (barra e menu de contexto):** Abrir, Abrir somente leitura, Copiar para o computador…, Enviar arquivos…, Nova subpasta, Renomear, Mover para…, Excluir. Arrastar e soltar de e para o explorador do sistema e entre subpastas (mover).
- **Carregamento sob demanda:** itens buscados em páginas de 200, carregados conforme a rolagem (`canFetchMore` / `fetchMore`).
- **Faixas de aviso:** "Arquivo em edição: relatorio.docx — [Salvar edição]"; "Pasta em encerramento. Restam 00:45:12. Copie o que precisar."; "Servidor offline. Tentando reconectar…"; "Somente leitura".
- **Durante o encerramento:** ações de alteração desativadas, com dica "A pasta está em encerramento e aceita apenas cópias."
- **Estados:** vazio ("Esta pasta está vazia. Arraste arquivos para cá."), carregando, erro, sem permissão (acesso revogado → volta ao dashboard com aviso).
- **Confirmação de exclusão:** "Excluir N itens? Eles irão para a lixeira da pasta, de onde só o dono poderá restaurá-los."

### 12.10 Painel de transferências

- Usa o componente "Inspector / Detail Drawer" do `docs/DESIGN.md`: painel direito acoplado de 320px, acessível pela barra lateral e pela bandeja.
- Lista de transferências com nome, direção (enviar ou copiar para o computador), barra de progresso, velocidade, tempo restante, botão "Cancelar".
- Transferências concluídas ficam visíveis até o fim da sessão, com "Limpar concluídas".
- **Diálogo de nome repetido:** "Já existe um item chamado 'relatorio.docx' no destino." Botões "Substituir", "Manter os dois", "Pular" e caixa "Aplicar a todos".

### 12.11 Configurações da pasta (dono)

Janela com abas:

1. **Geral:** nome (somente leitura), local, data de criação, situação; **Trocar PIN** (novo PIN de 6 dígitos sugerido e editável; aviso "Quem já tem acesso continua conectado."); **Limite** (valor atual, uso e faixa permitida calculada pela RN-20, ex.: "Faixa permitida: 3,2 GB a 41,6 GB (80% de 48,8 GB livres + 3,2 GB ocupados)"). Quando o máximo se reduz ao ocupado, mostra o aviso "O disco está quase cheio: o limite só pode ser igual ao espaço já ocupado. Libere espaço no disco para aumentá-lo."
2. **Usuários:** tabela com `nome@host`, "Conectado agora" ou "Último acesso em", data de entrada; ação "Remover…".
3. **Bloqueados:** tabela com `nome@host`, data do bloqueio; ação "Desbloquear".
4. **Lixeira:** tabela com nome, caminho original, tamanho, excluído por, excluído em, dias restantes; ações "Restaurar" (um ou vários) e "Esvaziar lixeira". Total ocupado pela lixeira.
5. **Em edição:** arquivos em edição com `nome@host`, desde quando e último sinal; ação "Liberar".
6. **Auditoria:** consulta da seção 22.2, restrita a esta pasta.
7. **Encerramento:** se não houver encerramento: botões "Desativar compartilhamento" e "Apagar pasta" (vermelho). Se houver encerramento programado: tipo, horário final, contagem regressiva, botões "Alterar prazo" e "Cancelar encerramento". Se a pasta estiver desativada: botão "Reativar compartilhamento" e "Apagar pasta".

### 12.12 Configurações de usuário e do app

- **Configurações de usuário:** alterar nome (campo + "Salvar"); alterar PIN ("PIN atual", "Novo PIN", "Confirmar"); "Excluir minha conta" (vermelho); "Sair da conta".
- **Configurações do app:** placa de rede (lista com "Automática (recomendado)" e as placas disponíveis, VPN marcadas como "VPN — ignorada por padrão"; fluxo 13.27); servidores adicionados manualmente (lista com "Remover", fluxo 13.28); versão do DriveLan e porta em uso (somente leitura).

### 12.13 Diálogos de confirmação

| Diálogo | Conteúdo | Opções |
|---|---|---|
| Remover usuário | "Remover joao@LAB-PC07 da pasta Financeiro?" | "Apenas desconectar" (explicação: pode voltar com o PIN atual), "Remover e bloquear", "Cancelar" |
| Desativar compartilhamento | "N clientes conectados e M com acesso perderão o acesso." | "Encerrar imediatamente" ou "Definir prazo" (5 minutos a 7 dias, padrão 1 hora, com seletor de dias, horas e minutos); "Confirmar", "Cancelar" |
| Apagar pasta | Mesmo conteúdo do anterior, mais "Os arquivos serão enviados para a Lixeira do sistema." e campo "Digite o nome da pasta para confirmar". Para pasta já desativada, a escolha de prazo não aparece e a exclusão é imediata | Botão "Apagar pasta" habilitado só com o nome idêntico (diferenciando maiúsculas e minúsculas) |
| Reativar | "Como os usuários voltarão a acessar?" | "Restaurar acessos anteriores" (padrão), "Exigir PIN de todos novamente"; "A lista de bloqueados será mantida." |
| Alterar prazo | Novo prazo contado a partir de agora | 5 minutos a 7 dias |
| Sair da pasta | "Deseja copiar os arquivos antes de sair?" | "Copiar para uma pasta…", "Sair sem copiar", "Cancelar" |
| Esvaziar lixeira | "Apagar definitivamente N itens (X GB)? Esta ação não pode ser desfeita." | "Esvaziar", "Cancelar" |
| Excluir conta | Exige PIN atual | "Excluir conta", "Cancelar" |
| Identidade alterada | Texto da RN-67 com host, impressão digital registrada e nova (JetBrains Mono, abreviadas) | "Entendi" |
| Arquivo em edição por outra pessoa | "em edição por joao@LAB-PC07" | "Abrir somente leitura", "Cancelar" |

### 12.14 Notificações

Exibidas como balão da bandeja (`QSystemTrayIcon.showMessage`) e como aviso dentro da janela quando ela estiver aberta. Só são entregues enquanto houver sessão do DriveLan ativa para a conta envolvida (seção 15.3); não ficam acumuladas para depois.

| Para | Evento | Texto |
|---|---|---|
| Cliente | Encerramento com prazo | "A pasta Financeiro será encerrada em 1 hora. Copie o que precisar." (com contagem regressiva na faixa de aviso) |
| Cliente | Encerramento cancelado | "Encerramento cancelado: a pasta Financeiro voltou ao normal." |
| Cliente | Pasta encerrada ou desativada | "A pasta Financeiro foi encerrada." / "A pasta Financeiro foi desativada pelo dono." |
| Cliente | Acesso revogado | "Seu acesso à pasta Financeiro foi revogado pelo dono." |
| Cliente | Servidor offline ou reconectado | "A pasta Financeiro está offline." / "A pasta Financeiro voltou a ficar disponível." |
| Cliente | Conflito ao salvar | "Conflito ao salvar relatorio.docx. Sua versão foi guardada como 'relatorio (conflito joao).docx'." |
| Dono | Novo usuário entrou | "joao@LAB-PC07 entrou na pasta Financeiro." |
| Dono | Pasta perto do limite | "A pasta Financeiro atingiu 90% do limite." |
| Dono | Envio recusado por falta de espaço no disco | "Um envio para a pasta Financeiro foi recusado: o disco deste computador está sem espaço." |
| Dono | Bloqueio por tentativas de PIN | "O computador LAB-PC07 foi bloqueado por 15 minutos na pasta Financeiro após 5 PINs incorretos." |

A alteração do prazo de um encerramento **não** gera notificação: apenas a contagem regressiva da faixa de aviso e do chip é atualizada com o novo horário final.

### 12.15 Janela da chave de segurança

- Aberta com **Shift + F12** quando qualquer janela do DriveLan está em foco, inclusive a tela de login (atalho `QShortcut` com contexto de aplicação, registrado em todas as janelas). Não há atalho global.
- Pequena janela sempre em primeiro plano (`WindowStaysOnTopHint`), 520 × 220, fundo `#0E1024`, texto em JetBrains Mono, simulando um terminal:
  ```
  DriveLan — acesso administrativo
  chave> ●●●●●●●●
  ```
- O campo não ecoa caracteres (nem asteriscos em quantidade real: exibe um cursor piscando). Enter envia; Esc fecha.
- Mensagens: "Chave incorreta." / "Janela bloqueada. Tente novamente às HH:MM." (com contagem regressiva; o campo fica desativado).
- Chave correta → abre a janela de administração e fecha a janela da chave.

### 12.16 Janela de administração

Janela própria, independente da sessão de conta (funciona com ou sem usuário logado). Fechar a janela encerra a sessão de administrador.

1. **Logs de erros:** seletor de mês/ano e dia; visualizador de texto somente leitura (JetBrains Mono) carregado em partes de 1.000 linhas, com "Carregar mais"; campo "Buscar no log" com resultados progressivos (até 1.000 ocorrências) e navegação entre ocorrências; botão "Limpar logs…" com opções "Dia selecionado", "Mês selecionado" e "Todos os logs", e confirmação. Aviso no topo quando o log estiver desligado na configuração ("O registro de logs está desligado no arquivo de configuração.") ou quando houver falha de gravação (seção 19.1.5).
2. **Auditoria das pastas:** consulta da seção 22.2 com o filtro adicional por pasta (incluindo pastas apagadas há até 1 mês, marcadas "(apagada em DD/MM)").
3. **Resgate de usuários:** tabela de contas (nome, situação: Ativa, Desativada, PIN temporário pendente; criada em). Contas excluídas não aparecem. Ação "Definir PIN temporário…": campos "PIN temporário (4 dígitos)" e "Confirmar". Mensagem: "PIN temporário definido. A conta foi reativada e o usuário deverá trocar o PIN no próximo login."

Não há nenhuma ação que abra conteúdo de pastas, apague ou desative pastas.

### 12.17 Bandeja do sistema

- Ícone com menu: "Abrir DriveLan", "Criar pasta…", "Transferências", "Configurações", "Sair do DriveLan".
- Clique no ícone abre a janela (com a tela de desbloqueio, se houver sessão em segundo plano).
- Se a bandeja não estiver disponível (`QSystemTrayIcon.isSystemTrayAvailable()` falso, comum em alguns ambientes Wayland), o botão fechar da janela passa a **minimizar**, e as notificações aparecem só dentro da janela; "Sair do DriveLan" fica no menu da conta.

---

## 13. Fluxos Funcionais

### 13.1 Cadastro de usuário
- **Perfil:** qualquer pessoa. **Pré-condição:** serviço respondendo.
- **Passos:** (1) escolhe "Criar conta"; (2) informa nome, PIN e confirmação; (3) o app valida formato; (4) o serviço valida nome único (normalizado) e formato; (5) cria identidade local e conta ativa numa transação.
- **Resultado:** "Conta criada com sucesso. Faça login para continuar."
- **Erros:** nome inválido, nome em uso, PIN inválido, PINs diferentes.
- **Auditoria:** nenhuma.

### 13.2 Login
- **Perfil:** usuário. **Pré-condição:** conta existente.
- **Passos:** (1) informa nome e PIN; (2) o serviço localiza a conta (nome normalizado, situação diferente de excluída); (3) se desativada: "Conta bloqueada após 5 tentativas incorretas. Procure o Administrador do Aplicativo para redefinir seu PIN."; (4) se PIN correto: zera `erros_pin`, cria sessão local (seção 15.5) e, se `pin_temporario = 1`, exige a troca (13.3); (5) se PIN errado: incrementa `erros_pin` e informa as tentativas restantes; (6) no 5º erro seguido executa o bloqueio (13.4).
- **Resultado:** dashboard; reconexão automática dos acessos de cliente da conta; envio das alterações pendentes do usuário do SO atual.
- **Erros:** um nome inexistente recebe exatamente as mesmas mensagens de uma conta real, para não revelar se o nome existe. O serviço mantém em memória um contador fictício por nome normalizado (descartado após 15 minutos sem tentativas ou ao reiniciar o serviço), mostra "Tentativas restantes: N" de 4 a 1 e, no 5º erro, mostra a mesma mensagem de conta bloqueada. Nada é gravado no banco nem na auditoria, e nenhuma conta é bloqueada.

### 13.3 Troca obrigatória de PIN temporário
- **Passos:** (1) informa novo PIN e confirmação; (2) o serviço recusa se igual ao temporário; (3) grava o hash, zera `pin_temporario`.
- **Auditoria:** `conta_pin_trocado`.

### 13.4 Bloqueio da conta após 5 erros
- **Executor:** sistema, numa única transação.
- **Passos:** (1) conta → `desativada`; (2) toda pasta da conta em `ativa` ou `em_encerramento` → `desativada` com `desativada_por_bloqueio = 1`; encerramentos programados dessas pastas → `cancelado`; (3) conexões de clientes dessas pastas encerradas com o evento `pasta_desativada`; (4) acessos de cliente da conta → `suspenso`, conexões fechadas; (5) arquivos intactos; (6) sessões locais da conta encerradas.
- **Auditoria:** `conta_bloqueada` (com `detalhes`: quantidade de pastas desativadas e de acessos de cliente suspensos); `pasta_desativada` (com detalhe `motivo: bloqueio_conta`) para cada pasta; `encerramento_cancelado` quando houver.

### 13.5 Alterar nome
- **Passos:** (1) informa novo nome; (2) validação e unicidade; (3) atualiza conta, identidade (`nome_anterior` = nome antigo) e histórico.
- **Propagação:** nas próximas conexões com servidores remotos, a sessão de transporte envia o nome atual; o servidor remoto atualiza a identidade correspondente e o histórico, mantendo os registros antigos ligados à mesma pessoa.
- **Auditoria:** `conta_nome_alterado` (local) e, em cada servidor remoto, `identidade_nome_alterado` na primeira conexão após a troca.

### 13.6 Alterar PIN
- **Passos:** PIN atual (conta como tentativa de login em caso de erro), novo PIN e confirmação. **Auditoria:** `conta_pin_trocado`.

### 13.7 Excluir a própria conta
- **Pré-condição:** nenhuma pasta da conta em situação diferente de `apagada`.
- **Passos:** (1) se houver pastas: "Você ainda é dono de pastas. Apague-as antes de excluir a conta." e para; (2) pede o PIN (erro conta tentativa); (3) para cada acesso de cliente, o serviço avisa o servidor remoto (sair da pasta) quando ele estiver online; sem resposta, apenas apaga o acesso local; (4) apaga servidores manuais e alterações pendentes da conta; (5) marca a conta como `excluida`; (6) encerra a sessão.
- **Auditoria:** `conta_excluida` no computador local; `usuario_saiu` em cada servidor que respondeu.

### 13.8 Criar pasta compartilhada
- **Perfil:** usuário logado.
- **Passos:**
  1. Informa o nome; o app consulta o serviço para validar o nome (RN-68 e unicidade).
  2. O serviço calcula o local sugerido (RN-14) e devolve espaço livre, sugestão de 10% e máximo de 80%.
  3. O usuário pode escolher outro local; o serviço valida contra a RN-15.
  4. O app sugere um PIN aleatório de 6 dígitos (gerador criptográfico, evitando sequências e repetições como 123456 e 000000).
  5. Ao confirmar, **o app cria o diretório final com as permissões do usuário do SO**, o que comprova que ele pode gravar ali. Se o diretório já existir, recusa (RN-13).
  6. O serviço revalida: diretório vazio, recém-criado, pertencente ao usuário do SO que chamou (dono do arquivo igual à identidade do chamador do canal local), fora dos locais proibidos, sem conflito com outras pastas.
  7. O serviço cria a área interna `.drivelan/` (seção 21.3), grava a pasta (`ativa`) e anuncia na rede.
- **Resultado:** pasta em "Minhas pastas"; resumo com o PIN.
- **Erros:** nome duplicado, local proibido, sem permissão, limite fora da faixa, disco indisponível. Se o passo 6 ou 7 falhar, o app remove o diretório vazio que criou.
- **Auditoria:** `pasta_criada`.

### 13.9 Descoberta e lista de pastas da rede
- **Executor:** serviço, continuamente, enquanto houver ao menos uma sessão ativa no computador.
- **Passos:** (1) navega os serviços `_drivelan._tcp` por mDNS e envia broadcast UDP a cada 30 segundos (e ao abrir a lista); (2) para cada servidor encontrado (inclusive manuais), abre sessão de transporte (seção 23.4) e consulta `GET /v1/pastas`; (3) verifica a identidade do servidor (RN-67); se dois endereços diferentes anunciarem o mesmo identificador de instalação ao mesmo tempo, registra `AVISO` no log de erros ("Identificador de instalação duplicado: possível computador clonado"), usa apenas o endereço do registro mais antigo e mostra os demais como offline; (4) combina com os acessos de cliente locais para calcular a situação de acesso; (5) envia a lista ao app pelo canal local, com atualizações incrementais.
- **Status:** "Offline" quando o servidor não responde por 90 segundos ou sai do mDNS; pastas de servidores offline com acesso local continuam listadas como offline.

### 13.10 Entrar numa pasta como cliente
- **Perfil:** usuário logado, sem acesso ativo à pasta.
- **Passos:** (1) escolhe a pasta "Precisa do PIN"; (2) digita o PIN; (3) o serviço local envia `POST /v1/pastas/{uuid}/entrar` ao servidor; (4) o servidor verifica, nesta ordem: pasta ativa ou em encerramento (durante o encerramento a entrada é permitida e o novo cliente recebe a pasta em somente leitura, com a contagem regressiva) → bloqueio temporário por instalação ou IP → bloqueio pelo dono → PIN; (5) PIN correto: cria acesso, gera token, zera os contadores de erro daquela instalação e IP na pasta, devolve token; (6) o serviço local grava o acesso de cliente, registra o servidor conhecido (se primeiro contato) e abre o WebSocket de eventos.
- **Erros:** `pasta_desativada`, `pin_bloqueado_temporariamente` (com horário de liberação), `usuario_bloqueado`, `pin_incorreto` (com tentativas restantes). No 5º erro: bloqueio de 15 minutos da instalação e do IP naquela pasta.
- **Auditoria (no servidor):** `usuario_entrou`; `pin_pasta_bloqueio_temporario` no bloqueio. **Notificações ao dono:** entrada e bloqueio.

### 13.11 Reconexão automática
- **Gatilhos:** login na conta, volta do servidor na descoberta, falha de conexão.
- **Passos:** para cada acesso de cliente `ativo` ou `desativada` da conta, abre sessão de transporte e WebSocket com o token. O servidor sempre verifica primeiro a existência e a situação da pasta e só depois o token, para que uma pasta apagada responda `pasta_encerrada` mesmo com o token já invalidado (RN-38). Respostas, que atualizam `cliente_acesso.situacao`: `token_invalido` → estado "Acesso revogado"; `pasta_desativada` → "Desativada"; `pasta_encerrada` ou pasta inexistente → "Encerrada"; `em_encerramento` → mostra contagem (RN-38).
- **Após reconectar:** envia as alterações pendentes (13.16).

### 13.12 Navegar e operar arquivos
- **Perfil:** dono ou cliente com acesso.
- **Listar:** paginado; nunca registrado na auditoria.
- **Copiar para o computador:** o app escolhe o destino (diálogo ou soltura), recebe o fluxo pelo canal local e grava em `temp/` do usuário, renomeando ao final; aplica nome compatível com o SO de destino (RN-68) e a escolha de nome repetido (RN-63). Não gera auditoria (RN-42).
- **Enviar arquivos:** 13.13.
- **Nova subpasta, renomear, mover (dentro da mesma pasta), excluir:** o serviço valida caminho (seção 21.4), regra de nomes, somente leitura durante encerramento, arquivos em edição (não é permitido renomear, mover ou excluir um arquivo em edição por outra pessoa: "Este arquivo está em edição por nome@host.") e executa. Excluir move para a lixeira (13.17).
- **Auditoria:** `subpasta_criada`, `item_renomeado`, `item_movido`, `item_excluido`.

### 13.13 Enviar arquivos para a pasta
1. O usuário escolhe arquivos ou pastas (botão "Enviar arquivos…" ou arrastar e soltar).
2. O app monta a lista (com subpastas) e o tamanho total, e pede ao serviço a verificação prévia.
3. O servidor verifica: pasta não está em encerramento; nomes válidos (RN-68); espaço (`ocupado + reservado + novos − substituídos ≤ limite`, senão `pasta_cheia`); disco do servidor com espaço livre de pelo menos o total + 100 MiB de reserva (senão `disco_dono_cheio`, com notificação ao dono); lista de nomes já existentes.
4. Para nomes repetidos, o app pergunta "Substituir", "Manter os dois" ou "Pular" (com "Aplicar a todos").
5. Cada arquivo é enviado em fluxo para a área temporária `.drivelan/tmp/` do servidor, com reserva de espaço em memória enquanto durar o envio; o servidor confere o tamanho recebido continuamente e interrompe se exceder o limite ou o disco.
6. Ao concluir cada arquivo, o servidor move de `tmp/` para o destino de forma atômica, ajusta dono e permissões (seção 24.7), atualiza o contador de espaço e grava a auditoria. "Substituir" move a versão anterior para a lixeira da pasta.
7. Cancelamento ou falha: o arquivo incompleto em `tmp/` é apagado; os arquivos já concluídos permanecem.
8. Se o uso atingir 90% do limite, o dono é notificado (uma vez até o uso voltar abaixo de 90%).
- **Auditoria:** `arquivo_criado` (ou `arquivo_substituido`, que registra também a ida da versão anterior para a lixeira); `subpasta_criada` para pastas enviadas.

### 13.14 Abrir e editar um arquivo
1. O usuário pede "Abrir".
2. O serviço pede a trava ao servidor (`POST /v1/pastas/{uuid}/edicoes`). Se já existir trava de outra identidade: "em edição por joao@LAB-PC07" com opção de abrir somente leitura (13.15). Se a trava for da mesma identidade e instalação, é reaproveitada.
3. Com a trava: o app baixa o arquivo para `edicao/<pasta>/<id>/<nome>` no disco do usuário, o serviço grava a edição ativa (`cliente_edicao_ativa`) com trava e versão base, e o app abre o arquivo no programa padrão (`QDesktopServices.openUrl`).
4. A janela do DriveLan mostra a faixa "Arquivo em edição: <nome> — [Salvar edição]".
5. **Sinal de presença:** o app informa ao serviço a cada 60 segundos que a edição continua; o serviço repassa ao servidor (`edicao_sinal` no WebSocket), que atualiza `ultimo_sinal_em`.
6. **Envio automático:** o monitor (watchdog) detecta alterações no arquivo; após 2 segundos sem novas mudanças e com o arquivo legível, o app envia a nova versão com `If-Match: <versão base>` e o identificador da trava. Em sucesso, a versão base passa a ser a nova versão. Arquivos temporários do programa (`~$*`, `.~lock.*#`, `*.tmp`, `.goutputstream-*`) nunca são enviados.
7. **Fim da edição:** (a) botão "Salvar edição": envia a versão pendente, se houver, e libera a trava; (b) liberação automática quando o app detecta o fechamento: no Windows, quando o arquivo deixa de estar travado por outro processo (teste de abertura exclusiva) e, em qualquer sistema, quando o arquivo de trava do programa (`~$<nome>` ou `.~lock.<nome>#`) desaparece; (c) 10 minutos sem sinal (o servidor libera); (d) liberação manual pelo dono. Programas que não travam o arquivo nem criam arquivo de trava dependem do botão "Salvar edição" ou da falta de sinal.
8. Após o fim da edição, a edição ativa é removida e o arquivo local da pasta de edição é apagado (exceto quando houver alteração pendente ou rejeitada).
9. **Retomada após fechamento ou queda do app:** no login, o app pede ao serviço as edições ativas da conta para o usuário do SO atual. Para cada uma:
   - se o arquivo local não existir mais, a edição ativa é removida e a trava liberada;
   - o serviço consulta o servidor: se a trava ainda for da mesma identidade e instalação, a edição é retomada (monitor, sinal de presença e faixa "Arquivo em edição") e, se o arquivo local tiver sido alterado depois do último envio, a nova versão é enviada;
   - se a trava não existir mais (liberada por falta de sinal ou pelo dono) e o arquivo local tiver alterações não enviadas, ele é enviado sem trava com `If-Match` da versão base, sujeito à regra de conflito (RN-47); com o servidor offline, vira alteração pendente (fluxo 13.16);
   - se não houver alterações, o arquivo local é apagado e a edição ativa removida.
   A detecção de "alterado depois do último envio" compara a data de modificação e o tamanho do arquivo local com `local_mtime_envio` e `local_tamanho_envio` da edição ativa (nulos = nunca enviado; qualquer diferença em relação à versão baixada conta como alteração).
- **Conflito:** se a versão no servidor for diferente da versão base, o servidor grava a versão recebida como cópia de conflito (RN-47) e, numa única operação:
  1. libera a trava do arquivo original, se ela for de quem salvou;
  2. cria uma trava da mesma identidade e instalação na cópia de conflito;
  3. devolve o caminho da cópia, a nova trava e a versão da cópia.

  O serviço do cliente atualiza a edição ativa (`caminho_remoto`, `trava_uuid`, `versao_base`), a faixa passa a mostrar "Arquivo em edição: relatorio (conflito joao).docx — [Salvar edição]" e o usuário é notificado. O arquivo local continua o mesmo e os próximos salvamentos vão para a cópia de conflito. O arquivo original não é alterado e fica livre para os outros. Se o conflito vier de um envio sem trava (retomada ou alteração pendente), nenhuma trava é criada e a edição termina após o envio.
- **Durante encerramento:** o envio é recusado com "A pasta está em encerramento e aceita apenas cópias." O arquivo editado permanece na pasta de edição e o app mostra o caminho local para que o usuário não perca o trabalho.
- **Auditoria:** `arquivo_editado` (a cada envio aceito), `conflito_salvamento`, `edicao_liberada_automatica`, `edicao_liberada_manual`. Abrir e liberar normalmente pelo próprio editor não gera registro.

### 13.15 Abrir somente leitura
- Baixa o arquivo para `edicao/somente-leitura/<id>/`, marca o arquivo local como somente leitura e abre no programa padrão. Não cria trava, não monitora e não envia. Não gera auditoria.

### 13.16 Salvar com o servidor offline e envio posterior
1. Um envio automático falha por servidor offline.
2. O app move a cópia editada para `pendentes/` no disco do usuário e o serviço registra a alteração pendente (acesso, caminho, versão base, arquivo local, usuário do SO).
3. Mensagem: "Servidor offline. Sua alteração foi guardada neste computador."
4. Novos salvamentos do mesmo arquivo substituem a cópia pendente (permanece uma alteração por arquivo).
5. Quando o servidor volta e há sessão do mesmo usuário do SO com a conta logada, o app envia com `If-Match` da versão base. Versão diferente no servidor → conflito (RN-47).
6. Sucesso: remove o registro e a cópia local.
- **Auditoria (no servidor):** `alteracao_pendente_enviada` e, se houver, `conflito_salvamento`.

### 13.17 Excluir, restaurar e esvaziar a lixeira
- **Excluir:** o servidor move o item para `.drivelan/lixeira/<uuid>` (mesmo disco, operação atômica), grava `lixeira_item`, move os bytes de `bytes_conteudo` para `bytes_lixeira`. Auditoria `item_excluido`.
- **Restaurar (dono):** recria pastas intermediárias que não existam; se já houver item com o mesmo nome no local original, restaura como "nome (2)" (próximo número livre); devolve os bytes ao conteúdo. Auditoria `item_restaurado`.
- **Esvaziar (dono):** apaga definitivamente todos os itens `na_lixeira`. Auditoria `lixeira_esvaziada` (com quantidade e tamanho).
- **Expiração:** a tarefa diária apaga itens com mais de 30 dias. Auditoria `lixeira_item_expirado` (ator `sistema`).

### 13.18 Remover, bloquear e desbloquear usuário
- **Perfil:** dono.
- **Passos:** (1) escolhe usuário e "Remover…"; (2) escolhe "Apenas desconectar" ou "Remover e bloquear"; (3) o serviço marca o acesso como `removido` (motivo `desconectado` ou `bloqueado`), cria o bloqueio se for o caso, libera travas de edição dessa identidade, envia `acesso_revogado` e fecha as conexões.
- **Desbloquear:** marca o bloqueio como `desbloqueado`; o usuário precisa digitar o PIN para voltar.
- **Auditoria:** `usuario_desconectado`, `usuario_bloqueado`, `usuario_desbloqueado`.

### 13.19 Trocar PIN e alterar limite
- **Trocar PIN:** grava novo hash; acessos existentes não são afetados. Auditoria `pin_pasta_trocado`.
- **Alterar limite:** valida a faixa da RN-20: mínimo igual ao ocupado (ou 1 MB, se maior) e máximo igual a 80% de (espaço livre atual + ocupado pela pasta), nunca menor que o ocupado. Exemplo: pasta com 50 GB ocupados e disco com 40 GB livres → máximo de 72 GB (80% de 90 GB). Sem auditoria (não é evento listado na RN-41).

### 13.20 Desativar ou apagar pasta
1. O dono escolhe a ação; o serviço informa clientes conectados e com acesso. Para uma pasta já desativada, só existe "Apagar pasta" e ele é sempre imediato (sem prazo).
2. Escolhe "Encerrar imediatamente" ou prazo (5 min a 7 dias, padrão 1 h). Para apagar, digita o nome.
3. **Com prazo:** pasta → `em_encerramento`; grava `pasta_encerramento`; envia `encerramento_programado` com `termina_em` e segundos restantes; a pasta passa a aceitar apenas leitura e cópia; uploads em andamento são interrompidos e descartados. Auditoria `encerramento_programado`.
4. **No fim do prazo ou imediatamente:**
   - **Desativar:** pasta → `desativada`; envia `pasta_desativada`; fecha conexões; libera travas; acessos permanecem guardados para uma possível reativação. Auditoria `pasta_desativada`.
   - **Apagar:** pasta → `apagada`, `apagada_em = agora`, `lixeira_so_pendente = 1`; retirada do anúncio; envia `pasta_encerrada`; fecha conexões; acessos → `removido`. Os arquivos são enviados à Lixeira do sistema operacional **pelo app do usuário do SO que criou a pasta** (`so_dono`), assim que ele tiver o app em execução (não exige login na conta): o app pede ao serviço as pastas pendentes do seu usuário do SO e usa Send2Trash; ao concluir, o serviço zera `lixeira_so_pendente`. Até lá, os arquivos ficam intactos no local, fora da rede. Auditoria `pasta_apagada` e, depois, `pasta_enviada_lixeira_so` (ator `sistema`).
5. Clientes offline: ao reconectar dentro do prazo veem a contagem; depois do fim, recebem "pasta encerrada" ou "pasta desativada".

### 13.21 Cancelar ou alterar encerramento
- **Cancelar:** encerramento → `cancelado`; pasta → `ativa`; envia `encerramento_cancelado`. Auditoria `encerramento_cancelado`.
- **Alterar prazo:** novo prazo de 5 min a 7 dias contado a partir do momento da alteração; atualiza `termina_em`; envia `encerramento_alterado`. Os clientes conectados não recebem balão: a faixa de aviso e o chip passam a mostrar a nova contagem regressiva (RN-69). Auditoria `encerramento_alterado`.

### 13.22 Reativar pasta desativada
- **Perfil:** dono, com a pasta `desativada`.
- **Passos:** escolhe "Restaurar acessos anteriores" ou "Exigir PIN de todos novamente"; o serviço marca a pasta como `ativa` e `desativada_por_bloqueio = 0`; se exigir PIN, todos os acessos ativos → `removido` (motivo `pin_exigido_na_reativacao`); a lista de bloqueados é mantida; volta a anunciar.
- **Resultado:** com restauração, os clientes reconectam automaticamente; com PIN, veem "Acesso revogado" e podem entrar novamente com o PIN.
- **Auditoria:** `pasta_reativada` (com a opção escolhida).

### 13.23 Sair de uma pasta (cliente)
1. "Sair da pasta" → "Copiar para uma pasta…", "Sair sem copiar" ou "Cancelar".
2. Copiar: exige servidor online ("O servidor está offline. Não é possível copiar agora. Você pode sair sem copiar ou tentar mais tarde."); copia toda a árvore para o local escolhido, com nomes compatíveis (RN-68) e tratamento de nome repetido.
3. O serviço envia `POST /v1/pastas/{uuid}/sair` (se online), libera travas, apaga o acesso de cliente e as alterações pendentes dessa pasta (perguntando antes, se houver: "Há alterações guardadas neste computador que ainda não foram enviadas. Elas serão descartadas.").
- **Auditoria (no servidor):** `usuario_saiu`.

### 13.24 Liberação manual de arquivo em edição
- **Perfil:** dono. Remove a trava e envia `edicao_liberada` ao editor (o app dele encerra a edição local e, se houver salvamento posterior, ele é tratado como envio sem trava, sujeito à regra de conflito). Auditoria `edicao_liberada_manual`.

### 13.25 Acesso de administrador e resgate
1. Shift + F12 abre a janela da chave.
2. Se bloqueada: mostra o horário de liberação.
3. Chave correta: zera erros e ciclos; cria sessão de administrador; abre a janela de administração. Auditoria `admin_acesso`.
4. Chave errada: incrementa `erros_no_ciclo`; no 5º erro, bloqueia por `15 min × 2^(ciclos_bloqueio)`, incrementa `ciclos_bloqueio` e zera `erros_no_ciclo`. Auditoria `chave_admin_incorreta` em cada erro (sem o conteúdo digitado) e `chave_admin_bloqueio` no bloqueio.
5. Resgate: define PIN temporário → conta `ativa`, `pin_temporario = 1`, `erros_pin = 0`; pastas com `desativada_por_bloqueio = 1` → `ativa`; acessos de cliente `suspenso` → `ativo`. Auditoria `admin_pin_temporario` e `conta_reativada`, além de `pasta_reativada` para cada pasta.
6. Limpar logs: apaga os arquivos escolhidos. Auditoria `admin_logs_limpos` (com o escopo).

### 13.26 Instalação e reinstalação
- **Instalação:** instala programa, define a chave, gera certificado e identidade, registra o serviço e o início automático, cria regras de firewall.
- **Reinstalação com "Manter dados e trocar apenas a chave" (padrão):** mantém banco, certificado e logs; grava o hash da nova chave; zera `admin_controle`; executa migrations pendentes.
- **Reinstalação com "Apagar dados do DriveLan":** remove banco, certificado e logs; gera nova identidade. As pastas compartilhadas deixam de ser compartilhadas, mas seus arquivos permanecem no disco.
- **Desinstalação:** remove programa, serviço, início automático e regras de firewall; pergunta se os dados do DriveLan devem ser mantidos. Nunca apaga arquivos das pastas.

### 13.27 Trocar a placa de rede
- **Perfil:** usuário logado (a configuração vale para o computador inteiro).
- **Passos:** (1) em Configurações do app, escolhe "Automática (recomendado)" ou uma placa da lista; (2) o serviço valida que a placa existe e tem IPv4; (3) grava `rede.interface` no `drivelan.toml` de forma atômica; (4) retira o anúncio mDNS da placa anterior e anuncia na nova; (5) reinicia a descoberta por mDNS e broadcast na nova faixa; (6) envia ao app as novas informações de rede, e o dashboard é atualizado; (7) conexões de cliente abertas são refeitas pela reconexão automática.
- **Resultado:** "Placa de rede alterada."
- **Erros:** placa sem IPv4 ("Esta placa não tem endereço IPv4 no momento."); falha ao gravar a configuração (mensagem genérica com código de log).
- **Auditoria:** nenhuma (não é evento da RN-41).

### 13.28 Remover servidor manual
- **Perfil:** usuário logado. **Passos:** em Configurações do app, escolhe "Remover" no servidor; o serviço apaga o registro da conta e deixa de consultá-lo. Acessos de cliente às pastas desse servidor não são afetados e continuam reconectando pelo último endereço conhecido. **Auditoria:** nenhuma.

---

## 14. Validações e Regras de Negócio

### 14.1 Regras de negócio

**Contas**
- **RN-01:** Existe um único tipo de conta, que pode atuar como dona, cliente ou ambos.
- **RN-02:** A conta é local ao computador onde foi criada. Na rede, o usuário é identificado como `nome@host` (ex.: `joao@LAB-PC07`).
- **RN-03:** Cadastro com nome e PIN de 4 dígitos. Nome único por computador (sem diferenciar maiúsculas e minúsculas). Qualquer pessoa no computador pode criar conta.
- **RN-04:** Login exigido toda vez que a janela do app é aberta. Cada pessoa vê e gerencia apenas as próprias pastas e acessos.
- **RN-05:** O próprio usuário não recupera o PIN esquecido.
- **RN-06:** Após 5 erros seguidos de PIN no login, exibir "Conta bloqueada após 5 tentativas incorretas. Procure o Administrador do Aplicativo para redefinir seu PIN." e: desativar a conta (reversível), desativar as pastas da conta (reversível), preservar todos os arquivos, suspender os acessos como cliente e registrar tudo na auditoria.
- **RN-07:** Conta desativada só volta pelo resgate do administrador.
- **RN-08:** O nome pode ser alterado; a troca é auditada e os registros antigos continuam ligados à mesma pessoa, exibindo o nome atual seguido do anterior entre parênteses.
- **RN-09:** O usuário pode excluir a própria conta, confirmando com o PIN, somente depois de apagar todas as suas pastas. Os acessos como cliente são revogados e a exclusão é auditada. A identidade (`nome@host` e histórico de nomes) é preservada durante a retenção da auditoria.
- **RN-10:** No resgate, o administrador define um PIN temporário, que o usuário é obrigado a trocar no primeiro login.

**Rede e lista de pastas**
- **RN-11:** Usar automaticamente a placa de rede principal; permitir a troca nas configurações; ignorar placas VPN por padrão.
- **RN-12:** Cada pasta da lista mostra nome, `dono@host`, status (online, offline, em encerramento) e situação de acesso (tem acesso, bloqueado, precisa do PIN).

**Criação e configuração de pastas**
- **RN-13:** Criar um compartilhamento sempre cria uma pasta nova. Não é possível compartilhar pasta existente.
- **RN-14:** O local sugerido é uma pasta `DriveLan` no disco com mais espaço livre (ex.: `D:\DriveLan\<nome>`; no Linux, `~/DriveLan/<nome>` ou `<ponto de montagem>/DriveLan/<nome>` de outro disco fixo onde o usuário possa gravar).
- **RN-15:** Locais proibidos: raiz de qualquer disco; pastas do sistema operacional e de programas; a pasta inteira do perfil do usuário (subpastas são permitidas); dentro de outra pasta compartilhada do DriveLan (e uma pasta que contenha outra pasta compartilhada); unidades removíveis e unidades de rede.
- **RN-16:** O nome da pasta é único no computador (sem diferenciar maiúsculas e minúsculas).
- **RN-17:** O PIN da pasta tem 6 dígitos numéricos, é sugerido pelo app, editável pelo dono e não expira.
- **RN-18:** O dono troca o PIN a qualquer momento sem desconectar quem já tem acesso.

**Limite de tamanho**
- **RN-19:** Sugestão de limite: 10% do espaço livre do disco.
- **RN-20:** O limite nunca passa de 80% do **espaço disponível para a pasta** no momento em que é definido ou alterado. Espaço disponível para a pasta = espaço livre do disco + espaço já ocupado pela pasta (conteúdo + lixeira). Na criação, o ocupado é zero, então o máximo é 80% do espaço livre. Se o cálculo resultar num valor menor que o ocupado, o máximo passa a ser igual ao ocupado (seção 14.5).
- **RN-21:** Envio que ultrapasse o limite é recusado: "Pasta cheia. Contate o dono da pasta."
- **RN-22:** O dono é avisado ao atingir 90% do limite. Os itens da lixeira contam no limite.
- **RN-23:** O limite pode ser alterado a qualquer momento, mas não abaixo do espaço já ocupado.
- **RN-56:** Se o disco do dono encher antes do limite, o envio é recusado: "Sem espaço no computador do dono. Contate o dono da pasta." O dono é notificado; o limite não muda automaticamente.

**Acesso dos clientes**
- **RN-24:** Ao remover um usuário, o dono escolhe "Apenas desconectar" ou "Remover e bloquear".
- **RN-25:** Usuário bloqueado não entra nem com o PIN correto, até ser desbloqueado. Remoções e desbloqueios são auditados.
- **RN-26:** As pastas ficam ativas em segundo plano enquanto o computador estiver ligado, independentemente de quem esteja logado, e iniciam com o sistema.
- **RN-27:** Após 5 erros de PIN de uma pasta, o computador que tentou fica bloqueado por 15 minutos naquela pasta, com auditoria e notificação ao dono. O computador é identificado pelo identificador da instalação (verificado criptograficamente) e também pelo IP de origem; ambos ficam bloqueados.
- **RN-28:** O acesso do cliente é por tempo indeterminado, até remoção pelo dono, desativação ou exclusão da pasta.
- **RN-29:** O acesso é concedido ao usuário naquele computador (conta + instalação). Outra pessoa logada no mesmo computador precisa digitar o PIN.
- **RN-30:** Ao sair da pasta, o cliente pode copiar os arquivos antes; a cópia exige o servidor online.
- **RN-59:** Usuário apenas desconectado pode voltar a qualquer momento com o PIN atual. Para impedir, o dono usa "Remover e bloquear" ou troca o PIN.

**Lixeira**
- **RN-31:** Itens excluídos vão para a lixeira da pasta, no computador do dono.
- **RN-32:** Só o dono restaura ou esvazia a lixeira.
- **RN-33:** Itens ficam 30 dias e depois são apagados automaticamente. Exclusões, restaurações e esvaziamentos são auditados.

**Encerramento**
- **RN-34:** Duas ações: "Desativar compartilhamento" (reversível, arquivos ficam) e "Apagar pasta" (encerra e remove os arquivos para a Lixeira do SO).
- **RN-35:** A confirmação mostra quantos clientes estão conectados e quantos têm acesso.
- **RN-36:** Nas duas ações, encerrar imediatamente ou definir prazo.
- **RN-37:** Prazo de 5 minutos a 7 dias, padrão 1 hora. Durante o prazo, a pasta fica somente leitura (só cópia) e todos os conectados veem contagem regressiva sugerindo copiar os arquivos.
- **RN-38:** Quem estava offline vê o aviso ao reconectar dentro do prazo; depois do fim, é informado do encerramento.
- **RN-39:** Apagar envia os arquivos para a Lixeira do SO, com confirmação reforçada digitando o nome da pasta.
- **RN-40:** A pasta só existe para a rede com o computador do dono ligado; desligado, aparece offline e os clientes reconectam quando ela voltar.
- **RN-57:** Na reativação, "Restaurar acessos anteriores" (padrão) ou "Exigir PIN de todos novamente". A lista de bloqueados é mantida; a reativação é auditada.
- **RN-60:** Durante o prazo, o dono pode cancelar ou alterar o prazo. Ao cancelar, a pasta volta ao normal e os conectados recebem "Encerramento cancelado". Tudo é auditado.

**Auditoria**
- **RN-41:** Registrar, com data, horário e usuário (`nome@host`): criação, edição, renomeação, movimentação, exclusão e restauração de arquivos e pastas; entrada, saída e remoção de usuários; troca de PIN; bloqueios; conflitos ao salvar; reativação de pastas e cancelamento ou alteração de encerramentos; liberação automática ou manual de arquivos em edição; envio de alterações guardadas durante queda do servidor; tentativas erradas na chave de segurança (sem o que foi digitado); ações do administrador.
- **RN-42:** Leituras e downloads não são registrados.
- **RN-43:** O dono vê a auditoria das próprias pastas; o administrador vê a de todas as pastas do computador.
- **RN-44:** Registros mantidos por 12 meses.
- **RN-61:** Após apagar uma pasta, sua auditoria fica consultável por 1 mês, só pelo administrador; depois é removida.

**Edição**
- **RN-45:** O arquivo abre no programa padrão; ao salvar, as alterações são enviadas automaticamente; enquanto houver arquivo aberto, a janela mostra "arquivo em edição".
- **RN-46:** Ao abrir arquivo em edição por outra pessoa: "em edição por joao@LAB-PC07", com opção somente leitura.
- **RN-47:** Em conflito, as duas versões são mantidas (ex.: `relatorio (conflito joao).docx`; se já existir, `relatorio (conflito joao 2).docx`) e o conflito é auditado.
- **RN-65:** Com o servidor offline, ao salvar: "Servidor offline. Sua alteração foi guardada neste computador."; envio automático quando o servidor volta; se o arquivo foi alterado nesse intervalo, aplica RN-47; tudo auditado.
- **RN-66:** O aviso "em edição" termina ao fechar o arquivo; após 10 minutos sem sinal do computador de quem editava, o arquivo é liberado automaticamente; o dono pode liberar manualmente. Liberações automáticas e manuais são auditadas.

**Transferências**
- **RN-62:** Cópias com barra de progresso e cancelamento; arquivo incompleto descartado.
- **RN-63:** Nome repetido no destino: "Substituir", "Manter os dois" (ex.: `relatorio (2).docx`) ou "Pular", com "Aplicar a todos".
- **RN-64:** Arrastar e soltar entre o computador e a janela, nos dois sentidos.

**Administrador e chave de segurança**
- **RN-48:** Cada computador tem a sua chave, criada pelo TI na instalação, que é responsável por guardá-la.
- **RN-49:** A chave é guardada de forma irreversível e não pode ser vista nem alterada pelo app.
- **RN-50:** A janela de acesso abre com Shift + F12, fica em primeiro plano e simula um terminal.
- **RN-51:** A chave só é trocada reinstalando o app.
- **RN-52:** Ao reativar um usuário, as pastas desativadas pelo bloqueio e os acessos como cliente voltam automaticamente, com auditoria.
- **RN-53:** O administrador atua só no computador local, não abre conteúdo, não apaga pastas; toda ação é auditada.
- **RN-58:** Após 5 erros na janela da chave, bloqueio de 15 minutos; a cada novo ciclo de 5 erros, o bloqueio dobra (30 min, 1 h, 2 h…). Os ciclos voltam a zero após um acesso correto. Tentativas erradas auditadas sem o conteúdo.

**Logs**
- **RN-54:** Logs somente em arquivos, em subpastas por mês e ano, um arquivo por dia; ativados ou desativados pela configuração.
- **RN-55:** Limpeza manual exclusiva do administrador; exclusão automática após 3 meses (fixo).

**Regras técnicas de coerência**
- **RN-67 (confiança no primeiro uso):** no primeiro contato com um servidor, o cliente registra o identificador da instalação (impressão digital do certificado). Toda conexão posterior confere a impressão digital. Se um computador com o mesmo nome de host de um servidor conhecido, ou o mesmo endereço de um acesso existente, apresentar outra identidade, as pastas antigas desse servidor passam ao estado "Identidade alterada", nenhuma conexão é feita com a identidade antiga e o usuário vê: "A identidade de segurança do computador <host> mudou. Isso acontece quando o DriveLan é reinstalado sem manter os dados ou quando outro computador tenta se passar por ele. Por segurança, as pastas antigas desse computador foram bloqueadas. Se o DriveLan foi reinstalado nele, saia das pastas antigas e entre novamente com o PIN. Em caso de dúvida, procure o TI." O app não oferece "confiar mesmo assim".
- **RN-68 (regra única de nomes):** vale na criação, renomeação, envio e movimentação, em qualquer sistema:
  - recusar os caracteres `\ / : * ? " < > |` e caracteres de controle (códigos 0 a 31);
  - recusar nomes reservados `CON`, `PRN`, `AUX`, `NUL`, `COM1` a `COM9`, `LPT1` a `LPT9`, com ou sem extensão (ex.: `con.txt`), sem diferenciar maiúsculas e minúsculas;
  - recusar nomes terminados em ponto ou espaço, nomes vazios, `.` e `..`;
  - recusar o nome `.drivelan` na raiz da pasta (área interna);
  - limite de 255 caracteres por nome e 1.024 caracteres no caminho relativo;
  - nomes normalizados em Unicode NFC; nomes que diferem só por maiúsculas e minúsculas são iguais dentro da mesma subpasta.
  - **Itens já existentes fora da regra** (colocados direto no disco do dono): continuam intactos no disco e aparecem na lista com ícone de alerta e a dica "Nome incompatível com Windows". Podem ser copiados (com nome adaptado no destino), abertos somente leitura, renomeados para um nome válido e excluídos (vão para a lixeira com o nome original preservado). Não podem ser editados nem movidos enquanto não forem renomeados. Quando dois itens existentes diferem só por maiúsculas e minúsculas, ambos aparecem com o alerta e seguem a mesma restrição.
  - **Nome adaptado na cópia para o computador:** cada caractere proibido vira `_`; nomes reservados recebem `_` no início; pontos e espaços finais são removidos; se o resultado colidir com outro item no destino (inclusive por maiúsculas e minúsculas no Windows), aplica-se a escolha de nome repetido da RN-63. O arquivo original nunca é alterado.
- **RN-69 (notificações):** apenas os eventos da tabela da seção 12.14 geram notificação, entregues somente a sessões ativas da conta envolvida.

### 14.2 Validações por campo

| Campo | Regras | Mensagem de erro |
|---|---|---|
| Nome de usuário | Obrigatório; 3 a 32 caracteres; letras (inclusive acentuadas), números, `.`, `-` e `_`; sem espaços e sem `@`; único (normalizado) | "Use de 3 a 32 caracteres: letras, números, ponto, hífen ou sublinhado." / "Este nome já está em uso neste computador." |
| PIN da conta e PIN temporário | Exatamente 4 dígitos `0-9` | "O PIN deve ter exatamente 4 números." |
| Confirmação de PIN | Igual ao PIN | "Os PINs não conferem." |
| Nome da pasta | Obrigatório; 1 a 64 caracteres; RN-68; único no computador | "Nome inválido: <motivo>." / "Já existe uma pasta compartilhada com esse nome neste computador." |
| Local da pasta | RN-13, RN-15; gravável pelo usuário do SO; disco local fixo | "Este local não pode ser usado: <motivo>." |
| PIN da pasta | Exatamente 6 dígitos `0-9` | "O PIN da pasta deve ter exatamente 6 números." |
| Limite | Número positivo; mínimo 1 MB ou o ocupado, o que for maior; no máximo 80% de (espaço livre + ocupado pela pasta), nunca menor que o ocupado (RN-20) | "O limite deve ficar entre X e Y." |
| Prazo de encerramento | 5 minutos a 7 dias | "Escolha um prazo entre 5 minutos e 7 dias." |
| Confirmação de exclusão da pasta | Igual ao nome da pasta | Botão desativado enquanto diferente |
| Endereço do servidor manual | IPv4 válido ou nome de computador (letras, números, `-` e `.`, até 253 caracteres) | "Informe um IP ou nome de computador válido." |
| Porta | Inteiro 1 a 65535 | "Informe uma porta entre 1 e 65535." |
| Nome de arquivo ou subpasta | RN-68 | "Nome inválido: <motivo>." |
| Chave de segurança (instalador) | 12 a 128 caracteres, digitada duas vezes | "A chave deve ter de 12 a 128 caracteres." / "As chaves não conferem." |

### 14.3 Regras de situação

| Entidade | Transições permitidas |
|---|---|
| Conta | `ativa` → `desativada` (5 erros); `desativada` → `ativa` (resgate); `ativa` → `excluida` (pelo titular, sem pastas). `excluida` é final. |
| Pasta | `ativa` ↔ `em_encerramento` (programar ou cancelar); `em_encerramento` → `desativada` ou `apagada` (fim do prazo); `ativa` → `desativada` ou `apagada` (imediato ou bloqueio da conta); `desativada` → `ativa` (reativar) ou `apagada` (apagar, sempre imediato, pois a pasta desativada já não tem clientes conectados). `apagada` é final. |
| Acesso | `ativo` → `removido`. Novo acesso = nova linha. |
| Item da lixeira | `na_lixeira` → `restaurado`, `esvaziado` ou `expirado`. |
| Encerramento | `programado` → `concluido` ou `cancelado`. |

### 14.4 Situações especiais

- **Relógio:** prazos e retenções usam o relógio do computador que hospeda a pasta. A contagem regressiva no cliente usa os segundos restantes informados pelo servidor, e não o relógio do cliente.
- **Computador hospedeiro desligado durante o prazo:** ao religar, encerramentos vencidos são executados imediatamente.
- **Edição durante desativação ou remoção:** a trava é liberada; envios posteriores são recusados e o arquivo local permanece na pasta de edição, com aviso ao usuário mostrando o caminho.
- **Arquivo alterado direto no disco do dono:** passa a ter nova versão; um envio com versão base antiga gera conflito.
- **Links simbólicos e junções dentro da pasta:** não são exibidos nem seguidos (seção 21.4).
- **Várias sessões da mesma conta:** uma conta só pode ter uma sessão ativa no computador. Um novo login na mesma conta encerra a sessão anterior, que recebe o aviso "Sua conta foi aberta em outra sessão deste computador."

### 14.5 Interpretações adotadas para as regras

As regras abaixo foram aplicadas com a leitura indicada. Cada uma é uma decisão aprovada e não deve ser reinterpretada na implementação.

| Regra | Leitura adotada | Justificativa e efeitos |
|---|---|---|
| RN-06 (revogar acessos como cliente) | Os acessos de cliente da conta bloqueada são **suspensos localmente** (`cliente_acesso.situacao = 'suspenso'`), e não revogados nos servidores | A RN-52 exige que os acessos voltem automaticamente no resgate, o que uma revogação no servidor impediria. Efeito: o dono remoto continua vendo o usuário na lista de usuários, com "Último acesso em", e pode removê-lo normalmente. A suspensão é registrada nos detalhes de `conta_bloqueada` no computador local; os servidores não são avisados e não registram nada |
| RN-20 (máximo de 80% do espaço livre) | O máximo é 80% de (espaço livre + espaço já ocupado pela pasta), nunca menor que o ocupado | Sem isso, uma pasta grande num disco quase cheio teria uma faixa vazia e o dono ficaria impedido de alterar o limite. Na criação, o resultado é igual a 80% do espaço livre |
| RN-36 (imediato ou com prazo nas duas ações) | Apagar uma pasta já desativada é sempre imediato | A pasta desativada não tem clientes conectados, então o prazo não teria efeito |
| RN-37 (somente leitura durante o prazo) | Novos clientes podem entrar durante o prazo, em somente leitura, vendo a contagem regressiva | Permite copiar o material antes do encerramento |
| RN-04 (login sempre que a janela é aberta) | Fechar a janela mantém a sessão em segundo plano; reabrir exige o PIN (seção 15.3) | Mantém transferências, edições e notificações sem abrir mão do PIN |
| RN-39 (arquivos para a Lixeira do SO) | O envio é feito pelo app do usuário do SO que criou a pasta, assim que ele estiver em execução (fluxo 13.20) | A Lixeira do SO pertence ao usuário do SO, e o serviço roda como sistema |
| RN-53 (toda ação do administrador auditada) | Consultas de logs e de auditoria ficam cobertas por `admin_acesso`; ações que alteram dados têm código próprio | Evita registrar leituras, coerente com a RN-42 |
| RN-60 e seção de notificações | A alteração do prazo não gera notificação; atualiza apenas a contagem na faixa de aviso e no chip | Mantém a lista fechada de notificações (RN-69) |
| Notificações | Só são entregues a sessões ativas e não ficam acumuladas | Decisão aprovada (seção 12.14) |
| Sessões | Uma conta tem no máximo uma sessão ativa no computador (seção 14.4) | Decisão aprovada |

---

## 15. Autenticação e Sessão

### 15.1 Tipos de autenticação

| Credencial | Formato | Onde é verificada | Armazenamento |
|---|---|---|---|
| PIN da conta | 4 dígitos | Serviço local | Hash Argon2id em `conta.pin_hash` |
| PIN da pasta | 6 dígitos | Serviço que hospeda a pasta | Hash Argon2id em `pasta.pin_hash` |
| Token de acesso à pasta | 32 bytes aleatórios (base64url) | Serviço que hospeda a pasta | Servidor: SHA-256 em `acesso.token_hash`; cliente: em `cliente_acesso.token`, legível só pelo serviço |
| Chave de segurança | 12 a 128 caracteres | Serviço local | Hash Argon2id em `instalacao.chave_admin_hash` |
| Sessão local | 32 bytes aleatórios | Serviço local | Somente em memória (serviço e app) |
| Sessão de transporte | Identificador aleatório | Serviço que hospeda a pasta | Somente em memória |

Parâmetros Argon2id: memória 64 MiB, 3 iterações, paralelismo 1, sal aleatório de 16 bytes (formato codificado padrão da biblioteca). Como os PINs são curtos, a proteção real depende de três fatores combinados: banco legível somente pelo serviço, bloqueios por tentativas e o custo do Argon2id. O cálculo do hash roda fora do laço principal (pool de threads).

### 15.2 Login e logout

- **Login:** fluxo 13.2. A comparação usa a verificação do Argon2id; o tempo de resposta para nome inexistente deve ser semelhante ao de PIN errado (calcular um hash fictício).
- **Logout ("Sair da conta"):** encerra a sessão local, fecha os WebSockets de cliente da conta, libera travas de edição enviando a versão pendente quando possível (se o servidor estiver offline, guarda como alteração pendente), e volta à tela de login.
- **Sair do DriveLan (bandeja):** faz logout e fecha o app. O serviço continua rodando.

### 15.3 Ciclo de vida da sessão

- A sessão começa no login e termina com: "Sair da conta", "Sair do DriveLan", "Entrar com outra conta", novo login da mesma conta em outra sessão do SO, encerramento da sessão do sistema operacional, bloqueio da conta ou exclusão da conta.
- **Fechar a janela não encerra a sessão:** a janela é ocultada e o app continua na bandeja, mantendo conexões, transferências, edições, envio de alterações pendentes e notificações.
- **Reabrir a janela exige o PIN** (tela de desbloqueio, seção 12.4), atendendo à exigência de login sempre que a janela é aberta.
- Não há expiração por tempo de inatividade na v1.
- Reinício do computador: o app inicia na sessão do SO sem conta logada; ao abrir a janela, pede login, e então reconecta as pastas.

### 15.4 Recuperação de acesso

Não existe recuperação pelo próprio usuário. O caminho é o resgate pelo administrador (fluxo 13.25), que define PIN temporário de troca obrigatória.

### 15.5 Canal local e proteção das rotas

- O serviço identifica o **usuário do sistema operacional** de cada conexão no canal local: no Linux, pelas credenciais do socket (`SO_PEERCRED`, UID); no Windows, pelo processo cliente do named pipe (`GetNamedPipeClientProcessId` e token do processo, SID). O named pipe recusa clientes remotos (`PIPE_REJECT_REMOTE_CLIENTS`).
- O login devolve um **token de sessão local** vinculado à conta, ao usuário do SO e ao **processo do app** que fez o login (PID e horário de criação do processo, para evitar reaproveitamento de PID). A sessão **não** fica presa a uma conexão: o app pode abrir e fechar quantas conexões precisar (pool de conexões, transferências, cancelamentos).
- Em cada conexão nova, o serviço identifica o usuário do SO e o PID do processo cliente (Linux: `SO_PEERCRED`, que traz UID e PID; Windows: `GetNamedPipeClientProcessId` e token do processo). A cada pedido, confere que o token pertence a esse mesmo usuário do SO e processo.
- Toda rota (exceto cadastro, login, informações públicas da tela de login e janela da chave) exige o token no cabeçalho `X-DriveLan-Sessao`. Um token apresentado por outro usuário do SO ou por outro processo é recusado e registrado no log de erros como acesso inválido.
- Além dos casos da seção 15.3, a sessão local termina quando o processo do app termina ou quando o WebSocket de eventos local desse processo fica fechado por mais de 60 segundos. Fechar uma conexão HTTP, por exemplo para cancelar uma transferência (seção 23.8), nunca encerra a sessão.
- Rotas de administrador exigem o **token de sessão de administrador**, obtido com a chave e vinculado da mesma forma ao usuário do SO e ao processo que o obteve. Ele termina ao fechar a janela de administração ou quando o processo termina.
- Rotas que tocam o disco do usuário (alterações pendentes, envio à Lixeira do SO) só aceitam registros cujo `so_usuario` ou `so_dono` seja o usuário do SO da conexão.
- O app guarda tokens apenas em memória.

#### 15.5.1 Servidor do named pipe no Windows

O suporte a named pipe do `asyncio`, usado pelo `NamedPipeSite` do aiohttp, cria o pipe com flags e descritor de segurança fixos: não permite rejeitar clientes remotos nem conceder escrita a usuários comuns. Por isso o serviço implementa o próprio servidor do pipe em `src/drivelan/servico/plataforma/windows_pipe.py`:

- cada instância é criada com `win32pipe.CreateNamedPipe`, com `PIPE_ACCESS_DUPLEX | FILE_FLAG_OVERLAPPED` e `PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS`, instâncias ilimitadas e sempre uma instância aguardando conexão;
- o descritor de segurança é explícito, em SDDL: `D:P(D;;GA;;;NU)(A;;GA;;;SY)(A;;GA;;;BA)(A;;GRGW;;;IU)` (nega usuários de rede; controle total para SYSTEM e administradores; leitura e escrita para usuários interativos);
- ao conectar, o serviço obtém o PID (`GetNamedPipeClientProcessId`), abre o processo e lê o SID do token antes de aceitar qualquer pedido;
- cada instância conectada é entregue ao laço `asyncio` como um transporte próprio (leitura e escrita sobrepostas com eventos do Windows ou, como alternativa, uma ponte com uma thread por conexão) e atendida pelo servidor HTTP de baixo nível do aiohttp (`aiohttp.web.Server`), que não depende de socket;
- no app, o cliente usa `aiohttp.NamedPipeConnector`.

**Critério de saída da etapa 5, obrigatório antes da etapa 6:** num Windows 11 com o serviço rodando como LocalSystem, o app de um usuário comum faz pedidos HTTP e abre o WebSocket pelo pipe; o serviço identifica o SID e o PID corretos; um cliente de outro computador é recusado; um usuário de rede não consegue abrir o pipe. Se o critério não for atingido, a implementação para e este FSD é revisado. Não é permitido substituir o pipe por TCP local sem essa revisão.

### 15.6 Chave de segurança

- Definida apenas pelo instalador, por meio de `drivelan-service --definir-chave`, que exige privilégios de administrador do SO e lê a chave pela entrada padrão (nunca por argumento de linha de comando, que aparece na lista de processos).
- Nunca é exibida, registrada em log, gravada em texto ou enviada pela rede.
- Não existe rota no canal local para alterá-la.

### 15.7 Usuário sem permissão

- Rotas do canal local sem sessão válida: `401 sessao_invalida`; o app volta à tela de login com "Sua sessão terminou. Entre novamente."
- Ações sem permissão: `403 acesso_negado`; o app mostra "Você não tem permissão para esta ação." (situação que só ocorre com chamadas forjadas, pois a interface esconde ações não permitidas).

---

## 16. Controle de Acesso

### 16.1 Papéis

Papéis fixos e contextuais: **usuário**, **dono** (da pasta), **cliente** (da pasta) e **administrador do sistema**. A matriz completa está na seção 8.5.

### 16.2 Verificações no serviço (backend)

Toda rota executa, na camada `regras/`, as verificações abaixo antes de qualquer efeito:

| Tipo de rota | Verificações |
|---|---|
| Gestão de pasta (canal local) | Sessão local válida; conta ativa; `pasta.conta_dono_id` = conta da sessão; situação da pasta compatível com a ação |
| Conteúdo da própria pasta (canal local) | As mesmas do dono, mais as regras de conteúdo |
| Conteúdo de pasta remota (canal local → rede) | Sessão local válida; acesso de cliente da conta em situação `ativo` |
| Rotas de rede de conteúdo | Sessão de transporte válida (identidade da instalação verificada); token válido para aquela pasta, conta e instalação; acesso `ativo`; pasta `ativa` (ou `em_encerramento` para leitura); identidade não bloqueada; caminho validado |
| Rotas de administrador | Sessão de administrador válida; nenhuma rota de administrador toca conteúdo de pastas |

### 16.3 Menus por perfil

- Usuário sem pastas: Início, Pastas da rede, Transferências, Configurações.
- Dono: adiciona o ícone de configurações nos cartões de "Minhas pastas" e no navegador da pasta.
- Cliente: navegador da pasta sem configurações, com "Sair da pasta"; ações de alteração desativadas durante encerramento.
- Administrador: apenas a janela de administração; não há menus de administrador na janela principal.

### 16.4 Mensagens de acesso negado

| Situação | Mensagem |
|---|---|
| Usuário bloqueado pelo dono | "Você foi bloqueado pelo dono desta pasta." |
| Computador em bloqueio temporário | "Muitas tentativas incorretas. Este computador poderá tentar novamente às HH:MM." |
| Token revogado | "Seu acesso a esta pasta foi revogado." |
| Pasta em encerramento (alteração) | "A pasta está em encerramento e aceita apenas cópias." |
| Pasta desativada | "Esta pasta está desativada no momento." |
| Ação de dono por não dono | "Você não tem permissão para esta ação." |

---

## 17. Auditoria e Histórico

### 17.1 Onde e como é registrada

- No computador que hospeda a pasta, para todos os eventos de pasta e conteúdo, com o relógio desse computador.
- No computador local, para eventos de conta e de administrador.
- Somente inclusão: nenhum registro é editado. Exclusão apenas pela retenção.
- O usuário é exibido como `nome_atual@host`, seguido de `(nome_anterior)` quando houver troca de nome (ex.: `joao.silva@LAB-PC07 (joao)`).

### 17.2 Ações auditadas

| Código | Rótulo exibido | Ator |
|---|---|---|
| `pasta_criada` | Pasta criada | usuário |
| `arquivo_criado` | Arquivo criado | usuário |
| `arquivo_substituido` | Arquivo substituído | usuário |
| `subpasta_criada` | Pasta criada dentro da pasta | usuário |
| `arquivo_editado` | Arquivo editado | usuário |
| `item_renomeado` | Renomeado | usuário |
| `item_movido` | Movido | usuário |
| `item_excluido` | Excluído (enviado à lixeira) | usuário |
| `item_restaurado` | Restaurado da lixeira | usuário (dono) |
| `lixeira_esvaziada` | Lixeira esvaziada | usuário (dono) |
| `lixeira_item_expirado` | Removido da lixeira após 30 dias | sistema |
| `usuario_entrou` | Usuário entrou | usuário |
| `usuario_saiu` | Usuário saiu | usuário |
| `usuario_desconectado` | Usuário desconectado pelo dono | usuário (dono) |
| `usuario_bloqueado` | Usuário removido e bloqueado | usuário (dono) |
| `usuario_desbloqueado` | Usuário desbloqueado | usuário (dono) |
| `pin_pasta_trocado` | PIN da pasta trocado | usuário (dono) |
| `pin_pasta_bloqueio_temporario` | Computador bloqueado por 15 minutos após 5 PINs incorretos | computador |
| `conflito_salvamento` | Conflito ao salvar (cópia de conflito criada) | usuário |
| `edicao_liberada_automatica` | Arquivo liberado automaticamente (sem sinal por 10 minutos) | sistema |
| `edicao_liberada_manual` | Arquivo liberado manualmente pelo dono | usuário (dono) |
| `alteracao_pendente_enviada` | Alteração guardada durante queda do servidor enviada | usuário |
| `encerramento_programado` | Encerramento programado | usuário (dono) |
| `encerramento_alterado` | Prazo de encerramento alterado | usuário (dono) |
| `encerramento_cancelado` | Encerramento cancelado | usuário (dono) ou sistema |
| `pasta_desativada` | Compartilhamento desativado | usuário (dono) ou sistema |
| `pasta_reativada` | Compartilhamento reativado | usuário (dono) ou administrador |
| `pasta_apagada` | Pasta apagada | usuário (dono) ou sistema |
| `pasta_enviada_lixeira_so` | Arquivos enviados à Lixeira do sistema | sistema |
| `conta_bloqueada` | Conta bloqueada após 5 PINs incorretos | sistema |
| `conta_pin_trocado` | PIN da conta trocado | usuário |
| `conta_nome_alterado` / `identidade_nome_alterado` | Nome de usuário alterado | usuário |
| `conta_excluida` | Conta excluída | usuário |
| `conta_reativada` | Conta reativada | administrador |
| `chave_admin_incorreta` | Chave de segurança incorreta | administrador (tentativa) |
| `chave_admin_bloqueio` | Janela de administrador bloqueada | sistema |
| `admin_acesso` | Acesso de administrador | administrador |
| `admin_pin_temporario` | PIN temporário definido | administrador |
| `admin_logs_limpos` | Logs de erros limpos | administrador |

Leituras, listagens, downloads e cópias para o computador **não** são auditados. PINs, tokens e o conteúdo digitado na chave **nunca** aparecem em nenhum campo.

As consultas do administrador (logs de erros e auditoria) não geram registro próprio: a sessão de administrador inteira é registrada por `admin_acesso`, e as ações que alteram dados (`admin_pin_temporario`, `admin_logs_limpos`) têm código próprio (seção 14.5).

### 17.3 Campos mínimos

Data e horário, pasta (nome no momento do evento), ator (`nome@host`, "Administrador do sistema", "Sistema" ou computador com host e instalação abreviada), ação, item afetado e destino, detalhes relevantes (ex.: prazo escolhido, opção de reativação, quantidade de itens esvaziados).

### 17.4 Quem visualiza

- **Dono:** aba Auditoria das configurações de cada pasta própria que não esteja apagada.
- **Administrador:** aba Auditoria das pastas, com todas as pastas do computador (incluindo apagadas há até 1 mês) e os eventos de conta e de administração (sem pasta).
- Clientes não veem auditoria.

### 17.5 Retenção

- Tarefa diária remove registros com mais de 12 meses.
- Para pastas com `situacao = 'apagada'` e `apagada_em` há mais de 1 mês: remove os registros da pasta e a linha da pasta (cascata), mantendo identidades ainda referenciadas por outros registros. Uma identidade só pode ser removida quando nenhuma tabela a referenciar (`conta`, `auditoria`, `acesso`, `bloqueio_dono`, `lixeira_item`, `arquivo_em_edicao` e `identidade_nome_historico`); a tarefa diária verifica isso para identidades de contas excluídas e de usuários remotos.

---

## 18. Soft Delete e Exclusões

| Entidade | Como é excluída | Quem exclui | Quem restaura | Exclusão definitiva |
|---|---|---|---|---|
| Arquivo ou subpasta | Lixeira da pasta (`.drivelan/lixeira/`), 30 dias | Dono e clientes | Só o dono | Esvaziar (dono) ou expiração de 30 dias |
| Pasta compartilhada | **Desativar** (reversível) ou **apagar** (arquivos na Lixeira do SO; registro mantido 1 mês para auditoria) | Dono; desativação automática pelo bloqueio da conta | Desativada: dono reativa (ou resgate do administrador, se foi pelo bloqueio). Apagada: só pela Lixeira do SO, fora do DriveLan | Remoção do registro após 1 mês |
| Conta | **Desativada** (bloqueio) ou **excluída** (identidade preservada) | Sistema (bloqueio) e titular (exclusão) | Administrador (desativada) | Excluída é final; identidade some quando não houver mais auditoria que a referencie |
| Acesso | `removido` | Dono, o próprio cliente, regras | Novo acesso com PIN; reativação com restauração mantém os acessos ativos | — |
| Bloqueio pelo dono | `desbloqueado` | Dono | — | — |

Regras de exibição:

- Listas comuns mostram apenas registros ativos: pastas `apagada` não aparecem em lugar algum para usuários; contas `excluida` não aparecem no resgate.
- Pastas desativadas aparecem em "Minhas pastas" com o chip "Desativada" e a ação "Reativar compartilhamento".
- Itens da lixeira aparecem só na aba Lixeira, com dias restantes.

Cuidados contra exclusão indevida: confirmação em toda exclusão; confirmação reforçada (digitar o nome) para apagar pasta; esvaziar lixeira com confirmação explícita; a área `.drivelan/` nunca é exibida nem aceita operações pelo protocolo; o instalador nunca apaga arquivos das pastas.

---

## 19. Logs

### 19.1 Log de erros

#### 19.1.1 O que é registrado
- Exceções não tratadas no serviço e no app (com rastreamento da pilha).
- Falhas de rede relevantes: porta ocupada, falha de anúncio mDNS, falha de TLS, conexão recusada repetidamente.
- Falhas de disco: sem permissão, disco cheio, caminho inválido, falha ao mover para a lixeira.
- Falhas de banco: erro de migration, banco bloqueado, corrupção detectada.
- Falhas de configuração: arquivo ilegível ou valor inválido (com o valor padrão adotado).
- Tentativas de uso do canal local com sessão de outro usuário do SO e pedidos malformados na rede.
- Falhas de tarefas periódicas.

Não são registrados: eventos normais de uso (esses vão para a auditoria), PINs, tokens, chave, conteúdo de arquivos.

#### 19.1.2 Formato e local
- Pasta: `<logs>/AAAA-MM/AAAA-MM-DD.log` (ex.: `/var/log/drivelan/2026-11/2026-11-12.log`).
- Uma linha por evento, em texto UTF-8: `2026-11-12T10:15:03.120-03:00 | ERRO | servico.rede.anuncio_mdns | mensagem | contexto=valores`, seguida do rastreamento da pilha indentado, quando houver.
- Níveis: `ERRO` e `CRITICO`. `AVISO` só para valores de configuração inválidos.
- Erros do app são enviados ao serviço pelo canal local (rota `app/erros`) e gravados com a origem `app` e o usuário do SO.

#### 19.1.3 Ligar e desligar
Controlado por `log.ativo` no arquivo de configuração (padrão: `true`). Lido na inicialização do serviço e quando o arquivo é alterado (verificação a cada 60 segundos pela data de modificação). Desligado, nada é gravado.

#### 19.1.4 Mensagens seguras ao usuário
O usuário nunca vê rastreamento da pilha, caminhos internos ou mensagens técnicas. Mensagem genérica: "Não foi possível concluir a ação. Tente novamente. Se o problema continuar, procure o TI." Cada erro inesperado recebe um código curto (8 caracteres) exibido na mensagem ("Código: 7F3A91C2") e gravado no log, para o TI localizar o registro.

#### 19.1.5 Contingência quando a gravação do log falha
- Se a gravação em arquivo falhar (disco cheio, sem permissão, pasta removida), o serviço **não para** e não trava: guarda os últimos 500 eventos num buffer em memória, escreve na saída de erro padrão (capturada pelo journald no Linux) e tenta gravar de novo a cada 60 segundos, despejando o buffer quando conseguir.
- A aba Logs de erros mostra o aviso "Houve falha ao gravar o log em arquivo desde HH:MM. Os registros mais recentes estão sendo mantidos temporariamente na memória." e permite ver o buffer.
- Se o app não conseguir falar com o serviço, grava o erro em `log-contingencia/AAAA-MM-DD.log` na pasta de dados do usuário e envia esses registros ao serviço quando o canal voltar, apagando o arquivo em seguida.
- Falhas antes da inicialização completa do serviço (ex.: configuração ilegível) são gravadas assim que o módulo de log estiver ativo, que é sempre a primeira etapa da inicialização.

#### 19.1.6 Consulta, limpeza e retenção
- Visível somente na janela de administração (seção 12.16). A leitura dos arquivos é feita em partes, numa tarefa separada, para não travar a interface.
- Limpeza manual: dia, mês ou todos, pelo administrador, auditada.
- Retenção automática: a tarefa diária apaga arquivos com data anterior a 3 meses e remove subpastas de mês vazias.

#### 19.1.7 Proteção
Pasta de logs acessível apenas ao serviço e aos administradores do SO (seção 5.6). Os logs nunca são servidos pela rede.

### 19.2 Log de segurança

Não há log de segurança separado. Os eventos de segurança são registrados na auditoria (seção 17.2): erros de PIN de conta com bloqueio, bloqueio temporário de computador numa pasta, tentativas erradas e bloqueios da chave de segurança, remoções, bloqueios e desbloqueios, trocas de PIN, ações do administrador e reativação de contas. Uso indevido do canal local e pedidos malformados vão para o log de erros (seção 19.1.1).

---

## 20. Configurações Globais

### 20.1 Configurações funcionais

Não há configurações globais editáveis por usuários além da escolha da placa de rede. Valores fixos do produto (não configuráveis): limites de PIN, 5 tentativas, 15 minutos de bloqueio, 30 dias de lixeira, 12 meses de auditoria, 1 mês para pastas apagadas, 3 meses de logs, 10 minutos sem sinal, prazos de 5 minutos a 7 dias, 10% e 80% do limite, aviso de 90%.

### 20.2 Arquivo de configuração técnica

- **Formato:** TOML, em `C:\ProgramData\DriveLan\config\drivelan.toml` (Windows) ou `/etc/drivelan/drivelan.toml` (Linux).
- **Não é usado arquivo `.env`.** O arquivo não contém credenciais nem segredos; PINs, chave, tokens e chave privada ficam no banco e na pasta de dados protegidos.
- **Conteúdo e padrões:**

```toml
[log]
ativo = true          # liga ou desliga o log de erros

[rede]
interface = ""        # vazio = placa principal automática; ou o nome da placa
porta = 47820         # porta TCP (protocolo) e UDP (descoberta por broadcast)
```

| Chave | Padrão | Quem altera | Impacto | Validação | Fallback |
|---|---|---|---|---|---|
| `log.ativo` | `true` | Administrador do SO, editando o arquivo | Liga ou desliga a gravação de logs | Booleano | `true` |
| `rede.interface` | `""` | Qualquer usuário logado, pela tela Configurações do app (o serviço grava) | Placa usada para anúncio, descoberta e identificação da rede | Nome de placa existente | Automática, com aviso no log se a placa não existir |
| `rede.porta` | `47820` | Administrador do SO, editando o arquivo | Porta de todas as conexões e da descoberta UDP | Inteiro 1024 a 65535 | `47820` |

- **Leitura:** somente pelo serviço, com `tomllib`. **Gravação:** somente pelo serviço, com `tomli-w`, de forma atômica (arquivo temporário e substituição), preservando as demais chaves.
- A porta é anunciada no mDNS e nas respostas de broadcast, então clientes com outra porta configurada continuam encontrando o servidor por descoberta. A adição manual usa a porta informada.
- Arquivo ausente: o serviço cria com os padrões. Arquivo ilegível: usa os padrões, registra `AVISO` no log e não sobrescreve o arquivo.

---

## 21. Uploads, Anexos e Arquivos

Não existe upload no sentido de sistema web nem anexos. A **transferência de arquivos entre computadores** é a função central do DriveLan e segue as regras abaixo.

### 21.1 Onde os arquivos são usados

Conteúdo das pastas compartilhadas, cópias para o computador do cliente, pasta de edição, alterações pendentes e área interna da pasta (lixeira e temporários).

### 21.2 Tipos e tamanhos

- Qualquer tipo de arquivo é aceito; o DriveLan não abre nem interpreta o conteúdo.
- Não há tamanho máximo por arquivo além do limite da pasta e do espaço livre do disco.
- Arquivos são abertos apenas pelo programa padrão do computador, a pedido explícito do usuário. O app nunca executa nem abre arquivos por conta própria.

### 21.3 Área interna da pasta compartilhada

Cada pasta tem, na raiz, a pasta oculta `.drivelan/` (atributo oculto no Windows), no mesmo disco, com:

- `lixeira/<uuid>`: itens excluídos (arquivo ou pasta inteira), renomeados para o UUID do item. O nome e o caminho original ficam no banco;
- `tmp/`: arquivos sendo recebidos. Na inicialização do serviço, todo conteúdo de `tmp/` é apagado (são envios interrompidos).

A área `.drivelan/` nunca aparece na listagem do protocolo, não aceita nenhuma operação dos clientes e é contada no espaço ocupado apenas pela lixeira (`bytes_lixeira`).

### 21.4 Validação de caminhos no servidor

Todo caminho recebido do protocolo:

1. É texto relativo à raiz da pasta, com `/` como separador; não pode começar com `/`, conter `\`, letra de unidade, componentes vazios, `.` ou `..`.
2. Passa pela normalização NFC e pela regra de nomes (RN-68) quando for criar ou renomear.
3. É convertido para o formato do SO do servidor e resolvido; o caminho resolvido precisa estar dentro da raiz da pasta.
4. Nenhum componente pode ser link simbólico, junção (junction) ou ponto de montagem. Esses itens não são listados e qualquer operação que passe por eles é recusada com `caminho_invalido`.
5. Nenhum componente pode ser `.drivelan` na raiz.
6. A busca do item existente compara nomes normalizados sem diferenciar maiúsculas e minúsculas, para que `Relatorio.docx` e `relatorio.docx` sejam tratados como o mesmo item, mesmo com o servidor no Linux.

### 21.5 Locais proibidos para criar pastas (RN-15)

| Sistema | Locais proibidos |
|---|---|
| Windows | Raiz de qualquer unidade (`C:\`, `D:\`…); `%WINDIR%`; `%ProgramFiles%`; `%ProgramFiles(x86)%`; `%ProgramData%`; a raiz de qualquer perfil de usuário (`C:\Users\<nome>`) e a própria `C:\Users`; `AppData` de qualquer perfil e suas subpastas; unidades removíveis (tipo de unidade removível ou CD/DVD); unidades de rede e caminhos UNC (`\\servidor\...`); pastas dentro de outra pasta compartilhada do DriveLan ou que contenham uma; a pasta de dados do DriveLan |
| Linux | `/`; pontos de montagem de qualquer disco (raiz do sistema de arquivos montado); `/bin`, `/boot`, `/dev`, `/etc`, `/lib`, `/lib64`, `/opt`, `/proc`, `/root`, `/run`, `/sbin`, `/srv`, `/sys`, `/tmp`, `/usr`, `/var` e subpastas; `/home` e a raiz de qualquer perfil (`/home/<nome>`); `~/.config`, `~/.local` e `~/.cache`; dispositivos removíveis (`/media`, `/run/media` e discos marcados como removíveis); sistemas de arquivos de rede (`nfs`, `nfs4`, `cifs`, `smb3`, `sshfs` e outros `fuse.*` de rede); pastas dentro de outra pasta compartilhada ou que contenham uma; a pasta de dados do DriveLan |

Os caminhos são comparados depois de resolvidos (sem links) e, no Windows, sem diferenciar maiúsculas e minúsculas.

### 21.6 Verificação de espaço (RN-20 a RN-23, RN-56)

- Espaço ocupado = `bytes_conteudo + bytes_lixeira`, mantido em contador no banco e corrigido por varredura em segundo plano na inicialização e diariamente.
- Antes de um envio: verificação prévia do total (fluxo 13.13).
- Durante o envio: reservas em memória por envio, para que envios simultâneos de vários clientes não ultrapassem o limite juntos; o servidor confere o volume recebido e interrompe se passar do limite ou se o espaço livre do disco cair abaixo de 100 MiB.
- Espaço livre do disco: consultado com `psutil.disk_usage` no disco da pasta.

### 21.7 Arquivos incompletos (RN-62)

Recebimentos ficam em `.drivelan/tmp/` e só são movidos para o destino ao terminar com o tamanho esperado. Cancelamento, queda de conexão ou erro apagam o arquivo temporário. No cliente, as cópias para o computador são gravadas em `temp/` e só renomeadas para o destino ao final; cancelamento apaga o temporário.

### 21.8 Nomes de conflito e de duplicidade

- **Manter os dois (RN-63):** `nome (2).ext`, `nome (3).ext`…, escolhendo o primeiro número livre (comparação sem diferenciar maiúsculas e minúsculas).
- **Conflito de edição (RN-47):** `nome (conflito <usuário>).ext`, onde `<usuário>` é o nome de usuário de quem salvou; se existir, `nome (conflito <usuário> 2).ext`.
- **Restauração com nome ocupado:** `nome (2).ext` (próximo livre).
- Todos os nomes gerados respeitam a RN-68 e o limite de 255 caracteres (o nome base é encurtado quando necessário, preservando a extensão).

### 21.9 Cópias de pastas em Linux para clientes Windows

Ao copiar para o computador (inclusive em "Sair da pasta"), o app aplica o nome adaptado da RN-68 a cada item cujo nome não seja válido no SO de destino e resolve colisões (inclusive de maiúsculas e minúsculas no Windows) com a escolha da RN-63, sem que um arquivo sobrescreva outro silenciosamente. No Windows, o app usa caminhos com o prefixo `\\?\` para suportar caminhos longos.

### 21.10 Arrastar e soltar (RN-64)

- **Para dentro da janela:** arquivos e pastas soltos sobre o navegador da pasta (ou uma subpasta) seguem o fluxo 13.13.
- **Para fora da janela:** o app oferece os itens como arquivos ao gerenciador de arquivos usando entrega sob demanda (`QMimeData` com `retrieveData` sobrescrito): o download para `temp/` acontece quando o destino pede os dados, com janela de progresso e cancelamento; ao terminar, o gerenciador de arquivos copia do temporário para o destino. Se o ambiente gráfico pedir os dados já no início do arraste, o download acontece antes da soltura, com o mesmo indicador de progresso.
- **Dentro da janela:** arrastar itens para uma subpasta move os itens (fluxo 13.12).

### 21.11 Permissões e visualização

- Leitura, cópia, abertura e download: dono e clientes com acesso ativo (inclusive durante encerramento).
- Alteração (criar, editar, renomear, mover, excluir): dono e clientes, fora do encerramento.
- Restauração e esvaziamento da lixeira: só o dono.
- O administrador não acessa conteúdo.

### 21.12 Riscos de segurança tratados

Fuga da pasta por `..` e links (21.4); nomes perigosos no Windows (RN-68); preenchimento do disco (21.6); arquivos parciais (21.7); abertura de arquivos apenas a pedido do usuário (21.2); sobrescrita silenciosa (21.8 e 21.9); acesso a arquivos de outros usuários do computador (seção 24.6 e 24.7).

---

## 22. Relatórios, Consultas e Exportações

A v1 **não tem relatórios gerenciais, gráficos, indicadores nem exportações**. Existem apenas as consultas abaixo, sempre dentro do app.

### 22.1 Consultas simples

| Consulta | Informações | Quem acessa | Índices |
|---|---|---|---|
| Dashboard | Conta, computador, rede, minhas pastas, pastas que acesso, pastas da rede | Usuário | `pasta (conta_dono_id, situacao)`, `cliente_acesso (conta_id, situacao)` |
| Pastas da rede | Nome, `dono@host`, IP, status, situação de acesso | Usuário | Dados em memória da descoberta + `cliente_acesso` |
| Usuários da pasta | `nome@host`, conectado agora ou último acesso, entrada | Dono | `acesso (pasta_id, situacao)` |
| Bloqueados | `nome@host`, data | Dono | `bloqueio_dono (pasta_id, situacao)` |
| Uso do limite | Ocupado (conteúdo + lixeira) e limite | Dono | Campos da `pasta` |
| Lixeira | Nome, caminho original, tamanho, quem excluiu, quando, dias restantes | Dono | `lixeira_item (pasta_id, situacao, excluido_em)` |
| Em edição | Arquivo, `nome@host`, início, último sinal | Dono | `arquivo_em_edicao UNIQUE (pasta_id, caminho_normalizado)` |

### 22.2 Consulta de auditoria

- **Objetivo:** investigar alterações e responsabilidades.
- **Quem acessa:** dono (uma pasta própria por vez) e administrador (todas as pastas do computador e eventos sem pasta).
- **Filtros (todos opcionais):** período (data inicial e final; padrão: últimos 30 dias), usuário (`nome@host`, lista das identidades presentes nos registros), tipo de ação (lista da seção 17.2), busca por nome de arquivo ou pasta (mínimo 3 caracteres). Para o administrador, também filtro por pasta, incluindo "Eventos sem pasta (contas e administração)".
- **Ordenação:** mais recentes primeiro (`ocorrido_em DESC, id DESC`), fixa.
- **Colunas:** Data e hora, Pasta (somente na visão do administrador), Usuário, Ação, Item, Detalhes.
- **Paginação:** 100 registros por página, carregados conforme a rolagem, com cursor.
- **Índices:** seção 11.2 (`auditoria`) e FTS5 `auditoria_busca` para a busca por nome.
- **Segurança:** o serviço aplica o escopo (pasta do dono ou acesso de administrador) antes dos filtros; nenhum parâmetro do app amplia o escopo.

### 22.3 Consulta de logs de erros

- **Quem acessa:** administrador.
- **Filtros:** mês/ano e dia (obrigatórios, padrão: hoje) e busca por texto (opcional, sem diferenciar maiúsculas e minúsculas).
- **Leitura em partes:** blocos de 1.000 linhas; busca executada em tarefa separada com resultados progressivos e cancelamento.

### 22.4 Exportações

Não fazem parte da v1.

---

## 23. APIs e Integrações Externas

### 23.1 Declaração

**Não há APIs públicas, webhooks nem integrações externas na v1.** O DriveLan possui apenas dois protocolos internos, usados exclusivamente pelos próprios componentes:

1. **Canal local** entre o app e o serviço do mesmo computador.
2. **Protocolo DriveLan v1** entre serviços de computadores diferentes na LAN.

Nenhum dos dois é documentado ou suportado para uso por terceiros. Ambos usam JSON em UTF-8.

### 23.2 Descoberta

- **mDNS/DNS-SD:** o serviço registra `_drivelan._tcp.local.` com nome de instância igual ao host, porta configurada e registros TXT `v=1` (versão do protocolo), `id=<identificador completo da instalação (64 caracteres hexadecimais)>` e `h=<host>`. O anúncio é feito somente nos endereços da placa escolhida. A implementação usa python-zeroconf compartilhando a porta 5353 com outros serviços (como o Avahi), sem exigir exclusividade.
- **Broadcast UDP (reserva):** o cliente envia para o endereço de broadcast da sub-rede, na porta configurada (UDP), a mensagem `{"tipo":"drivelan_procura","v":1}`. Cada servidor responde por unicast com `{"tipo":"drivelan_servidor","v":1,"id":"<instalação completa>","host":"<host>","porta":47820}`. Mensagens maiores que 1 KB ou fora do formato são descartadas. O servidor responde no máximo 10 vezes por segundo por IP de origem.
- **Adição manual:** conexão direta ao endereço e porta informados.

### 23.3 Rotas do protocolo DriveLan v1 (rede, porta TLS)

Todas as rotas usam o prefixo `/v1`. Exceto `GET /v1/servidor` e as rotas de sessão, todas exigem o cabeçalho `X-DriveLan-Transporte` (sessão de transporte). As rotas de conteúdo exigem também `Authorization: Bearer <token de acesso>`.

| Método e rota | Finalidade |
|---|---|
| `GET /v1/servidor` | Host, identificador da instalação, versão do protocolo, horário atual do servidor |
| `POST /v1/sessao/desafio` | Devolve um desafio aleatório de 32 bytes, válido por 60 segundos |
| `POST /v1/sessao` | Recebe certificado do cliente, assinatura do desafio, UUID da conta, nome e host; devolve o identificador da sessão de transporte |
| `GET /v1/pastas` | Pastas ativas e em encerramento do servidor, com dono, status, segundos restantes de encerramento e situação de acesso para a identidade da sessão |
| `POST /v1/pastas/{uuid}/entrar` | PIN → token |
| `POST /v1/pastas/{uuid}/sair` | Encerra o acesso do chamador |
| `GET /v1/pastas/{uuid}/itens?caminho=&cursor=&limite=` | Lista uma subpasta (máx. 200 por página): nome, tipo, tamanho, modificado em, versão, em edição por, nome compatível |
| `GET /v1/pastas/{uuid}/arquivo?caminho=` | Download em fluxo, com `ETag` = versão |
| `POST /v1/pastas/{uuid}/envios/verificar` | Verificação prévia de espaço, nomes e repetidos |
| `PUT /v1/pastas/{uuid}/arquivo?caminho=&modo=` | Envio em fluxo; `modo` = `novo`, `substituir` ou `manter_os_dois`; cabeçalhos `X-DriveLan-Tamanho`, `If-Match` (edição) e `X-DriveLan-Edicao` (trava) |
| `POST /v1/pastas/{uuid}/subpastas` | Cria subpasta |
| `POST /v1/pastas/{uuid}/renomear` | Renomeia item |
| `POST /v1/pastas/{uuid}/mover` | Move item dentro da pasta |
| `DELETE /v1/pastas/{uuid}/itens?caminho=` | Envia o item para a lixeira da pasta |
| `POST /v1/pastas/{uuid}/edicoes` | Pede a trava de edição; devolve trava e versão, ou `em_edicao` com `nome@host` |
| `DELETE /v1/pastas/{uuid}/edicoes/{id}` | Libera a própria trava |
| `GET /v1/eventos` | WebSocket de eventos e presença |

**Versão do arquivo:** texto `<mtime em nanossegundos>-<tamanho>` lido do sistema de arquivos do servidor.

Rotas de gestão de pasta (PIN, limite, usuários, bloqueados, lixeira, auditoria, encerramento, reativação, liberação manual) e de contas e administração **não existem na rede**; estão apenas no canal local.

### 23.4 Sessão de transporte e identidade da instalação

1. O cliente conecta por TLS e confere a impressão digital SHA-256 do certificado do servidor com o identificador da instalação esperado (anunciado na descoberta ou registrado no primeiro uso), usando `aiohttp.Fingerprint`. Diferença → conexão abortada e RN-67.
2. O cliente pede o desafio, assina com a chave privada da sua instalação e envia junto com o seu certificado. O servidor verifica a assinatura; o identificador da instalação do cliente é a impressão digital desse certificado.
3. O servidor cria a sessão de transporte (válida por 12 horas e vinculada ao IP de origem), cria ou atualiza a identidade (`instalação + UUID da conta`), atualiza nome e host e registra a troca de nome, se houver.

### 23.5 Eventos WebSocket

Formato de toda mensagem: `{"tipo": "<tipo>", "id": "<uuid>", "dados": {...}, "enviado_em": "<ISO 8601>"}`.

| Direção | Tipo | Dados |
|---|---|---|
| Cliente → servidor | `assinar` | Lista de pastas (UUID e token) a acompanhar |
| Cliente → servidor | `edicao_sinal` | Travas ativas do cliente |
| Servidor → cliente | `assinatura_resultado` | Estado de cada pasta (`ok`, `token_invalido`, `pasta_desativada`, `pasta_encerrada`, `em_encerramento` com segundos restantes) |
| Servidor → cliente | `encerramento_programado` / `encerramento_alterado` | `termina_em`, `restante_segundos`, tipo |
| Servidor → cliente | `encerramento_cancelado` | — |
| Servidor → cliente | `pasta_desativada` / `pasta_encerrada` | — |
| Servidor → cliente | `acesso_revogado` | Motivo |
| Servidor → cliente | `edicao_liberada` | Trava liberada pelo dono ou por falta de sinal |
| Servidor → cliente | `conteudo_alterado` | Subpasta alterada, para atualizar a lista aberta (não gera notificação) |

Presença: ping WebSocket a cada 30 segundos; sem resposta em 90 segundos, a conexão é considerada perdida.

### 23.6 Formato de erro e códigos

Resposta de erro: `{"erro": {"codigo": "<código>", "mensagem": "<texto para o usuário>", "dados": {...}}}`.

| Código | HTTP | Uso |
|---|---|---|
| `requisicao_invalida` | 400 | Corpo ou parâmetros malformados |
| `nome_invalido` | 400 | RN-68 (com motivo) |
| `caminho_invalido` | 400 | Seção 21.4 |
| `sessao_invalida` / `transporte_invalido` | 401 | Sessão local ou de transporte ausente ou expirada |
| `token_invalido` | 401 | Token de acesso revogado ou inexistente |
| `pin_incorreto` | 401 | Com `tentativas_restantes` |
| `acesso_negado` | 403 | Ação não permitida |
| `usuario_bloqueado` | 403 | Bloqueio pelo dono |
| `pasta_desativada` | 403 | — |
| `pin_bloqueado_temporariamente` | 429 | Com `liberado_em` |
| `nao_encontrado` | 404 | Pasta ou item inexistente |
| `nome_existente` | 409 | Item com o mesmo nome |
| `em_edicao` | 409 | Com `por` (`nome@host`) |
| `pasta_encerrada` | 410 | Pasta apagada |
| `pasta_cheia` | 507 | RN-21 |
| `disco_dono_cheio` | 507 | RN-56 |
| `pasta_somente_leitura` | 423 | Encerramento em andamento |
| `nome_incompativel_bloqueado` | 423 | Item com nome fora da RN-68 em operação não permitida |
| `erro_interno` | 500 | Com `codigo_log` |

### 23.7 Falhas, novas tentativas e idempotência

- Falhas de rede no cliente: reconexão com espera crescente (seção 12.6). Transferências interrompidas não são retomadas: o usuário inicia de novo.
- Envios usam a área temporária e movimentação atômica; repetir o mesmo envio não gera arquivo parcial.
- Cada pedido de alteração leva o cabeçalho `X-DriveLan-Pedido` (UUID). O servidor guarda em memória os últimos 1.000 pedidos por 10 minutos e responde com o mesmo resultado se o pedido for repetido, evitando ações em dobro (ex.: exclusão repetida após falha de rede).
- O envio de alterações pendentes é idempotente pela versão base: se já foi aplicado, o servidor responde com a nova versão e o cliente remove a pendência.
- Erros de protocolo são registrados no log de erros do lado que os detectou.

### 23.8 Rotas do canal local

O canal local usa HTTP/1.1 e WebSocket sobre o socket Unix ou o named pipe da seção 5.6, com o prefixo `/local/v1`. Corpo e respostas em JSON (UTF-8), com o mesmo formato de erro da seção 23.6. Cabeçalhos: `X-DriveLan-Sessao` (sessão de conta) e `X-DriveLan-Admin` (sessão de administrador). Legenda da coluna "Sessão": **—** nenhuma; **C** sessão de conta; **A** sessão de administrador; **SO** apenas a identidade do usuário do SO.

| Grupo | Método e rota | Sessão | Finalidade |
|---|---|---|---|
| Serviço | `GET /local/v1/estado` | — | Versão, host e se o serviço está pronto |
| Sessão | `POST /local/v1/contas` | — | Cadastro (13.1) |
| Sessão | `POST /local/v1/sessao` | — | Login; devolve token de sessão e indica PIN temporário (13.2) |
| Sessão | `POST /local/v1/sessao/desbloquear` | C | Confirma o PIN ao reabrir a janela (12.4) |
| Sessão | `DELETE /local/v1/sessao` | C | Sair da conta |
| Conta | `PUT /local/v1/conta/pin` | C | Troca de PIN, inclusive a obrigatória (13.3, 13.6) |
| Conta | `PUT /local/v1/conta/nome` | C | Troca de nome (13.5) |
| Conta | `DELETE /local/v1/conta` | C | Exclusão da conta com PIN (13.7) |
| Rede | `GET /local/v1/rede` | C | Rede atual: placa, nome, IP, faixa |
| Rede | `GET /local/v1/rede/placas` · `PUT /local/v1/rede/placa` | C | Lista de placas e troca (13.27) |
| Descoberta | `GET /local/v1/rede/pastas` | C | Lista de pastas da rede com situação de acesso (13.9) |
| Servidores manuais | `GET` · `POST /local/v1/servidores` · `DELETE /local/v1/servidores/{id}` | C | Listar, adicionar e remover (13.28) |
| Cliente | `GET /local/v1/acessos` | C | Pastas que a conta acessa, com estado da conexão |
| Cliente | `POST /local/v1/acessos` | C | Entrar numa pasta com PIN (13.10) |
| Cliente | `DELETE /local/v1/acessos/{id}` | C | Sair da pasta ou remover da lista (13.23) |
| Dono | `GET /local/v1/pastas/locais/sugestao?nome=` | C | Nome válido, local sugerido, espaço livre, 10% e 80% |
| Dono | `POST /local/v1/pastas/locais/validar-local` | C | Validação de local (RN-15) |
| Dono | `POST /local/v1/pastas` | C | Adotar o diretório criado pelo app como pasta compartilhada (13.8) |
| Dono | `GET /local/v1/pastas` · `GET /local/v1/pastas/{uuid}` | C | Minhas pastas e detalhes (uso do limite, situação, encerramento) |
| Dono | `PUT /local/v1/pastas/{uuid}/pin` · `PUT /local/v1/pastas/{uuid}/limite` | C | 13.19 |
| Dono | `GET /local/v1/pastas/{uuid}/usuarios` · `POST /local/v1/pastas/{uuid}/usuarios/{id}/remover` | C | Usuários e remoção (13.18) |
| Dono | `GET /local/v1/pastas/{uuid}/bloqueados` · `DELETE /local/v1/pastas/{uuid}/bloqueados/{id}` | C | Bloqueados e desbloqueio |
| Dono | `GET /local/v1/pastas/{uuid}/lixeira` · `POST .../lixeira/restaurar` · `DELETE .../lixeira` | C | Lixeira (13.17) |
| Dono | `GET /local/v1/pastas/{uuid}/edicoes` · `DELETE /local/v1/pastas/{uuid}/edicoes/{id}` | C | Arquivos em edição e liberação manual (13.24) |
| Dono | `GET /local/v1/pastas/{uuid}/auditoria` | C | Consulta da seção 22.2 |
| Dono | `POST /local/v1/pastas/{uuid}/encerramento` · `PUT` · `DELETE` | C | Programar ou executar, alterar prazo, cancelar (13.20, 13.21) |
| Dono | `POST /local/v1/pastas/{uuid}/reativar` | C | 13.22 |
| Conteúdo | `/local/v1/conteudo/{origem}/{uuid}/...` | C | Mesmas operações de conteúdo da rede (itens, arquivo, envios/verificar, subpastas, renomear, mover, excluir, edições), onde `{origem}` é `propria` (pasta do dono, atendida localmente) ou `acesso/{id}` (repassada ao servidor remoto) |
| Edição | `GET /local/v1/edicoes-ativas` · `POST` · `PUT /{id}` · `DELETE /{id}` · `POST /{id}/sinal` | C | Edições ativas da conta para o usuário do SO (13.14) |
| Pendências | `GET /local/v1/pendencias` · `POST` · `DELETE /{id}` | C | Alterações guardadas com o servidor offline (13.16) |
| Lixeira do SO | `GET /local/v1/lixeira-so/pendentes` · `POST /local/v1/lixeira-so/{uuid}/concluida` | SO | Pastas apagadas do usuário do SO aguardando envio à Lixeira (13.20) |
| Erros do app | `POST /local/v1/app/erros` | SO | Registro de erros do app no log (19.1.2) |
| Administrador | `POST /local/v1/admin/sessao` · `DELETE` | — / A | Entrada com a chave (RN-58) e saída |
| Administrador | `GET /local/v1/admin/logs` · `GET /local/v1/admin/logs/{data}?a_partir=&linhas=` · `GET .../busca?texto=` · `DELETE /local/v1/admin/logs?escopo=` | A | Meses e dias disponíveis, leitura em partes, busca e limpeza |
| Administrador | `GET /local/v1/admin/auditoria` | A | Auditoria de todas as pastas do computador |
| Administrador | `GET /local/v1/admin/contas` · `POST /local/v1/admin/contas/{uuid}/pin-temporario` | A | Resgate (13.25) |
| Eventos | `GET /local/v1/eventos` (WebSocket) | C ou SO | Notificações, mudanças de estado das pastas, progresso de transferências, contagem regressiva, `sessao_encerrada`, `mostrar_lixeira_so` |

**Streaming de arquivos no canal local:** downloads respondem com o corpo binário em blocos (`Transfer-Encoding: chunked`) e o cabeçalho `X-DriveLan-Tamanho`; envios usam corpo binário em blocos com `X-DriveLan-Tamanho` e `X-DriveLan-Transferencia` (UUID). O serviço publica o progresso no WebSocket local (evento `transferencia_progresso` a cada 250 ms, com bytes transferidos e total). Cancelar uma transferência = fechar a conexão HTTP (a sessão local não é afetada, seção 15.5); o serviço repassa o cancelamento ao servidor remoto e descarta os temporários. Blocos de 256 KB.

A conexão do app sem conta logada (bandeja na sessão do SO) usa apenas as rotas marcadas com **—** e **SO**; o WebSocket de eventos aberto sem sessão de conta recebe somente eventos do usuário do SO (ex.: `mostrar_lixeira_so`).

---

## 24. Segurança Funcional

### 24.1 Proteção de rotas

- Rotas de gestão, contas e administração apenas no canal local; rotas de rede limitadas ao conteúdo das pastas (23.3).
- Validação de papel, sessão e token em toda rota no serviço (seção 16.2); a interface nunca é a única barreira.

### 24.2 Criptografia e identidade

- Certificado próprio por computador: ECDSA P-256, autoassinado, validade de 20 anos, gerado na instalação e preservado na reinstalação com "manter dados".
- O identificador da instalação é a impressão digital SHA-256 do certificado.
- TLS 1.2 ou superior (preferência por TLS 1.3) em toda conexão de rede; nenhum tráfego sem TLS, exceto descoberta mDNS e broadcast, que não carregam dados sensíveis.
- Confiança no primeiro uso e bloqueio em mudança de identidade (RN-67).

### 24.3 Tokens de acesso

- Gerados com `secrets.token_urlsafe(32)` ao aceitar o PIN.
- Vinculados à pasta, à conta (UUID) e à instalação do cliente: o servidor só aceita o token numa sessão de transporte da mesma instalação e conta (RN-29).
- Revogados ao: desconectar, bloquear, sair da pasta, apagar a pasta, reativar exigindo PIN e excluir a conta. Na desativação, os acessos ficam guardados mas inúteis até a reativação com restauração.
- No bloqueio da conta (RN-06), o cliente suspende localmente os tokens da conta; eles voltam no resgate (RN-52).

### 24.4 Bloqueios por tentativas

Conta: 5 erros seguidos (RN-06). Pasta: 5 erros por instalação e por IP, bloqueio de 15 minutos (RN-27). Chave: 5 erros por ciclo, bloqueio crescente (RN-58). Contadores persistidos no banco (sobrevivem a reinícios).

### 24.5 Dados sensíveis e mensagens de erro

- PINs, chave e tokens nunca aparecem em logs, auditoria, mensagens ou eventos.
- Mensagens de erro sem detalhes técnicos (seção 19.1.4).
- Login com nome inexistente responde exatamente como uma conta real, com contador fictício em memória (fluxo 13.2).
- A tela de resumo da criação da pasta é o único momento em que o PIN da pasta é mostrado; depois disso ele não pode ser recuperado (somente trocado).

### 24.6 Canal local

- Identificação do usuário do SO de cada conexão (seção 15.5) e sessões vinculadas a ele.
- Um usuário do SO não acessa dados de outro: alterações pendentes, envios à Lixeira do SO e arquivos locais são filtrados pelo usuário do SO.
- Entre contas do DriveLan num mesmo usuário do SO, a separação é feita pelo PIN e pela sessão.

### 24.7 Permissões de sistema de arquivos

- O serviço roda com privilégios do sistema (LocalSystem ou root) apenas para hospedar as pastas.
- O diretório da pasta é criado pelo app com as permissões do usuário do SO, que comprova poder gravar no local (fluxo 13.8).
- **Windows:** arquivos e subpastas criados pelo serviço herdam a ACL da pasta, garantindo ao usuário do SO dono acesso normal pelo Explorador.
- **Linux:** após criar ou receber cada arquivo ou subpasta, o serviço define dono e grupo iguais aos da raiz da pasta (UID de `so_dono` e seu grupo primário), com modo `0644` para arquivos e `0755` para pastas. A área `.drivelan/` tem modo `0700` e o mesmo dono.
- No Fedora com SELinux, a unidade systemd do serviço deve rodar num contexto que permita acessar pastas nos diretórios pessoais; isso deve ser verificado no piloto.

### 24.8 Proteção da instalação

Programa somente leitura para usuários comuns; banco, certificado e logs em pastas restritas; configuração sem segredos; comandos administrativos (`--definir-chave`, `--migrar`, `--configurar-firewall`, `--regenerar-identidade`) exigem privilégio de administrador do SO.

### 24.9 Exposição na rede

- Regras de firewall restritas à sub-rede local (Windows) e à zona padrão (Linux).
- Limites contra abuso: corpo JSON de no máximo 64 KB; no máximo 20 sessões de transporte por IP; no máximo 10 pedidos de PIN por minuto por IP em todo o servidor (além do bloqueio da RN-27).
- Placas VPN ignoradas por padrão (RN-11); acesso fora da LAN não é suportado.

### 24.10 Revisão de segurança recomendada

Antes da entrega: revisão de validação de caminhos (testes com `..`, links, junções, nomes reservados e Unicode), revisão do canal local (tentativas com sessão de outro usuário do SO), testes de TLS e mudança de identidade, conferência de que nenhum segredo aparece em logs, e verificação das permissões das pastas do sistema em Windows e Linux.

---

## 25. Organização Sugerida da Implementação

O projeto é desenvolvido localmente no Fedora, a partir do `[Diretório do Projeto - Repositório]`, com testes numa VM Windows 11 em modo ponte. Cada etapa é pequena e termina com algo funcionando e testado.

| # | Etapa | Entrega verificável |
|---|---|---|
| 1 | Preparação do repositório | `pyproject.toml`, dependências fixadas, estrutura de pastas da seção 5.5, ruff, mypy e pytest rodando; LICENSE GPLv3 |
| 2 | Módulos comuns | Regra de nomes (RN-68), caminhos do protocolo, diretórios por plataforma, códigos de erro; testes unitários extensos |
| 3 | Configuração e log de erros | Leitura e gravação do `drivelan.toml` com padrões; log diário por mês/ano; contingência; retenção de 3 meses (sem `.env`) |
| 4 | Banco e migrations | Executor com `schema_migracoes`, checksum, cópia de segurança, `0001_inicial.sql` completa; testes de execução duplicada e de alteração indevida |
| 5 | Serviço mínimo | `drivelan-service --console` iniciando na ordem da seção 6.1; canal local com identificação do usuário do SO e do processo no Linux e no Windows; no Windows, servidor de pipe próprio cumprindo o critério de saída da seção 15.5.1 |
| 6 | App mínimo | Janela com barra de título própria, folha QSS central, fontes embutidas, ponte assíncrona, tela "serviço indisponível" |
| 7 | Contas e sessão | Cadastro, login, desbloqueio, bloqueio após 5 erros, troca de nome e PIN, exclusão, troca obrigatória de PIN |
| 8 | Administrador | Instalação da chave por CLI, Shift + F12, janela terminal, bloqueio crescente, janela de administração com logs e resgate |
| 9 | Auditoria | Registro, consulta com filtros, FTS5, paginação, retenção; aba de auditoria do administrador |
| 10 | Rede local | Identificação da placa, VPN, nome da rede; escolha de placa nas configurações |
| 11 | Identidade e TLS | Certificado, identificador da instalação, servidor TLS, sessão de transporte com desafio, confiança no primeiro uso |
| 12 | Descoberta | mDNS e broadcast, adição manual, lista de pastas da rede, status online e offline |
| 13 | Criação e gestão básica de pastas | Criar pasta (locais proibidos, limite, PIN), dashboard com minhas pastas, trocar PIN, alterar limite |
| 14 | Entrada de clientes | Entrar com PIN, bloqueio temporário, tokens, acessos de cliente, reconexão, WebSocket de eventos, estados da conexão |
| 15 | Navegação e operações | Listagem paginada, subpasta, renomear, mover, excluir para a lixeira; nomes incompatíveis |
| 16 | Transferências | Envio e cópia em fluxo, progresso, cancelamento, nome repetido, verificação de espaço, notificações de limite e disco |
| 17 | Arrastar e soltar | Para dentro, para fora (entrega sob demanda) e entre subpastas |
| 18 | Lixeira | Restaurar, esvaziar, expiração de 30 dias, contagem no limite |
| 19 | Gestão de usuários | Usuários conectados, desconectar, bloquear, desbloquear |
| 20 | Encerramento | Desativar e apagar com prazo, contagem regressiva, cancelar e alterar prazo, reativar, envio à Lixeira do SO pelo app |
| 21 | Edição | Travas, pasta de edição, envio automático, "Salvar edição", detecção de fechamento, somente leitura, conflito, liberação automática e manual |
| 22 | Servidor offline | Alterações pendentes e envio posterior com conflito |
| 23 | Notificações e bandeja | Todos os eventos da seção 12.14, menu da bandeja e modo sem bandeja |
| 24 | Sair da pasta | Cópia com nomes adaptados, saída sem cópia, descarte de pendências |
| 25 | Revisão de segurança | Itens da seção 24.10 |
| 26 | Revisão de qualidade | Cobertura de testes das regras, testes de integração com dois serviços, revisão de textos e traduções, revisão de desempenho com auditoria de 12 meses simulada |
| 27 | Empacotamento e instalador | `.exe`, `.rpm` e `.deb` atendendo à seção 4.5 |
| 28 | Piloto em laboratório | Lista de verificação da seção 26.3 |

---

## 26. Critérios de Aceitação Técnica e Funcional

### 26.1 Critérios técnicos

- [ ] Stack da seção 3 respeitada, com dependências de licença compatível com a GPLv3.
- [ ] Dois processos implementados com as responsabilidades da seção 5.2: rede só no serviço, disco do usuário só no app.
- [ ] Separação MVC respeitada: telas sem acesso a banco, rede, canal local ou disco; regras apenas em `servico/regras/`.
- [ ] Estrutura do projeto organizada a partir do `[Diretório do Projeto - Repositório]`, sem nomes de pastas públicas de servidor web.
- [ ] Nenhuma operação de rede ou disco na thread da interface; a janela nunca trava.
- [ ] Configuração em `drivelan.toml`, sem `.env` e sem credenciais; valores padrão aplicados quando ausente ou inválida.
- [ ] Banco, certificado, configuração e logs nas pastas protegidas da seção 5.6; nenhum desses arquivos é servido pela rede.
- [ ] Migrations criam todas as tabelas, campos, chaves, índices, constraints, FTS5 e gatilhos; execução duplicada impedida pela `schema_migracoes`; executadas só na inicialização do serviço ou pelo comando administrativo; nenhuma rota permite executá-las.
- [ ] Índices da seção 11.2 criados; consulta de auditoria com 12 meses de registros simulados responde em menos de 1 segundo por página.
- [ ] Logs diários funcionando, liga e desliga pela configuração, contingência em memória e no app funcionando quando a gravação falha.
- [ ] Auditoria com todos os eventos da seção 17.2 e sem leituras, downloads ou segredos.
- [ ] TLS em toda conexão de rede; mudança de identidade bloqueada.
- [ ] Validação de caminhos impedindo acesso fora da pasta, inclusive por links e junções.
- [ ] Canal local recusa sessões de outro usuário do SO ou de outro processo e conexões remotas; fechar uma conexão (inclusive ao cancelar transferência) não encerra a sessão.
- [ ] Rotas do canal local implementadas conforme a seção 23.8, com a exigência de sessão de cada grupo.
- [ ] Instância única do app por usuário do SO.
- [ ] Estados dos acessos de cliente e edições ativas persistidos e recuperados após reiniciar o app.
- [ ] Telas aderentes ao `docs/DESIGN.md` com as correções da seção 12.1.
- [ ] Todos os textos em português e marcados para tradução.
- [ ] Nenhuma funcionalidade fora deste FSD (seção 7).
- [ ] Revisões de segurança e de qualidade concluídas.

### 26.2 Critérios funcionais

**Cadastro e login**
- [ ] Cria conta com nome e PIN de 4 dígitos; impede nome repetido (sem diferenciar maiúsculas) e PIN inválido, com mensagem clara.
- [ ] Login exigido sempre que a janela é aberta, inclusive ao reabrir da bandeja.
- [ ] 5 erros seguidos: mensagem exata, conta e pastas desativadas, acessos de cliente suspensos, arquivos preservados, auditoria.
- [ ] PIN temporário obriga a troca antes do uso.
- [ ] Troca de nome auditada; auditoria mostra nome atual com o anterior entre parênteses.
- [ ] Exclusão da conta só sem pastas e com PIN.

**Rede e lista de pastas**
- [ ] Dashboard mostra nome da rede (ou "Rede cabeada"), IP e faixa.
- [ ] Usa a placa principal, permite trocar e ignora VPN por padrão.
- [ ] Lista mostra pastas da rede com nome, `dono@host`, status e situação de acesso.
- [ ] Adição manual de servidor funciona.

**Criação e gestão de pastas**
- [ ] Sempre cria pasta nova; local sugerido no disco com mais espaço; locais proibidos recusados com motivo.
- [ ] Nome único no computador; PIN de 6 dígitos sugerido e editável.
- [ ] Limite sugerido de 10% do espaço livre; máximo de 80% de (espaço livre + ocupado pela pasta), que na criação equivale a 80% do livre; nunca abaixo do ocupado, inclusive com o disco quase cheio.
- [ ] Troca de PIN não desconecta quem já tem acesso.
- [ ] Pasta disponível com a janela fechada e com qualquer pessoa logada no computador, inclusive após reiniciar.

**Acesso de clientes**
- [ ] Entrada com PIN correto; pasta aparece em "Pastas que acesso".
- [ ] 5 erros de PIN bloqueiam o computador por 15 minutos naquela pasta; dono notificado; auditoria.
- [ ] Usuário bloqueado não entra com PIN correto.
- [ ] Outra conta no mesmo computador precisa do PIN.
- [ ] Reconexão automática após reiniciar e quando o servidor volta.
- [ ] Estado da conexão sempre visível.

**Remoção e bloqueio**
- [ ] Opções "Apenas desconectar" e "Remover e bloquear"; lista de bloqueados com desbloqueio.
- [ ] Cliente removido recebe "acesso revogado"; apenas desconectado volta com o PIN atual.

**Edição e conflitos**
- [ ] Abre no programa padrão; salvamentos chegam à pasta sem ação extra; "arquivo em edição" visível.
- [ ] Arquivo em edição por outra pessoa mostra quem edita e oferece somente leitura.
- [ ] Conflito mantém as duas versões, notifica e audita.
- [ ] Servidor offline: alteração guardada com a mensagem definida e enviada quando ele volta.
- [ ] Aviso de edição termina ao fechar, com "Salvar edição", após 10 minutos sem sinal ou por liberação do dono.

**Transferências**
- [ ] Progresso e cancelamento com descarte do incompleto.
- [ ] Nome repetido com "Substituir", "Manter os dois", "Pular" e "Aplicar a todos".
- [ ] Arrastar e soltar nos dois sentidos.

**Limite, lixeira e exclusões**
- [ ] Envio além do limite recusado com "Pasta cheia. Contate o dono da pasta."
- [ ] Aviso ao dono em 90%; lixeira conta no limite.
- [ ] Disco do dono cheio: envio recusado com a mensagem definida e dono notificado.
- [ ] Exclusões vão para a lixeira; só o dono restaura ou esvazia; expiração em 30 dias.

**Encerramento**
- [ ] "Desativar compartilhamento" e "Apagar pasta" separados; confirmação com conectados e com acesso.
- [ ] Imediato ou prazo de 5 minutos a 7 dias (padrão 1 hora); somente leitura e contagem regressiva durante o prazo.
- [ ] Offline vê o aviso ao reconectar dentro do prazo ou é informado do encerramento depois.
- [ ] Apagar exige o nome e envia os arquivos à Lixeira do SO.
- [ ] Reativação com escolha entre restaurar acessos e exigir PIN; bloqueados mantidos.
- [ ] Cancelar ou alterar prazo; clientes recebem "Encerramento cancelado".

**Saída do cliente**
- [ ] Oferece cópia antes de sair; cópia só com servidor online, com aviso quando não for possível.

**Auditoria**
- [ ] Eventos da seção 17.2 com data, horário e `nome@host`; sem leituras e downloads.
- [ ] Dono vê só as próprias pastas; administrador vê todas, inclusive apagadas por 1 mês.
- [ ] Remoção após 12 meses; filtros por período, usuário, tipo de ação e busca por nome, mais recentes primeiro.

**Administrador**
- [ ] Shift + F12 abre a janela terminal em primeiro plano, inclusive na tela de login.
- [ ] Chave correta abre as três abas; 5 erros bloqueiam 15 minutos, dobrando a cada ciclo.
- [ ] Chave nunca exibida nem alterável pelo app.
- [ ] PIN temporário reativa conta, pastas e acessos.
- [ ] Administrador não abre conteúdo nem apaga pastas; toda ação auditada.
- [ ] Reinstalação oferece manter dados (padrão) e nunca apaga arquivos das pastas.

**Logs de erros**
- [ ] Arquivos diários em subpastas por mês e ano; liga e desliga pela configuração.
- [ ] Só o administrador vê e limpa; exclusão automática após 3 meses; consulta por mês/ano, dia e texto.

**Notificações**
- [ ] Cliente e dono recebem somente os eventos da seção 12.14; alterações comuns não notificam.

**Interoperabilidade**
- [ ] Pasta hospedada no Linux usada por clientes Windows e pasta hospedada no Windows usada por clientes Linux, com todas as funcionalidades.
- [ ] Nomes que diferem só por maiúsculas são tratados como iguais também com servidor Linux.
- [ ] Itens com nomes incompatíveis colocados direto no disco do dono são copiados para Windows sem perda nem sobrescrita, e o original permanece intacto.

### 26.3 Lista de verificação do piloto em laboratório

- [ ] Vários clientes (mínimo 10) na mesma pasta, enviando e editando ao mesmo tempo.
- [ ] Windows Defender Firewall com perfil de rede "Público" e "Privado".
- [ ] `firewalld` ativo no Fedora, com Avahi em execução.
- [ ] Reinício do computador do dono e dos clientes: pastas voltam e clientes reconectam após login.
- [ ] Conflitos de edição com Microsoft Office, LibreOffice e editores de texto simples, em Windows e Linux.
- [ ] Detecção de fechamento por trava (Windows) e por arquivos de trava (`~$`, `.~lock`).
- [ ] Wi-Fi com isolamento de clientes (resultado esperado e mensagem orientando adição manual ou rede cabeada).
- [ ] Descoberta somente por mDNS e somente por broadcast (bloqueando um de cada vez).
- [ ] Teste misto nos dois sentidos (Linux hospedando para Windows e Windows hospedando para Linux): descoberta, entrada com PIN, edição, conflito, transferências e encerramento.
- [ ] Arrastar para fora no Windows, no GNOME com Wayland e com X11.
- [ ] Bandeja no GNOME (com e sem extensão de bandeja) e no KDE.
- [ ] Pasta criada em `~/Documentos` no Fedora com SELinux ativo.
- [ ] Disco do dono enchendo durante um envio.
- [ ] Reinstalação mantendo dados e apagando dados, conferindo que os arquivos das pastas continuam no disco.
- [ ] Computadores clonados por imagem com o DriveLan já instalado: detecção do identificador duplicado no log e correção com `--regenerar-identidade`.
- [ ] Retomada da edição após fechar o app à força com um arquivo aberto e alterado.
- [ ] Windows 10 (64 bits, 22H2) como dono e como cliente: instalação, serviço, firewall, descoberta, entrada com PIN, edição, conflito, transferências, arrastar e soltar e bandeja.
- [ ] Windows 11 24H2 com a localização desligada e ligada: o dashboard mostra "Rede sem fio" ou o SSID, sem erro.
- [ ] Barra de título própria no Windows 11: Snap Layouts no botão maximizar, encaixe ao arrastar para as bordas, redimensionamento e cantos arredondados.
- [ ] Canal local no Windows: critério de saída da seção 15.5.1 repetido nos computadores do laboratório.
- [ ] Cliente de pasta hospedada no mesmo computador por outra conta (seção 5.2.1).
- [ ] Alteração do limite com o disco quase cheio (RN-20).

---

## 27. Pontos Pendentes e Decisões Futuras

Nenhuma pendência impede o início da codificação. Ficam registrados os itens abaixo, que não bloqueiam as etapas 1 a 26 da seção 25:

1. **Ferramenta de empacotamento e de instalador** (por exemplo, PyInstaller ou Nuitka; Inno Setup ou NSIS; ferramentas nativas de `.rpm` e `.deb`): escolher na etapa 27, desde que atenda aos requisitos da seção 4.5, inclusive registro do serviço do Windows, unidade systemd, regras de firewall e a opção "Manter dados e trocar apenas a chave" marcada por padrão.
2. **Validação no piloto de pontos dependentes do ambiente:** entrega sob demanda no arrastar para fora (Wayland e X11), comportamento da bandeja em ambientes sem suporte, contexto SELinux do serviço no Fedora, convivência do mDNS com o Avahi, SSID no Windows 11 24H2 sem localização, Snap Layouts da barra de título própria e funcionamento no Windows 10. Se algum ponto falhar, a solução deve ser registrada numa revisão deste FSD antes da entrega.
3. **Decisões funcionais aprovadas pelo dono do produto** (definitivas para a v1; não dependem do piloto, ver também a seção 14.5):
   - fechar a janela mantém a sessão em segundo plano, e reabrir exige o PIN (seção 15.3);
   - notificações não ficam acumuladas para contas sem sessão ativa (seção 12.14);
   - o envio dos arquivos de uma pasta apagada para a Lixeira do SO é feito pelo app do usuário do SO que criou a pasta, assim que ele estiver em execução (fluxo 13.20);
   - limites de tamanho de nomes de usuário (3 a 32) e de pastas (1 a 64), chave de segurança de 12 a 128 caracteres e porta padrão 47820;
   - uma conta só pode ter uma sessão ativa no computador; novo login encerra a anterior (seção 14.4);
   - novos clientes podem entrar numa pasta durante o prazo de encerramento, em somente leitura (fluxo 13.10).
4. **Melhorias futuras** (fora da v1, listadas na seção 7): unidade virtual, permissões por usuário, pastas ocultas, busca, histórico de versões, retomada de transferências, transferência de posse, IPv6, macOS e celular.

---

## 28. Conclusão

Este FSD está **pronto para orientar uma IA codificadora** na implementação da v1 do DriveLan. Ele consolida escopo, regras de negócio, perfis e permissões, arquitetura em dois processos com organização MVC, modelo de dados e migrations, protocolo de rede e canal local, segurança, telas, fluxos, logs, auditoria e critérios de aceitação, sem depender de outros documentos ou conversas.

Documentos que devem ser entregues à IA codificadora:

- `docs/FSD.md`;
- `docs/DESIGN.md`, aplicado com as correções da seção 12.1.

# DECISÕES TÉCNICAS DO PROJETO

**Projeto:** DriveLan — Compartilhamento de pastas na rede local
**Data:** novembro de 2026
**Etapa:** decisões técnicas, preparatória para o `docs/FSD.md`

---

## 1. Documentos recebidos

- **PRD:** recebido (`PRD_DriveLan.md`, versão 1.1, consolidado e sem pendências funcionais).
- **DESIGN:** recebido (`DESIGN.md`). No projeto final ficará em `docs/DESIGN.md`.
- **Observações sobre os documentos:**
  - O PRD é a fonte funcional e não foi alterado nesta etapa.
  - O `DESIGN.md` tinha inconsistências internas e alguns conflitos com o PRD: duas paletas, arredondamentos divergentes, textos em inglês e termos de sincronização. Elas foram resolvidas na seção 3 e prevalecem sobre o texto original do `DESIGN.md`.
  - Os padrões genéricos do fluxo (PHP, MySQL, Bootstrap, XAMPP e Hostnet) **não foram aplicados**. Eles são voltados a sistemas web hospedados e contradizem o PRD, que pede app desktop instalado, serviço do sistema, funcionamento offline na LAN e nenhum acesso por navegador.

## 2. Identificação do sistema

- **Nome:** DriveLan. O nome anterior era Fontinele Rede-Files.
- **Objetivo principal:** permitir que qualquer pessoa crie, encontre e use pastas compartilhadas na rede local de forma simples, segura e controlada, sem nuvem e sem o compartilhamento nativo do Windows (SMB).
- **Público:**
  - escritórios e ambientes corporativos;
  - laboratórios de informática e salas de aula;
  - equipes de TI.
- **Contexto de uso:**
  - app desktop instalado em cada computador, para Windows e Linux;
  - funciona apenas na LAN, sem dependência de internet;
  - código aberto sob GPLv3;
  - interface em português, preparada para outros idiomas.
- **Resumo funcional:**
  - contas locais com PIN;
  - descoberta de pastas na rede, com adição manual de servidor;
  - pastas compartilhadas com PIN e limite de tamanho;
  - controle de clientes, com desconexão e bloqueio;
  - transferências com progresso;
  - edição no programa padrão com controle de conflito;
  - lixeira da pasta;
  - encerramento com prazo;
  - notificações;
  - auditoria;
  - logs de erros;
  - administrador local por chave de segurança.

## 3. Decisões técnicas confirmadas

### Stack
- Linguagem **Python**, com interface em **PySide6 (Qt)**.
- Interface construída com **Qt Widgets** e estilizada com **QSS** (Qt Style Sheets).

### Ambientes
- **Desenvolvimento:** Fedora, Python em ambiente virtual (`venv` ou `uv`), VS Code e Git.
- **Testes locais:** máquina virtual Windows 11.
- **Homologação:** piloto em laboratório real com computadores Windows 11 antes de cada versão.
- **Produção:**
  - publicação no GitHub Releases;
  - instalador `.exe` para Windows;
  - pacotes `.rpm` e `.deb` para Linux.

### Arquitetura
- **Dois processos:**
  - **`drivelan-service`:** serviço do sistema, sem interface, que inicia com o computador. Responde por rede, pastas, dados, auditoria, logs, lixeira, encerramentos e limites.
  - **`drivelan`:** app de janela com ícone na bandeja, aberto em cada sessão de usuário. Responde por login, telas, notificações, abertura de arquivos no programa padrão e arrastar e soltar.
- Os dois processos se comunicam por um **canal local restrito ao próprio computador**.
- Organização inspirada em **MVC** (ver seção 6).

### Armazenamento
- **Banco de dados:** SQLite, gravado **somente pelo serviço**, numa pasta de dados do sistema protegida contra edição por usuários comuns.
- **Configurações:** arquivo de texto com o log ligado ou desligado, a placa de rede escolhida e a porta TCP.
- **Logs de erros:** gravados em arquivos separados do banco.
- **Alterações salvas com o servidor offline (RN-65):** guardadas no computador do cliente até serem enviadas.

### Rede
- **Descoberta:** mDNS/DNS-SD como método principal e broadcast UDP como reserva. A adição manual por IP ou nome do computador continua disponível.
- **Comunicação:**
  - HTTP para pedidos e transferências de arquivos;
  - WebSocket para eventos, notificações e sinal de presença;
  - uma única porta TCP fixa, com valor padrão e possibilidade de alteração no arquivo de configuração.
- Bibliotecas e formato das mensagens: definidos no FSD.
- **Firewall:** o instalador cria as regras necessárias no Windows Defender Firewall e no `firewalld` ou `ufw`.

### Segurança da comunicação
- Toda a comunicação, HTTP e WebSocket, usa **TLS**.
- **Certificado próprio por computador:** gerado na instalação e preservado na reinstalação com "manter dados".
- **Confiança no primeiro acesso:** o cliente guarda a impressão digital do certificado e é avisado e bloqueado se ela mudar.
- **Token de acesso:** emitido após o PIN ser aceito e usado na reconexão automática, para que o PIN não seja reenviado.

### Interoperabilidade entre sistemas
- **Compatibilidade total entre Windows e Linux, nos dois sentidos.** Uma pasta criada no Linux pode ser descoberta, acessada e usada por clientes Windows, e uma pasta criada no Windows pode ser descoberta, acessada e usada por clientes Linux, com todas as funcionalidades do PRD.
- O protocolo do DriveLan (mDNS, broadcast UDP, HTTP, WebSocket e TLS) é **independente do sistema operacional**. Nenhuma funcionalidade pode depender do sistema do servidor ou do cliente.
- **Caminhos no protocolo:** sempre com `/` e relativos à raiz da pasta compartilhada. Cada lado converte para o formato do próprio sistema.
- **Nomes de arquivos e pastas:** seguem uma regra única, válida nos dois sistemas.
  - São recusados na criação e na renomeação, em qualquer sistema, os caracteres proibidos no Windows (`\ / : * ? " < > |`), os nomes reservados (`CON`, `PRN`, `AUX`, `NUL`, `COM1` a `COM9`, `LPT1` a `LPT9`) e os nomes terminados em ponto ou espaço.
  - Nomes que diferem apenas por maiúsculas e minúsculas são tratados como **iguais** dentro da pasta. Assim, `Relatorio.docx` e `relatorio.docx` não podem coexistir, mesmo com o servidor no Linux.
- **Arquivos já existentes com nomes incompatíveis:** quando a pasta tiver um arquivo colocado direto no disco do dono, fora do DriveLan, com nome fora dessa regra, o FSD deverá definir como ele aparece e é copiado para clientes Windows. O arquivo original não pode ser alterado nem perdido.
- **Detecção de edição:** precisa funcionar nos dois sistemas. O botão "Salvar edição" e a detecção por arquivos de trava (`~$`, `.~lock`) garantem comportamento igual, já que o travamento de arquivo é comum no Windows e raro no Linux.

### Autenticação
- **Conta local:** nome de usuário e PIN de 4 dígitos.
- **Acesso a pastas:** PIN de 6 dígitos.
- **Administrador do sistema:** chave de segurança por computador, guardada de forma irreversível.

### Edição de arquivos
- **Envio automático:** os salvamentos feitos no programa padrão são detectados e enviados automaticamente (RN-45).
- **Botão "Salvar edição":** fica na janela do DriveLan, envia a versão final pendente e **encerra a edição**, liberando o arquivo.
- **Liberação automática:** acontece quando o app consegue detectar o fechamento do arquivo, por exemplo quando o arquivo deixa de estar travado no Windows ou quando arquivos de trava como `~$arquivo` ou `.~lock` desaparecem.
- **Outras formas de liberação (RN-66):** continuam valendo a liberação após 10 minutos sem sinal e a liberação manual pelo dono.

### Acesso de administrador
- **Shift + F12** funciona quando qualquer janela do DriveLan está em foco, inclusive a tela de login, com comportamento igual em Windows e Linux.
- Não haverá atalho global nem outro meio de abertura.

### Interface e design
- **Folha de estilo:** os tokens do `DESIGN.md` vão para uma folha de estilo QSS central.
- **Paleta:** vale a do **texto descritivo** do `DESIGN.md`:
  - fundos: `#0E1024`, `#181B3A`, `#22264C`;
  - bordas: `#2A2E5C`;
  - cores de destaque: `#3D6BFF`, `#8B5CF6`, `#22D3EE`;
  - gradiente de 135° de `#3D6BFF` para `#8B5CF6`;
  - cores de status: `#22C55E`, `#64748B`, `#F59E0B`, `#F43F5E`;
  - os tokens do cabeçalho do `DESIGN.md` foram descartados.
- **Arredondamentos:**
  - 12px em cartões e painéis;
  - 8px em botões e campos;
  - formato de pílula em selos e chips.
- **Desfoque de fundo:** substituído por um fundo escuro semitransparente.
- **Selos em português:** "Pasta local" e "Pasta da rede".
- **Termos de sincronização** ("sync", "peer-to-peer", "Syncing"): tratados apenas como linguagem visual, não como funcionalidade. O chip âmbar representa "reconectando", "em edição" e "em encerramento".
- **Fontes:** Inter e JetBrains Mono embutidas no app (licença OFL).

### Fora de escopo técnico
- APIs públicas, integrações externas, exportações, upload de arquivos no sentido web, relatórios gerenciais, interface web, nuvem, Active Directory e LDAP, atalho global e unidade virtual.

## 4. Decisões adotadas por padrão

- **Exclusão da própria conta (RN-09):** a identidade do usuário (nome@host e histórico de nomes) é preservada para manter a auditoria coerente durante a retenção. A conta deixa de existir para uso.
- **Log de segurança:** não haverá log de segurança separado. Os eventos de segurança ficam na auditoria, como define a RN-41.
- **Internacionalização:** o sistema de tradução do próprio Qt, com textos marcados para tradução desde a primeira versão. O português é o idioma único da v1.
- **Versão do Python:** 3.12 ou superior. A versão exata será fixada no FSD.
- **Identificação do "computador que tentou" (RN-27):** o FSD deve usar um identificador da instalação, e não apenas o IP, porque o IP pode mudar por DHCP.
- **Horário dos registros:** data e horário da auditoria vêm do relógio do **computador do dono da pasta**, para evitar divergência entre máquinas.
- **Divisão da implementação:** etapas pequenas e testáveis, cada uma terminando com algo funcionando. Essa foi uma escolha explícita do usuário e fica registrada aqui como diretriz para o FSD.

## 5. Stack e ambientes

| Item | Decisão |
|---|---|
| Linguagem | Python 3.12 ou superior |
| Interface | PySide6 (Qt Widgets) com QSS |
| Banco de dados | SQLite local, gravado somente pelo serviço |
| Rede | mDNS/DNS-SD com broadcast UDP de reserva; HTTP e WebSocket sobre TLS em porta TCP fixa e configurável |
| Bibliotecas | Escolhidas no FSD, com conferência de compatibilidade com a GPLv3 (o PySide6 é LGPLv3, compatível) |
| Ambiente local | Fedora, `venv` ou `uv`, VS Code e Git; VM Windows 11 com rede em modo ponte (bridge) |
| Testes e homologação | Teste local antes de cada versão, seguido de piloto em laboratório real com Windows 11 |
| Produção | GitHub Releases: `.exe` (Windows), `.rpm` e `.deb` (Linux) |
| Deploy | Tratado em etapa própria do fluxo, incluindo empacotamento, instalador, registro do serviço e regras de firewall |

**Observações sobre o instalador.** O formato escolhido precisa permitir quatro coisas:

- definir a chave de segurança;
- reinstalar mantendo os dados, com "Manter dados e trocar apenas a chave" marcado por padrão;
- nunca apagar os arquivos das pastas compartilhadas;
- registrar o serviço do sistema e criar as regras de firewall.

**Observações sobre o Linux.** O `firewalld` vem ativo por padrão no Fedora. Os pacotes `.rpm` e `.deb` precisam liberar a porta TCP do DriveLan e o tráfego de descoberta; sem isso, os clientes Windows não encontram as pastas hospedadas no Linux. O serviço do Avahi costuma estar ativo e já usa a porta 5353 do mDNS, por isso a descoberta do DriveLan precisa conviver com ele sem desativá-lo.

## 6. Arquitetura obrigatória

O sistema segue organização inspirada em **MVC**, aplicada aos dois processos:

- **Model:** serviços e dados. Inclui o acesso ao SQLite, as regras de negócio (limites, bloqueios, lixeira, encerramentos, conflitos e auditoria) e a comunicação de rede, principalmente no `drivelan-service`.
- **View:** telas em Qt Widgets estilizadas pela folha QSS central, no app `drivelan`. As telas não acessam o banco nem a rede diretamente.
- **Controller:** classes que recebem as ações do usuário, acionam as regras por meio do canal local com o serviço e decidem o que a tela exibe.

A separação entre dados, regras de negócio e interface deve ser preservada no FSD. A estrutura de pastas será definida no FSD.

## 7. Recursos estruturais definidos

| Recurso | Decisão |
|---|---|
| Autenticação | Conta local com nome e PIN de 4 dígitos; PIN de pasta de 6 dígitos; token após aceite do PIN; chave de administrador por computador |
| RBAC | Não é um RBAC com perfis configuráveis. São papéis fixos e contextuais: usuário, dono e cliente, definidos por pasta, além do administrador do sistema |
| Auditoria | Eventos da RN-41, com retenção de 12 meses; pastas apagadas ficam consultáveis por 1 mês, só pelo administrador |
| Exclusão lógica | Lixeira da pasta por 30 dias, desativação reversível de contas e pastas e preservação da identidade em contas excluídas; a pasta apagada vai para a Lixeira do sistema operacional |
| Log de erros | Somente em arquivos, um por dia, em subpastas por mês e ano; liga e desliga por configuração; retenção fixa de 3 meses |
| Log de segurança | Não separado; os eventos ficam na auditoria |
| Configurações globais | Arquivo de texto com log ligado ou desligado, placa de rede e porta TCP |
| Uploads e anexos | Não se aplica; a transferência de arquivos é a função central do app |
| Exportações | Não fazem parte da v1 |
| APIs | Nenhuma API pública; existe apenas o protocolo interno do DriveLan |
| Integrações externas | Nenhuma |

## 8. Perfis e permissões em nível alto

- **Usuário:** gerencia apenas a própria conta (nome, PIN e exclusão) e vê o dashboard e as pastas da rede.
- **Dono da pasta:** tem controle total das pastas que criou:
  - PIN e limite de tamanho;
  - usuários e bloqueios;
  - lixeira e auditoria;
  - desativar, reativar e apagar a pasta;
  - encerramentos;
  - liberação de arquivos em edição;
  - conteúdo da pasta.
- **Cliente:** lê, abre, edita, copia, renomeia, move e exclui o conteúdo e sai da pasta com opção de cópia. Não gerencia a pasta.
- **Administrador do sistema:** atua só no computador local. Pode:
  - consultar e limpar logs;
  - consultar a auditoria de todas as pastas do computador;
  - definir PIN temporário para usuários.

  Não abre o conteúdo das pastas e não as apaga.

A matriz detalhada será criada no FSD, com base na seção 13 do PRD.

## 9. Entidades prováveis em nível alto

**No serviço:**

- conta de usuário, com histórico de nomes e situação da conta;
- pasta compartilhada, com PIN, limite, situação e encerramento programado;
- acesso concedido (usuário nome@host em cada pasta), com o token;
- bloqueio feito pelo dono;
- bloqueio temporário por erro de PIN, por computador e por pasta;
- item da lixeira;
- arquivo em edição, com o último sinal recebido;
- registro de auditoria;
- tentativas erradas na chave de segurança;
- certificado e identidade da instalação.

**No lado do cliente:**

- pastas acessadas como cliente;
- servidores adicionados manualmente;
- certificados confiáveis registrados no primeiro uso;
- alterações guardadas localmente;
- transferências em andamento.

**Relações evidentes:**

- a conta é dona de pastas;
- a pasta tem acessos, bloqueios, itens de lixeira, arquivos em edição e registros de auditoria.

O modelo de dados será definido no FSD.

## 10. Módulos, telas e fluxos esperados em nível alto

O FSD deverá detalhar os seguintes módulos:

- **Serviço do sistema:** inicialização com o computador, canal local com o app e tarefas periódicas (limpeza da lixeira com 30 dias, retenção da auditoria e dos logs, prazos de encerramento e liberação após 10 minutos sem sinal).
- **Contas:** cadastro, login, bloqueio após 5 erros, troca obrigatória de PIN temporário, alteração de nome e PIN e exclusão da conta.
- **Rede:** identificação da rede e da placa, descoberta (mDNS e broadcast), adição manual de servidor, TLS e confiança no primeiro uso.
- **Dashboard e bandeja do sistema.**
- **Gestão de pastas pelo dono:** criação, PIN, limite, usuários, bloqueados, lixeira, auditoria, desativação, reativação, apagar, encerramento com prazo, cancelamento e liberação de arquivos em edição.
- **Uso pelo cliente:** entrada com PIN, reconexão automática, estados da conexão, navegação e operações com arquivos, saída com cópia.
- **Transferências:** progresso, cancelamento, nome repetido e arrastar e soltar.
- **Edição:** abertura no programa padrão, envio automático, botão "Salvar edição", detecção de fechamento, somente leitura, conflito e alterações guardadas com o servidor offline.
- **Notificações** previstas na seção 5.6 do PRD.
- **Administração:** janela no estilo terminal aberta por Shift + F12, bloqueio crescente e abas de logs, auditoria e resgate.
- **Instalação e reinstalação.**

## 11. Alertas para relatórios, consultas, exportações e desempenho

- **Relatórios:** não haverá relatórios gerenciais nem exportações. Existem apenas as consultas da seção 12 do PRD.
- **Consultas mais pesadas:** a **auditoria**, com 12 meses de registros e filtros por período, usuário (nome@host), tipo de ação, pasta e busca por nome de arquivo ou pasta, ordenada dos mais recentes para os mais antigos. O FSD deverá avaliar índices no SQLite para esses filtros e para a ordenação por data.
- **Outras consultas que merecem atenção:**
  - itens da lixeira por pasta e data de exclusão, para a limpeza de 30 dias;
  - acessos e bloqueios por pasta;
  - bloqueios temporários por computador e pasta;
  - arquivos em edição pelo último sinal;
  - encerramentos pelo horário final.
- **Cálculo do espaço ocupado pela pasta, incluindo a lixeira (RN-22):** o FSD deve evitar recalcular o tamanho percorrendo o disco inteiro a cada envio.
- **Logs:** a busca por texto é feita em arquivos diários. O FSD deve prever leitura por partes para não travar a interface.
- **Interface:** listas grandes de arquivos e de auditoria devem carregar sob demanda. Operações de rede e de disco não podem bloquear a janela.

## 12. Alertas para uploads, anexos e arquivos

Não há upload de arquivos no sentido de sistema web. A transferência de arquivos entre computadores é a função central do produto e já está definida no PRD. O FSD deverá detalhar:

- validação de caminhos no servidor, para impedir que um cliente acesse algo fora da pasta compartilhada, por exemplo com `..` ou links simbólicos;
- aplicação dos locais proibidos da RN-15 e bloqueio de pastas compartilhadas dentro de outras;
- verificação do limite da pasta e do espaço livre do disco antes e durante o envio (RN-21 e RN-56);
- descarte de arquivos incompletos (RN-62);
- local da lixeira da pasta, que precisa contar no limite, e regras de restauração;
- nomes de conflito e de duplicidade (RN-47 e RN-63), aplicando a regra única de nomes da seção 3. Essa regra recusa caracteres e nomes inválidos no Windows e trata como iguais os nomes que só diferem por maiúsculas e minúsculas;
- cópia de arquivos de uma pasta no Linux para o disco de um cliente Windows, incluindo "Sair da pasta" com cópia (RN-30), sem que um arquivo sobrescreva outro por causa de nomes incompatíveis.

## 13. Alertas para logs, auditoria e segurança

**Auditoria:**

- registrar todos os eventos da RN-41;
- não registrar leituras nem downloads (RN-42);
- nunca registrar o conteúdo digitado na chave de segurança;
- exibir o nome atual do usuário com o nome anterior entre parênteses (RN-08);
- usar o horário do computador do dono.

**Log de erros:**

- é gravado em arquivo, por isso não depende do banco de dados;
- a pasta de logs fica protegida contra acesso por usuários comuns.

O FSD deve especificar:

- quais erros são registrados e com quais informações;
- como o usuário vê mensagens seguras, sem detalhes técnicos;
- a visualização apenas pelo administrador;
- a limpeza manual e a exclusão automática após 3 meses;
- o que acontece quando a própria gravação do log falha (por exemplo, disco cheio ou sem permissão), sem travar o app.

**Eventos sensíveis, todos já incluídos na auditoria:**

- 5 erros de PIN de conta;
- bloqueio temporário de computador em uma pasta;
- tentativas erradas na chave de segurança, com bloqueio crescente;
- remoções, bloqueios e desbloqueios de usuários;
- troca de PIN;
- ações do administrador;
- reativação de contas.

**Cuidados que o FSD deve detalhar:**

- **PINs e chave:** guardar o PIN da conta, o PIN da pasta e a chave de segurança com algoritmo próprio para senhas, resistente a força bruta. Como os PINs são curtos, a proteção real depende de três coisas: o banco só pode ser lido pelo serviço, os bloqueios por tentativas e o algoritmo escolhido.
- **Token de acesso:**
  - como é guardado;
  - como é revogado ao desconectar, bloquear, desativar a pasta, reativar a pasta exigindo PIN ou bloquear a conta;
  - como fica vinculado ao usuário naquele computador (RN-29).
- **Certificado:** o que a tela mostra quando o certificado de um servidor muda.
- **Canal local entre o app e o serviço:** como garantir que só o app legítimo do usuário logado envie comandos e que um usuário do computador não acesse dados de outro.
- **Permissões de sistema de arquivos:** o serviço roda com privilégios do sistema. O FSD deve definir o dono e as permissões das pastas compartilhadas e dos arquivos criados por clientes, para que o dono local continue tendo acesso normal.
- **Linux com Wayland:** não haverá atalho global. A bandeja do sistema pode variar conforme o ambiente gráfico.

## 14. Itens que não devem ser inventados

- APIs públicas, webhooks ou integrações externas.
- Exportações em CSV, PDF ou Excel.
- Relatórios gerenciais, gráficos, estatísticas ou dashboards de indicadores.
- Sincronização contínua ou acesso offline às pastas, apesar dos termos usados no `DESIGN.md`.
- Unidade virtual no explorador de arquivos.
- Permissões diferentes por usuário, modo "professor publica / aluno entrega" ou pastas ocultas.
- Busca de arquivos dentro da pasta, histórico de versões e retomada de transferências interrompidas.
- Transferência de posse de pasta.
- Descoberta através de roteadores ou VLANs.
- Interface web, versão para macOS ou versão mobile.
- Active Directory, LDAP ou qualquer serviço de nuvem.
- Administração remota ou poderes extras do administrador.
- Atalho global para Shift + F12 ou outros meios de abrir a janela de administrador.
- Log de segurança separado da auditoria.
- Notificações de alterações comuns em arquivos.
- Recuperação de PIN pelo próprio usuário.
- Qualquer automação, telemetria ou atualização automática não aprovada.

## 15. Pendências não bloqueantes

- **Ferramenta de empacotamento e instalador** para `.exe`, `.rpm` e `.deb` (por exemplo PyInstaller ou Nuitka, Inno Setup ou NSIS): definida na etapa de deploy, desde que atenda às exigências da seção 5.
- **Bibliotecas exatas** de HTTP, WebSocket, mDNS e criptografia e o **formato das mensagens**: definidos no FSD, com conferência de licença frente à GPLv3.
- **Valor padrão da porta TCP:** definido no FSD.
- **Lista de verificações do piloto em laboratório:** definida no FSD ou na etapa de testes. Deve incluir, no mínimo:
  - vários clientes na mesma pasta;
  - firewall do Windows;
  - reinício dos computadores;
  - conflitos de edição;
  - Wi-Fi com isolamento de clientes;
  - descoberta por mDNS e por broadcast;
  - teste misto nos dois sentidos: pasta hospedada no Linux usada por clientes Windows e pasta hospedada no Windows usada por clientes Linux, cobrindo descoberta, entrada com PIN, edição, conflito, transferências e encerramento.

## 16. Pronto para o FSD

As decisões técnicas estão **prontas para a criação do FSD**. Não há lacunas que impeçam a definição do modelo de dados, das permissões, dos fluxos principais, das telas essenciais ou das regras de negócio centrais.

O próximo passo é gerar:

`docs/FSD.md`

O FSD deverá ser criado com base em:

- `PRD.md`;
- `DECISOES_TECNICAS.md`;
- `docs/DESIGN.md`, considerando as correções registradas na seção 3 deste documento.

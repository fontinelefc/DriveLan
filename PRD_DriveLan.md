# DOCUMENTO DE REQUISITOS DO PRODUTO (PRD)

## DriveLan — Compartilhamento de pastas na rede local

> **Status:** PRD consolidado e revisado (versão 1.1), com os 14 pontos pendentes resolvidos; pronto para o FSD
> **Data:** novembro de 2026
> **Documentos de origem:** prompt inicial do DriveLan, documento-base `PROJECT_FONTINELE_REDE-FILES.md` e respostas da entrevista incremental
> **Próxima etapa:** FSD (Documento de Especificação Funcional e Técnica), onde serão definidas tecnologias e detalhes de implementação

---

## 1. Visão Geral do Produto

### Nome do sistema

**DriveLan**. O projeto se chamava anteriormente **Fontinele Rede-Files**.

### Descrição resumida

O DriveLan é um aplicativo para computador (desktop) que permite criar pastas compartilhadas na rede local e acessar pastas compartilhadas por outras pessoas da mesma rede, sem depender de serviços de nuvem e sem depender do compartilhamento nativo do Windows.

**Rede local (LAN)** é a rede interna de uma empresa, escola ou casa, como os computadores ligados ao mesmo roteador ou ao mesmo Wi-Fi.

O mesmo aplicativo pode ser usado de três formas:

- **Como dono de pasta (modo servidor):** a pessoa cria uma pasta compartilhada no próprio computador, define um PIN de acesso e controla quem entra.
- **Como cliente:** a pessoa vê as pastas disponíveis na rede, entra nelas com o PIN e trabalha com os arquivos.
- **De forma híbrida:** a pessoa é dona de uma ou mais pastas e, ao mesmo tempo, cliente de pastas de outras pessoas.

### Público principal

- Ambientes corporativos e pequenos escritórios.
- Laboratórios de informática e salas de aula, cenário de origem do projeto: o professor compartilha material e os alunos acessam.
- Administradores de rede e analistas de TI que precisam de uma alternativa simples ao compartilhamento nativo do Windows.

### Principal benefício esperado

Compartilhar e acessar arquivos dentro da rede interna de forma **simples, visual e direta**, sem configurar IP, firewall ou permissões manualmente e sem precisar enviar e baixar arquivos da nuvem a cada compartilhamento.

### Contexto geral de uso

- O aplicativo é instalado em cada computador que vai participar. O app instalado é obrigatório; não há acesso apenas por navegador.
- Plataformas previstas: **Windows e Linux**.
- O projeto será de **código aberto**, gratuito, sem fins lucrativos e aberto a contribuições da comunidade, com meta de custo financeiro zero para o autor.
- Licença escolhida: **GPLv3**, que garante que versões modificadas e distribuídas do DriveLan continuem abertas. A compatibilidade com as dependências será conferida no FSD.
- A interface será em português e preparada para receber outros idiomas no futuro.

---

## 2. Problema que o Sistema Resolve

### Cenário atual sem o sistema

Hoje, para compartilhar arquivos dentro da rede interna, as pessoas costumam recorrer a duas alternativas, e ambas trazem dificuldades.

**1. Compartilhamento nativo do Windows (SMB).** É frágil e exige ajustes técnicos frequentes. Problemas comuns:

- O perfil de rede está como "Público" e bloqueia a descoberta dos computadores.
- Serviços de descoberta de rede estão desativados.
- O firewall bloqueia o compartilhamento.
- Versões recentes do Windows bloqueiam o acesso de convidado e passaram a exigir configurações de segurança adicionais.
- Há confusão entre permissões de compartilhamento e permissões de pasta.
- Ocorrem problemas de usuário e senha entre computadores que não fazem parte de um domínio corporativo.

**2. Serviços de nuvem.** Obrigam a enviar o arquivo para a internet e baixá-lo novamente em outro computador que está na mesma sala. Isso gasta tempo, consome internet e depende de conexão externa.

### Dores que o DriveLan pretende reduzir

- **Dependência de suporte técnico:** usuários leigos não conseguem compartilhar uma pasta sozinhos.
- **Perda de tempo:** subir e baixar arquivos da nuvem para transferi-los entre computadores vizinhos.
- **Falta de visibilidade:** não há uma forma simples de ver quais pastas compartilhadas existem na rede e quem é o responsável por cada uma.
- **Falta de controle sobre quem fez alterações:** em pastas compartilhadas comuns, é difícil saber quem criou, editou, moveu ou apagou um arquivo.
- **Perda acidental de arquivos:** exclusões por engano, encerramento de pastas sem aviso e duas pessoas salvando o mesmo arquivo ao mesmo tempo.
- **Controle de acesso fraco:** dificuldade para remover alguém do acesso ou impedir que essa pessoa volte a entrar.
- **Disco do computador lotado:** arquivos de outras pessoas ocupam o espaço sem nenhum limite.

---

## 3. Objetivos do Sistema

### Objetivo principal

Permitir que qualquer pessoa crie, encontre e use pastas compartilhadas na rede local de forma simples, segura e controlada, sem conhecimento técnico de redes.

### Objetivos específicos

1. Permitir criar uma pasta compartilhada em poucos passos, protegida por PIN.
2. Permitir que outros computadores encontrem automaticamente as pastas da rede, sem digitar endereços. Quando a descoberta não funcionar, deve ser possível adicionar um servidor manualmente.
3. Permitir que o cliente trabalhe com os arquivos da pasta: copiar, abrir, editar, renomear, mover e excluir.
4. Dar ao dono da pasta controle sobre quem acessa, com possibilidade de desconectar ou bloquear usuários e trocar o PIN.
5. Registrar quem fez cada alteração importante e quando, numa auditoria consultável.
6. Proteger contra perda acidental de arquivos, por meio da lixeira da pasta, do controle de conflito na edição, do aviso antecipado de encerramento e da oferta de cópia ao sair.
7. Evitar que as pastas compartilhadas lotem o disco do computador do dono, por meio de um limite de tamanho por pasta.
8. Manter as pastas e as conexões funcionando de forma persistente, inclusive após reiniciar o computador.
9. Oferecer ao TI um acesso de administrador de último recurso em cada computador, para recuperar contas e diagnosticar problemas.

---

## 4. Personas e Perfis de Usuário

Existe **um único tipo de conta de usuário** no aplicativo. Os perfis "dono da pasta" e "cliente" não são contas diferentes: são **papéis** que a mesma pessoa assume conforme o que está fazendo. O **administrador do sistema** é um acesso especial liberado por uma chave de segurança.

> **Convenção de nomes:** neste documento, **Dono da pasta** é quem criou o compartilhamento, chamado de "ADM" no documento-base antigo. **Administrador do sistema** é o técnico de TI que usa a chave de segurança.

| Perfil | Descrição simples | Principais ações no sistema | Permissões básicas |
| ------ | ----------------- | --------------------------- | ------------------ |
| **Usuário** (conta comum) | Qualquer pessoa que cria uma conta no aplicativo de um computador. A conta existe apenas naquele computador. | Criar conta, fazer login, alterar o próprio nome e PIN, excluir a própria conta, ver o dashboard e as pastas da rede. | Gerencia apenas a própria conta, as próprias pastas e os próprios acessos. |
| **Dono da pasta** (papel do usuário) | Usuário que criou uma ou mais pastas compartilhadas no computador dele. | Criar pasta, definir e trocar PIN, definir limite de tamanho, ver e remover usuários, gerenciar bloqueados, usar a lixeira, consultar a auditoria, desativar, reativar ou apagar a pasta. | Todas as permissões sobre as pastas que criou e sobre o conteúdo delas. |
| **Cliente** (papel do usuário) | Usuário que entrou numa pasta de outra pessoa usando o PIN. | Entrar em pastas, ler, abrir, editar, copiar, renomear, mover e excluir o conteúdo, e sair da pasta com opção de cópia. | Leitura, escrita e exclusão do **conteúdo** da pasta. Não gerencia a pasta em si. |
| **Administrador do sistema** | Técnico de TI que conhece a chave de segurança daquele computador. Recurso de último caso. | Acessar a janela especial com as abas de logs de erros, auditoria das pastas e resgate de PIN de usuários do computador. | Atua **somente no computador** onde a chave foi digitada. Não abre o conteúdo das pastas e não as apaga. |

**Uso híbrido:** um mesmo usuário pode ser dono de pastas e cliente de outras pastas ao mesmo tempo.

---

## 5. Escopo da Primeira Versão

Escopo é o conjunto de funcionalidades que fará parte desta versão. Todas as funcionalidades abaixo foram discutidas e confirmadas.

### 5.1 Contas de usuário e acesso ao aplicativo

| Funcionalidade | O que permite | Quem usa | Problema que resolve | Regras já definidas |
|---|---|---|---|---|
| **Cadastro de usuário** | Criar uma conta com nome de usuário e PIN de 4 dígitos. | Qualquer pessoa no computador | Identificar quem usa o app e quem faz cada alteração | Nome único por computador; qualquer pessoa pode criar conta (RN-01 a RN-03) |
| **Login** | Entrar no aplicativo com nome e PIN. | Usuário | Impedir que outra pessoa use a conta | Login exigido toda vez que a janela do app é aberta (RN-04) |
| **Bloqueio por erros de PIN** | Desativar a conta após 5 erros seguidos de PIN. | Sistema | Impedir tentativas de adivinhação do PIN | Desativa conta e pastas, revoga acessos e preserva arquivos (RN-05 a RN-07) |
| **Alterar nome** | Trocar o próprio nome de usuário. | Usuário | Corrigir ou atualizar a identificação | Registrado na auditoria, mantendo o histórico (RN-08) |
| **Alterar PIN** | Trocar o próprio PIN. | Usuário | Manter a conta segura | — |
| **Excluir a própria conta** | Remover a conta do computador. | Usuário | Encerrar o uso do app | Exige confirmação com PIN e que todas as pastas do usuário já tenham sido apagadas (RN-09) |
| **Troca obrigatória de PIN temporário** | Exigir um novo PIN no primeiro login após o resgate feito pelo administrador. | Usuário | Garantir que só o usuário conheça o próprio PIN | RN-10 |

### 5.2 Rede e descoberta de pastas

| Funcionalidade | O que permite | Quem usa | Problema que resolve | Regras já definidas |
|---|---|---|---|---|
| **Identificação da rede** | Mostrar o nome da rede (nome do Wi-Fi ou "Rede cabeada"), o IP do computador e a faixa da rede. | Usuário | Saber em qual rede o computador está | Usa a placa de rede principal automaticamente; permite trocar nas configurações; placas de VPN são ignoradas por padrão (RN-11) |
| **Descoberta automática de pastas** | Encontrar sozinho as pastas do DriveLan disponíveis na rede. | Cliente | Dispensar a digitação de endereços | — |
| **Adição manual de servidor** | Informar manualmente o endereço de um computador servidor. | Cliente | Acessar pastas quando a descoberta automática não alcança, como em redes divididas por roteadores | Origem: documento-base |
| **Lista de pastas da rede** | Exibir todas as pastas do DriveLan na rede. | Usuário | Ver de forma visual o que existe e onde | Cada pasta mostra nome, dono@host, status e situação de acesso (RN-12) |

**Exemplo de item na lista:** "Financeiro — maria@ADM-PC02 — Online — Precisa do PIN".

### 5.3 Dashboard (painel inicial)

O dashboard é a tela principal após o login. Deve exibir:

- a conta de usuário logada;
- o nome do computador (host);
- a rede à qual o computador está conectado (ver 5.2);
- as pastas das quais o usuário é dono;
- as pastas às quais o usuário tem acesso como cliente;
- todas as pastas do DriveLan disponíveis na rede;
- um ícone de configurações de pasta;
- um ícone de configurações de usuário.

Além disso, o aplicativo terá um **ícone na bandeja do sistema** (área perto do relógio) com acesso rápido às funções principais.

### 5.4 Gestão de pastas pelo dono (modo servidor)

| Funcionalidade | O que permite | Problema que resolve | Regras já definidas |
|---|---|---|---|
| **Criar pasta compartilhada** | O app cria uma **nova** pasta e começa a compartilhá-la na rede. | Compartilhar sem configuração técnica | Sempre cria pasta nova; local sugerido no disco com mais espaço; nome único no computador; locais proibidos definidos (RN-13 a RN-16) |
| **Definir PIN da pasta** | Definir o PIN de acesso na criação. | Controlar quem entra | 6 dígitos numéricos, sugeridos pelo app e editáveis pelo dono; não expira (RN-17) |
| **Trocar PIN da pasta** | Definir um novo PIN a qualquer momento. | Impedir novos acessos com o PIN antigo | Usuários já conectados continuam com acesso (RN-18) |
| **Definir limite de tamanho** | Definir o espaço máximo que a pasta pode ocupar. | Evitar que a pasta lote o disco | Sugestão de 10% do espaço livre do disco; máximo de 80% do espaço livre (RN-19 a RN-23) |
| **Ver usuários da pasta** | Ver quem tem acesso e quem está conectado no momento. | Saber quem usa a pasta | Usuários identificados como nome@host |
| **Remover usuário** | Escolher entre "Apenas desconectar" e "Remover e bloquear". | Retirar o acesso de alguém | RN-24 e RN-25 |
| **Lista de bloqueados** | Ver e desbloquear usuários bloqueados. | Desfazer um bloqueio | RN-25 |
| **Lixeira da pasta** | Ver, restaurar ou esvaziar itens excluídos da pasta. | Recuperar exclusões feitas por engano | Itens guardados por 30 dias; só o dono restaura ou esvazia (RN-31 a RN-33) |
| **Auditoria da pasta** | Consultar o histórico de alterações da pasta. | Saber quem alterou o quê e quando | RN-41 a RN-44 |
| **Desativar compartilhamento** | Interromper o acesso dos clientes sem apagar os arquivos, de forma reversível. | Pausar o compartilhamento sem perder nada | Com encerramento imediato ou com prazo (RN-34 a RN-38) |
| **Reativar compartilhamento** | Voltar a compartilhar uma pasta desativada. | Retomar o uso | O dono escolhe entre restaurar os acessos anteriores ou exigir o PIN de todos novamente (RN-57) |
| **Apagar pasta** | Encerrar o compartilhamento e enviar os arquivos para a Lixeira do sistema. | Remover uma pasta que não é mais usada | Confirmação reforçada digitando o nome da pasta (RN-39) |
| **Cancelar ou alterar encerramento** | Cancelar um encerramento programado ou mudar o prazo antes do fim. | Corrigir um encerramento feito por engano ou mudar de ideia | Clientes conectados recebem "Encerramento cancelado" (RN-60) |
| **Liberar arquivo em edição** | Liberar manualmente um arquivo marcado como "em edição". | Destravar arquivos presos, por exemplo quando o computador de quem editava desligou | RN-66 |
| **Trabalhar com o conteúdo** | Ler, editar e excluir pastas e arquivos dentro da pasta que criou. | Uso normal da pasta | Mesmas regras de edição e conflito dos clientes |
| **Funcionamento em segundo plano** | Manter as pastas ativas enquanto o computador estiver ligado, mesmo com a janela do app fechada. | Garantir que a pasta esteja sempre disponível | Inicia junto com o sistema; não depende de quem está logado (RN-26) |

### 5.5 Uso de pastas pelo cliente

| Funcionalidade | O que permite | Problema que resolve | Regras já definidas |
|---|---|---|---|
| **Entrar numa pasta** | Conectar-se a uma pasta da rede digitando o PIN. | Acesso controlado | Bloqueio de 15 minutos após 5 erros (RN-27); usuário bloqueado pelo dono não entra (RN-25) |
| **Várias pastas ao mesmo tempo** | Estar conectado a uma ou mais pastas simultaneamente. | Trabalhar com várias equipes ou fontes | — |
| **Acesso permanente** | Permanecer com acesso por tempo indeterminado. | Evitar digitar o PIN repetidamente | Até ser removido pelo dono ou a pasta ser desativada ou apagada (RN-28) |
| **Reconexão automática** | Reconectar sozinho às pastas após reiniciar o computador ou quando o servidor volta a ficar online. | Continuidade de uso | Acesso concedido ao usuário naquele computador (RN-29) |
| **Estado da conexão** | Mostrar claramente se a pasta está conectada, reconectando, offline, em encerramento ou com acesso revogado. | Evitar que o usuário pense que o app está com defeito | — |
| **Operações com arquivos** | Navegar, copiar arquivos para dentro e para fora da pasta, criar subpastas, renomear, mover e excluir. | Uso do dia a dia | Exclusão envia para a lixeira da pasta (RN-31); envio recusado se a pasta estiver cheia (RN-21) ou se o disco do dono estiver sem espaço (RN-56) |
| **Acompanhar transferências** | Ver uma barra de progresso das cópias e cancelar uma transferência em andamento. | Saber se uma cópia grande está avançando e poder interrompê-la | Arquivo incompleto é descartado ao cancelar (RN-62) |
| **Nome repetido ao copiar** | Escolher o que fazer quando já existe um arquivo com o mesmo nome no destino. | Evitar substituir um arquivo sem perceber | Opções "Substituir", "Manter os dois" e "Pular", com "aplicar a todos" (RN-63) |
| **Arrastar e soltar** | Arrastar arquivos entre o computador e a janela do DriveLan. | Copiar com rapidez e naturalidade | Funciona nos dois sentidos (RN-64) |
| **Abrir e editar arquivos** | Abrir o arquivo no programa padrão do computador; ao salvar, as alterações são enviadas automaticamente para a pasta. | Editar sem baixar e reenviar manualmente | A janela do DriveLan mostra "arquivo em edição" enquanto houver arquivo aberto (RN-45) |
| **Controle de edição simultânea** | Avisar quando outra pessoa já está editando o arquivo. | Evitar que um usuário apague o trabalho do outro | Mensagem "em edição por joao@LAB-PC07", com opção de abrir somente leitura; em caso de conflito, as duas versões são mantidas (RN-46, RN-47 e RN-66) |
| **Salvar com o servidor offline** | Guardar no computador do cliente a alteração que não pôde ser enviada porque o servidor caiu. | Não perder trabalho quando o computador do dono desliga | Envio automático quando o servidor volta (RN-65) |
| **Sair da pasta** | Desconectar-se de uma pasta, com a opção de copiar os arquivos antes. | Não perder o acesso ao material ao sair | RN-30 |

### 5.6 Notificações

Mensagens exibidas na tela do computador apenas para eventos importantes.

- **Para o cliente:**
  - aviso de encerramento com prazo, com contagem regressiva;
  - encerramento cancelado;
  - pasta encerrada ou desativada;
  - acesso revogado;
  - servidor offline ou reconectado;
  - conflito ao salvar.
- **Para o dono:**
  - novo usuário entrou na pasta;
  - pasta perto do limite (90%);
  - envio recusado por falta de espaço no disco do computador;
  - bloqueio por tentativas erradas de PIN.

Alterações comuns em arquivos **não** geram notificação; elas ficam registradas apenas na auditoria.

### 5.7 Auditoria

Registro com data e horário das ações importantes, vinculadas ao usuário no formato **nome@host**.

- **O dono** consulta a auditoria das pastas que criou.
- **O administrador do sistema** consulta a auditoria de todas as pastas hospedadas naquele computador.
- Os registros são mantidos por **12 meses**.
- Depois que uma pasta é apagada, a auditoria dela continua consultável **por 1 mês**, apenas pelo administrador do sistema.
- A consulta tem filtros por período, usuário (nome@host), tipo de ação e busca por nome de arquivo ou pasta, com os registros mais recentes primeiro.

Os eventos registrados estão listados na regra RN-41.

### 5.8 Administração do sistema (chave de segurança)

| Funcionalidade | O que permite | Regras já definidas |
|---|---|---|
| **Definição da chave na instalação** | O técnico de TI cria uma chave de segurança própria para cada computador, no momento da instalação. | Não pode ser vista nem alterada pelo app; para trocá-la, é preciso reinstalar (RN-48 a RN-51) |
| **Acesso por atalho** | O atalho **Shift + F12** abre uma pequena janela em primeiro plano, simulando um terminal, onde a chave deve ser digitada. | A chave nunca aparece em nenhum lugar do app (RN-49); após 5 erros, a janela fica bloqueada por tempo crescente (RN-58) |
| **Aba de logs de erros** | Consultar os logs de erros do computador e fazer a limpeza manual. | RN-54 e RN-55 |
| **Aba de auditoria das pastas** | Consultar a auditoria de todas as pastas hospedadas no computador. | RN-43 |
| **Aba de resgate de usuários** | Definir um PIN temporário para um usuário do computador, reativando a conta. | Ao reativar, as pastas e os acessos do usuário voltam automaticamente (RN-10, RN-52) |

O administrador **não** abre o conteúdo das pastas, **não** apaga pastas e atua **apenas no computador local** (RN-53).

### 5.9 Logs de erros

Registro de erros do aplicativo para facilitar o diagnóstico de problemas, inclusive durante o desenvolvimento.

- Gravados **somente em arquivos**.
- Organizados em **subpastas por mês e ano**, com **um arquivo por dia**.
- Podem ser **ativados ou desativados** por um arquivo de configuração.
- Visíveis no app **apenas para o administrador do sistema**.
- Limpeza **manual** pelo administrador e **exclusão automática** após **3 meses** (prazo fixo).
- Consulta por mês/ano e por dia, com busca por texto dentro do log.

### 5.10 Instalação e reinstalação

- Na instalação, o TI define a chave de segurança daquele computador.
- Na reinstalação, que é a forma de trocar a chave, o instalador pergunta se deve manter os dados atuais. A opção **"Manter dados e trocar apenas a chave"** vem marcada por padrão.
- Os arquivos das pastas compartilhadas **nunca** são apagados pelo instalador, em nenhuma das opções.

### 5.11 Mensagens ao usuário

- O app exibe mensagens claras de sucesso e de erro em todas as ações.
- A interface é em português e preparada para outros idiomas.

---

## 6. Funcionalidades Fora de Escopo

Os itens abaixo **não** serão desenvolvidos na primeira versão. A lista foi confirmada pelo usuário.

| Item | Motivo |
|---|---|
| **Unidade virtual no explorador** (ex.: `Z:`) | Decisão do usuário: fora da v1. É uma das partes mais trabalhosas do projeto e depende do sistema operacional. Na v1, os arquivos são acessados pela janela do DriveLan. |
| **Permissões diferentes por usuário** (ex.: somente leitura) | Na v1, todos os clientes têm o mesmo poder sobre o conteúdo, o que simplifica o produto. |
| **Modo "professor publica / aluno entrega"** | Ideia do documento-base para salas de aula; depende de permissões por usuário. |
| **Pastas ocultas** (que não aparecem na lista da rede) | Adiado pelo usuário. |
| **Bloqueio de cópia (exportação) pelo dono** | Pouco eficaz na v1, pois o cliente já pode copiar arquivos durante o uso. |
| **Retomada de transferências interrompidas** | Útil para arquivos muito grandes, mas trabalhoso. |
| **Busca de arquivos dentro da pasta** | Recurso de conforto, adiado. |
| **Histórico de versões de arquivos** | Exige espaço extra e regras de retenção. |
| **Transferência de posse de uma pasta para outro usuário** | Adiado. |
| **Acesso offline** (trabalhar com a pasta com o servidor desligado) | Exigiria cópias locais sincronizadas. |
| **Descoberta através de roteadores/VLANs** | Na v1, a descoberta funciona na mesma rede, e outros segmentos dependem da adição manual. |
| **Interface web de contingência** (acesso por navegador) | O app instalado é obrigatório. |
| **Versões para macOS e celular** | Plataformas da v1: Windows e Linux. |
| **Integração com Active Directory/LDAP** (diretórios corporativos de login) | Complexa demais para a primeira versão. |
| **Sincronização contínua** (no estilo Syncthing) | É outro tipo de produto, com regras complexas de conflito. |
| **Edição simultânea em tempo real** por várias pessoas | Exige mesclagem de alterações; na v1 há aviso de edição e cópia de conflito. |
| **Acesso fora da rede local** (internet ou VPN) | Foge do propósito do produto e aumenta os riscos. |
| **Administração remota** (gerenciar outros computadores) | O administrador atua apenas no computador local. |
| **Poderes extras do administrador** (desativar contas ou pastas de terceiros) | O usuário decidiu manter apenas os recursos já definidos. |
| **Notificação de alterações comuns em arquivos** | Decisão do usuário: essas alterações ficam só na auditoria. |

### Itens descartados

Os trechos do prompt inicial que pertenciam a outro projeto foram **descartados por completo** e não fazem parte do DriveLan:

- validações de "lançamentos sem valor, sem data, sem tipo ou sem categoria";
- interface responsiva para celular;
- proteção de pasta de logs contra acesso por navegador;
- menção a "soft delete já definido". O conceito de lixeira do DriveLan foi definido do zero nesta entrevista.

---

## 7. Regras de Negócio

### Contas de usuário

- **RN-01:** Existe apenas um tipo de conta. A mesma conta pode atuar como dona de pasta, como cliente ou das duas formas.
- **RN-02:** A conta é **local**, ou seja, existe apenas no computador onde foi criada. Na rede, o usuário é identificado como **nome@host** (ex.: joao@LAB-PC07).
- **RN-03:** O cadastro exige nome de usuário e PIN de **4 dígitos**. O nome é **único por computador**. Qualquer pessoa no computador pode criar uma conta.
- **RN-04:** O login é exigido **toda vez que a janela do app é aberta**. Cada pessoa vê e gerencia apenas as próprias pastas e acessos.
- **RN-05:** Não existe forma de o próprio usuário recuperar o PIN esquecido.
- **RN-06:** Após **5 erros seguidos** de PIN no login, o app exibe a mensagem **"Conta bloqueada após 5 tentativas incorretas. Procure o Administrador do Aplicativo para redefinir seu PIN."** e:
  - desativa o usuário, de forma reversível;
  - desativa as pastas das quais ele é dono, de forma reversível;
  - preserva todos os arquivos;
  - revoga os acessos dele como cliente;
  - registra tudo na auditoria.
- **RN-07:** Uma conta desativada só volta a funcionar por meio do resgate feito pelo administrador do sistema.
- **RN-08:** O nome de usuário pode ser alterado. A troca é registrada na auditoria, e os registros antigos continuam ligados à mesma pessoa, exibindo o nome atual seguido do anterior entre parênteses.
- **RN-09:** O usuário pode excluir a própria conta, confirmando com o PIN, **somente depois de apagar todas as suas pastas**. Os acessos dele como cliente são revogados, e a exclusão é registrada na auditoria.
- **RN-10:** No resgate, o administrador define um **PIN temporário**, que o usuário é **obrigado a trocar** no primeiro login.

### Rede e lista de pastas

- **RN-11:** O app usa automaticamente a placa de rede principal, permite trocá-la nas configurações e ignora placas de VPN por padrão.
- **RN-12:** Na lista de pastas da rede, cada pasta mostra:
  - **nome**;
  - **dono@host**;
  - **status:** online, offline ou em encerramento;
  - **situação de acesso do usuário:** tem acesso, está bloqueado ou precisa do PIN.

### Criação e configuração de pastas

- **RN-13:** Ao criar um compartilhamento, o app **obrigatoriamente cria uma nova pasta**. Não é possível compartilhar uma pasta já existente.
- **RN-14:** O app sugere uma pasta própria do DriveLan (ex.: `D:\DriveLan\<nome da pasta>`) **no disco com mais espaço livre**.
- **RN-15:** O dono pode escolher outro local, exceto os locais proibidos:
  - a raiz de qualquer disco (ex.: `C:\`, `/`);
  - as pastas do sistema operacional e dos programas instalados;
  - a pasta inteira do perfil do usuário (subpastas dentro dela são permitidas, ex.: `Documentos\DriveLan`);
  - dentro de outra pasta compartilhada do DriveLan;
  - unidades removíveis, como pen drives, e unidades de rede.
- **RN-16:** O nome da pasta é **único naquele computador**.
- **RN-17:** O PIN da pasta tem **6 dígitos numéricos**, é sugerido pelo app, pode ser editado pelo dono e **não expira**.
- **RN-18:** O dono pode trocar o PIN da pasta a qualquer momento, sem desconectar os usuários que já têm acesso (regra do documento-base).

### Limite de tamanho da pasta

- **RN-19:** O dono define o limite de tamanho da pasta. O app verifica o espaço livre do disco e sugere **10% do espaço livre**.
- **RN-20:** O limite nunca pode passar de **80% do espaço livre** do disco no momento em que é definido ou alterado.
- **RN-21:** Um envio que ultrapasse o limite é **recusado**, com a mensagem **"Pasta cheia. Contate o dono da pasta."**.
- **RN-22:** O dono é avisado quando a pasta atinge **90%** do limite. Os itens da **lixeira contam** no limite.
- **RN-23:** O dono pode alterar o limite a qualquer momento, mas **não pode defini-lo abaixo do espaço já ocupado**.
- **RN-56:** Se o disco do dono encher antes de a pasta atingir o limite, o envio é **recusado** com a mensagem **"Sem espaço no computador do dono. Contate o dono da pasta."**, e o dono é notificado. O limite não é alterado automaticamente.

### Acesso dos clientes

- **RN-24:** Ao remover um usuário, o dono escolhe entre **"Apenas desconectar"** e **"Remover e bloquear"**.
- **RN-25:** Um usuário bloqueado **não consegue entrar mesmo com o PIN correto**, até que o dono o desbloqueie na lista de bloqueados. Remoções e desbloqueios são registrados na auditoria.
- **RN-59:** Um usuário que foi **apenas desconectado** pode voltar a entrar a qualquer momento digitando o PIN atual da pasta. Para impedir o retorno, o dono deve usar "Remover e bloquear" ou trocar o PIN.
- **RN-26:** As pastas continuam ativas em segundo plano enquanto o computador estiver ligado, independentemente de quem esteja logado no app, e iniciam junto com o sistema.
- **RN-27:** Após **5 erros** no PIN de uma pasta, **o computador que tentou** fica bloqueado por **15 minutos** naquela pasta, com registro na auditoria.
- **RN-28:** O cliente permanece com acesso por tempo indeterminado, até ser removido pelo dono ou até a pasta ser desativada ou apagada.
- **RN-29:** O acesso é concedido ao **usuário naquele computador**. Se outra pessoa fizer login no mesmo computador, ela precisa digitar o PIN da pasta.
- **RN-30:** Ao sair de uma pasta, o cliente é perguntado se deseja copiar os arquivos para uma pasta local antes de se desconectar. A cópia exige que o servidor esteja online.

### Lixeira da pasta

- **RN-31:** Itens excluídos da pasta vão para uma **lixeira da pasta**, guardada no computador do dono.
- **RN-32:** Somente o **dono** pode restaurar itens ou esvaziar a lixeira.
- **RN-33:** Os itens ficam guardados por **30 dias** e depois são apagados automaticamente. Exclusões, restaurações e esvaziamentos são registrados na auditoria.

### Encerramento de pastas

- **RN-34:** O dono tem duas ações de encerramento:
  - **Desativar compartilhamento:** os clientes perdem o acesso, os arquivos permanecem e a ação é reversível.
  - **Apagar pasta:** encerra o compartilhamento e remove os arquivos.
- **RN-35:** Antes de encerrar, o app exibe uma confirmação com o número de clientes conectados e com acesso (regra do documento-base).
- **RN-36:** Nas duas ações, o dono escolhe entre **encerrar imediatamente** ou **definir um prazo**.
- **RN-37:** O prazo vai de **5 minutos a 7 dias**, com padrão de **1 hora**. Durante o prazo:
  - a pasta fica **somente leitura**, permitindo apenas copiar;
  - uma mensagem com contagem regressiva aparece para todos os conectados, alertando sobre o tempo restante e sugerindo a cópia dos arquivos.
- **RN-38:** Quem estava offline vê o aviso ao reconectar, se ainda estiver dentro do prazo. Quem reconectar depois do encerramento é informado de que a pasta foi encerrada.
- **RN-39:** Ao apagar, os arquivos vão para a **Lixeira do sistema operacional**, com **confirmação reforçada**: o dono digita o nome da pasta para confirmar.
- **RN-40:** Uma pasta só existe para a rede enquanto o computador do dono estiver ligado. Com o computador desligado, a pasta aparece como offline e os clientes reconectam automaticamente quando ela voltar.
- **RN-57:** Ao reativar uma pasta desativada, o dono escolhe entre **"Restaurar acessos anteriores"** (marcada por padrão) e **"Exigir PIN de todos novamente"**. Em qualquer caso, a lista de bloqueados é mantida, e a reativação é registrada na auditoria.
- **RN-60:** Durante o prazo de encerramento, o dono pode **cancelar** o encerramento ou **alterar o prazo**. Ao cancelar, a pasta volta ao normal, saindo do modo somente leitura, e os clientes conectados recebem a notificação **"Encerramento cancelado"**. Tudo é registrado na auditoria.

### Auditoria

- **RN-41:** A auditoria registra, com data, horário e usuário (nome@host):
  - criação, edição, renomeação, movimentação, exclusão e restauração de arquivos e pastas;
  - entrada, saída e remoção de usuários;
  - troca de PIN;
  - bloqueios;
  - conflitos ao salvar;
  - reativação de pastas e cancelamento ou alteração de encerramentos;
  - liberação automática ou manual de arquivos em edição;
  - envio de alterações guardadas durante uma queda do servidor;
  - tentativas erradas na chave de segurança, sem registrar o que foi digitado;
  - ações do administrador do sistema.
- **RN-42:** **Leituras e downloads não são registrados.**
- **RN-43:** O dono vê a auditoria das próprias pastas. O administrador vê a auditoria de todas as pastas daquele computador.
- **RN-44:** Os registros de auditoria são mantidos por **12 meses**.
- **RN-61:** Depois que uma pasta é apagada, a auditoria dela continua consultável por **1 mês**, **somente pelo administrador do sistema**. Depois disso, os registros dessa pasta são removidos.

### Edição de arquivos

- **RN-45:** O arquivo abre no programa padrão do computador. Ao salvar, as alterações são enviadas automaticamente para a pasta. Enquanto houver arquivo aberto, a janela do DriveLan mostra o aviso "arquivo em edição".
- **RN-46:** Ao tentar abrir um arquivo que já está em edição, o usuário vê a mensagem **"em edição por joao@LAB-PC07"** e pode abri-lo **somente para leitura**.
- **RN-47:** Se mesmo assim houver conflito ao salvar, o app guarda **as duas versões** (ex.: `relatorio (conflito joao).docx`) e registra o conflito na auditoria.
- **RN-65:** Se o servidor ficar offline enquanto um arquivo está sendo editado, ao salvar o app avisa **"Servidor offline. Sua alteração foi guardada neste computador."** e mantém a alteração no computador do cliente. Quando o servidor volta, a alteração é **enviada automaticamente**. Se outra pessoa tiver alterado o arquivo nesse intervalo, vale a regra de conflito (RN-47). Tudo é registrado na auditoria.
- **RN-66:** O aviso "em edição" termina **quando o arquivo é fechado** no programa. Se o computador de quem editava ficar **sem sinal por 10 minutos**, o arquivo é liberado automaticamente. O dono também pode **liberar manualmente** a qualquer momento. As liberações automáticas e manuais são registradas na auditoria.

### Transferência de arquivos

- **RN-62:** As cópias exibem uma **barra de progresso** e podem ser **canceladas**. Ao cancelar, o arquivo incompleto é descartado.
- **RN-63:** Quando já existe um arquivo com o mesmo nome no destino, o app pergunta **"Substituir"**, **"Manter os dois"** (ex.: `relatorio (2).docx`) ou **"Pular"**, com a opção **"aplicar a todos"**.
- **RN-64:** É possível **arrastar e soltar** arquivos entre o computador e a janela do DriveLan, nos dois sentidos.

### Chave de segurança e administrador do sistema

- **RN-48:** Cada computador tem a **sua própria chave**, criada pelo TI na instalação. O técnico é responsável por guardar as chaves de cada computador.
- **RN-49:** A chave é guardada de forma irreversível: nem o app consegue mostrá-la depois. Ela **não pode ser visualizada nem alterada** em nenhuma parte do aplicativo.
- **RN-50:** A janela de acesso abre com **Shift + F12**, fica em primeiro plano e simula um terminal.
- **RN-51:** A chave só pode ser trocada **reinstalando o aplicativo**.
- **RN-52:** Ao reativar um usuário, as pastas e os acessos dele como cliente **voltam automaticamente**, com registro na auditoria.
- **RN-53:** O administrador atua **somente no computador local**. Ele **não abre o conteúdo** das pastas e **não apaga pastas**. Toda ação dele é registrada na auditoria.
- **RN-58:** Após **5 erros** na janela da chave de segurança, a janela fica **bloqueada por 15 minutos**. A cada novo ciclo de 5 erros, o bloqueio **dobra** (30 minutos, 1 hora, e assim por diante). As tentativas erradas são registradas na auditoria, sem mostrar o que foi digitado.

### Logs de erros

- **RN-54:** Os logs são gravados somente em arquivos, em subpastas por mês e ano, com um arquivo por dia. Podem ser ativados ou desativados por arquivo de configuração.
- **RN-55:** A limpeza manual é exclusiva do administrador. Os registros são apagados automaticamente após **3 meses** (prazo fixo, não ajustável).

---

## 8. Informações que o Sistema Precisa Controlar

| Informação | Para que serve no sistema | Observações importantes |
| ---------- | ------------------------- | ----------------------- |
| **Contas de usuário** | Identificar quem usa o app naquele computador | Nome único por computador e PIN de 4 dígitos guardado de forma que não possa ser lido. Guarda também o histórico de nomes anteriores. |
| **Situação da conta** | Saber se a conta está ativa, desativada ou com PIN temporário pendente de troca | Inclui a contagem de erros seguidos de PIN. |
| **Pastas compartilhadas** | Saber quais pastas o computador compartilha e onde elas estão no disco | Nome único no computador, dono, local, situação (ativa, desativada ou em encerramento) e data de criação. |
| **PIN da pasta** | Controlar a entrada de novos clientes | 6 dígitos; guardado de forma que não possa ser lido. |
| **Limite de tamanho da pasta** | Controlar o espaço que a pasta pode ocupar | Inclui o espaço ocupado atualmente, com a lixeira incluída. |
| **Acessos concedidos** | Saber quais usuários (nome@host) podem entrar em cada pasta | Inclui quem está conectado no momento. |
| **Lista de bloqueados por pasta** | Impedir a entrada de usuários bloqueados pelo dono | — |
| **Bloqueios temporários por erro de PIN** | Bloquear por 15 minutos o computador que errou 5 vezes | Por computador e por pasta. |
| **Pastas acessadas como cliente** | Reconectar automaticamente e mostrar no dashboard | Por usuário, naquele computador. |
| **Servidores adicionados manualmente** | Acessar pastas que a descoberta automática não encontra | — |
| **Lixeira da pasta** | Permitir a restauração de itens excluídos | Data de exclusão (para contar os 30 dias), quem excluiu e local original. |
| **Arquivos em edição** | Mostrar "em edição por…" e evitar conflitos | Quem está editando, desde quando e o último sinal do computador (para a liberação após 10 minutos). |
| **Alterações guardadas localmente** | Não perder alterações feitas enquanto o servidor estava offline | Ficam no computador do cliente até serem enviadas. |
| **Transferências em andamento** | Exibir o progresso e permitir o cancelamento | Arquivos incompletos são descartados ao cancelar. |
| **Encerramentos programados** | Controlar o prazo e a contagem regressiva | Tipo (desativar ou apagar), prazo e horário final. |
| **Auditoria** | Registrar quem fez o quê, quando e em qual pasta | Retenção de 12 meses; de pastas apagadas, 1 mês, visível só ao administrador. |
| **Logs de erros** | Diagnosticar problemas | Em arquivos, por dia; retenção fixa de 3 meses. |
| **Configurações do app** | Ajustar o funcionamento | Log ligado ou desligado e placa de rede escolhida. |
| **Chave de segurança** | Liberar o acesso de administrador | Uma por computador; guardada de forma irreversível, sem visualização. |
| **Tentativas erradas na chave** | Aplicar o bloqueio crescente da janela de administrador | Contagem de erros e tempo de bloqueio atual. |
| **Informações da rede atual** | Exibir no dashboard | Nome da rede, IP do computador e faixa da rede. |

---

## 9. Fluxos Principais de Uso

### 9.1 Cadastro de usuário

1. A pessoa abre o DriveLan e escolhe criar conta.
2. Informa o nome de usuário e um PIN de 4 dígitos.
3. O sistema verifica se o nome já existe naquele computador e se o PIN tem 4 dígitos.
4. Se houver problema, o sistema exibe uma mensagem clara e não cria a conta.
5. Se estiver tudo certo, o sistema cria a conta e exibe mensagem de sucesso.

### 9.2 Login

1. O usuário abre a janela do DriveLan.
2. Informa o nome e o PIN.
3. Se o PIN estiver correto, o sistema exibe o dashboard.
4. Se o PIN estiver errado, o sistema informa o erro e conta a tentativa.
5. Na 5ª tentativa errada seguida, o sistema exibe "Conta bloqueada após 5 tentativas incorretas. Procure o Administrador do Aplicativo para redefinir seu PIN.". Em seguida, desativa a conta e as pastas do usuário, revoga os acessos dele como cliente, preserva os arquivos e registra tudo na auditoria.
6. Se a conta tiver um PIN temporário, o sistema exige a criação de um novo PIN antes de liberar o uso.

### 9.3 Criar uma pasta compartilhada

1. O usuário escolhe criar uma nova pasta compartilhada.
2. Informa o nome da pasta.
3. O sistema sugere o local, no disco com mais espaço livre, e permite escolher outro local, bloqueando os locais proibidos (RN-15).
4. O sistema sugere um PIN de 6 dígitos, que o dono pode editar.
5. O sistema sugere o limite de tamanho de 10% do espaço livre do disco e não aceita valores acima de 80% do espaço livre.
6. O usuário confirma.
7. O sistema verifica se o nome é único no computador e se os dados são válidos.
8. O sistema cria a nova pasta, começa a anunciá-la na rede e registra a criação na auditoria.
9. A pasta aparece no dashboard entre as pastas das quais o usuário é dono.

### 9.4 Entrar numa pasta como cliente

1. O usuário vê a lista de pastas da rede no dashboard. Se a pasta desejada não aparecer, ele pode adicionar o servidor manualmente.
2. Escolhe uma pasta com a situação "precisa do PIN".
3. Digita o PIN da pasta.
4. Se o usuário estiver bloqueado pelo dono, o sistema informa e não permite a entrada.
5. Se o PIN estiver errado, o sistema informa o erro. Após 5 erros, o computador fica bloqueado por 15 minutos naquela pasta, com registro na auditoria e notificação ao dono.
6. Se o PIN estiver correto, o sistema concede o acesso ao usuário naquele computador, registra a entrada na auditoria e notifica o dono.
7. A pasta passa a aparecer entre as pastas às quais o usuário tem acesso e é reconectada automaticamente nas próximas vezes.

### 9.5 Abrir e editar um arquivo

1. O cliente ou o dono escolhe um arquivo da pasta e pede para abri-lo.
2. Se ninguém estiver editando o arquivo, o sistema o abre no programa padrão do computador e mostra o aviso "arquivo em edição" na janela do DriveLan.
3. Se outra pessoa já estiver editando, o sistema mostra "em edição por joao@LAB-PC07" e oferece abrir somente para leitura.
4. Ao salvar, o sistema envia as alterações automaticamente para a pasta e registra a edição na auditoria.
5. Se houver conflito ao salvar, o sistema guarda as duas versões (ex.: `relatorio (conflito joao).docx`), notifica o usuário e registra o conflito na auditoria.
6. Se o servidor estiver offline no momento de salvar, o sistema avisa "Servidor offline. Sua alteração foi guardada neste computador." e guarda a alteração localmente.
7. Quando o servidor volta, o sistema envia a alteração automaticamente. Se o arquivo tiver sido alterado por outra pessoa nesse intervalo, aplica a regra de conflito.
8. O aviso "em edição" termina quando o arquivo é fechado, após 10 minutos sem sinal do computador de quem editava ou quando o dono libera o arquivo manualmente.

### 9.6 Enviar arquivos para a pasta

1. O cliente escolhe os arquivos a enviar, pelo botão de cópia ou arrastando e soltando na janela do DriveLan.
2. O sistema verifica se o envio cabe no limite da pasta e no espaço livre do disco do dono.
3. Se não couber no limite, o sistema recusa o envio e exibe "Pasta cheia. Contate o dono da pasta.".
4. Se o disco do dono estiver sem espaço, o sistema recusa o envio, exibe "Sem espaço no computador do dono. Contate o dono da pasta." e notifica o dono.
5. Se já existir um arquivo com o mesmo nome, o sistema pergunta "Substituir", "Manter os dois" ou "Pular", com a opção "aplicar a todos".
6. O sistema copia os arquivos exibindo uma barra de progresso. Se o usuário cancelar, o arquivo incompleto é descartado.
7. Ao concluir, o sistema registra a criação na auditoria.
8. Se a pasta atingir 90% do limite, o dono é notificado.

### 9.7 Excluir e restaurar itens

1. Um usuário com acesso exclui um arquivo ou uma subpasta.
2. O sistema move o item para a lixeira da pasta e registra a exclusão na auditoria.
3. O dono abre a lixeira da pasta.
4. O dono escolhe restaurar o item ou esvaziar a lixeira.
5. O sistema executa a ação e registra na auditoria.
6. Itens com mais de 30 dias na lixeira são apagados automaticamente.

### 9.8 Remover ou bloquear um usuário

1. O dono abre a lista de usuários da pasta.
2. Escolhe um usuário e a opção de remover.
3. O sistema pergunta: "Apenas desconectar" ou "Remover e bloquear".
4. O dono confirma a escolha.
5. O sistema retira o acesso do usuário. Se a opção for bloquear, inclui o usuário na lista de bloqueados.
6. O sistema notifica o cliente de que o acesso foi revogado e registra a ação na auditoria.
7. Para desfazer um bloqueio, o dono abre a lista de bloqueados e desbloqueia o usuário.
8. Um usuário que foi apenas desconectado pode voltar a entrar a qualquer momento com o PIN atual da pasta.

### 9.9 Desativar ou apagar uma pasta

1. O dono escolhe "Desativar compartilhamento" ou "Apagar pasta".
2. O sistema mostra quantos clientes estão conectados e quantos têm acesso, avisando que eles perderão o acesso.
3. O dono escolhe "encerrar imediatamente" ou "definir um prazo" (de 5 minutos a 7 dias; padrão de 1 hora).
4. Se escolher "Apagar pasta", o sistema pede que o dono digite o nome da pasta para confirmar.
5. Se houver prazo, a pasta passa a ficar somente leitura e todos os conectados veem uma mensagem com contagem regressiva, sugerindo a cópia dos arquivos. Quem estava offline vê a mensagem ao reconectar, se ainda estiver dentro do prazo.
6. Ao fim do prazo, ou imediatamente:
   - **Desativar:** o acesso dos clientes é encerrado e os arquivos permanecem.
   - **Apagar:** os arquivos vão para a Lixeira do sistema.
7. Os clientes são notificados, e a ação é registrada na auditoria.
8. Enquanto o prazo não termina, o dono pode cancelar o encerramento ou alterar o prazo. Ao cancelar, a pasta volta ao normal e os clientes conectados recebem a notificação "Encerramento cancelado".

### 9.10 Sair de uma pasta (cliente)

1. O cliente escolhe sair de uma pasta.
2. O sistema pergunta se ele deseja copiar os arquivos antes de sair: "Copiar para uma pasta…", "Sair sem copiar" ou "Cancelar".
3. Se escolher copiar, o sistema verifica se o servidor está online e copia os arquivos para o local escolhido.
4. O sistema remove o acesso do cliente àquela pasta e registra a saída na auditoria.

### 9.11 Acesso de administrador e resgate de usuário

1. O técnico de TI pressiona Shift + F12.
2. O sistema abre uma pequena janela em primeiro plano, no estilo terminal.
3. O técnico digita a chave de segurança daquele computador.
4. Se a chave estiver correta, o sistema abre a janela de administração com as abas de logs de erros, auditoria das pastas e resgate de usuários. Se estiver errada, o sistema informa o erro. Após 5 erros, a janela fica bloqueada por 15 minutos, e o bloqueio dobra a cada novo ciclo de 5 erros.
5. Na aba de resgate, o técnico escolhe o usuário e define um PIN temporário.
6. O sistema reativa a conta, devolve automaticamente as pastas e os acessos do usuário e registra a ação na auditoria.
7. No próximo login, o usuário é obrigado a trocar o PIN temporário.

### 9.12 Trocar a chave de segurança (reinstalação)

1. O técnico reinstala o DriveLan no computador.
2. O instalador pergunta se os dados atuais devem ser mantidos, com "Manter dados e trocar apenas a chave" marcado por padrão.
3. O técnico define a nova chave.
4. O instalador conclui sem apagar nenhum arquivo das pastas compartilhadas.

### 9.13 Excluir a própria conta

1. O usuário escolhe excluir a conta nas configurações de usuário.
2. Se ele ainda for dono de alguma pasta, o sistema informa que é preciso apagá-las antes e não prossegue.
3. Se não houver pastas, o sistema pede o PIN para confirmar.
4. O sistema exclui a conta, revoga os acessos do usuário como cliente e registra a exclusão na auditoria.

### 9.14 Reativar uma pasta desativada

1. O dono escolhe uma pasta desativada e pede para reativá-la.
2. O sistema pergunta: "Restaurar acessos anteriores" (marcada por padrão) ou "Exigir PIN de todos novamente".
3. O dono confirma a escolha.
4. O sistema volta a compartilhar a pasta, mantendo a lista de bloqueados.
5. Se a escolha foi restaurar os acessos, os clientes reconectam automaticamente. Se foi exigir PIN, eles precisam digitar o PIN para entrar.
6. O sistema registra a reativação na auditoria.

---

## 10. Histórias de Usuário

### Contas

- Como **usuário**, eu quero criar uma conta com nome e PIN para que minhas ações fiquem identificadas.
- Como **usuário**, eu quero que o app peça meu PIN sempre que a janela for aberta para que outra pessoa no mesmo computador não use minha conta.
- Como **usuário**, eu quero alterar meu nome e meu PIN para manter meus dados atualizados e minha conta segura.
- Como **usuário**, eu quero excluir minha conta quando não precisar mais dela para não deixar acessos abertos.
- Como **usuário que esqueceu o PIN**, eu quero ser orientado a procurar o administrador para recuperar o acesso sem perder minhas pastas.

### Rede e dashboard

- Como **usuário**, eu quero ver em qual rede meu computador está para saber quais pastas devo esperar encontrar.
- Como **usuário**, eu quero ver no dashboard minhas pastas, as pastas que acesso e todas as pastas da rede para me orientar rapidamente.
- Como **cliente**, eu quero ver o dono, o computador e o status de cada pasta para escolher a pasta certa, mesmo quando houver nomes iguais.
- Como **cliente**, eu quero adicionar um servidor manualmente para acessar pastas que não aparecem na lista.

### Dono da pasta

- Como **dono**, eu quero criar uma pasta compartilhada com PIN para dividir arquivos com minha equipe ou turma.
- Como **dono**, eu quero definir um limite de tamanho para que a pasta não lote o disco do meu computador.
- Como **dono**, eu quero trocar o PIN para impedir novos acessos sem desconectar quem já usa a pasta.
- Como **dono**, eu quero ver quem tem acesso e quem está conectado para controlar o uso da pasta.
- Como **dono**, eu quero desconectar ou bloquear um usuário para retirar o acesso de quem não deve mais usar a pasta.
- Como **dono**, eu quero restaurar itens da lixeira para recuperar arquivos excluídos por engano.
- Como **dono**, eu quero consultar a auditoria para saber quem alterou cada arquivo e quando.
- Como **dono**, eu quero desativar ou apagar a pasta com prazo para dar tempo aos usuários de copiarem os arquivos.
- Como **dono**, eu quero ser avisado quando a pasta estiver perto do limite para agir antes que ela fique cheia.
- Como **dono**, eu quero cancelar ou alterar um encerramento programado para corrigir uma decisão feita por engano.
- Como **dono**, eu quero escolher se os acessos voltam ao reativar uma pasta para decidir se recomeço o controle de quem entra.
- Como **dono**, eu quero liberar manualmente um arquivo preso "em edição" para que os outros voltem a editá-lo.

### Cliente

- Como **cliente**, eu quero entrar numa pasta com o PIN para acessar os arquivos compartilhados.
- Como **cliente**, eu quero ser reconectado automaticamente para não precisar digitar o PIN de novo após reiniciar.
- Como **cliente**, eu quero abrir e editar arquivos no programa que já uso e ter as alterações salvas na pasta automaticamente.
- Como **cliente**, eu quero saber se alguém já está editando um arquivo para não perder o meu trabalho nem o do outro.
- Como **cliente**, eu quero ser avisado com antecedência quando uma pasta for encerrada para copiar o que precisar.
- Como **cliente**, eu quero copiar os arquivos ao sair de uma pasta para manter uma cópia do material.
- Como **cliente**, eu quero ver o progresso das cópias e poder cancelá-las para controlar transferências grandes.
- Como **cliente**, eu quero escolher o que fazer com arquivos de nome repetido para não substituir nada sem querer.
- Como **cliente**, eu quero arrastar e soltar arquivos na janela do DriveLan para copiar com rapidez.
- Como **cliente**, eu quero que minha alteração seja guardada se o servidor cair para não perder o trabalho que estava fazendo.

### Administrador do sistema

- Como **administrador do sistema**, eu quero acessar uma janela especial com a chave do computador para resolver problemas que o usuário não consegue resolver sozinho.
- Como **administrador do sistema**, eu quero definir um PIN temporário para um usuário bloqueado para que ele volte a usar o app sem perder suas pastas.
- Como **administrador do sistema**, eu quero consultar e limpar os logs de erros para diagnosticar problemas.
- Como **administrador do sistema**, eu quero consultar a auditoria de todas as pastas do computador para investigar ocorrências.
- Como **administrador do sistema**, eu quero manter os dados ao reinstalar o app para trocar a chave sem prejudicar os usuários.

---

## 11. Critérios de Aceitação

### Cadastro e login

- [ ] O usuário consegue criar uma conta informando nome e PIN de 4 dígitos.
- [ ] O sistema impede o cadastro com nome já existente no computador ou com PIN diferente de 4 dígitos, exibindo mensagem clara.
- [ ] O login é solicitado toda vez que a janela do app é aberta.
- [ ] Após 5 erros seguidos de PIN, o sistema exibe a mensagem definida, desativa a conta e as pastas do usuário, revoga os acessos dele como cliente, preserva os arquivos e registra tudo na auditoria.
- [ ] Um usuário com PIN temporário é obrigado a definir um novo PIN antes de usar o app.
- [ ] A alteração de nome fica registrada, e a auditoria passa a mostrar o nome atual com o anterior entre parênteses.
- [ ] O sistema só permite excluir a própria conta se o usuário não for dono de nenhuma pasta, e exige o PIN para confirmar.

### Rede e lista de pastas

- [ ] O dashboard mostra o nome da rede (ou "Rede cabeada"), o IP do computador e a faixa da rede.
- [ ] Com mais de uma placa de rede, o app usa a principal e permite trocá-la nas configurações. Placas de VPN são ignoradas por padrão.
- [ ] A lista mostra todas as pastas do DriveLan na rede, com nome, dono@host, status e situação de acesso.
- [ ] O usuário consegue adicionar manualmente um servidor que não apareceu na lista.

### Criação e gestão de pastas

- [ ] O app sempre cria uma nova pasta ao criar um compartilhamento.
- [ ] O local sugerido fica no disco com mais espaço livre, e o app não permite usar nenhum dos locais proibidos: raiz do disco, pastas do sistema e de programas, pasta inteira do perfil, dentro de outra pasta compartilhada, unidades removíveis e unidades de rede.
- [ ] O app impede criar duas pastas com o mesmo nome no mesmo computador.
- [ ] O app sugere um PIN de 6 dígitos numéricos e aceita a edição pelo dono, desde que continue com 6 dígitos numéricos.
- [ ] O limite sugerido é de 10% do espaço livre, e o app não aceita limite acima de 80% do espaço livre.
- [ ] O app impede definir um limite abaixo do espaço já ocupado.
- [ ] A troca do PIN não desconecta quem já tem acesso.
- [ ] A pasta continua disponível na rede com a janela do app fechada e com qualquer pessoa logada no computador.

### Acesso de clientes

- [ ] O cliente consegue entrar numa pasta com o PIN correto e passa a vê-la entre as pastas que acessa.
- [ ] Após 5 erros de PIN, aquele computador fica impedido de tentar entrar na pasta por 15 minutos, e o dono é notificado.
- [ ] Um usuário bloqueado não consegue entrar mesmo com o PIN correto.
- [ ] Outro usuário logado no mesmo computador precisa digitar o PIN da pasta.
- [ ] O cliente é reconectado automaticamente após reiniciar o computador ou quando o servidor volta a ficar online.
- [ ] O estado da conexão (conectado, reconectando, offline, em encerramento, acesso revogado) é sempre visível.

### Remoção e bloqueio

- [ ] Ao remover um usuário, o app oferece as opções "Apenas desconectar" e "Remover e bloquear".
- [ ] O dono consegue ver a lista de bloqueados e desbloquear usuários.
- [ ] O cliente removido recebe a notificação de acesso revogado.
- [ ] Um usuário apenas desconectado consegue voltar a entrar com o PIN atual da pasta.

### Edição e conflitos

- [ ] O arquivo abre no programa padrão, e as alterações salvas chegam à pasta sem ação extra do usuário.
- [ ] Enquanto houver arquivo aberto, a janela do DriveLan mostra "arquivo em edição".
- [ ] Ao tentar abrir um arquivo em edição por outra pessoa, o app mostra quem está editando e oferece abrir somente para leitura.
- [ ] Em caso de conflito, as duas versões são mantidas, e o conflito é notificado e registrado na auditoria.
- [ ] Com o servidor offline, a alteração salva é guardada no computador do cliente, com a mensagem definida, e é enviada automaticamente quando o servidor volta.
- [ ] O aviso "em edição" termina ao fechar o arquivo ou após 10 minutos sem sinal do computador de quem editava, e o dono consegue liberar o arquivo manualmente.

### Transferências

- [ ] As cópias exibem uma barra de progresso e podem ser canceladas, e o arquivo incompleto é descartado ao cancelar.
- [ ] Com nome repetido no destino, o app oferece "Substituir", "Manter os dois" e "Pular", com a opção "aplicar a todos".
- [ ] É possível arrastar e soltar arquivos entre o computador e a janela do DriveLan, nos dois sentidos.

### Limite, lixeira e exclusões

- [ ] Um envio que ultrapassa o limite é recusado com a mensagem "Pasta cheia. Contate o dono da pasta.".
- [ ] O dono é notificado quando a pasta atinge 90% do limite.
- [ ] O espaço da lixeira é contado no limite.
- [ ] Se o disco do dono estiver sem espaço, o envio é recusado com a mensagem "Sem espaço no computador do dono. Contate o dono da pasta.", e o dono é notificado.
- [ ] Itens excluídos vão para a lixeira da pasta, e apenas o dono consegue restaurá-los ou esvaziar a lixeira.
- [ ] Itens com mais de 30 dias na lixeira são apagados automaticamente.

### Encerramento de pastas

- [ ] O app oferece "Desativar compartilhamento" e "Apagar pasta" como ações separadas.
- [ ] A confirmação mostra o número de clientes conectados e com acesso.
- [ ] O dono pode encerrar imediatamente ou escolher um prazo entre 5 minutos e 7 dias, com padrão de 1 hora.
- [ ] Durante o prazo, a pasta fica somente leitura e todos os conectados veem a contagem regressiva.
- [ ] Quem estava offline vê o aviso ao reconectar dentro do prazo, ou é informado do encerramento se o prazo já tiver acabado.
- [ ] Apagar exige digitar o nome da pasta, e os arquivos vão para a Lixeira do sistema.
- [ ] Uma pasta desativada pode ser reativada pelo dono, com os arquivos intactos.
- [ ] Ao reativar, o dono escolhe entre restaurar os acessos anteriores e exigir o PIN de todos, e a lista de bloqueados é mantida.
- [ ] O dono consegue cancelar ou alterar o prazo de um encerramento antes do fim, e os clientes conectados recebem "Encerramento cancelado".

### Saída do cliente

- [ ] Ao sair de uma pasta, o app oferece copiar os arquivos antes.
- [ ] A cópia só é feita com o servidor online, e o app informa o usuário quando não for possível.

### Auditoria

- [ ] Todos os eventos definidos em RN-41 são registrados com data, horário e nome@host.
- [ ] Leituras e downloads não aparecem na auditoria.
- [ ] O dono vê somente a auditoria das próprias pastas, e o administrador vê a de todas as pastas do computador.
- [ ] Registros com mais de 12 meses são removidos.
- [ ] A consulta permite filtrar por período, usuário e tipo de ação e buscar por nome de arquivo ou pasta, com os mais recentes primeiro.
- [ ] A auditoria de uma pasta apagada fica visível só para o administrador, por 1 mês.

### Administrador do sistema

- [ ] Shift + F12 abre a janela no estilo terminal, em primeiro plano.
- [ ] Com a chave correta, abre a janela de administração com as três abas definidas.
- [ ] Após 5 erros, a janela fica bloqueada por 15 minutos, e o bloqueio dobra a cada novo ciclo de 5 erros.
- [ ] A chave não aparece em nenhum lugar do app e não pode ser alterada por ele.
- [ ] O administrador consegue definir um PIN temporário, e a conta, as pastas e os acessos do usuário voltam automaticamente.
- [ ] O administrador não consegue abrir o conteúdo das pastas nem apagá-las.
- [ ] Toda ação do administrador aparece na auditoria.
- [ ] A reinstalação oferece manter os dados, com essa opção marcada por padrão, e nunca apaga os arquivos das pastas compartilhadas.

### Logs de erros

- [ ] Os logs são gravados em arquivos, um por dia, em subpastas por mês e ano.
- [ ] O registro de logs pode ser ligado e desligado pelo arquivo de configuração.
- [ ] Somente o administrador vê e limpa os logs no app.
- [ ] Logs com mais de 3 meses são apagados automaticamente.
- [ ] A consulta de logs permite escolher mês/ano e dia e buscar por texto.

### Notificações

- [ ] O cliente recebe notificações somente dos eventos definidos em 5.6.
- [ ] O dono recebe notificações somente dos eventos definidos em 5.6.
- [ ] Alterações comuns em arquivos não geram notificação.

---

## 12. Consultas, Relatórios e Indicadores

A primeira versão **não terá relatórios ou indicadores** no sentido gerencial, como gráficos ou estatísticas. Terá as consultas e listagens abaixo.

| Consulta | Informações exibidas | Quem acessa | Decisão que apoia |
|---|---|---|---|
| **Dashboard** | Conta logada, computador, rede, minhas pastas, pastas que acesso e pastas da rede | Usuário | Para onde ir e o que fazer |
| **Lista de pastas da rede** | Nome, dono@host, status e situação de acesso | Usuário | Em qual pasta entrar |
| **Usuários da pasta** | Quem tem acesso e quem está conectado agora | Dono | Quem remover ou bloquear; impacto de um encerramento |
| **Lista de bloqueados** | Usuários bloqueados naquela pasta | Dono | Quem desbloquear |
| **Uso do limite da pasta** | Espaço ocupado em relação ao limite | Dono | Se é preciso aumentar o limite ou limpar a pasta |
| **Lixeira da pasta** | Itens excluídos, quem excluiu e quando | Dono | O que restaurar ou esvaziar |
| **Auditoria da pasta** | Eventos com data, horário e usuário | Dono (próprias pastas) e administrador (todas do computador, inclusive pastas apagadas por até 1 mês) | Investigar alterações e responsabilidades |
| **Logs de erros** | Registros de erro por dia | Administrador | Diagnosticar falhas |

**Filtros definidos:**

- **Auditoria:** período, usuário (nome@host), tipo de ação e busca por nome de arquivo ou pasta, com os registros mais recentes primeiro.
- **Logs de erros:** escolha do mês/ano e do dia, com busca por texto dentro do log.

---

## 13. Permissões e Segurança Funcional

| Perfil | Pode fazer | Não pode fazer | Observações |
| ------ | ---------- | -------------- | ----------- |
| **Usuário** | Criar conta; fazer login; alterar o próprio nome e PIN; excluir a própria conta; ver o dashboard e a lista de pastas da rede; adicionar servidor manualmente | Ver ou gerenciar contas, pastas ou acessos de outros usuários do computador; recuperar o próprio PIN sozinho; ver logs de erros | Conta local; identificação na rede como nome@host |
| **Dono da pasta** | Criar pastas; definir e trocar PIN; definir limite; ver usuários; desconectar, bloquear e desbloquear; restaurar e esvaziar a lixeira; ver a auditoria das próprias pastas; desativar, reativar (restaurando acessos ou exigindo PIN) e apagar as próprias pastas; cancelar ou alterar encerramentos programados; liberar manualmente arquivos em edição; ler, editar e excluir o conteúdo | Compartilhar pasta já existente; usar locais proibidos; definir limite abaixo do ocupado ou acima de 80% do espaço livre; ver a auditoria de pastas de outros donos; consultar a auditoria das próprias pastas depois de apagadas | Pastas funcionam em segundo plano enquanto o computador estiver ligado |
| **Cliente** | Entrar em pastas com PIN; ler, abrir, editar, copiar, renomear, mover e excluir o conteúdo; sair com opção de cópia | Gerenciar a pasta (PIN, limite, usuários, encerramento); restaurar ou esvaziar a lixeira; ver a auditoria; entrar se estiver bloqueado; editar durante o prazo de encerramento; enviar além do limite | Mesmo poder para todos os clientes na v1 |
| **Administrador do sistema** | Acessar a janela especial com a chave; ver e limpar logs de erros; ver a auditoria de todas as pastas do computador, inclusive de pastas apagadas por até 1 mês; definir PIN temporário e reativar usuários | Ver ou alterar a chave pelo app; abrir o conteúdo das pastas; apagar pastas; desativar contas ou pastas de outros; atuar em outros computadores | Toda ação é registrada na auditoria; chave própria de cada computador |

---

## 14. Limitações da Primeira Versão

- **Sem unidade virtual:** os arquivos são acessados apenas pela janela do DriveLan, e não pelo explorador de arquivos como um disco `Z:`.
- **Sem acesso offline:** se o computador do dono estiver desligado, a pasta fica indisponível. A cópia ao sair também exige o servidor ligado. A única exceção é a alteração de um arquivo que já estava aberto: ela é guardada no computador do cliente e enviada quando o servidor voltar.
- **Contas locais:** cada computador tem as próprias contas, e não existe uma conta única válida na rede inteira.
- **Administrador local:** o administrador atua apenas no computador onde digitou a chave. O TI precisa guardar a chave de cada computador.
- **Permissões iguais para todos os clientes:** não há acesso somente leitura por usuário, exceto durante o prazo de encerramento.
- **Descoberta limitada à mesma rede:** pastas em outros segmentos da rede só podem ser acessadas pela adição manual do servidor.
- **Edição sem colaboração em tempo real:** se duas pessoas editarem o mesmo arquivo, há aviso e cópia de conflito, mas não há mesclagem das alterações.
- **Sem recuperação de PIN pelo próprio usuário:** só o administrador do sistema resolve.
- **Plataformas:** apenas Windows e Linux; sem macOS e sem celular.
- **Sem integração** com diretórios corporativos (Active Directory/LDAP) nem com serviços de nuvem.
- **Sem relatórios gerenciais;** apenas as consultas e listagens descritas na seção 12.

---

## 15. Pontos Pendentes Antes do FSD

Não foram identificadas dúvidas funcionais pendentes para a criação do FSD.

Os 14 pontos pendentes da versão anterior foram resolvidos com o usuário:

| # | Ponto | Decisão | Onde está registrado |
|---|---|---|---|
| 1 | Recursos de transferência | Barra de progresso com cancelamento, tratamento de nome repetido e arrastar e soltar entram na v1 | RN-62 a RN-64 |
| 2 | Servidor cai durante uma edição | A alteração é guardada no computador do cliente e enviada automaticamente quando o servidor volta | RN-65 |
| 3 | Aviso "em edição" que não termina | Termina ao fechar o arquivo, após 10 minutos sem sinal ou por liberação manual do dono | RN-66 |
| 4 | Reativação de pasta pelo dono | O dono escolhe restaurar os acessos ou exigir PIN; a lista de bloqueados é mantida | RN-57 |
| 5 | Cancelamento do encerramento | O dono pode cancelar ou alterar o prazo; os clientes recebem "Encerramento cancelado" | RN-60 |
| 6 | Tentativas erradas na chave | Bloqueio de 15 minutos após 5 erros, dobrando a cada novo ciclo | RN-58 |
| 7 | Locais proibidos para a pasta | Lista definida | RN-15 |
| 8 | Limite e espaço em disco | Sugestão de 10% do espaço livre; máximo de 80%; regra dos 5 GB removida; envio recusado se o disco encher | RN-19, RN-20 e RN-56 |
| 9 | Filtros de auditoria e logs | Filtros definidos | Seção 12 |
| 10 | Auditoria após apagar a pasta | Consultável por 1 mês, somente pelo administrador | RN-61 |
| 11 | Prazo dos logs | Fixo em 3 meses | RN-55 |
| 12 | Texto da mensagem dos 5 erros | "Conta bloqueada após 5 tentativas incorretas. Procure o Administrador do Aplicativo para redefinir seu PIN." | RN-06 |
| 13 | "Apenas desconectar" | O usuário pode voltar a qualquer momento com o PIN atual | RN-59 |
| 14 | Licença | GPLv3 | Seção 1 |

**Observação para o FSD (não funcional):** conferir a compatibilidade da licença GPLv3 com as dependências que forem escolhidas.

---

## 16. Resumo Final do PRD

**O que será construído:** o DriveLan, um aplicativo desktop de código aberto, para Windows e Linux, que permite criar pastas compartilhadas na rede local e acessar pastas de outras pessoas, sem nuvem e sem o compartilhamento nativo do Windows.

**Quem usará:** pessoas em ambientes corporativos, escritórios, laboratórios e salas de aula. Cada uma usa uma conta local e pode atuar como dona de pasta, como cliente ou das duas formas. O TI usa a chave de segurança de cada computador como administrador de último recurso.

**Principais funcionalidades:**
- contas locais com PIN e bloqueio após 5 erros;
- descoberta automática das pastas na rede, com adição manual;
- dashboard;
- criação de pastas com PIN de 6 dígitos e limite de tamanho;
- controle de usuários, com desconexão e bloqueio;
- transferências com barra de progresso, cancelamento, tratamento de nomes repetidos e arrastar e soltar;
- edição de arquivos no programa padrão, com aviso de edição, cópia de conflito e proteção contra queda do servidor;
- lixeira de 30 dias;
- auditoria de 12 meses;
- encerramento de pastas com prazo e contagem regressiva;
- notificações de eventos importantes;
- logs de erros;
- janela de administrador por Shift + F12.

**Fora da primeira versão:** unidade virtual, permissões por usuário, pastas ocultas, bloqueio de cópia, busca, histórico de versões, acesso offline, administração remota, interface web, macOS, celular e integrações corporativas.

**Pontos a confirmar:** nenhum ponto funcional pendente. Os 14 pontos da versão anterior foram resolvidos (ver seção 15).

**Pronto para o FSD?** **Sim.** O escopo, os perfis, as regras, os fluxos e os critérios de aceitação estão definidos e consistentes. Fica apenas a observação não funcional de conferir a compatibilidade da licença GPLv3 com as dependências.

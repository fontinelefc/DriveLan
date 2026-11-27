-- DriveLan — migration 0001: estrutura inicial completa do banco (FSD 11.2 e 11.3).
--
-- Regras:
-- - nunca editar esta migration depois de aplicada: criar 0002_<descricao>.sql;
-- - datas em TEXT, ISO 8601 UTC com milissegundos (ex.: 2026-11-12T13:45:10.123Z);
-- - situações em TEXT com CHECK listando os valores permitidos;
-- - *_normalizado = nome em Unicode NFC com casefold() (calculado pelo serviço);
-- - sem PRAGMAs aqui: a conexão já os aplica (FSD 11.1).

-- ---------------------------------------------------------------- controle das migrations

CREATE TABLE schema_migracoes (
    versao      INTEGER PRIMARY KEY,
    nome        TEXT NOT NULL,
    checksum    TEXT NOT NULL,
    aplicada_em TEXT NOT NULL
);

-- ---------------------------------------------------------------- instalação (linha única)

CREATE TABLE instalacao (
    id               INTEGER PRIMARY KEY CHECK (id = 1),
    instalacao_id    TEXT NOT NULL UNIQUE,
    host_nome        TEXT NOT NULL,
    chave_admin_hash TEXT NOT NULL,
    versao_app       TEXT NOT NULL,
    criado_em        TEXT NOT NULL,
    atualizado_em    TEXT NOT NULL
);

-- Bloqueio crescente da janela da chave de segurança (RN-58), linha única.
CREATE TABLE admin_controle (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    erros_no_ciclo  INTEGER NOT NULL DEFAULT 0 CHECK (erros_no_ciclo BETWEEN 0 AND 4),
    ciclos_bloqueio INTEGER NOT NULL DEFAULT 0 CHECK (ciclos_bloqueio >= 0),
    bloqueado_ate   TEXT NULL,
    atualizado_em   TEXT NOT NULL
);

-- ---------------------------------------------------------------- identidades e contas

CREATE TABLE identidade (
    id             INTEGER PRIMARY KEY,
    instalacao_id  TEXT NOT NULL,
    conta_uuid     TEXT NOT NULL,
    host_nome      TEXT NOT NULL,
    nome_atual     TEXT NOT NULL,
    nome_anterior  TEXT NULL,
    criado_em      TEXT NOT NULL,
    atualizado_em  TEXT NOT NULL,
    UNIQUE (instalacao_id, conta_uuid)
);

CREATE TABLE identidade_nome_historico (
    id            INTEGER PRIMARY KEY,
    identidade_id INTEGER NOT NULL REFERENCES identidade (id) ON DELETE CASCADE,
    nome_anterior TEXT NOT NULL,
    nome_novo     TEXT NOT NULL,
    alterado_em   TEXT NOT NULL
);

CREATE INDEX idx_identidade_nome_historico_identidade
    ON identidade_nome_historico (identidade_id, alterado_em);

CREATE TABLE conta (
    id               INTEGER PRIMARY KEY,
    uuid             TEXT NOT NULL UNIQUE,
    identidade_id    INTEGER NOT NULL UNIQUE REFERENCES identidade (id),
    nome             TEXT NOT NULL,
    nome_normalizado TEXT NOT NULL,
    pin_hash         TEXT NOT NULL,
    situacao         TEXT NOT NULL CHECK (situacao IN ('ativa', 'desativada', 'excluida')),
    pin_temporario   INTEGER NOT NULL DEFAULT 0 CHECK (pin_temporario IN (0, 1)),
    erros_pin        INTEGER NOT NULL DEFAULT 0 CHECK (erros_pin >= 0),
    desativada_em    TEXT NULL,
    excluida_em      TEXT NULL,
    criado_em        TEXT NOT NULL,
    atualizado_em    TEXT NOT NULL
);

-- Permite reutilizar o nome de uma conta excluída (RN-03).
CREATE UNIQUE INDEX uq_conta_nome_normalizado
    ON conta (nome_normalizado) WHERE situacao <> 'excluida';
CREATE INDEX idx_conta_situacao ON conta (situacao);

-- ---------------------------------------------------------------- pastas hospedadas

CREATE TABLE pasta (
    id                      INTEGER PRIMARY KEY,
    uuid                    TEXT NOT NULL UNIQUE,
    conta_dono_id           INTEGER NOT NULL REFERENCES conta (id) ON DELETE RESTRICT,
    nome                    TEXT NOT NULL,
    nome_normalizado        TEXT NOT NULL,
    caminho                 TEXT NOT NULL,
    caminho_normalizado     TEXT NOT NULL,
    so_dono                 TEXT NOT NULL,
    pin_hash                TEXT NOT NULL,
    limite_bytes            INTEGER NOT NULL CHECK (limite_bytes > 0),
    bytes_conteudo          INTEGER NOT NULL DEFAULT 0 CHECK (bytes_conteudo >= 0),
    bytes_lixeira           INTEGER NOT NULL DEFAULT 0 CHECK (bytes_lixeira >= 0),
    situacao                TEXT NOT NULL
        CHECK (situacao IN ('ativa', 'em_encerramento', 'desativada', 'apagada')),
    desativada_por_bloqueio INTEGER NOT NULL DEFAULT 0 CHECK (desativada_por_bloqueio IN (0, 1)),
    aviso_90_enviado        INTEGER NOT NULL DEFAULT 0 CHECK (aviso_90_enviado IN (0, 1)),
    lixeira_so_pendente     INTEGER NOT NULL DEFAULT 0 CHECK (lixeira_so_pendente IN (0, 1)),
    desativada_em           TEXT NULL,
    apagada_em              TEXT NULL,
    criado_em               TEXT NOT NULL,
    atualizado_em           TEXT NOT NULL
);

CREATE UNIQUE INDEX uq_pasta_nome_normalizado
    ON pasta (nome_normalizado) WHERE situacao <> 'apagada';
CREATE UNIQUE INDEX uq_pasta_caminho_normalizado
    ON pasta (caminho_normalizado) WHERE situacao <> 'apagada';
CREATE INDEX idx_pasta_dono_situacao ON pasta (conta_dono_id, situacao);
CREATE INDEX idx_pasta_situacao_apagada_em ON pasta (situacao, apagada_em);
CREATE INDEX idx_pasta_lixeira_so_pendente ON pasta (lixeira_so_pendente, so_dono);

CREATE TABLE pasta_encerramento (
    id            INTEGER PRIMARY KEY,
    pasta_id      INTEGER NOT NULL REFERENCES pasta (id) ON DELETE CASCADE,
    tipo          TEXT NOT NULL CHECK (tipo IN ('desativar', 'apagar')),
    iniciado_em   TEXT NOT NULL,
    termina_em    TEXT NOT NULL,
    situacao      TEXT NOT NULL CHECK (situacao IN ('programado', 'concluido', 'cancelado')),
    criado_em     TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);

-- No máximo um encerramento programado por pasta.
CREATE UNIQUE INDEX uq_pasta_encerramento_programado
    ON pasta_encerramento (pasta_id) WHERE situacao = 'programado';
CREATE INDEX idx_pasta_encerramento_situacao_termina
    ON pasta_encerramento (situacao, termina_em);

CREATE TABLE acesso (
    id                INTEGER PRIMARY KEY,
    pasta_id          INTEGER NOT NULL REFERENCES pasta (id) ON DELETE CASCADE,
    identidade_id     INTEGER NOT NULL REFERENCES identidade (id),
    token_hash        TEXT NOT NULL UNIQUE,
    situacao          TEXT NOT NULL CHECK (situacao IN ('ativo', 'removido')),
    motivo_remocao    TEXT NULL CHECK (
        motivo_remocao IS NULL OR motivo_remocao IN (
            'desconectado', 'bloqueado', 'saiu', 'pin_exigido_na_reativacao', 'conta_excluida'
        )
    ),
    concedido_em      TEXT NOT NULL,
    ultima_conexao_em TEXT NULL,
    removido_em       TEXT NULL,
    criado_em         TEXT NOT NULL,
    atualizado_em     TEXT NOT NULL
);

CREATE UNIQUE INDEX uq_acesso_ativo
    ON acesso (pasta_id, identidade_id) WHERE situacao = 'ativo';
CREATE INDEX idx_acesso_pasta_situacao ON acesso (pasta_id, situacao);

CREATE TABLE bloqueio_dono (
    id              INTEGER PRIMARY KEY,
    pasta_id        INTEGER NOT NULL REFERENCES pasta (id) ON DELETE CASCADE,
    identidade_id   INTEGER NOT NULL REFERENCES identidade (id),
    situacao        TEXT NOT NULL CHECK (situacao IN ('ativo', 'desbloqueado')),
    bloqueado_em    TEXT NOT NULL,
    desbloqueado_em TEXT NULL,
    criado_em       TEXT NOT NULL,
    atualizado_em   TEXT NOT NULL
);

CREATE UNIQUE INDEX uq_bloqueio_dono_ativo
    ON bloqueio_dono (pasta_id, identidade_id) WHERE situacao = 'ativo';
CREATE INDEX idx_bloqueio_dono_pasta_situacao ON bloqueio_dono (pasta_id, situacao);

-- Bloqueio temporário de 15 minutos após 5 PINs de pasta incorretos (RN-27).
CREATE TABLE bloqueio_pin_pasta (
    id             INTEGER PRIMARY KEY,
    pasta_id       INTEGER NOT NULL REFERENCES pasta (id) ON DELETE CASCADE,
    tipo_chave     TEXT NOT NULL CHECK (tipo_chave IN ('instalacao', 'ip')),
    valor_chave    TEXT NOT NULL,
    erros          INTEGER NOT NULL DEFAULT 0 CHECK (erros >= 0),
    bloqueado_ate  TEXT NULL,
    ultimo_erro_em TEXT NOT NULL,
    criado_em      TEXT NOT NULL,
    atualizado_em  TEXT NOT NULL,
    UNIQUE (pasta_id, tipo_chave, valor_chave)
);

CREATE TABLE lixeira_item (
    id                         INTEGER PRIMARY KEY,
    uuid                       TEXT NOT NULL UNIQUE,
    pasta_id                   INTEGER NOT NULL REFERENCES pasta (id) ON DELETE CASCADE,
    caminho_original           TEXT NOT NULL,
    tipo                       TEXT NOT NULL CHECK (tipo IN ('arquivo', 'pasta')),
    tamanho_bytes              INTEGER NOT NULL CHECK (tamanho_bytes >= 0),
    excluido_por_identidade_id INTEGER NOT NULL REFERENCES identidade (id),
    excluido_em                TEXT NOT NULL,
    situacao                   TEXT NOT NULL
        CHECK (situacao IN ('na_lixeira', 'restaurado', 'esvaziado', 'expirado')),
    finalizado_em              TEXT NULL,
    criado_em                  TEXT NOT NULL,
    atualizado_em              TEXT NOT NULL
);

CREATE INDEX idx_lixeira_item_pasta_situacao_excluido
    ON lixeira_item (pasta_id, situacao, excluido_em);
CREATE INDEX idx_lixeira_item_situacao_excluido ON lixeira_item (situacao, excluido_em);
CREATE INDEX idx_lixeira_item_situacao_finalizado ON lixeira_item (situacao, finalizado_em);

CREATE TABLE arquivo_em_edicao (
    id                  INTEGER PRIMARY KEY,
    uuid                TEXT NOT NULL UNIQUE,
    pasta_id            INTEGER NOT NULL REFERENCES pasta (id) ON DELETE CASCADE,
    caminho             TEXT NOT NULL,
    caminho_normalizado TEXT NOT NULL,
    identidade_id       INTEGER NOT NULL REFERENCES identidade (id),
    instalacao_id       TEXT NOT NULL,
    versao_base         TEXT NOT NULL,
    iniciado_em         TEXT NOT NULL,
    ultimo_sinal_em     TEXT NOT NULL,
    criado_em           TEXT NOT NULL,
    atualizado_em       TEXT NOT NULL
);

CREATE UNIQUE INDEX uq_arquivo_em_edicao_caminho
    ON arquivo_em_edicao (pasta_id, caminho_normalizado);
CREATE INDEX idx_arquivo_em_edicao_ultimo_sinal ON arquivo_em_edicao (ultimo_sinal_em);

-- ---------------------------------------------------------------- auditoria (somente inclusão)

CREATE TABLE auditoria (
    id                INTEGER PRIMARY KEY,
    pasta_id          INTEGER NULL REFERENCES pasta (id) ON DELETE CASCADE,
    pasta_nome        TEXT NULL,
    ator_tipo         TEXT NOT NULL
        CHECK (ator_tipo IN ('usuario', 'administrador', 'sistema', 'computador')),
    identidade_id     INTEGER NULL REFERENCES identidade (id),
    ator_rotulo       TEXT NULL,
    acao              TEXT NOT NULL,
    alvo_caminho      TEXT NULL,
    alvo_caminho_novo TEXT NULL,
    detalhes          TEXT NULL CHECK (detalhes IS NULL OR json_valid(detalhes)),
    ocorrido_em       TEXT NOT NULL,
    CHECK (ator_tipo <> 'usuario' OR identidade_id IS NOT NULL)
);

CREATE INDEX idx_auditoria_ocorrido ON auditoria (ocorrido_em DESC, id DESC);
CREATE INDEX idx_auditoria_pasta_ocorrido ON auditoria (pasta_id, ocorrido_em DESC, id DESC);
CREATE INDEX idx_auditoria_identidade_ocorrido ON auditoria (identidade_id, ocorrido_em DESC);
CREATE INDEX idx_auditoria_acao_ocorrido ON auditoria (acao, ocorrido_em DESC);
CREATE INDEX idx_auditoria_pasta_identidade ON auditoria (pasta_id, identidade_id);

-- Busca por nome de arquivo ou pasta (FSD 11.2 e 22.2). Se o SQLite em uso não suportar o
-- tokenizador trigram, o executor de migrations pula este bloco e a consulta usa LIKE.
-- drivelan:fts5-trigram:inicio
CREATE VIRTUAL TABLE auditoria_busca USING fts5 (
    alvo_caminho,
    alvo_caminho_novo,
    pasta_nome,
    content = 'auditoria',
    content_rowid = 'id',
    tokenize = 'trigram'
);

CREATE TRIGGER auditoria_busca_inclusao AFTER INSERT ON auditoria BEGIN
    INSERT INTO auditoria_busca (rowid, alvo_caminho, alvo_caminho_novo, pasta_nome)
    VALUES (new.id, new.alvo_caminho, new.alvo_caminho_novo, new.pasta_nome);
END;

CREATE TRIGGER auditoria_busca_exclusao AFTER DELETE ON auditoria BEGIN
    INSERT INTO auditoria_busca (auditoria_busca, rowid, alvo_caminho, alvo_caminho_novo, pasta_nome)
    VALUES ('delete', old.id, old.alvo_caminho, old.alvo_caminho_novo, old.pasta_nome);
END;
-- drivelan:fts5-trigram:fim

-- ---------------------------------------------------------------- lado cliente

CREATE TABLE cliente_servidor_manual (
    id            INTEGER PRIMARY KEY,
    conta_id      INTEGER NOT NULL REFERENCES conta (id) ON DELETE CASCADE,
    endereco      TEXT NOT NULL,
    porta         INTEGER NOT NULL CHECK (porta BETWEEN 1 AND 65535),
    criado_em     TEXT NOT NULL,
    atualizado_em TEXT NOT NULL,
    UNIQUE (conta_id, endereco, porta)
);

CREATE TABLE cliente_servidor_conhecido (
    id                  INTEGER PRIMARY KEY,
    instalacao_id       TEXT NOT NULL UNIQUE,
    host_nome           TEXT NOT NULL,
    ultimo_endereco     TEXT NULL,
    ultima_porta        INTEGER NULL CHECK (ultima_porta IS NULL OR ultima_porta BETWEEN 1 AND 65535),
    local               INTEGER NOT NULL DEFAULT 0 CHECK (local IN (0, 1)),
    primeiro_contato_em TEXT NOT NULL,
    ultimo_contato_em   TEXT NOT NULL,
    criado_em           TEXT NOT NULL,
    atualizado_em       TEXT NOT NULL
);

CREATE INDEX idx_cliente_servidor_conhecido_host ON cliente_servidor_conhecido (host_nome);
-- No máximo um registro da própria instalação (FSD 5.2.1).
CREATE UNIQUE INDEX uq_cliente_servidor_conhecido_local
    ON cliente_servidor_conhecido (local) WHERE local = 1;

CREATE TABLE cliente_acesso (
    id                    INTEGER PRIMARY KEY,
    conta_id              INTEGER NOT NULL REFERENCES conta (id) ON DELETE CASCADE,
    servidor_conhecido_id INTEGER NOT NULL REFERENCES cliente_servidor_conhecido (id),
    pasta_uuid            TEXT NOT NULL,
    pasta_nome            TEXT NOT NULL,
    dono_rotulo           TEXT NOT NULL,
    token                 TEXT NOT NULL,
    situacao              TEXT NOT NULL CHECK (
        situacao IN (
            'ativo', 'suspenso', 'identidade_alterada', 'revogado', 'desativada', 'encerrada'
        )
    ),
    concedido_em          TEXT NOT NULL,
    ultima_conexao_em     TEXT NULL,
    criado_em             TEXT NOT NULL,
    atualizado_em         TEXT NOT NULL,
    UNIQUE (conta_id, servidor_conhecido_id, pasta_uuid)
);

CREATE INDEX idx_cliente_acesso_conta_situacao ON cliente_acesso (conta_id, situacao);

CREATE TABLE cliente_alteracao_pendente (
    id                INTEGER PRIMARY KEY,
    cliente_acesso_id INTEGER NOT NULL REFERENCES cliente_acesso (id) ON DELETE CASCADE,
    caminho_remoto    TEXT NOT NULL,
    versao_base       TEXT NOT NULL,
    arquivo_local     TEXT NOT NULL,
    so_usuario        TEXT NOT NULL,
    guardada_em       TEXT NOT NULL,
    tentativas        INTEGER NOT NULL DEFAULT 0 CHECK (tentativas >= 0),
    ultimo_erro       TEXT NULL,
    criado_em         TEXT NOT NULL,
    atualizado_em     TEXT NOT NULL,
    UNIQUE (cliente_acesso_id, caminho_remoto)
);

CREATE INDEX idx_cliente_alteracao_pendente_so_usuario ON cliente_alteracao_pendente (so_usuario);

CREATE TABLE cliente_edicao_ativa (
    id                  INTEGER PRIMARY KEY,
    conta_id            INTEGER NOT NULL REFERENCES conta (id) ON DELETE CASCADE,
    cliente_acesso_id   INTEGER NULL REFERENCES cliente_acesso (id) ON DELETE CASCADE,
    pasta_id            INTEGER NULL REFERENCES pasta (id) ON DELETE CASCADE,
    caminho_remoto      TEXT NOT NULL,
    trava_uuid          TEXT NOT NULL,
    versao_base         TEXT NOT NULL,
    local_mtime_envio   INTEGER NULL,
    local_tamanho_envio INTEGER NULL CHECK (local_tamanho_envio IS NULL OR local_tamanho_envio >= 0),
    arquivo_local       TEXT NOT NULL,
    so_usuario          TEXT NOT NULL,
    iniciada_em         TEXT NOT NULL,
    criado_em           TEXT NOT NULL,
    atualizado_em       TEXT NOT NULL,
    -- Exatamente um entre pasta remota (cliente_acesso_id) e pasta própria (pasta_id).
    CHECK ((cliente_acesso_id IS NULL) <> (pasta_id IS NULL))
);

CREATE UNIQUE INDEX uq_cliente_edicao_ativa_acesso
    ON cliente_edicao_ativa (conta_id, cliente_acesso_id, caminho_remoto);
CREATE UNIQUE INDEX uq_cliente_edicao_ativa_pasta
    ON cliente_edicao_ativa (conta_id, pasta_id, caminho_remoto);
CREATE INDEX idx_cliente_edicao_ativa_so_usuario ON cliente_edicao_ativa (so_usuario);

-- ---------------------------------------------------------------- dados iniciais obrigatórios

INSERT INTO admin_controle (id, erros_no_ciclo, ciclos_bloqueio, bloqueado_ate, atualizado_em)
VALUES (1, 0, 0, NULL, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'));

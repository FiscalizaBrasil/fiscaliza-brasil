#!/usr/bin/env python
"""
Script de inicialização do banco de dados.
Cria os schemas e tabelas necessários se não existirem,
e importa automaticamente todos os dados JSON já baixados em data/.
"""

import sys
import os
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from database import db
except ImportError as e:
    logging.error(f"Error importing database module: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def ensure_schema(cursor):
    """Cria todas as tabelas necessárias se não existirem."""
    logging.info("Criando schemas e tabelas...")

    # --- Schema camara ---
    cursor.execute("CREATE SCHEMA IF NOT EXISTS camara;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS camara.legislaturas (
            id INTEGER PRIMARY KEY,
            data_inicio DATE NOT NULL,
            data_fim DATE
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS camara.deputados (
            id INTEGER PRIMARY KEY,
            nome_civil TEXT NOT NULL,
            cpf VARCHAR(14) UNIQUE,
            sexo CHAR(1),
            data_nascimento DATE,
            data_falecimento DATE,
            uf_nascimento CHAR(2),
            municipio_nascimento TEXT,
            escolaridade TEXT,
            email TEXT
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS camara.deputados_mandatos (
            id VARCHAR(20) PRIMARY KEY,
            deputado_id INTEGER NOT NULL REFERENCES camara.deputados(id),
            legislatura_id INTEGER NOT NULL REFERENCES camara.legislaturas(id),
            nome_eleitoral TEXT NOT NULL,
            sigla_partido VARCHAR(20),
            sigla_uf CHAR(2),
            url_foto TEXT,
            email TEXT,
            situacao TEXT,
            condicao_eleitoral TEXT,
            data_inicio_mandato DATE,
            data_fim_mandato DATE
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS camara.deputados_despesas (
            id SERIAL PRIMARY KEY,
            ano INTEGER NOT NULL,
            mes INTEGER NOT NULL,
            tipo_despesa TEXT NOT NULL,
            cod_documento VARCHAR(50) NOT NULL,
            tipo_documento TEXT,
            cod_tipo_documento INTEGER,
            data_documento DATE NOT NULL,
            num_documento TEXT NOT NULL,
            valor_documento NUMERIC(15,2) NOT NULL,
            url_documento TEXT,
            nome_fornecedor TEXT NOT NULL,
            cnpj_cpf_fornecedor VARCHAR(14),
            valor_liquido NUMERIC(15,2) NOT NULL,
            valor_glosa NUMERIC(15,2) DEFAULT 0.0,
            num_ressarcimento TEXT,
            cod_lote INTEGER NOT NULL,
            parcela INTEGER DEFAULT 0,
            mandato_id VARCHAR(20) NOT NULL REFERENCES camara.deputados_mandatos(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(cod_documento, num_documento, data_documento, valor_documento, nome_fornecedor)
        );
    """)
    
    # Migra coluna cod_documento de BIGINT para VARCHAR(50) se necessário
    cursor.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'camara'
                  AND table_name = 'deputados_despesas'
                  AND column_name = 'cod_documento'
                  AND data_type = 'bigint'
            ) THEN
                ALTER TABLE camara.deputados_despesas 
                ALTER COLUMN cod_documento TYPE VARCHAR(50);
            END IF;
        END
        $$;
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS camara.proposicoes (
            id INTEGER PRIMARY KEY,
            sigla_tipo VARCHAR(10),
            cod_tipo INTEGER,
            numero INTEGER,
            ano INTEGER,
            ementa TEXT,
            data_apresentacao TIMESTAMP,
            descricao_tipo TEXT,
            ementa_detalhada TEXT,
            keywords TEXT,
            url_inteiro_teor TEXT,
            urn_final TEXT,
            texto TEXT,
            justificativa TEXT,
            uri TEXT,
            uri_orgao_numerador TEXT,
            uri_prop_principal TEXT,
            uri_prop_anterior TEXT,
            uri_prop_posterior TEXT
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS camara.votacoes (
            id VARCHAR(20) PRIMARY KEY,
            uri TEXT,
            data DATE,
            data_hora_registro TIMESTAMP,
            sigla_orgao VARCHAR(20),
            uri_orgao TEXT,
            id_orgao INTEGER,
            uri_evento TEXT,
            id_evento INTEGER,
            descricao TEXT,
            aprovacao INTEGER,
            desc_ultima_abertura_votacao TEXT,
            data_hora_ultima_abertura_votacao TIMESTAMP
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS camara.votacoes_proposicoes (
            votacao_id VARCHAR(20) REFERENCES camara.votacoes(id),
            proposicao_id INTEGER REFERENCES camara.proposicoes(id),
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            UNIQUE(votacao_id, proposicao_id)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS camara.votacoes_votos (
            votacao_id VARCHAR(20) NOT NULL REFERENCES camara.votacoes(id),
            deputado_id INTEGER NOT NULL REFERENCES camara.deputados(id),
            tipo_voto TEXT NOT NULL,
            data_registro_voto TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            UNIQUE(votacao_id, deputado_id)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS camara.proposicoes_autores (
            id SERIAL PRIMARY KEY,
            proposicao_id INTEGER NOT NULL REFERENCES camara.proposicoes(id) ON DELETE CASCADE,
            deputado_id INTEGER REFERENCES camara.deputados(id) ON DELETE CASCADE,
            tipo_autor VARCHAR(50),
            ordem_assinatura INTEGER,
            proponente BOOLEAN DEFAULT FALSE,
            UNIQUE(proposicao_id, deputado_id)
        );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_proposicoes_autores_proposicao ON camara.proposicoes_autores(proposicao_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_proposicoes_autores_deputado ON camara.proposicoes_autores(deputado_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_proposicoes_ano ON camara.proposicoes(ano);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_proposicoes_sigla_tipo ON camara.proposicoes(sigla_tipo);")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS camara.summary_empresas_geral (
            legislatura_id INTEGER PRIMARY KEY,
            total_empresas INTEGER,
            total_pago NUMERIC(20,2),
            total_contratos INTEGER,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS camara.summary_empresas_ranking (
            id SERIAL PRIMARY KEY,
            legislatura_id INTEGER,
            rank INTEGER,
            cnpj_raiz TEXT,
            nome_completo TEXT,
            total_valor NUMERIC(20,2),
            qtd_contratos INTEGER,
            principais_partidos TEXT,
            percentual NUMERIC(10,2),
            nome_chave TEXT,
            UNIQUE(legislatura_id, rank)
        );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_camara_ranking_leg ON camara.summary_empresas_ranking(legislatura_id);")

    # --- Índices de performance para queries de perfil de deputado ---
    # Índice para acelerar JOIN de despesas com mandatos (mandato_id é VARCHAR)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deputados_despesas_mandato_id ON camara.deputados_despesas(mandato_id);")
    # Índice composto para acelerar a query principal de despesas por deputado (mais usado)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deputados_despesas_mandato_tipo ON camara.deputados_despesas(mandato_id, tipo_despesa);")
    # Índice para acelerar busca de despesas por ano/mês
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deputados_despesas_ano_mes ON camara.deputados_despesas(ano, mes);")
    # Índice para acelerar busca de mandatos por deputado
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deputados_mandatos_deputado_id ON camara.deputados_mandatos(deputado_id);")
    # Índice composto para acelerar filtros por legislatura
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deputados_mandatos_deputado_legislatura ON camara.deputados_mandatos(deputado_id, legislatura_id);")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS camara.deputados_historico (
            id SERIAL PRIMARY KEY,
            deputado_id INTEGER NOT NULL REFERENCES camara.deputados(id) ON DELETE CASCADE,
            data_hora TIMESTAMP NOT NULL,
            situacao TEXT,
            condicao_eleitoral TEXT,
            descricao_status TEXT,
            sigla_partido VARCHAR(20),
            sigla_uf CHAR(2),
            nome_eleitoral TEXT,
            url_foto TEXT,
            id_legislatura INTEGER,
            UNIQUE(deputado_id, data_hora)
        );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deputados_historico_deputado ON camara.deputados_historico(deputado_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deputados_historico_legislatura ON camara.deputados_historico(id_legislatura);")

    # --- Schema senado ---
    cursor.execute("CREATE SCHEMA IF NOT EXISTS senado;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS senado.legislatura (
            numero VARCHAR(10) PRIMARY KEY,
            data_inicio DATE,
            data_fim DATE
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS senado.parlamentar (
            codigo INTEGER PRIMARY KEY,
            codigo_publico INTEGER,
            nome_parlamentar VARCHAR(200) NOT NULL,
            nome_completo VARCHAR(200),
            sexo VARCHAR(20),
            url_foto TEXT,
            url_pagina TEXT,
            email VARCHAR(100),
            sigla_partido VARCHAR(20),
            uf CHAR(2),
            data_nascimento DATE,
            naturalidade VARCHAR(100),
            uf_naturalidade CHAR(2),
            endereco TEXT,
            telefones TEXT[]
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS senado.mandato (
            codigo_mandato VARCHAR(20) PRIMARY KEY,
            codigo_parlamentar INTEGER REFERENCES senado.parlamentar(codigo) ON DELETE CASCADE,
            uf CHAR(2),
            descricao_participacao VARCHAR(50),
            primeira_legislatura VARCHAR(10) NOT NULL REFERENCES senado.legislatura(numero),
            segunda_legislatura VARCHAR(10) NOT NULL DEFAULT '' REFERENCES senado.legislatura(numero),
            CONSTRAINT mandato_legislatura_check CHECK (primeira_legislatura IS NOT NULL AND TRIM(primeira_legislatura) != '')
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS senado.despesa_ceaps (
            id BIGSERIAL PRIMARY KEY,
            ano INTEGER NOT NULL,
            mes INTEGER NOT NULL,
            cod_senador INTEGER REFERENCES senado.parlamentar(codigo) ON DELETE CASCADE,
            nome_senador VARCHAR(200),
            tipo_despesa TEXT,
            cpf_cnpj VARCHAR(20),
            fornecedor TEXT,
            documento VARCHAR(50),
            data_despesa DATE,
            detalhamento TEXT,
            valor_reembolsado NUMERIC(10,2),
            tipo_documento VARCHAR(50),
            UNIQUE(ano, mes, cod_senador, documento, valor_reembolsado, fornecedor)
        );
    """);
    
    # Remove duplicatas existentes na senado.despesa_ceaps (mantém apenas uma por grupo)
    cursor.execute("""
        DELETE FROM senado.despesa_ceaps WHERE id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY ano, mes, cod_senador, COALESCE(documento,''), COALESCE(valor_reembolsado,0), COALESCE(fornecedor,'')
                    ORDER BY id
                ) as rn
                FROM senado.despesa_ceaps
            ) sub WHERE rn > 1
        );
    """);
    logging.info(f"Duplicatas removidas de senado.despesa_ceaps.")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS senado.materia (
            codigo INTEGER PRIMARY KEY,
            identificacao_processo VARCHAR(35),
            descricao_identificacao VARCHAR(100),
            sigla VARCHAR(50),
            numero VARCHAR(20),
            ano INTEGER,
            ementa TEXT,
            data DATE,
            -- Novos campos do endpoint /processo
            id_processo INTEGER,
            situacao_atual TEXT,
            data_situacao_atual DATE,
            tramitando BOOLEAN DEFAULT FALSE,
            url_documento TEXT,
            objetivo VARCHAR(50),
            tipo_conteudo TEXT,
            casa_identificadora VARCHAR(10),
            ente_identificador VARCHAR(10),
            indexacao TEXT,
            data_ultima_atualizacao TIMESTAMP
        );
    """);
    
    # Migração: adiciona colunas se não existirem (para banco existente)
    cursor.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'senado' AND table_name = 'materia' AND column_name = 'id_processo') THEN
                ALTER TABLE senado.materia ADD COLUMN id_processo INTEGER;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'senado' AND table_name = 'materia' AND column_name = 'situacao_atual') THEN
                ALTER TABLE senado.materia ADD COLUMN situacao_atual TEXT;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'senado' AND table_name = 'materia' AND column_name = 'data_situacao_atual') THEN
                ALTER TABLE senado.materia ADD COLUMN data_situacao_atual DATE;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'senado' AND table_name = 'materia' AND column_name = 'tramitando') THEN
                ALTER TABLE senado.materia ADD COLUMN tramitando BOOLEAN DEFAULT FALSE;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'senado' AND table_name = 'materia' AND column_name = 'url_documento') THEN
                ALTER TABLE senado.materia ADD COLUMN url_documento TEXT;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'senado' AND table_name = 'materia' AND column_name = 'objetivo') THEN
                ALTER TABLE senado.materia ADD COLUMN objetivo VARCHAR(50);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'senado' AND table_name = 'materia' AND column_name = 'tipo_conteudo') THEN
                ALTER TABLE senado.materia ADD COLUMN tipo_conteudo TEXT;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'senado' AND table_name = 'materia' AND column_name = 'casa_identificadora') THEN
                ALTER TABLE senado.materia ADD COLUMN casa_identificadora VARCHAR(10);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'senado' AND table_name = 'materia' AND column_name = 'ente_identificador') THEN
                ALTER TABLE senado.materia ADD COLUMN ente_identificador VARCHAR(10);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'senado' AND table_name = 'materia' AND column_name = 'indexacao') THEN
                ALTER TABLE senado.materia ADD COLUMN indexacao TEXT;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'senado' AND table_name = 'materia' AND column_name = 'data_ultima_atualizacao') THEN
                ALTER TABLE senado.materia ADD COLUMN data_ultima_atualizacao TIMESTAMP;
            END IF;
        END
        $$;
    """)
    
    # Índices para a tabela materia
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_senado_materia_ano ON senado.materia(ano);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_senado_materia_sigla ON senado.materia(sigla);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_senado_materia_situacao ON senado.materia(situacao_atual);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_senado_materia_tramitando ON senado.materia(tramitando);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_senado_materia_id_processo ON senado.materia(id_processo);")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS senado.autoria (
            id SERIAL PRIMARY KEY,
            codigo_parlamentar INTEGER REFERENCES senado.parlamentar(codigo) ON DELETE CASCADE,
            codigo_materia INTEGER REFERENCES senado.materia(codigo) ON DELETE CASCADE,
            autor_principal BOOLEAN,
            outros_autores BOOLEAN
        );
    """)

    # Atualiza a tabela autoria para aceitar autor_texto (fallback quando não há código)
    cursor.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'senado' AND table_name = 'autoria' AND column_name = 'autor_texto') THEN
                ALTER TABLE senado.autoria ADD COLUMN autor_texto TEXT;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'senado' AND table_name = 'autoria' AND column_name = 'sigla_partido_autor') THEN
                ALTER TABLE senado.autoria ADD COLUMN sigla_partido_autor VARCHAR(20);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'senado' AND table_name = 'autoria' AND column_name = 'uf_autor') THEN
                ALTER TABLE senado.autoria ADD COLUMN uf_autor CHAR(2);
            END IF;
        END
        $$;
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS senado.votacao_parlamentar (
            id SERIAL PRIMARY KEY,
            codigo_parlamentar INTEGER REFERENCES senado.parlamentar(codigo) ON DELETE CASCADE,
            codigo_sessao_votacao VARCHAR(50),
            sequencial INTEGER,
            indicador_votacao_secreta BOOLEAN,
            descricao_votacao TEXT,
            descricao_resultado VARCHAR(100),
            total_votos_sim INTEGER,
            total_votos_nao INTEGER,
            total_votos_abstencao INTEGER,
            sigla_descricao_voto VARCHAR(50),
            descricao_voto TEXT,
            codigo_sessao INTEGER,
            codigo_materia INTEGER REFERENCES senado.materia(codigo)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS senado.summary_empresas_geral (
            legislatura INTEGER PRIMARY KEY,
            total_empresas INTEGER,
            total_pago NUMERIC(20,2),
            total_contratos INTEGER,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS senado.summary_empresas_ranking (
            id SERIAL PRIMARY KEY,
            legislatura INTEGER,
            rank INTEGER,
            empresa TEXT,
            partidos TEXT,
            cnpj TEXT,
            valor_total NUMERIC(20,2),
            contratos INTEGER,
            percentual NUMERIC(10,2),
            UNIQUE(legislatura, rank)
        );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_senado_ranking_leg ON senado.summary_empresas_ranking(legislatura);")

    # --- Schema portal ---
    cursor.execute("CREATE SCHEMA IF NOT EXISTS portal;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portal.emendas (
            id SERIAL PRIMARY KEY,
            codigo_emenda VARCHAR(50),
            ano INTEGER,
            tipo_emenda TEXT,
            autor TEXT,
            nome_autor TEXT,
            numero_emenda TEXT,
            localidade_gasto TEXT,
            funcao TEXT,
            subfuncao TEXT,
            valor_empenhado NUMERIC(15,2),
            valor_liquidado NUMERIC(15,2),
            valor_pago NUMERIC(15,2),
            valor_resto_inscrito NUMERIC(15,2),
            valor_resto_cancelado NUMERIC(15,2),
            valor_resto_pago NUMERIC(15,2),
            UNIQUE(codigo_emenda, tipo_emenda, localidade_gasto, funcao, subfuncao)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portal.emenda_documentos (
            id SERIAL PRIMARY KEY,
            api_id BIGINT UNIQUE,
            emenda_id INTEGER REFERENCES portal.emendas(id) ON DELETE CASCADE,
            data DATE,
            fase TEXT,
            codigo_documento VARCHAR(50),
            codigo_documento_resumido TEXT,
            especie_tipo TEXT,
            tipo_emenda TEXT
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portal.emenda_documento_despesa (
            id SERIAL PRIMARY KEY,
            emenda_documento_id INTEGER REFERENCES portal.emenda_documentos(id),
            codigo_documento VARCHAR(50),
            data DATE,
            documento TEXT,
            documento_resumido TEXT,
            observacao TEXT,
            funcao TEXT,
            subfuncao TEXT,
            programa TEXT,
            acao TEXT,
            subtitulo TEXT,
            fase TEXT,
            especie TEXT,
            favorecido TEXT,
            nome_favorecido TEXT,
            valor NUMERIC(15,2),
            orgao TEXT,
            orgao_superior TEXT,
            numero_processo TEXT
        );
    """)

    # Índices do schema portal
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_emendas_autor_lower ON portal.emendas(lower(autor));")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_emendas_ano ON portal.emendas(ano);")

    logging.info("Tabelas criadas/verificadas com sucesso.")


def main():
    """Executa a criação das tabelas no banco de dados."""
    conn = None
    try:
        conn = db.get_db_connection()
        conn.autocommit = False

        with conn.cursor() as cursor:
            ensure_schema(cursor)

        conn.commit()
        logging.info("Banco de dados inicializado com sucesso!")

    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"Erro ao inicializar banco de dados: {e}")
        raise
    finally:
        if conn:
            db.release_db_connection(conn)


if __name__ == "__main__":
    main()

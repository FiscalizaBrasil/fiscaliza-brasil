import psycopg2
import os
import sys
from dotenv import load_dotenv

# Adiciona o diretório backend ao sys.path para importar as configurações do BD do projeto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import database.db as db

load_dotenv()

def create_indexes():
    print("Iniciando a criação de índices no banco de dados...")
    conn = None
    try:
        # Pega a conexão do pool já configurado no projeto
        conn = db.get_db_connection()
        if not conn:
            print("Erro: Não foi possível conectar ao banco de dados.")
            return

        conn.autocommit = True
        cursor = conn.cursor()

        # Lista de criação de índices baseada nas maiores queries
        indexes = [
            # ----- Senado -----
            "CREATE INDEX IF NOT EXISTS idx_sen_mandato_parlamentar ON senado.mandato(codigo_parlamentar);",
            "CREATE INDEX IF NOT EXISTS idx_sen_mandato_legs ON senado.mandato(primeira_legislatura, segunda_legislatura);",
            "CREATE INDEX IF NOT EXISTS idx_sen_despesa_cod_senador ON senado.despesa_ceaps(cod_senador);",
            "CREATE INDEX IF NOT EXISTS idx_sen_despesa_data ON senado.despesa_ceaps(data_despesa DESC);",
            "CREATE INDEX IF NOT EXISTS idx_sen_despesa_tipo ON senado.despesa_ceaps(tipo_despesa);",
            "CREATE INDEX IF NOT EXISTS idx_sen_materia_busca ON senado.materia(ano DESC, sigla, numero);",
            "CREATE INDEX IF NOT EXISTS idx_sen_parlamentar_nome ON senado.parlamentar(nome_parlamentar);",
            "CREATE INDEX IF NOT EXISTS idx_sen_parlamentar_uf ON senado.parlamentar(uf);",
            "CREATE INDEX IF NOT EXISTS idx_sen_mandato_legislatura ON senado.mandato(codigo_legislatura);",
            "CREATE INDEX IF NOT EXISTS idx_sen_despesa_ano_mes ON senado.despesa_ceaps(ano, mes);",
            
            # ----- Câmara -----
            "CREATE INDEX IF NOT EXISTS idx_cam_mandatos_deputado ON camara.deputados_mandatos(deputado_id);",
            "CREATE INDEX IF NOT EXISTS idx_cam_mandatos_legislatura ON camara.deputados_mandatos(legislatura_id);",
            "CREATE INDEX IF NOT EXISTS idx_cam_despesas_mandato ON camara.deputados_despesas(mandato_id);",
            "CREATE INDEX IF NOT EXISTS idx_cam_despesas_tipo ON camara.deputados_despesas(tipo_despesa);",
            "CREATE INDEX IF NOT EXISTS idx_cam_despesas_data ON camara.deputados_despesas(ano DESC, mes DESC);",
            "CREATE INDEX IF NOT EXISTS idx_cam_proposicoes_busca ON camara.proposicoes(ano DESC, sigla_tipo);",
            "CREATE INDEX IF NOT EXISTS idx_cam_votacoes_prop ON camara.votacoes_proposicoes(proposicao_id);",
            "CREATE INDEX IF NOT EXISTS idx_cam_votacoes_votos_votacao ON camara.votacoes_votos(votacao_id);",
            "CREATE INDEX IF NOT EXISTS idx_cam_votacoes_votos_deputado ON camara.votacoes_votos(deputado_id);",
            
            # ----- Índices para busca textual (ILIKE) -----
            "CREATE INDEX IF NOT EXISTS idx_cam_deputados_nome_lower ON camara.deputados(LOWER(nome_civil));",
            "CREATE INDEX IF NOT EXISTS idx_cam_mandatos_nome_lower ON camara.deputados_mandatos(LOWER(nome_eleitoral));",
            "CREATE INDEX IF NOT EXISTS idx_sen_parlamentar_nome_lower ON senado.parlamentar(LOWER(nome_parlamentar));",
            "CREATE INDEX IF NOT EXISTS idx_sen_parlamentar_completo_lower ON senado.parlamentar(LOWER(nome_completo));",
            
            # ----- Portal (Emendas) - Otimizado para joins com parlamentares -----
            "CREATE INDEX IF NOT EXISTS idx_portal_emendas_autor_lower ON portal.emendas(LOWER(autor));",
            "CREATE INDEX IF NOT EXISTS idx_portal_emendas_autor ON portal.emendas(autor);",
            "CREATE INDEX IF NOT EXISTS idx_portal_emendas_nome_autor ON portal.emendas(nome_autor);",
            "CREATE INDEX IF NOT EXISTS idx_portal_emendas_ano_valor ON portal.emendas(ano DESC, valor_pago DESC);",
            "CREATE INDEX IF NOT EXISTS idx_portal_emendas_funcao ON portal.emendas(funcao);",
            "CREATE INDEX IF NOT EXISTS idx_portal_emendas_localidade ON portal.emendas(localidade_gasto);",
            
            # ----- Índices compostos para queries complexas -----
            "CREATE INDEX IF NOT EXISTS idx_cam_mandatos_dep_leg ON camara.deputados_mandatos(deputado_id, legislatura_id);",
            "CREATE INDEX IF NOT EXISTS idx_sen_despesa_senador_data ON senado.despesa_ceaps(cod_senador, data_despesa DESC);",
            "CREATE INDEX IF NOT EXISTS idx_portal_emendas_autor_ano ON portal.emendas(LOWER(autor), ano DESC, valor_pago DESC);",
            "CREATE INDEX IF NOT EXISTS idx_sen_mandato_codigo_legs ON senado.mandato(codigo_parlamentar, primeira_legislatura, segunda_legislatura);"
        ]

        for query in indexes:
            print(f"Executando: \n  {query}")
            try:
                cursor.execute(query)
                print("  -> OK\n")
            except Exception as e:
                print(f"  -> Erro ao criar índice: {e}\n")

        cursor.close()
        print("Todos os índices foram processados com sucesso!")

    except Exception as e:
        print(f"Erro inesperado: {e}")
    finally:
        if conn:
            db.release_db_connection(conn)

if __name__ == "__main__":
    create_indexes()

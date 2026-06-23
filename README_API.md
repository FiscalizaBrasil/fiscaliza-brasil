# Documentação da API - Fiscaliza Brasil

Esta documentação descreve as rotas disponíveis no backend para consulta de dados da **Câmara dos Deputados** e do **Senado Federal**.

## Configuração para Postman
- **Base URL**: `http://localhost:8000/api`
- **Dica**: O FastAPI gera automaticamente uma documentação interativa em `http://localhost:8000/docs`, onde você pode testar cada rota e ver os esquemas de resposta.

### Lista Rápida de URLs (Copy & Paste)

A legislatura é um **parâmetro de caminho (path parameter)** — use variáveis no Postman (ex: `{{legislatura}}`).

#### Câmara
```text
http://localhost:8000/api/camara/{legislatura}/lista
http://localhost:8000/api/camara/{legislatura}/estatisticas
http://localhost:8000/api/camara/{legislatura}/{deputado_id}
http://localhost:8000/api/camara/{legislatura}/{deputado_id}/despesas
http://localhost:8000/api/camara/{legislatura}/{deputado_id}/emendas
http://localhost:8000/api/camara/{legislatura}/comparar
http://localhost:8000/api/camara/{legislatura}/despesas/evolucao
http://localhost:8000/api/camara/{legislatura}/despesas/estatisticas
http://localhost:8000/api/camara/{legislatura}/empresas/estatisticas
http://localhost:8000/api/camara/{legislatura}/emendas
http://localhost:8000/api/camara/{legislatura}/emendas/resumo
http://localhost:8000/api/camara/{legislatura}/proposicoes
http://localhost:8000/api/camara/{legislatura}/proposicoes/{proposicao_id}/votos
http://localhost:8000/api/camara/legislaturas
http://localhost:8000/api/camara/maior-legislatura
http://localhost:8000/api/camara/resumo-principal
```

#### Senado
```text
http://localhost:8000/api/senado/{legislatura}/lista
http://localhost:8000/api/senado/{legislatura}/estatisticas
http://localhost:8000/api/senado/{legislatura}/{senador_codigo}
http://localhost:8000/api/senado/{legislatura}/{senador_codigo}/despesas
http://localhost:8000/api/senado/{legislatura}/{senador_codigo}/emendas/lista
http://localhost:8000/api/senado/{legislatura}/comparar
http://localhost:8000/api/senado/{legislatura}/despesas/evolucao
http://localhost:8000/api/senado/{legislatura}/despesas/estatisticas
http://localhost:8000/api/senado/{legislatura}/empresas/estatisticas
http://localhost:8000/api/senado/{legislatura}/emendas
http://localhost:8000/api/senado/{legislatura}/emendas/resumo
http://localhost:8000/api/senado/{legislatura}/materia/listar
http://localhost:8000/api/senado/{legislatura}/materia/votacao
http://localhost:8000/api/senado/legislaturas
http://localhost:8000/api/senado/maior-legislatura
http://localhost:8000/api/senado/resumo-principal
```

#### Portal da Transparência
```text
http://localhost:8000/api/portal/emendas
```

#### Infra
```text
http://localhost:8000/api/scraping-status
http://localhost:8000/api/cache-stats
http://localhost:8000/api/cache-invalidate    (POST)
```

---

## 🏛️ Câmara dos Deputados (`/api/camara`)

### Legislaturas
- **`GET /legislaturas`**: Lista os IDs de todas as legislaturas disponíveis (ex: 57, 56, 55...).
- **`GET /maior-legislatura`**: Retorna a maior legislatura disponível na base.

### Deputados e Estatísticas
- **`GET /{legislatura}/lista`**: Lista todos os deputados ativos. Retorna `deputados`, `total`, `paginacao`.
- **`GET /{legislatura}/estatisticas`**: Estatísticas gerais (total de deputados, distribuição por região). Resposta inclui `total_deputados`, `total_regioes`, `total_ufs` e `deputados_por_regiao`.
- **`GET /{legislatura}/{deputado_id}`**: Perfil detalhado de um deputado com estatísticas focadas na legislatura.
- **`GET /{legislatura}/{deputado_id}/despesas`**: Extrato de despesas de um deputado.
    - **Params**: `ano` (int, opcional), `mes` (int, opcional).
- **`GET /{legislatura}/{deputado_id}/emendas`**: Lista de emendas parlamentares de um deputado.
- **`GET /{legislatura}/comparar`**: Compara perfil e gastos entre dois deputados.
    - **Params**: `id1` (int), `id2` (int), `ano` (int, opcional).

### Despesas
- **`GET /{legislatura}/despesas/evolucao`**: Evolução de gastos (mensal ou anual).
    - **Params**: `agrupamento` (string: "mensal" ou "anual", padrão "mensal").
- **`GET /{legislatura}/despesas/estatisticas`**: Panorama geral de gastos da Câmara. Retorna `total_deputados`, `total_despesas`, `media_por_deputado`, `top_deputados`, `despesas_por_tipo`, `evolucao_mensal`.

### Ranking de Empresas
- **`GET /{legislatura}/empresas/estatisticas`**: Ranking de fornecedores e empresas que mais receberam pagamentos.
    - **Params**: `limit` (int, padrão 20).

### Emendas Parlamentares
- **`GET /{legislatura}/emendas`**: Lista detalhada de emendas.
    - **Params**: `nome_deputado` (string), `ano` (int), `pagina` (int).
- **`GET /{legislatura}/emendas/resumo`**: Visão geral financeira das emendas por área e ranking de autores.

### Proposições (Projetos Legislativos)
- **`GET /{legislatura}/proposicoes`**: Lista de projetos de lei e outras proposições.
    - **Params**: `siglaTipo`, `ano`, `ementa`, `deputado` (nome), `pagina`.
    - **Resposta**: retorna `proposicoes`, `paginacao` e `estatisticas` (total, tipo mais frequente e distribuição por tipo).
- **`GET /{legislatura}/proposicoes/{proposicao_id}/votos`**: Histórico de votação nominal de um projeto específico.

### Resumo
- **`GET /resumo-principal`**: Resumo otimizado para a página principal (Câmara).

---

## 🏛️ Senado Federal (`/api/senado`)

### Legislaturas
- **`GET /legislaturas`**: Lista os IDs das legislaturas do Senado.
- **`GET /maior-legislatura`**: Retorna a maior legislatura disponível na base.

### Senadores e Estatísticas
- **`GET /{legislatura}/lista`**: Lista todos os senadores. Retorna `senadores`, `total`, `paginacao`.
- **`GET /{legislatura}/estatisticas`**: Estatísticas macro do Senado (gastos totais, parlamentares por região).
- **`GET /{legislatura}/{senador_codigo}`**: Perfil detalhado de um senador.
- **`GET /{legislatura}/{senador_codigo}/despesas`**: Extrato detalhado de gastos de um senador (CEAPS).
    - **Params**: `ano` (int, opcional), `pagina` (int).
- **`GET /{legislatura}/{senador_codigo}/emendas/lista`**: Lista de emendas parlamentares de um senador.
- **`GET /{legislatura}/comparar`**: Comparação entre dois senadores.
    - **Params**: `id1`, `id2`, `ano`.

### Despesas
- **`GET /{legislatura}/despesas/evolucao`**: Evolução de gastos do Senado (mensal ou anual).
    - **Params**: `agrupamento` (string: "mensal" ou "anual", padrão "mensal").
- **`GET /{legislatura}/despesas/estatisticas`**: Panorama geral de gastos do Senado. Retorna `total_senadores`, `total_despesas`, `media_por_senador`, `top_senadores`, `despesas_por_tipo`, `evolucao_mensal`.

### Ranking de Empresas
- **`GET /{legislatura}/empresas/estatisticas`**: Ranking das empresas fornecedoras do Senado.
    - **Params**: `limit` (int, padrão 20).

### Emendas Parlamentares
- **`GET /{legislatura}/emendas`**: Lista de emendas do Senado.
    - **Params**: `nome_senador`, `ano`, `pagina`.
- **`GET /{legislatura}/emendas/resumo`**: Resumo financeiro das emendas do Senado.

### Matérias Legislativas
- **`GET /{legislatura}/materia/listar`**: Consulta de matérias legislativas (projetos).
    - **Params**: `siglaTipo`, `ano`, `ementa`, `senador` (nome), `pagina`, `limite`.
    - **Resposta**: retorna `materia`, `paginacao` e `estatisticas` (total, tipo mais frequente e distribuição por tipo).
- **`GET /{legislatura}/materia/votacao`**: Histórico de votações de um projeto legislativo.
    - **Params**: `codigo_materia` (int).

### Resumo
- **`GET /resumo-principal`**: Resumo otimizado para a página principal (Senado).

---

## 💡 Sobre o parâmetro `legislatura`

A legislatura é um **parâmetro de caminho (path parameter)** obrigatório na maioria das rotas (ex: `/api/camara/57/lista`). Use os valores `57`, `56`, `55` etc.

- **Por que usar?** Os dados históricos são vastos. Ao passar a legislatura, você filtra os resultados para um período de 4 anos específico, tornando as estatísticas mais precisas e comparáveis.
- **Onde encontrar os IDs?** Use as rotas `/api/camara/legislaturas` ou `/api/senado/legislaturas` para ver quais períodos estão disponíveis na sua base de dados.

Algumas rotas `/{legislatura}/{deputado_id}` também aceitam `legislatura=0` para buscar em todas as legislaturas — porém, isso varre **todos** os dados históricos e pode ser lento.

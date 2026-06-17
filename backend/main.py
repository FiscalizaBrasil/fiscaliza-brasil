from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
import logging
import sys
import os

# Configura logging para ver as execuções no console do container
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Adiciona o diretório 'scripts' ao path para importar o módulo
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

# Importa a função main do script update_company_summaries
from update_company_summaries import main as atualizar_resumos

from api.camara.router import router as camara_router
from api.senado.router import router as senado_router

app = FastAPI()

# Configuração CORS (mantida)
origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Rotas existentes
app.include_router(camara_router, prefix="/api")
app.include_router(senado_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "API de Deputados em funcionamento"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# ---------- Agendamento ----------
def executar_atualizacao():
    """Wrapper para capturar logs e executar a função main do script."""
    try:
        logger.info("Iniciando atualização de resumos das empresas...")
        atualizar_resumos()   # Chama a função main() do script
        logger.info("Atualização concluída com sucesso.")
    except Exception as e:
        logger.error(f"Erro durante a atualização programada: {e}", exc_info=True)

# Inicializa o scheduler em background
scheduler = BackgroundScheduler()

# Agenda para rodar todos os dias às 03:00 da manhã (ajuste o horário se desejar)
scheduler.add_job(
    executar_atualizacao,
    trigger=CronTrigger(hour=3, minute=0),
    id="atualizacao_diaria",
    replace_existing=True,
)

# Inicia o scheduler
scheduler.start()
logger.info("Agendador iniciado. Próxima execução diária às 03:00.")

# Executa uma vez logo após a inicialização (em background)
async def executar_no_startup():
    # Pequeno delay para garantir que o banco de dados esteja pronto
    await asyncio.sleep(5)
    executar_atualizacao()

# Agenda a execução inicial no loop de eventos do FastAPI
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(executar_no_startup())

# ---------- Fim do Agendamento ----------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
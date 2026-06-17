import { defineStore } from "pinia"
import { ref, computed } from "vue"

export interface Deputado {
  id: number
  nome: string
  partido: string
  estado: string
  foto: string
}

export interface ProjetoLegislativo {
  id: number
  siglaTipo: string
  numero: number
  ano: number
  ementa: string
  dataApresentacao: string | null
  autor_principal: string
  url_inteiro_teor?: string | null
}

export interface DeputadoDetail {
  id: number
  nome_civil: string
  cpf: string
  sexo: string
  email: string
  data_nascimento: string | null
  escolaridade: string
  uf_nascimento: string
  municipio_nascimento: string
  sigla_partido: string
  sigla_uf?: string
  foto: string
  categorias?: { categoria: string; valor: number }[]
  despesas?: Despesa[]
  total_gasto?: number
  total_emendas?: number
  legislaturas_ativas?: number[]
}

export interface Emenda {
  codigo: string
  ano: number
  tipo: string
  valorEmpenhado: number
  valorLiquidado: number
  valorPago: number
  funcao: string
  localidade: string
}

export interface Despesa {
  ano: number
  mes: number
  tipo_despesa: string
  valor: number
  url_documento: string | null
}

export interface Categoria {
  categoria: string
  valor: number
}

export interface EstatisticasGerais {
  total_gastos_12_meses: number
  total_gastos: number
  total_empresas_contratadas: number
  gastos_por_categoria: { categoria: string; valor: number }[]
  gastos_por_mes: { ano: number; mes: number; valor: number }[]
  gastos_por_estado: { estado: string; valor: number }[]
  gastos_por_partido: { partido: string; valor: number }[]
  gastos_deputados: {
    deputado_id: number
    nome_civil: string
    sigla_partido: string
    estado: string
    total_gasto: number
  }[]
}

export interface EstatisticasDeputado {
  total_deputados: number
  total_regioes?: number
  total_ufs?: number
  deputados_por_regiao: { name: string; value: number }[]
}

export interface Filters {
  search: string
  partido: string
  estado: string
}

export interface ProjetosLegislativosFilters {
  search: string
  siglaTipo: string
  ano: string
  deputado: string
}

export interface VotoDeputado {
  deputado_id: number
  nome: string
  voto: string
}

export interface Votacao {
  id_votacao: string
  data: string
  descricao: string
  total_votos: number
  lista_votos: VotoDeputado[]
}

export interface VotosProjetoLegislativo {
  proposicao_id: number
  historico_votacoes: Votacao[]
}

export const useCamaraStore = defineStore("camara", () => {
  const filters = ref<Filters>({
    search: "",
    partido: "",
    estado: "",
  })

  const projetosLegislativosFilters = ref<ProjetosLegislativosFilters>({
    search: "",
    siglaTipo: "",
    ano: "",
    deputado: "",
  })

  const legislatura = ref(57)
  const apiUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"

  const legislaturasDisponiveis = ref<number[]>([57, 56, 55, 54, 53, 52, 51, 50])
  
  const fetchLegislaturasDisponiveis = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/camara/legislaturas`)
      if (!response.ok) throw new Error("Falha ao buscar legislaturas da câmara")
      const data = await response.json()
      if (data && data.length > 0) {
        legislaturasDisponiveis.value = data
      }
    } catch (e: any) {
      console.error("Erro ao carregar legislaturas globais:", e)
    }
  }
  fetchLegislaturasDisponiveis()

  // List state
  const deputadosList = ref<Deputado[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentPage = ref(1)
  const itemsPerPage = 12

  // Detail state
  const currentDeputado = ref<DeputadoDetail | null>(null)
  const currentDespesas = ref<Despesa[]>([])
  const currentCategorias = ref<Categoria[]>([])
  const totalDespesas = ref(0)
  const despesasPage = ref(1)
  const despesasTotalPages = ref(1)
  const currentEmendas = ref<Emenda[]>([])
  const totalEmendas = ref(0)
  const emendasPage = ref(1)
  const emendasTotalPages = ref(1)
  const loadingDetail = ref(false)

  // General Stats state
  const generalStats = ref<EstatisticasGerais | null>(null)
  const deputadoStats = ref<EstatisticasDeputado | null>(null)

  // Categories state
  const categorias = ref<Categoria[]>([])
  const loadingCategorias = ref(false)

  // Projetos Legislativos state
  const projetosLegislativosList = ref<ProjetoLegislativo[]>([])
  const totalProjetosLegislativos = ref(0)
  const loadingProjetosLegislativos = ref(false)
  const projetosLegislativosDistribuicao = ref<{ tipo: string; quantidade: number }[]>([])
  const projetosLegislativosPage = ref(1)
  const hasMoreProjetosLegislativos = ref(true)

  // Votos state
  const currentVotos = ref<VotosProjetoLegislativo | null>(null)
  const loadingVotos = ref(false)
  const loadingStats = ref(false)
  const selectedProjetoLegislativoId = ref<number | null>(null)

  const fetchDeputados = async () => {
    loading.value = true
    error.value = null
    try {
      const response = await fetch(`${apiUrl}/api/camara/${legislatura.value}/lista`)
      if (!response.ok) throw new Error("Falha ao buscar deputados")

      const data = await response.json()
      deputadosList.value = data.map((d: any) => ({
        id: d.id,
        nome: d.nome_civil,
        partido: d.sigla_partido,
        estado: d.uf,
        foto: `https://www.camara.leg.br/internet/deputado/bandep/${d.id}.jpg`
      }))
    } catch (e: any) {
      console.error("Erro ao buscar deputados:", e)
      error.value = "Erro ao carregar lista de deputados."
    } finally {
      loading.value = false
    }
  }

  const fetchDeputado = async (id: number) => {
    loadingDetail.value = true
    error.value = null
    currentDeputado.value = null
    currentDespesas.value = []
    currentCategorias.value = []
    totalDespesas.value = 0
    despesasPage.value = 1
    despesasTotalPages.value = 1
    currentEmendas.value = []
    totalEmendas.value = 0
    emendasPage.value = 1
    emendasTotalPages.value = 1

    try {
      const response = await fetch(`${apiUrl}/api/camara/${legislatura.value}/${id}`)
      if (!response.ok) throw new Error("Falha ao buscar detalhes do deputado")

      const data = await response.json()
      currentDeputado.value = data
      
      // Sincronizar legislatura exibida com o seletor
      if (data.legislatura_exibida && data.legislatura_exibida !== legislatura.value) {
        legislatura.value = data.legislatura_exibida
      }

      totalEmendas.value = data.total_emendas || 0

      await fetchDespesasDeputado(id)
      await fetchEmendasDeputado(id)
    } catch (e: any) {
      console.error("Erro ao buscar detalhes:", e)
      error.value = "Erro ao carregar detalhes do deputado."
    } finally {
      loadingDetail.value = false
    }
  }


  const fetchEstatisticasGerais = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/camara/${legislatura.value}/despesas/estatisticas`)
      if (!response.ok) throw new Error("Falha ao buscar estatísticas")
      generalStats.value = await response.json()
    } catch (e: any) {
      console.error("Erro ao buscar estatísticas gerais de despesas:", e)
    }
  }

  const fetchEstatisticasDeputados = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/camara/${legislatura.value}/estatisticas`)
      if (!response.ok) throw new Error("Falha ao buscar estatísticas")
      deputadoStats.value = await response.json()
    } catch (e: any) {
      console.error("Erro ao buscar estatísticas gerais de deputados:", e)
    }
  }


  const fetchProjetosLegislativos = async (pagina = 1) => {
    loadingProjetosLegislativos.value = true
    error.value = null

    try {
      const params = new URLSearchParams()
      params.append("pagina", String(pagina))
      params.append("limite", "15")

      if (projetosLegislativosFilters.value.siglaTipo) {
        params.append("siglaTipo", projetosLegislativosFilters.value.siglaTipo)
      }
      if (projetosLegislativosFilters.value.ano) {
        params.append("ano", projetosLegislativosFilters.value.ano)
      }
      if (projetosLegislativosFilters.value.search) {
        params.append("ementa", projetosLegislativosFilters.value.search)
      }
      if (projetosLegislativosFilters.value.deputado) {
        params.append("deputado", projetosLegislativosFilters.value.deputado)
      }

      const response = await fetch(`${apiUrl}/api/camara/${legislatura.value}/proposicoes?${params.toString()}`)
      if (!response.ok) throw new Error("Falha ao buscar projetos legislativos")

      const data = await response.json()
      const mapped = (data.proposicoes || []).map((p: any) => ({
        id: p.id,
        siglaTipo: p.siglaTipo,
        numero: p.numero,
        ano: p.ano,
        ementa: p.ementa,
        dataApresentacao: p.dataApresentacao,
        autor_principal: p.autor_principal || "Desconhecido",
      }))

      if (pagina === 1) {
        projetosLegislativosList.value = mapped
        selectedProjetoLegislativoId.value = null
        currentVotos.value = null
      } else {
        projetosLegislativosList.value = [...projetosLegislativosList.value, ...mapped]
      }

      totalProjetosLegislativos.value = data.paginacao?.total || 0
      projetosLegislativosDistribuicao.value = data.estatisticas?.distribuicao_tipos || []
      projetosLegislativosPage.value = pagina
      hasMoreProjetosLegislativos.value = projetosLegislativosList.value.length < totalProjetosLegislativos.value
    } catch (e: any) {
      console.error("Erro ao buscar projetos legislativos:", e)
      error.value = "Erro ao carregar projetos legislativos."
    } finally {
      loadingProjetosLegislativos.value = false
    }
  }

  const loadMoreProjetosLegislativos = async () => {
    if (!loadingProjetosLegislativos.value && hasMoreProjetosLegislativos.value) {
      await fetchProjetosLegislativos(projetosLegislativosPage.value + 1)
    }
  }

  const tiposUnicosProjetosLegislativos = computed(() => {
    const tipos = new Set(projetosLegislativosDistribuicao.value.map((p) => p.tipo))
    return Array.from(tipos).sort()
  })

  const anosUnicosProjetosLegislativos = computed(() => {
    const anos = new Set(projetosLegislativosList.value.map((p) => p.ano))
    return Array.from(anos).sort((a, b) => b - a)
  })

  const projetosLegislativosPorTipo = computed(() => projetosLegislativosDistribuicao.value)

  const fetchVotosProjetoLegislativo = async (id: number) => {
    loadingVotos.value = true
    currentVotos.value = null
    try {
      const response = await fetch(`${apiUrl}/api/camara/${legislatura.value}/proposicoes/${id}/votos`)
      if (!response.ok) throw new Error("Falha ao buscar votos")
      currentVotos.value = await response.json()
    } catch (e: any) {
      console.error("Erro ao buscar votos do projeto legislativo:", e)
    } finally {
      loadingVotos.value = false
    }
  }

  const fetchEmendasDeputado = async (id: number, page: number = 1) => {
    try {
      const response = await fetch(`${apiUrl}/api/camara/${legislatura.value}/${id}/emendas?pagina=${page}`)
      if (!response.ok) throw new Error("Falha ao buscar emendas")
      const data = await response.json()
      currentEmendas.value = data.emendas || []
      emendasPage.value = data.paginacao?.pagina || 1
      emendasTotalPages.value = data.paginacao?.total_paginas || 1
    } catch (e: any) {
      console.error("Erro ao buscar emendas do deputado:", e)
    }
  }

  const fetchDespesasDeputado = async (id: number, page: number = 1) => {
    loadingDetail.value = true
    try {
      const response = await fetch(`${apiUrl}/api/camara/${legislatura.value}/${id}/despesas?pagina=${page}`)
      if (!response.ok) throw new Error("Falha ao buscar despesas do deputado")
      const data = await response.json()
      currentDespesas.value = data.despesas || []
      currentCategorias.value = data.categorias || []
      totalDespesas.value = data.total_despesas || 0
      despesasPage.value = data.paginacao?.pagina || 1
      despesasTotalPages.value = data.paginacao?.total_paginas || 1
    } finally {
      loadingDetail.value = false
    }
  }

  const toggleProjetoLegislativoVotos = async (id: number) => {
    if (selectedProjetoLegislativoId.value === id) {
      selectedProjetoLegislativoId.value = null
      currentVotos.value = null
    } else {
      selectedProjetoLegislativoId.value = id
      await fetchVotosProjetoLegislativo(id)
    }
  }

  const setProjetosLegislativosFilter = (key: keyof ProjetosLegislativosFilters, value: string) => {
    projetosLegislativosFilters.value[key] = value
    fetchProjetosLegislativos(1)
  }

  const resetProjetosLegislativosFilters = () => {
    projetosLegislativosFilters.value = { search: "", siglaTipo: "", ano: "", deputado: "" }
    fetchProjetosLegislativos(1)
  }

  const partidosUnicos = computed(() => {
    const set = new Set(deputadosList.value.map(d => d.partido))
    return Array.from(set).sort()
  })

  const estadosUnicos = computed(() => {
    const set = new Set(deputadosList.value.map(d => d.estado))
    return Array.from(set).sort()
  })

  const normalizeString = (str: string) => {
    return str ? str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase() : ''
  }

  const filteredDeputados = computed(() => {
    return deputadosList.value.filter((dep) => {
      if (filters.value.search && !normalizeString(dep.nome).includes(normalizeString(filters.value.search))) {
        return false
      }
      if (filters.value.partido && dep.partido !== filters.value.partido) {
        return false
      }
      if (filters.value.estado && dep.estado !== filters.value.estado) {
        return false
      }
      return true
    })
  })

  const totalPages = computed(() => Math.ceil(filteredDeputados.value.length / itemsPerPage))

  const paginatedDeputados = computed(() => {
    const start = (currentPage.value - 1) * itemsPerPage
    return filteredDeputados.value.slice(start, start + itemsPerPage)
  })

  const setFilter = (key: keyof Filters, value: string) => {
    filters.value[key] = value
    currentPage.value = 1
  }

  const setPage = (page: number) => {
    currentPage.value = page
  }

  const setLegislatura = async (val: number) => {
    legislatura.value = val
    // Invalidate/Refetch data
    await Promise.allSettled([
      fetchDeputados(),
      fetchEstatisticasGerais(),
      fetchEstatisticasDeputados(),
      fetchProjetosLegislativos(1)
    ])
  }

  const resetFilters = () => {
    filters.value = { search: "", partido: "", estado: "" }
    currentPage.value = 1
  }

  return {
    filters,
    currentPage,
    partidosUnicos,
    estadosUnicos,
    deputadosList,
    filteredDeputados,
    paginatedDeputados,
    totalPages,
    loading,
    error,
    currentDeputado,
    currentDespesas,
    currentCategorias,
    totalDespesas,
    despesasPage,
    despesasTotalPages,
    currentEmendas,
    totalEmendas,
    emendasPage,
    emendasTotalPages,
    loadingDetail,
    generalStats,
    deputadoStats,
    loadingStats,
    categorias,
    loadingCategorias,
    fetchDeputados,
    fetchDeputado,
    fetchDespesasDeputado,
    fetchEmendasDeputado,
    fetchEstatisticasGerais,
    fetchEstatisticasDeputados,
    projetosLegislativosList,
    totalProjetosLegislativos,
    loadingProjetosLegislativos,
    hasMoreProjetosLegislativos,
    projetosLegislativosFilters,
    fetchProjetosLegislativos,
    loadMoreProjetosLegislativos,
    tiposUnicosProjetosLegislativos,
    anosUnicosProjetosLegislativos,
    projetosLegislativosPorTipo,
    setProjetosLegislativosFilter,
    resetProjetosLegislativosFilters,
    currentVotos,
    loadingVotos,
    selectedProjetoLegislativoId,
    fetchVotosProjetoLegislativo,
    toggleProjetoLegislativoVotos,
    setFilter,
    setPage,
    resetFilters,
    legislatura,
    setLegislatura,
    legislaturasDisponiveis,
    fetchLegislaturasDisponiveis,
  }
})

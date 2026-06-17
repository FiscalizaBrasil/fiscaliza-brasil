import { defineStore } from "pinia"
import { ref, computed } from "vue"

export interface Senador {
    id: number
    nome: string
    partido: string
    estado: string
    foto: string
}

export interface SenadorDetail {
    id: number
    nome_civil: string
    nome_parlamentar: string
    cpf: string
    sexo: string
    email: string
    data_nascimento: string | null
    escolaridade: string
    uf_nascimento: string
    municipio_nascimento: string
    sigla_partido: string
    uf: string
    foto: string
    total_emendas?: number
    legislaturas_ativas?: number[]
}

export interface EmendaSenado {
    codigo: string
    ano: number
    tipo: string
    valorEmpenhado: number
    valorLiquidado: number
    valorPago: number
    funcao: string
    localidade: string
}

export interface EstatisticasSenadoGerais {
    total_senadores: number
    total_gastos: number
    total_regioes: number
    senadores_por_regiao: { name: string; value: number }[]
}

export interface EstatisticasSenado {
    total_gastos: number
    media_por_senador: number
    total_12_meses: number
    gastos_por_mes: { ano: number; mes: number; valor: number }[]
    partidos: { partido: string; total: number; percentual: number }[]
    categorias: { categoria: string; total: number }[]
    top_10: { codigo: number; nome: string; partido: string; uf: string; foto: string; total: number }[]
}

export interface ProjetoLegislativoSenado {
    id: number
    siglaTipo: string
    numero: number
    ano: number
    ementa: string
    dataApresentacao: string | null
    autor_principal: string
}

export interface VotoSenador {
    materia: string
    ementa: string
    nomeParlamentar: string
    siglaPartido: string
    uf: string
    voto: string
    resultado: string
    codigo?: number
    foto?: string
}

export interface VotacaoMateriaSenado {
    votacao: VotoSenador[]
}

export interface ProjetosLegislativosFilters {
    search: string
    siglaTipo: string
    ano: string
    senador: string
}

export interface Filters {
    search: string
    partido: string
    estado: string
}

import { useCamaraStore } from "./camara"

export const useSenadoStore = defineStore("senado", () => {
    const camaraStore = useCamaraStore()
    const legislatura = computed(() => camaraStore.legislatura)
    const setLegislatura = async (val: number) => {
    await camaraStore.setLegislatura(val)
    // Refetch senator-specific data
    await Promise.allSettled([
        fetchSenadores(),
        fetchEstatisticasGerais(),
        fetchEstatisticasSenadores(),
        fetchProjetosLegislativos()
    ])
  }
    const apiUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"

    const legislaturasDisponiveis = ref<number[]>([57, 56, 55, 54, 53, 52, 51, 50])
    
    const fetchLegislaturasDisponiveis = async () => {
      try {
        const response = await fetch(`${apiUrl}/api/senado/legislaturas`)
        if (!response.ok) throw new Error("Falha ao buscar legislaturas do senado")
        const data = await response.json()
        if (data && data.length > 0) {
          legislaturasDisponiveis.value = data
        }
      } catch (e: any) {
        console.error("Erro ao carregar legislaturas globais (senado):", e)
      }
    }
    fetchLegislaturasDisponiveis()

    const filters = ref<Filters>({
        search: "",
        partido: "",
        estado: "",
    })

    // List state
    const senadoresList = ref<Senador[]>([])
    const loading = ref(false)
    const error = ref<string | null>(null)
    const currentPage = ref(1)
    const itemsPerPage = 12

    // Detail state
    const currentSenador = ref<SenadorDetail | null>(null)
    const currentEmendas = ref<EmendaSenado[]>([])
    const totalEmendas = ref(0)
    const emendasPage = ref(1)
    const emendasTotalPages = ref(1)

    const currentDespesas = ref<any[]>([])
    const totalDespesas = ref(0)
    const despesasPage = ref(1)
    const despesasTotalPages = ref(1)
    const currentCategorias = ref<any[]>([])
    const loadingDetail = ref(false)

    // General Stats state
    const generalStats = ref<EstatisticasSenado | null>(null)
    const senadorStats = ref<EstatisticasSenadoGerais | null>(null)

    // Projetos Legislativos state
    const projetosLegislativosFilters = ref<ProjetosLegislativosFilters>({
        search: "",
        siglaTipo: "",
        ano: "",
        senador: "",
    })
    const projetosLegislativosList = ref<ProjetoLegislativoSenado[]>([])
    const totalProjetosLegislativos = ref(0)
    const projetosLegislativosDistribuicao = ref<{ tipo: string; quantidade: number }[]>([])
    const loadingProjetosLegislativos = ref(false)
    const projetosLegislativosPage = ref(1)
    const hasMoreProjetosLegislativos = ref(true)
    const selectedProjetoLegislativoId = ref<number | null>(null)
    const currentVotos = ref<VotacaoMateriaSenado | null>(null)
    const loadingVotos = ref(false)
    const loadingStats = ref(false)

    const fetchSenadores = async () => {
        loading.value = true
        error.value = null
        try {
            const response = await fetch(`${apiUrl}/api/senado/${legislatura.value}/lista`)
            if (!response.ok) throw new Error("Falha ao buscar senadores")

            const data = await response.json()
            senadoresList.value = data.senadores.map((s: any) => ({
                id: s.codigo,
                nome: s.nomeParlamentar,
                partido: s.siglaPartido,
                estado: s.uf,
                foto: s.urlFoto
            }))
        } catch (e: any) {
            console.error("Erro ao buscar senadores:", e)
            error.value = "Erro ao carregar lista de senadores."
        } finally {
            loading.value = false
        }
    }

    const fetchSenador = async (id: number) => {
        loadingDetail.value = true
        error.value = null
        currentSenador.value = null
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
            const response = await fetch(`${apiUrl}/api/senado/${legislatura.value}/${id}`)
            if (!response.ok) throw new Error("Falha ao buscar detalhes do senador")
            const data = await response.json()
            const s = data.senador

            // Sincronizar legislatura exibida com o seletor (global na CamaraStore)
            if (s.legislatura_exibida && s.legislatura_exibida !== legislatura.value) {
                camaraStore.legislatura = s.legislatura_exibida
            }

            currentSenador.value = {
                id: s.codigo,
                nome_civil: s.nomeCompleto || s.nomeParlamentar,
                nome_parlamentar: s.nomeParlamentar,
                cpf: "N/A",
                sexo: s.sexo,
                email: s.email,
                data_nascimento: s.dataNascimento,
                escolaridade: "N/A",
                uf_nascimento: "N/A",
                municipio_nascimento: "N/A",
                sigla_partido: s.siglaPartido,
                uf: s.uf,
                foto: s.urlFoto,
                total_emendas: s.total_emendas || 0,
                legislaturas_ativas: s.legislaturas_ativas || []
            }
            totalEmendas.value = s.total_emendas || 0

            // Buscar despesas logo após
            await fetchDespesasSenador(id)
            // Buscar emendas logo após
            await fetchEmendasSenador(id)
        } catch (e: any) {
            console.error("Erro ao buscar detalhes do senador:", e)
            error.value = "Erro ao carregar perfil do senador."
        } finally {
            loadingDetail.value = false
        }
    }

    const fetchDespesasSenador = async (id: number, page: number = 1) => {
        loadingDetail.value = true
        try {
            const response = await fetch(`${apiUrl}/api/senado/${legislatura.value}/${id}/despesas?pagina=${page}`)
            if (!response.ok) throw new Error("Falha ao buscar despesas do senador")
            const data = await response.json()
            currentDespesas.value = data.despesas
            currentCategorias.value = data.categorias || []
            totalDespesas.value = data.total_despesas
            despesasPage.value = data.paginacao.pagina
            despesasTotalPages.value = data.paginacao.total_paginas
        } finally {
            loadingDetail.value = false
        }
    }

    const fetchEmendasSenador = async (id: number, page: number = 1) => {
        try {
            const response = await fetch(`${apiUrl}/api/senado/${legislatura.value}/${id}/emendas/lista?pagina=${page}`)
            if (!response.ok) throw new Error("Falha ao buscar emendas")
            const data = await response.json()
            currentEmendas.value = data.emendas
            emendasPage.value = data.paginacao.pagina
            emendasTotalPages.value = data.paginacao.total_paginas
        } catch (e: any) {
            console.error("Erro ao buscar emendas do senador:", e)
        }
    }

    const fetchEstatisticasGerais = async () => {
        error.value = null
        try {
            const response = await fetch(`${apiUrl}/api/senado/${legislatura.value}/despesas/estatisticas`)
            if (!response.ok) throw new Error('Falha ao buscar estatísticas do Senado')
            generalStats.value = await response.json()
        } catch (e: any) {
            console.error('Erro ao buscar estatísticas do senado:', e)
            error.value = "Não foi possível carregar as estatísticas do Senado."
        }
    }

    const fetchEstatisticasSenadores = async () => {
        loadingStats.value = true
        try {
            const response = await fetch(`${apiUrl}/api/senado/${legislatura.value}/estatisticas`)
            senadorStats.value = await response.json()
        } catch (e: any) {
            console.error('Erro ao buscar estatísticas gerais do senado:', e)
        } finally {
            loadingStats.value = false
        }
    }

    const partidosUnicos = computed(() => {
        const set = new Set(senadoresList.value.map(s => s.partido).filter(Boolean))
        return Array.from(set).sort()
    })

    const estadosUnicos = computed(() => {
        const set = new Set(senadoresList.value.map(s => s.estado).filter(Boolean))
        return Array.from(set).sort()
    })

    const normalizeString = (str: string) => {
        return str ? str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase() : ''
    }

    const filteredSenadores = computed(() => {
        return senadoresList.value.filter((sen) => {
            if (filters.value.search && !normalizeString(sen.nome).includes(normalizeString(filters.value.search))) {
                return false
            }
            if (filters.value.partido && sen.partido !== filters.value.partido) {
                return false
            }
            if (filters.value.estado && sen.estado !== filters.value.estado) {
                return false
            }
            return true
        })
    })

    const totalPages = computed(() => Math.ceil(filteredSenadores.value.length / itemsPerPage))

    const paginatedSenadores = computed(() => {
        const start = (currentPage.value - 1) * itemsPerPage
        return filteredSenadores.value.slice(start, start + itemsPerPage)
    })

    const setFilter = (key: keyof Filters, value: string) => {
        filters.value[key] = value
        currentPage.value = 1
    }

    const setPage = (page: number) => {
        currentPage.value = page
    }

    const resetFilters = () => {
        filters.value = { search: "", partido: "", estado: "" }
        currentPage.value = 1
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
            if (projetosLegislativosFilters.value.senador) {
                params.append("senador", projetosLegislativosFilters.value.senador)
            }

            const response = await fetch(`${apiUrl}/api/senado/${legislatura.value}/materia/listar?${params.toString()}`)
            if (!response.ok) throw new Error("Falha ao buscar projetos legislativos")
            const data = await response.json()

            const mapped = (data.materia || []).map((m: any) => ({
                id: m.id,
                siglaTipo: m.siglaTipo,
                numero: m.numero,
                ano: m.ano,
                ementa: m.ementa,
                dataApresentacao: m.dataApresentacao,
                autor_principal: m.autor_principal,
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

    const fetchVotacaoMateria = async (codigoMateria: number) => {
        loadingVotos.value = true
        currentVotos.value = null
        try {
            const response = await fetch(`${apiUrl}/api/senado/${legislatura.value}/materia/votacao?codigo_materia=${codigoMateria}`)
            if (!response.ok) throw new Error("Falha ao buscar votação")
            const data = await response.json()
            currentVotos.value = { votacao: data.votacao }
        } catch (e: any) {
            console.error("Erro ao buscar votação:", e)
        } finally {
            loadingVotos.value = false
        }
    }

    const toggleProjetoLegislativoVotos = async (id: number) => {
        if (selectedProjetoLegislativoId.value === id) {
            selectedProjetoLegislativoId.value = null
            currentVotos.value = null
            return
        }
        selectedProjetoLegislativoId.value = id
        await fetchVotacaoMateria(id)
    }

    const filteredProjetosLegislativos = computed(() => projetosLegislativosList.value)

    const tiposUnicosProjetosLegislativos = computed(() => {
        const tipos = new Set(projetosLegislativosDistribuicao.value.map((p) => p.tipo))
        return Array.from(tipos).sort()
    })

    const anosUnicosProjetosLegislativos = computed(() => {
        const anos = new Set(projetosLegislativosList.value.map((p) => p.ano))
        return Array.from(anos).sort((a, b) => b - a)
    })

    const projetosLegislativosPorTipo = computed(() => projetosLegislativosDistribuicao.value)

    const setProjetosLegislativosFilter = (key: keyof ProjetosLegislativosFilters, value: string) => {
        projetosLegislativosFilters.value[key] = value
        fetchProjetosLegislativos(1)
    }

    const resetProjetosLegislativosFilters = () => {
        projetosLegislativosFilters.value = { search: "", siglaTipo: "", ano: "", senador: "" }
        fetchProjetosLegislativos(1)
    }

    return {
        filters,
        senadoresList,
        filteredSenadores,
        paginatedSenadores,
        partidosUnicos,
        estadosUnicos,
        totalPages,
        currentPage,
        loading,
        error,
        currentSenador,
        currentEmendas,
        totalEmendas,
        emendasPage,
        emendasTotalPages,
        currentDespesas,
        totalDespesas,
        despesasPage,
        despesasTotalPages,
        currentCategorias,
        loadingDetail,
        generalStats,
        senadorStats,
        loadingStats,
        fetchSenadores,
        fetchSenador,
        fetchDespesasSenador,
        fetchEmendasSenador,
        fetchEstatisticasGerais,
        fetchEstatisticasSenadores,
        setFilter,
        setPage,
        resetFilters,
        legislatura,
        setLegislatura,
        // Projetos Legislativos
        projetosLegislativosFilters,
        projetosLegislativosList,
        totalProjetosLegislativos,
        loadingProjetosLegislativos,
        filteredProjetosLegislativos,
        tiposUnicosProjetosLegislativos,
        anosUnicosProjetosLegislativos,
        projetosLegislativosPorTipo,
        fetchProjetosLegislativos,
        loadMoreProjetosLegislativos,
        hasMoreProjetosLegislativos,
        fetchVotacaoMateria,
        toggleProjetoLegislativoVotos,
        selectedProjetoLegislativoId,
        currentVotos,
        loadingVotos,
        setProjetosLegislativosFilter,
        resetProjetosLegislativosFilters,
        apiUrl,
        legislaturasDisponiveis,
        fetchLegislaturasDisponiveis,
    }
})

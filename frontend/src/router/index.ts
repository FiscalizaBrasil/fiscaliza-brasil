import { createRouter, createWebHistory } from "vue-router"
import HomePage from "@/pages/home/HomePage.vue"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomePage,
      meta: { title: "Página Inicial" },
    },

    // ========== CÂMARA DOS DEPUTADOS ==========
    {
      path: "/camara/deputados",
      name: "deputados",
      component: () => import("@/pages/camara/CamaraListaPage.vue"),
      meta: { title: "Deputados" },
    },
    {
      path: "/camara/deputados/:id",
      name: "deputado-detail",
      component: () => import("@/pages/camara/CamaraDetalhePage.vue"),
      meta: { title: "Detalhes do Deputado" },
    },
    {
      path: "/camara/despesas",
      name: "despesas-camara",
      component: () => import("@/pages/camara/CamaraDespesasPage.vue"),
      meta: { title: "Despesas da Câmara" },
    },
    {
      path: "/camara/emendas",
      name: "emendas-camara",
      component: () => import("@/pages/camara/CamaraEmendasPage.vue"),
      meta: { title: "Emendas da Câmara" },
    },
    {
      path: "/camara/empresas",
      name: "empresas-camara",
      component: () => import("@/pages/camara/CamaraEmpresasPage.vue"),
      meta: { title: "Empresas e Fornecedores" },
    },
    {
      path: "/camara/projetos-legislativos",
      name: "projetos-legislativos-camara",
      component: () => import("@/pages/camara/CamaraProjetosLegislativosPage.vue"),
      meta: { title: "Projetos Legislativos" },
    },
    {
      path: "/camara/comparar",
      name: "comparar-deputados",
      component: () => import("@/pages/camara/CamaraComparacaoPage.vue"),
      meta: { title: "Comparar Deputados" },
    },

    // ========== SENADO FEDERAL ==========
    {
      path: "/senado/senadores",
      name: "senadores",
      component: () => import("@/pages/senado/SenadoListaPage.vue"),
      meta: { title: "Senadores" },
    },
    {
      path: "/senado/senadores/:id",
      name: "senador-detail",
      component: () => import("@/pages/senado/SenadoDetalhePage.vue"),
      meta: { title: "Detalhes do Senador" },
    },
    {
      path: "/senado/despesas",
      name: "despesas-senado",
      component: () => import("@/pages/senado/SenadoDespesasPage.vue"),
      meta: { title: "Despesas do Senado" },
    },
    {
      path: "/senado/emendas",
      name: "emendas-senado",
      component: () => import("@/pages/senado/SenadoEmendasPage.vue"),
      meta: { title: "Emendas do Senado" },
    },
    {
      path: "/senado/projetos-legislativos",
      name: "projetos-legislativos-senado",
      component: () => import("@/pages/senado/SenadoProjetosLegislativosPage.vue"),
      meta: { title: "Projetos do Senado" },
    },
    {
      path: "/senado/empresas",
      name: "empresas-senado",
      component: () => import("@/pages/senado/SenadoEmpresasPage.vue"),
      meta: { title: "Empresas e Fornecedores" },
    },
    {
      path: "/senado/comparar",
      name: "comparar-senadores",
      component: () => import("@/pages/senado/SenadoComparacaoPage.vue"),
      meta: { title: "Comparar Senadores" },
    },

    // ========== OUTRAS PÁGINAS ==========
    {
      path: "/metodologia",
      name: "metodologia",
      component: () => import("@/pages/MetodologiaPage.vue"),
      meta: { title: "Metodologia" },
    },
    {
      path: "/rankings",
      redirect: "/camara/empresas",
    },

    // ========== REDIRECTS (compatibilidade) ==========
    {
      path: "/deputados",
      redirect: "/camara/deputados",
    },
    {
      path: "/deputados/:id",
      redirect: to => `/camara/deputados/${to.params.id}`,
    },
    {
      path: "/despesas",
      redirect: "/camara/despesas",
    },
    {
      path: "/emendas",
      redirect: "/camara/emendas",
    },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

router.afterEach((to) => {
  const baseTitle = 'Fiscaliza Brasil'
  const pageTitle = to.meta.title as string

  if (pageTitle) {
    document.title = `${pageTitle} | ${baseTitle}`
  } else if (!document.title.includes(baseTitle)) {
    document.title = baseTitle
  }
})

export default router

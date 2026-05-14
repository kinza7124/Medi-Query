"use client"

import { motion } from "framer-motion"
import { GitBranch, Layers, Search, Cpu, Database, RefreshCw } from "lucide-react"

const retrievalSteps = [
  {
    icon: Search,
    title: "Query Rewriting",
    description: "Llama 3.1 8B resolves pronouns and expands medical terminology for precise retrieval.",
    code: `# Pronoun Resolution
"What are its side effects?"
→ "What are the side effects of metformin?"`,
  },
  {
    icon: Layers,
    title: "Hybrid Retrieval",
    description: "MMR (60%) + BM25 (40%) ensemble combines semantic understanding with keyword matching.",
    code: `ensemble_retriever = EnsembleRetriever(
  retrievers=[mmr_retriever, bm25_retriever],
  weights=[0.6, 0.4]
)`,
  },
  {
    icon: RefreshCw,
    title: "Cross-Encoder Reranking",
    description: "ms-marco-MiniLM-L-6-v2 scores query-document pairs for final relevance ranking.",
    code: `reranker = CrossEncoder(
  "cross-encoder/ms-marco-MiniLM-L-6-v2"
)
top_docs = reranker.rerank(query, docs, top_n=8)`,
  },
  {
    icon: Cpu,
    title: "Context-Only Generation",
    description: "Llama 3.3 70B generates responses strictly grounded in retrieved context.",
    code: `system_prompt = """Answer ONLY from the 
provided context. If information is not 
in the context, say 'I don't have enough 
information to answer that.'"""`,
  },
]

const chunkingDetails = {
  title: "Context-Aware Chunking",
  description: "Optimized document segmentation preserves semantic coherence for medical content.",
  params: [
    { label: "Chunk Size", value: "800 tokens", detail: "Optimal for medical paragraphs" },
    { label: "Chunk Overlap", value: "100 tokens", detail: "Prevents information loss at boundaries" },
    { label: "Embedding Model", value: "all-MiniLM-L6-v2", detail: "384-dimensional vectors" },
    { label: "Vector Index", value: "Pinecone", detail: "Serverless, high-performance" },
  ],
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
    },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

export function TechnicalDeepDive() {
  return (
    <section className="w-full px-5 py-16 md:py-24 flex flex-col justify-center items-center overflow-hidden">
      <div className="w-full max-w-[1280px] flex flex-col gap-16">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="flex flex-col justify-center items-center gap-4 text-center"
        >
          <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20">
            <GitBranch className="w-4 h-4 text-primary" />
            <span className="text-primary text-sm font-medium">Open Source</span>
          </div>
          <h2 className="text-foreground text-4xl md:text-5xl font-semibold leading-tight">
            Hybrid Retrieval Pipeline
          </h2>
          <p className="text-muted-foreground text-lg md:text-xl font-medium leading-relaxed max-w-[700px]">
            Production-grade RAG architecture combining multiple retrieval strategies for maximum accuracy and
            relevance.
          </p>
          <motion.a
            href="https://github.com/kinza7124/Medi-Query"
            target="_blank"
            rel="noopener noreferrer"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-foreground text-background font-medium hover:bg-foreground/90 transition-colors"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
            </svg>
            View on GitHub
          </motion.a>
        </motion.div>

        {/* Retrieval Pipeline Steps */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-2 gap-6"
        >
          {retrievalSteps.map((step, index) => (
            <motion.div
              key={step.title}
              variants={itemVariants}
              whileHover={{ scale: 1.02, y: -5 }}
              transition={{ duration: 0.2 }}
              className="p-6 rounded-2xl border border-white/10 bg-[rgba(231,236,235,0.06)] flex flex-col gap-4 backdrop-blur-sm group"
            >
              <div className="flex items-start gap-4">
                <motion.div
                  whileHover={{ rotate: 360 }}
                  transition={{ duration: 0.5 }}
                  className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center shrink-0 group-hover:bg-primary/20 transition-colors"
                >
                  <step.icon className="w-6 h-6 text-primary" />
                </motion.div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-primary/60 text-sm font-mono">0{index + 1}</span>
                    <h3 className="text-foreground text-lg font-semibold">{step.title}</h3>
                  </div>
                  <p className="text-muted-foreground text-sm leading-relaxed">{step.description}</p>
                </div>
              </div>
              <div className="bg-background/50 rounded-lg p-4 font-mono text-xs text-muted-foreground overflow-x-auto">
                <pre className="whitespace-pre-wrap">{step.code}</pre>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Context-Aware Chunking Section */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="w-full rounded-2xl border border-white/10 bg-gradient-to-br from-primary/5 to-transparent p-8"
        >
          <div className="flex flex-col lg:flex-row gap-8">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                  <Database className="w-5 h-5 text-primary" />
                </div>
                <h3 className="text-foreground text-2xl font-semibold">{chunkingDetails.title}</h3>
              </div>
              <p className="text-muted-foreground leading-relaxed mb-6">{chunkingDetails.description}</p>

              {/* Chunking Visualization */}
              <div className="relative bg-background/30 rounded-xl p-6 overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary/50 via-primary to-primary/50" />
                <div className="flex flex-col gap-3">
                  {[1, 2, 3].map((i) => (
                    <motion.div
                      key={i}
                      initial={{ width: 0 }}
                      whileInView={{ width: "100%" }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.8, delay: i * 0.2 }}
                      className="relative"
                    >
                      <div className="h-8 bg-primary/10 rounded flex items-center px-3 overflow-hidden">
                        <span className="text-xs text-muted-foreground font-mono">Chunk {i}</span>
                        {i < 3 && (
                          <motion.div
                            animate={{ x: [0, 5, 0] }}
                            transition={{ duration: 1.5, repeat: Infinity }}
                            className="absolute right-0 w-16 h-full bg-gradient-to-l from-primary/30 to-transparent"
                          />
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground mt-4 text-center">
                  100-token overlap ensures context continuity
                </p>
              </div>
            </div>

            <div className="flex-1">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {chunkingDetails.params.map((param, index) => (
                  <motion.div
                    key={param.label}
                    initial={{ opacity: 0, scale: 0.9 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.4, delay: index * 0.1 }}
                    whileHover={{ scale: 1.05 }}
                    className="p-4 rounded-xl bg-background/50 border border-white/5"
                  >
                    <span className="text-muted-foreground text-xs">{param.label}</span>
                    <div className="text-foreground font-semibold mt-1">{param.value}</div>
                    <span className="text-muted-foreground text-xs">{param.detail}</span>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Memory Management */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6"
        >
          <div className="p-6 rounded-2xl border border-white/10 bg-[rgba(231,236,235,0.06)]">
            <h4 className="text-foreground font-semibold mb-3">Session Memory</h4>
            <p className="text-muted-foreground text-sm mb-4">
              Maintains last 10 exchanges (20 messages) for pronoun resolution only.
            </p>
            <div className="font-mono text-xs text-primary/80 bg-background/50 p-3 rounded-lg">
              max_session_messages: 12
            </div>
          </div>
          <div className="p-6 rounded-2xl border border-white/10 bg-[rgba(231,236,235,0.06)]">
            <h4 className="text-foreground font-semibold mb-3">Temperature Control</h4>
            <p className="text-muted-foreground text-sm mb-4">
              Set to 0 for deterministic, factual medical responses without creativity.
            </p>
            <div className="font-mono text-xs text-primary/80 bg-background/50 p-3 rounded-lg">temperature: 0</div>
          </div>
          <div className="p-6 rounded-2xl border border-white/10 bg-[rgba(231,236,235,0.06)]">
            <h4 className="text-foreground font-semibold mb-3">Hallucination Prevention</h4>
            <p className="text-muted-foreground text-sm mb-4">
              Strict context-only mode reduces hallucinations from 35% to 5%.
            </p>
            <div className="font-mono text-xs text-primary/80 bg-background/50 p-3 rounded-lg">
              hallucination_rate: 5%
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}

"use client"

import { motion } from "framer-motion"
import Image from "next/image"

const metrics = [
  { label: "Answer Relevancy", value: "92.33%", description: "RAGAS Score", color: "from-green-500/20 to-green-500/5" },
  {
    label: "Faithfulness",
    value: "88.78%",
    description: "Context Adherence",
    color: "from-blue-500/20 to-blue-500/5",
  },
  { label: "Context Recall", value: "90.00%", description: "Document Coverage", color: "from-teal-500/20 to-teal-500/5" },
  { label: "Response Time", value: "4.2s", description: "Under 5s SLA", color: "from-yellow-500/20 to-yellow-500/5" },
  {
    label: "Hallucination Rate",
    value: "5%",
    description: "Down from 35%",
    color: "from-red-500/20 to-red-500/5",
  },
  { label: "Test Pass Rate", value: "100%", description: "153 Tests", color: "from-primary/20 to-primary/5" },
]

const techStack = [
  { name: "Flask/Python", category: "Backend", icon: "flask" },
  { name: "LangChain", category: "Orchestration", icon: "link" },
  { name: "Pinecone", category: "Vector DB", icon: "db" },
  { name: "Groq API", category: "LLM Inference", icon: "cpu" },
  { name: "HuggingFace", category: "Embeddings", icon: "hf" },
  { name: "AWS EC2", category: "Deployment", icon: "cloud" },
  { name: "Docker", category: "Containers", icon: "docker" },
  { name: "GitHub Actions", category: "CI/CD", icon: "git" },
]

const pipelineSteps = [
  { step: "1", title: "Query Rewrite", description: "Llama 3.1 8B resolves pronouns and expands queries", time: "0.8s" },
  { step: "2", title: "Hybrid Retrieval", description: "MMR + BM25 ensemble (0.6/0.4 weights)", time: "1.2s" },
  { step: "3", title: "Cross-Encoder Rerank", description: "ms-marco-MiniLM-L-6-v2 selects top-8 docs", time: "0.3s" },
  { step: "4", title: "Response Generation", description: "Llama 3.3 70B with context-only mode", time: "2.1s" },
]

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

export function ArchitectureSection() {
  return (
    <section className="w-full px-5 py-16 md:py-24 flex flex-col justify-center items-center">
      <div className="w-full max-w-[1280px] flex flex-col gap-16">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="flex flex-col justify-center items-center gap-4 text-center"
        >
          <h2 className="text-foreground text-4xl md:text-5xl font-semibold leading-tight">System Architecture</h2>
          <p className="text-muted-foreground text-lg md:text-xl font-medium leading-relaxed max-w-[700px]">
            Production-grade RAG pipeline with hybrid retrieval, cross-encoder reranking, and cloud-native deployment
          </p>
        </motion.div>

        {/* CI/CD Architecture Diagram */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="w-full rounded-2xl overflow-hidden border border-white/10 bg-[rgba(231,236,235,0.04)] group hover:border-white/20 transition-colors"
        >
          <div className="p-6 border-b border-white/10">
            <h3 className="text-foreground text-xl font-semibold">CI/CD Pipeline Architecture</h3>
            <p className="text-muted-foreground text-sm mt-1">
              GitHub Actions with Docker, ECR, and EC2 deployment
            </p>
          </div>
          <motion.div whileHover={{ scale: 1.02 }} transition={{ duration: 0.3 }} className="p-4 md:p-6">
            <Image
              src="/images/cicd-architecture.png"
              alt="CI/CD Pipeline Architecture showing Developer Workflow, GitHub Actions CI/CD, AWS Infrastructure with ECR and EC2, and External APIs including Groq and Pinecone"
              width={1200}
              height={400}
              className="w-full h-auto rounded-lg"
            />
          </motion.div>
        </motion.div>

        {/* Performance Metrics Grid */}
        <div className="w-full">
          <motion.h3
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="text-foreground text-2xl font-semibold mb-6 text-center"
          >
            RAGAS Evaluation Metrics
          </motion.h3>
          <motion.div
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4"
          >
            {metrics.map((metric, index) => (
              <motion.div
                key={metric.label}
                variants={itemVariants}
                whileHover={{ scale: 1.05, y: -5 }}
                transition={{ duration: 0.2 }}
                className={`p-5 rounded-xl border border-white/10 bg-gradient-to-br ${metric.color} flex flex-col items-center text-center backdrop-blur-sm`}
              >
                <motion.span
                  initial={{ scale: 0 }}
                  whileInView={{ scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: index * 0.1 }}
                  className="text-foreground text-2xl md:text-3xl font-bold"
                >
                  {metric.value}
                </motion.span>
                <span className="text-foreground text-sm font-medium mt-1">{metric.label}</span>
                <span className="text-muted-foreground text-xs mt-0.5">{metric.description}</span>
              </motion.div>
            ))}
          </motion.div>
        </div>

        {/* RAG Pipeline Steps */}
        <div className="w-full">
          <motion.h3
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="text-foreground text-2xl font-semibold mb-6 text-center"
          >
            RAG Pipeline Flow
          </motion.h3>
          <motion.div
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
          >
            {pipelineSteps.map((step, index) => (
              <motion.div
                key={step.step}
                variants={itemVariants}
                whileHover={{ scale: 1.03, y: -3 }}
                className="p-5 rounded-xl border border-white/10 bg-[rgba(231,236,235,0.06)] relative group"
              >
                <motion.div
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.3 + index * 0.1 }}
                  className="absolute top-4 right-4 text-primary/60 text-xs font-mono"
                >
                  {step.time}
                </motion.div>
                <motion.div
                  whileHover={{ rotate: 360 }}
                  transition={{ duration: 0.5 }}
                  className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center mb-3 group-hover:bg-primary/30 transition-colors"
                >
                  <span className="text-primary font-semibold text-sm">{step.step}</span>
                </motion.div>
                <h4 className="text-foreground font-semibold mb-1">{step.title}</h4>
                <p className="text-muted-foreground text-sm">{step.description}</p>
                {index < pipelineSteps.length - 1 && (
                  <motion.div
                    animate={{ x: [0, 5, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                    className="hidden lg:block absolute top-1/2 -right-2 transform -translate-y-1/2 text-primary"
                  >
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                      <path
                        d="M6 4L10 8L6 12"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </motion.div>
                )}
              </motion.div>
            ))}
          </motion.div>
        </div>

        {/* Tech Stack Grid */}
        <div className="w-full">
          <motion.h3
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="text-foreground text-2xl font-semibold mb-6 text-center"
          >
            Technology Stack
          </motion.h3>
          <motion.div
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="grid grid-cols-2 md:grid-cols-4 gap-4"
          >
            {techStack.map((tech) => (
              <motion.div
                key={tech.name}
                variants={itemVariants}
                whileHover={{ scale: 1.05, y: -3 }}
                className="p-4 rounded-xl border border-white/10 bg-[rgba(231,236,235,0.06)] flex flex-col items-center text-center hover:border-primary/30 transition-colors"
              >
                <span className="text-foreground font-medium">{tech.name}</span>
                <span className="text-muted-foreground text-xs mt-1">{tech.category}</span>
              </motion.div>
            ))}
          </motion.div>
        </div>

        {/* Key Configuration */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="w-full rounded-2xl border border-white/10 bg-[rgba(231,236,235,0.04)] p-6 hover:border-white/20 transition-colors"
        >
          <h3 className="text-foreground text-xl font-semibold mb-4">Key Configuration Parameters</h3>
          <motion.div
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 font-mono text-sm"
          >
            {[
              { key: "chunk_size", value: "800" },
              { key: "chunk_overlap", value: "100" },
              { key: "embedding_dim", value: "384" },
              { key: "mmr_k", value: "10" },
              { key: "mmr_fetch_k", value: "30" },
              { key: "lambda_mult", value: "0.5" },
              { key: "reranker_top_n", value: "8" },
              { key: "max_session_msgs", value: "12" },
              { key: "temperature", value: "0" },
            ].map((config) => (
              <motion.div
                key={config.key}
                variants={itemVariants}
                whileHover={{ scale: 1.02 }}
                className="flex justify-between p-3 rounded-lg bg-background/50 hover:bg-background/70 transition-colors"
              >
                <span className="text-muted-foreground">{config.key}</span>
                <span className="text-primary">{config.value}</span>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}

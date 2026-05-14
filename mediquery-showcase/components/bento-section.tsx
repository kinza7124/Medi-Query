"use client"

import { motion } from "framer-motion"
import AiCodeReviews from "./bento/ai-code-reviews"
import RealtimeCodingPreviews from "./bento/real-time-previews"
import OneClickIntegrationsIllustration from "./bento/one-click-integrations-illustration"
import MCPConnectivityIllustration from "./bento/mcp-connectivity-illustration"
import EasyDeployment from "./bento/easy-deployment"
import ParallelCodingAgents from "./bento/parallel-agents"

const BentoCard = ({
  title,
  description,
  Component,
  index,
}: {
  title: string
  description: string
  Component: React.ComponentType
  index: number
}) => (
  <motion.div
    initial={{ opacity: 0, y: 30 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true }}
    transition={{ duration: 0.5, delay: index * 0.1 }}
    whileHover={{ scale: 1.02, y: -5 }}
    className="overflow-hidden rounded-2xl border border-white/20 flex flex-col justify-start items-start relative group"
  >
    {/* Background with blur effect */}
    <div
      className="absolute inset-0 rounded-2xl transition-all duration-300"
      style={{
        background: "rgba(231, 236, 235, 0.08)",
        backdropFilter: "blur(4px)",
        WebkitBackdropFilter: "blur(4px)",
      }}
    />
    {/* Hover gradient overlay */}
    <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

    <div className="self-stretch p-6 flex flex-col justify-start items-start gap-2 relative z-10">
      <div className="self-stretch flex flex-col justify-start items-start gap-1.5">
        <p className="self-stretch text-foreground text-lg font-normal leading-7">
          {title} <br />
          <span className="text-muted-foreground">{description}</span>
        </p>
      </div>
    </div>
    <div className="self-stretch h-72 relative -mt-0.5 z-10">
      <Component />
    </div>
  </motion.div>
)

export function BentoSection() {
  const cards = [
    {
      title: "RAG-Powered Accuracy.",
      description: "92% answer relevancy with source-grounded medical responses.",
      Component: AiCodeReviews,
    },
    {
      title: "Hybrid Retrieval Pipeline",
      description: "MMR + BM25 ensemble with cross-encoder reranking for precision.",
      Component: RealtimeCodingPreviews,
    },
    {
      title: "AWS Cloud Deployment",
      description: "Docker containers on EC2 with GitHub Actions CI/CD pipeline.",
      Component: OneClickIntegrationsIllustration,
    },
    {
      title: "Vector Search with Pinecone",
      description: "384-dim embeddings for semantic medical document retrieval.",
      Component: MCPConnectivityIllustration,
    },
    {
      title: "Llama 3.3 70B Generation",
      description: "Context-only LLM responses with 88.7% faithfulness score.",
      Component: ParallelCodingAgents,
    },
    {
      title: "Comprehensive Testing Suite",
      description: "153 tests covering unit, integration, security, and performance.",
      Component: EasyDeployment,
    },
  ]

  return (
    <section className="w-full px-5 flex flex-col justify-center items-center overflow-visible bg-transparent">
      <div className="w-full py-8 md:py-16 relative flex flex-col justify-start items-start gap-6">
        {/* Animated background blob */}
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            rotate: [0, 45, 0],
          }}
          transition={{
            duration: 15,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          className="w-[547px] h-[938px] absolute top-[614px] left-[80px] origin-top-left rotate-[-33.39deg] bg-primary/10 blur-[130px] z-0"
        />

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="self-stretch py-8 md:py-14 flex flex-col justify-center items-center gap-2 z-10"
        >
          <div className="flex flex-col justify-start items-center gap-4">
            <h2 className="w-full max-w-[655px] text-center text-foreground text-4xl md:text-6xl font-semibold leading-tight md:leading-[66px]">
              Technical Architecture
            </h2>
            <p className="w-full max-w-[600px] text-center text-muted-foreground text-lg md:text-xl font-medium leading-relaxed">
              Built with production-grade RAG pipeline featuring hybrid retrieval, cross-encoder reranking, and
              cloud-native deployment on AWS infrastructure.
            </p>
          </div>
        </motion.div>

        <div className="self-stretch grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 z-10">
          {cards.map((card, index) => (
            <BentoCard key={card.title} {...card} index={index} />
          ))}
        </div>
      </div>
    </section>
  )
}

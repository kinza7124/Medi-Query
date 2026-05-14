"use client"

import { motion } from "framer-motion"
import { FileText, Shield, Zap, TestTube, Server, Database } from "lucide-react"

const docSections = [
  {
    icon: FileText,
    title: "Software Requirements Specification",
    description:
      "IEEE 830-1998 compliant SRS document covering functional and non-functional requirements, system architecture, and use cases.",
    features: ["27 Functional Requirements", "12 Non-Functional Requirements", "IEEE Standard Format"],
  },
  {
    icon: Database,
    title: "RAG Architecture",
    description:
      "Complete documentation of the Retrieval-Augmented Generation pipeline including document indexing, query processing, and response generation.",
    features: ["Document Indexing Pipeline", "Hybrid Retrieval System", "Cross-Encoder Reranking"],
  },
  {
    icon: Server,
    title: "CI/CD Pipeline",
    description:
      "GitHub Actions workflow with Docker containerization, Amazon ECR registry, and automated EC2 deployment.",
    features: ["Automated Testing", "Docker Containerization", "AWS Deployment"],
  },
  {
    icon: Zap,
    title: "RAGAS Evaluation Report",
    description:
      "Comprehensive evaluation using the RAGAS framework measuring faithfulness, relevancy, precision, and recall metrics.",
    features: ["92.33% Answer Relevancy", "88.78% Faithfulness", "90% Context Recall"],
  },
  {
    icon: TestTube,
    title: "Testing Documentation",
    description:
      "Complete test suite documentation covering unit, integration, security, performance, and system workflow tests.",
    features: ["153 Total Tests", "100% Pass Rate", "9 Test Categories"],
  },
  {
    icon: Shield,
    title: "Security Testing",
    description:
      "Security vulnerability testing including XSS prevention, SQL injection protection, and API key security validation.",
    features: ["XSS Protection", "SQLi Prevention", "API Security"],
  },
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

export function DocumentationSection() {
  return (
    <section className="w-full px-5 py-16 md:py-24 flex flex-col justify-center items-center">
      <div className="w-full max-w-[1280px] flex flex-col gap-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="flex flex-col justify-center items-center gap-4 text-center"
        >
          <h2 className="text-foreground text-4xl md:text-5xl font-semibold leading-tight">Technical Documentation</h2>
          <p className="text-muted-foreground text-lg md:text-xl font-medium leading-relaxed max-w-[700px]">
            Comprehensive documentation covering architecture, testing, deployment, and evaluation metrics
          </p>
        </motion.div>

        {/* Documentation Cards Grid */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {docSections.map((doc) => (
            <motion.div
              key={doc.title}
              variants={itemVariants}
              whileHover={{ scale: 1.02, y: -5 }}
              transition={{ duration: 0.2 }}
              className="p-6 rounded-2xl border border-white/10 bg-[rgba(231,236,235,0.06)] flex flex-col gap-4 hover:border-primary/30 transition-colors group"
            >
              <motion.div
                whileHover={{ rotate: 360 }}
                transition={{ duration: 0.5 }}
                className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors"
              >
                <doc.icon className="w-6 h-6 text-primary" />
              </motion.div>
              <div>
                <h3 className="text-foreground text-lg font-semibold mb-2">{doc.title}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">{doc.description}</p>
              </div>
              <div className="flex flex-wrap gap-2 mt-auto pt-2">
                {doc.features.map((feature) => (
                  <span
                    key={feature}
                    className="px-3 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary"
                  >
                    {feature}
                  </span>
                ))}
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Key Highlights */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="w-full rounded-2xl border border-white/10 bg-[rgba(231,236,235,0.04)] p-6 md:p-8 hover:border-white/20 transition-colors"
        >
          <h3 className="text-foreground text-xl font-semibold mb-6 text-center">Project Highlights</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="space-y-4"
            >
              <h4 className="text-foreground font-medium">Problem Solved</h4>
              <ul className="space-y-2 text-muted-foreground text-sm">
                {[
                  "Information overload in medical queries reduced through curated retrieval",
                  "Hallucination rate reduced from 35% to 5% using RAG architecture",
                  "Context loss in conversations handled via pronoun resolution",
                  "Source attribution enables response verification",
                ].map((item, index) => (
                  <motion.li
                    key={index}
                    initial={{ opacity: 0, x: -10 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.3, delay: index * 0.1 }}
                    className="flex items-start gap-2"
                  >
                    <span className="text-primary mt-1">&#8226;</span>
                    {item}
                  </motion.li>
                ))}
              </ul>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="space-y-4"
            >
              <h4 className="text-foreground font-medium">Key Achievements</h4>
              <ul className="space-y-2 text-muted-foreground text-sm">
                {[
                  "92% accuracy vs 65% for non-RAG systems (+27% improvement)",
                  "100% SLA compliance with all queries under 5 seconds",
                  "Production-ready with Gunicorn, health endpoint, and Docker",
                  "Automated CI/CD with GitHub Actions and AWS deployment",
                ].map((item, index) => (
                  <motion.li
                    key={index}
                    initial={{ opacity: 0, x: 10 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.3, delay: index * 0.1 }}
                    className="flex items-start gap-2"
                  >
                    <span className="text-primary mt-1">&#8226;</span>
                    {item}
                  </motion.li>
                ))}
              </ul>
            </motion.div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}

"use client"

import type React from "react"
import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { ChevronDown } from "lucide-react"

const faqData = [
  {
    question: "What is Medi-Query and how does it work?",
    answer:
      "Medi-Query is an AI-powered medical chatbot that uses Retrieval-Augmented Generation (RAG) to provide evidence-based health information. It retrieves relevant medical documents from a Pinecone vector database, uses Llama 3.3 70B for generation, and ensures responses are strictly grounded in verified medical sources.",
  },
  {
    question: "How accurate is the RAG pipeline?",
    answer:
      "Our RAG pipeline achieves 92.33% answer relevancy, 88.78% faithfulness (context adherence), and 90% context recall. The system reduces hallucinations from 35% (generic LLMs) to just 5%, with all responses under the 5-second SLA target.",
  },
  {
    question: "What technology stack powers Medi-Query?",
    answer:
      "The backend uses Flask/Python with LangChain for orchestration. We use Pinecone for vector storage, HuggingFace embeddings (all-MiniLM-L6-v2), cross-encoder reranking (ms-marco-MiniLM-L-6-v2), and Groq API for LLM inference with Llama 3.1 8B for query rewriting and Llama 3.3 70B for response generation.",
  },
  {
    question: "How is the system deployed?",
    answer:
      "Medi-Query runs on AWS EC2 instances with Docker containerization. We use GitHub Actions for CI/CD with automated testing, Amazon ECR for container registry, and Gunicorn as the production WSGI server on port 8080. The pipeline includes health checks and automatic rollback capabilities.",
  },
  {
    question: "What testing coverage does Medi-Query have?",
    answer:
      "Our comprehensive test suite includes 153 tests across 9 categories: unit tests, smoke tests, regression tests, functional tests, integration tests, security tests (XSS/SQLi protection), performance tests, and system workflow tests. All core tests pass with 100% success rate.",
  },
  {
    question: "How does the conversation memory work?",
    answer:
      "The system maintains session-based memory storing the last 10 chat exchanges (20 messages max). This is used exclusively for pronoun resolution (e.g., 'What are its causes?' referring to a previously mentioned condition) - not for topic substitution - ensuring responses stay current and accurate.",
  },
]

interface FAQItemProps {
  question: string
  answer: string
  isOpen: boolean
  onToggle: () => void
  index: number
}

const FAQItem = ({ question, answer, isOpen, onToggle, index }: FAQItemProps) => {
  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault()
    onToggle()
  }
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      whileHover={{ scale: 1.01 }}
      className={`w-full bg-[rgba(231,236,235,0.08)] shadow-[0px_2px_4px_rgba(0,0,0,0.16)] overflow-hidden rounded-[10px] outline outline-1 outline-border outline-offset-[-1px] transition-all duration-500 ease-out cursor-pointer hover:bg-[rgba(231,236,235,0.12)]`}
      onClick={handleClick}
    >
      <div className="w-full px-5 py-[18px] pr-4 flex justify-between items-center gap-5 text-left transition-all duration-300 ease-out">
        <div className="flex-1 text-foreground text-base font-medium leading-6 break-words">{question}</div>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.3 }}
          className="flex justify-center items-center"
        >
          <ChevronDown className="w-6 h-6 text-muted-foreground-dark" />
        </motion.div>
      </div>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-[18px] pt-2">
              <div className="text-foreground/80 text-sm font-normal leading-6 break-words">{answer}</div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export function FAQSection() {
  const [openItems, setOpenItems] = useState<Set<number>>(new Set())
  const toggleItem = (index: number) => {
    const newOpenItems = new Set(openItems)
    if (newOpenItems.has(index)) {
      newOpenItems.delete(index)
    } else {
      newOpenItems.add(index)
    }
    setOpenItems(newOpenItems)
  }
  return (
    <section className="w-full pt-[66px] pb-20 md:pb-40 px-5 relative flex flex-col justify-center items-center">
      <motion.div
        animate={{
          scale: [1, 1.1, 1],
          rotate: [0, 10, 0],
        }}
        transition={{
          duration: 10,
          repeat: Infinity,
          ease: "easeInOut",
        }}
        className="w-[300px] h-[500px] absolute top-[150px] left-1/2 -translate-x-1/2 origin-top-left rotate-[-33.39deg] bg-primary/10 blur-[100px] z-0"
      />
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        className="self-stretch pt-8 pb-8 md:pt-14 md:pb-14 flex flex-col justify-center items-center gap-2 relative z-10"
      >
        <div className="flex flex-col justify-start items-center gap-4">
          <h2 className="w-full max-w-[435px] text-center text-foreground text-4xl font-semibold leading-10 break-words">
            Frequently Asked Questions
          </h2>
          <p className="self-stretch text-center text-muted-foreground text-sm font-medium leading-[18.20px] break-words">
            Everything you need to know about Medi-Query&apos;s RAG architecture and technical implementation
          </p>
        </div>
      </motion.div>
      <div className="w-full max-w-[600px] pt-0.5 pb-10 flex flex-col justify-start items-start gap-4 relative z-10">
        {faqData.map((faq, index) => (
          <FAQItem key={index} {...faq} isOpen={openItems.has(index)} onToggle={() => toggleItem(index)} index={index} />
        ))}
      </div>
    </section>
  )
}

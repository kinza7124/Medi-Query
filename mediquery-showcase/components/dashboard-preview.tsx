"use client"

import Image from "next/image"
import { motion } from "framer-motion"

export function DashboardPreview() {
  return (
    <div className="w-[calc(100vw-32px)] md:w-[1160px] relative">
      {/* Floating badges */}
      <motion.div
        initial={{ opacity: 0, x: -50 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.8, duration: 0.6 }}
        className="absolute -left-4 md:-left-12 top-1/4 z-20 hidden md:block"
      >
        <div className="bg-background/90 backdrop-blur-sm border border-primary/20 rounded-xl p-3 shadow-lg">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
              <svg className="w-4 h-4 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-foreground">Hybrid Retrieval</p>
              <p className="text-[10px] text-muted-foreground">MMR + BM25</p>
            </div>
          </div>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: 50 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 1, duration: 0.6 }}
        className="absolute -right-4 md:-right-12 top-1/3 z-20 hidden md:block"
      >
        <div className="bg-background/90 backdrop-blur-sm border border-primary/20 rounded-xl p-3 shadow-lg">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center">
              <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-foreground">92% Accuracy</p>
              <p className="text-[10px] text-muted-foreground">RAGAS Evaluated</p>
            </div>
          </div>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1.2, duration: 0.6 }}
        className="absolute -bottom-6 left-1/4 z-20 hidden md:block"
      >
        <div className="bg-background/90 backdrop-blur-sm border border-primary/20 rounded-xl p-3 shadow-lg">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center">
              <svg className="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-foreground">Pinecone Vector DB</p>
              <p className="text-[10px] text-muted-foreground">384-dim embeddings</p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Main preview container */}
      <motion.div
        initial={{ opacity: 0, y: 30, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="relative"
      >
        {/* Glow effect */}
        <div className="absolute -inset-4 bg-gradient-to-r from-primary/20 via-primary/10 to-primary/20 rounded-3xl blur-2xl opacity-50" />
        
        {/* VS Code Preview */}
        <div className="relative bg-[#1e1e1e] rounded-2xl overflow-hidden shadow-2xl border border-white/10">
          {/* Window controls */}
          <div className="flex items-center gap-2 px-4 py-3 bg-[#323233] border-b border-white/5">
            <div className="flex gap-2">
              <div className="w-3 h-3 rounded-full bg-[#ff5f57]" />
              <div className="w-3 h-3 rounded-full bg-[#febc2e]" />
              <div className="w-3 h-3 rounded-full bg-[#28c840]" />
            </div>
            <div className="flex-1 text-center">
              <span className="text-xs text-gray-400 font-mono">Medical-AI-Chatbot - Visual Studio Code</span>
            </div>
          </div>
          
          {/* Code content */}
          <Image
            src="/images/vscode-preview.png"
            alt="VS Code showing Medi-Query RAG chatbot implementation with Python and HTML code"
            width={1160}
            height={650}
            className="w-full h-auto object-cover"
            priority
          />
        </div>

        {/* Decorative elements */}
        <motion.div
          animate={{ 
            rotate: [0, 360],
          }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          className="absolute -top-8 -right-8 w-16 h-16 border border-primary/20 rounded-full hidden lg:block"
        />
        <motion.div
          animate={{ 
            rotate: [360, 0],
          }}
          transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
          className="absolute -bottom-8 -left-8 w-20 h-20 border border-primary/10 rounded-full hidden lg:block"
        />
      </motion.div>
    </div>
  )
}

"use client"

import React from "react"
import { Button } from "@/components/ui/button"
import { Header } from "./header"
import Link from "next/link"
import { motion } from "framer-motion"
import { CheckCircle2, ShieldCheck, Activity, Github, ArrowRight } from "lucide-react"

export function HeroSection() {
  return (
    <section
      className="flex flex-col items-center text-center relative mx-auto rounded-3xl overflow-hidden my-6 py-0 px-4
         w-full h-auto min-h-[500px] md:w-[1220px] md:min-h-[600px] lg:min-h-[810px] md:px-0 bg-[#0c0f0e]"
    >
      {/* Dynamic Background Elements */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-primary/20 rounded-full blur-[120px] animate-pulse" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[400px] h-[400px] bg-primary-dark/10 rounded-full blur-[100px]" />
        
        {/* SVG Grid Overlay */}
        <svg className="absolute inset-0 w-full h-full opacity-[0.15]" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>

      {/* Header positioned at top of hero container */}
      <div className="absolute top-0 left-0 right-0 z-20">
        <Header />
      </div>

      {/* Animated content */}
      <div className="relative z-10 flex flex-col items-center justify-center h-full pt-24 md:pt-32 lg:pt-40 pb-20">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="space-y-6 md:space-y-8 max-w-4xl px-4"
        >
          {/* Enhanced Badge */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/30 backdrop-blur-md shadow-[0_0_15px_rgba(120,252,214,0.2)] mb-2"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
            </span>
            <span className="text-xs md:text-sm font-bold text-primary tracking-wider uppercase">RAG-Powered Medical Intelligence</span>
          </motion.div>

          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="text-white text-4xl md:text-6xl lg:text-7xl font-bold leading-[1.1] tracking-tight"
          >
            MediQuery <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-primary-light to-primary-dark animate-gradient">
              Powered by RAG
            </span>
          </motion.h1>

          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="text-gray-400 text-base md:text-lg lg:text-xl font-medium leading-relaxed max-w-2xl mx-auto"
          >
            Next-generation clinical assistant providing source-grounded medical insights. 
            Built for accuracy, reliability, and clinical safety.
          </motion.p>

          {/* Stats row with Icons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.5 }}
            className="flex flex-wrap justify-center gap-6 md:gap-12 pt-4"
          >
            <div className="flex items-center gap-2.5 group cursor-default">
              <div className="p-2 rounded-lg bg-green-500/10 group-hover:bg-green-500/20 transition-colors">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
              </div>
              <div className="text-left">
                <div className="text-white font-bold text-lg leading-none">92%</div>
                <div className="text-[10px] uppercase tracking-wider text-gray-500 font-bold">Accuracy</div>
              </div>
            </div>
            <div className="flex items-center gap-2.5 group cursor-default">
              <div className="p-2 rounded-lg bg-blue-500/10 group-hover:bg-blue-500/20 transition-colors">
                <ShieldCheck className="w-5 h-5 text-blue-500" />
              </div>
              <div className="text-left">
                <div className="text-white font-bold text-lg leading-none">5%</div>
                <div className="text-[10px] uppercase tracking-wider text-gray-500 font-bold">Hallucination</div>
              </div>
            </div>
            <div className="flex items-center gap-2.5 group cursor-default">
              <div className="p-2 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
                <Activity className="w-5 h-5 text-primary" />
              </div>
              <div className="text-left">
                <div className="text-white font-bold text-lg leading-none">153+</div>
                <div className="text-[10px] uppercase tracking-wider text-gray-500 font-bold">Test Cases</div>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            className="pt-8"
          >
            <Link href="https://github.com/kinza7124/Medi-Query" target="_blank" rel="noopener noreferrer">
              <Button className="relative z-10 bg-primary text-primary-foreground hover:bg-primary/90 px-10 py-7 rounded-full font-bold text-lg shadow-[0_0_20px_rgba(120,252,214,0.3)] hover:shadow-[0_0_30px_rgba(120,252,214,0.5)] transition-all duration-300 group overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000" />
                <Github className="w-6 h-6 mr-3" />
                Explore on GitHub
                <ArrowRight className="w-5 h-5 ml-3 group-hover:translate-x-2 transition-transform" />
              </Button>
            </Link>
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}

"use client"

import { motion } from "framer-motion"
import type { ReactNode } from "react"

interface TechLogo {
  name: string
  icon?: string
  svg?: ReactNode
}

const techLogos: TechLogo[] = [
  { name: "Python", icon: "https://cdn.simpleicons.org/python/eeeeee" },
  { name: "Flask", icon: "https://cdn.simpleicons.org/flask/eeeeee" },
  { name: "LangChain", icon: "https://cdn.simpleicons.org/langchain/eeeeee" },
  { 
    name: "Pinecone", 
    svg: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-full h-full scale-125">
        <path d="M12 2C12 2 15 6 15 10C15 14 12 18 12 18C12 18 9 14 9 10C9 6 12 2 12 2Z" />
        <path d="M12 18C12 18 15 19.5 15 21C15 22.5 12 23 12 23C12 23 9 22.5 9 21C9 19.5 12 18Z" />
      </svg>
    )
  },
  { 
    name: "Groq", 
    svg: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-full h-full scale-90">
        <path d="M13 2L3 14h9v8l10-12h-9l9-10z" />
      </svg>
    )
  },
  { 
    name: "AWS", 
    svg: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-full h-full scale-110">
        <path d="M12.428 14.302c-1.341 0-2.316-.403-2.316-1.536 0-1.111.975-1.513 2.316-1.513 1.321 0 2.296.402 2.296 1.513 0 1.133-.975 1.536-2.296 1.536zm4.613-5.267v2.106s-.613-.347-1.423-.347c-.829 0-1.282.427-1.282.427s-.403-.664-1.912-.664c-2.454 0-4.636 1.114-4.636 3.743 0 2.583 2.182 3.696 4.636 3.696.853 0 1.912-.426 1.912-.426s.213.615.995.615c.613 0 1.71-.346 1.71-.346v-3.697c0-2.302-1.854-3.565-3.83-3.565-1.87 0-3.351.877-3.351.877l.711 1.63s1.182-.828 2.64-.828c.95 0 1.83.473 1.83 1.403v.403s-.473-.347-1.423-.347c-2.582 0-4.636 1.303-4.636 3.696 0 2.455 2.155 3.696 4.636 3.696 2.086 0 2.702-1.303 2.702-1.303s.347.664.829.664c.563 0 1.83-.347 1.83-.347v-8.13s-.664-.403-1.636-.403c-1.185 0-1.782.427-1.782.427V9.035z" />
        <path d="M12.441 18.012c-4.42 0-8.256-1.574-10.437-3.955l-.75.67c2.316 2.568 6.471 4.285 11.187 4.285c3.313 0 6.643-.853 8.795-2.583l-.613-.71c-1.909 1.513-4.88 2.293-8.182 2.293z" />
      </svg>
    )
  },
  { name: "Docker", icon: "https://cdn.simpleicons.org/docker/eeeeee" },
  { name: "GitHub Actions", icon: "https://cdn.simpleicons.org/githubactions/eeeeee" },
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

export function SocialProof() {
  return (
    <section className="self-stretch py-12 flex flex-col justify-center items-center gap-8 overflow-hidden">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="text-center text-gray-400 text-sm font-semibold tracking-widest uppercase"
      >
        Built with production-grade technologies
      </motion.div>
      <motion.div
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true }}
        className="self-stretch grid grid-cols-4 md:grid-cols-8 gap-8 md:gap-12 justify-items-center px-4"
      >
        {techLogos.map((tech) => (
          <motion.div
            key={tech.name}
            variants={itemVariants}
            whileHover={{ scale: 1.1, y: -5 }}
            transition={{ type: "spring", stiffness: 300 }}
            className="group flex flex-col items-center gap-3"
          >
            <div className="relative w-10 h-10 md:w-12 md:h-12 flex items-center justify-center grayscale group-hover:grayscale-0 transition-all duration-300 opacity-60 group-hover:opacity-100 text-gray-300 group-hover:text-primary">
              {tech.svg ? (
                tech.svg
              ) : (
                <img 
                  src={tech.icon} 
                  alt={tech.name} 
                  className="max-w-full max-h-full object-contain"
                  onError={(e) => {
                    e.currentTarget.src = `https://ui-avatars.com/api/?name=${tech.name}&background=333&color=fff`;
                  }}
                />
              )}
            </div>
            <span className="text-gray-500 group-hover:text-gray-300 text-[10px] md:text-xs font-semibold transition-colors duration-300 whitespace-nowrap">
              {tech.name}
            </span>
          </motion.div>
        ))}
      </motion.div>
    </section>
  )
}

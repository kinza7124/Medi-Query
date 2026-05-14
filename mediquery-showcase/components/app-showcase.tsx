"use client"

import { motion } from "framer-motion"
import Image from "next/image"

export function AppShowcase() {
  return (
    <section className="w-full px-5 py-16 md:py-24 flex flex-col justify-center items-center overflow-hidden">
      <div className="w-full max-w-[1280px] flex flex-col gap-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="flex flex-col justify-center items-center gap-4 text-center"
        >
          <h2 className="text-foreground text-4xl md:text-5xl font-semibold leading-tight">
            Intelligent Medical Assistant
          </h2>
          <p className="text-muted-foreground text-lg md:text-xl font-medium leading-relaxed max-w-[700px]">
            Beautiful, responsive interface with light and dark modes. Get evidence-based medical information with
            source citations.
          </p>
        </motion.div>

        {/* Phone Mockups */}
        <div className="relative flex justify-center items-center gap-8 md:gap-16 py-8">
          {/* Floating gradient background */}
          <div className="absolute inset-0 overflow-hidden">
            <motion.div
              animate={{
                scale: [1, 1.2, 1],
                rotate: [0, 180, 360],
              }}
              transition={{
                duration: 20,
                repeat: Infinity,
                ease: "linear",
              }}
              className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary/10 rounded-full blur-[100px]"
            />
          </div>

          {/* Light Mode Phone */}
          <motion.div
            initial={{ opacity: 0, x: -50, rotateY: 15 }}
            whileInView={{ opacity: 1, x: 0, rotateY: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.2 }}
            whileHover={{ scale: 1.05, rotateY: -5 }}
            className="relative z-10"
          >
            <div className="relative">
              <Image
                src="/images/app-light-mode.png"
                alt="Medi-Query Light Mode - Showing asthma causes conversation"
                width={280}
                height={560}
                className="rounded-[2rem] shadow-2xl shadow-black/30"
              />
              <motion.div
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="absolute -bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 bg-foreground/10 backdrop-blur-sm rounded-full"
              >
                <span className="text-foreground text-sm font-medium">Light Mode</span>
              </motion.div>
            </div>
          </motion.div>

          {/* Dark Mode Phone */}
          <motion.div
            initial={{ opacity: 0, x: 50, rotateY: -15 }}
            whileInView={{ opacity: 1, x: 0, rotateY: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.4 }}
            whileHover={{ scale: 1.05, rotateY: 5 }}
            className="relative z-10"
          >
            <div className="relative">
              <Image
                src="/images/app-dark-mode.png"
                alt="Medi-Query Dark Mode - Showing asthma diagnosis and treatment conversation"
                width={280}
                height={560}
                className="rounded-[2rem] shadow-2xl shadow-black/30"
              />
              <motion.div
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 2, repeat: Infinity, delay: 1 }}
                className="absolute -bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 bg-foreground/10 backdrop-blur-sm rounded-full"
              >
                <span className="text-foreground text-sm font-medium">Dark Mode</span>
              </motion.div>
            </div>
          </motion.div>
        </div>

        {/* Feature Highlights */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-4"
        >
          {[
            { label: "Response Time", value: "<5s", icon: "lightning" },
            { label: "Accuracy", value: "92%", icon: "chart" },
            { label: "Source Citations", value: "Yes", icon: "book" },
            { label: "Themes", value: "2", icon: "palette" },
          ].map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: 0.1 * index }}
              whileHover={{ scale: 1.05, y: -5 }}
              className="p-5 rounded-2xl border border-white/10 bg-[rgba(231,236,235,0.06)] flex flex-col items-center text-center backdrop-blur-sm"
            >
              <span className="text-foreground text-3xl font-bold">{stat.value}</span>
              <span className="text-muted-foreground text-sm mt-1">{stat.label}</span>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}

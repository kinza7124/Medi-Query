"use client"

import { motion } from "framer-motion"
import Image from "next/image"

export function LargeTestimonial() {
  return (
    <section className="w-full px-5 overflow-hidden flex justify-center items-center">
      <div className="flex-1 flex flex-col justify-start items-start overflow-hidden">
        <div className="self-stretch px-4 py-12 md:px-6 md:py-16 lg:py-28 flex flex-col justify-start items-start gap-2">
          <div className="self-stretch flex justify-between items-center">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="flex-1 px-4 py-8 md:px-12 lg:px-20 md:py-8 lg:py-10 overflow-hidden rounded-lg flex flex-col justify-center items-center gap-6 md:gap-8 lg:gap-11 relative"
            >
              {/* Decorative quote marks */}
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                whileInView={{ opacity: 0.1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: 0.2 }}
                className="absolute top-0 left-0 md:left-10 text-primary text-[120px] md:text-[200px] font-serif leading-none select-none"
              >
                &ldquo;
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: 0.3 }}
                className="w-full max-w-[1024px] text-center text-foreground leading-7 md:leading-10 lg:leading-[64px] font-medium text-lg md:text-3xl lg:text-5xl relative z-10"
              >
                {
                  "Medi-Query's RAG pipeline achieves 92% answer relevancy and reduces hallucinations from 35% to just 5%, making medical AI truly reliable."
                }
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: 0.5 }}
                className="flex justify-start items-center gap-5"
              >
                <motion.div whileHover={{ scale: 1.1 }} transition={{ duration: 0.2 }}>
                  <Image
                    src="/images/guillermo-rauch.png"
                    alt="Project Lead avatar"
                    width={48}
                    height={48}
                    className="w-12 h-12 relative rounded-full ring-2 ring-primary/20"
                    style={{ border: "1px solid rgba(0, 0, 0, 0.08)" }}
                  />
                </motion.div>
                <div className="flex flex-col justify-start items-start">
                  <div className="text-foreground text-base font-medium leading-6">Kinza</div>
                  <div className="text-muted-foreground text-sm font-normal leading-6">{"Project Author"}</div>
                </div>
              </motion.div>

              {/* Stats row */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: 0.7 }}
                className="flex flex-wrap justify-center gap-6 md:gap-12 mt-6 pt-6 border-t border-white/10"
              >
                {[
                  { value: "92%", label: "Accuracy" },
                  { value: "5%", label: "Hallucination" },
                  { value: "<5s", label: "Response Time" },
                  { value: "153", label: "Tests Passed" },
                ].map((stat, index) => (
                  <motion.div
                    key={stat.label}
                    initial={{ opacity: 0, scale: 0.8 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.4, delay: 0.8 + index * 0.1 }}
                    className="flex flex-col items-center"
                  >
                    <span className="text-primary text-2xl md:text-3xl font-bold">{stat.value}</span>
                    <span className="text-muted-foreground text-xs md:text-sm">{stat.label}</span>
                  </motion.div>
                ))}
              </motion.div>
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  )
}

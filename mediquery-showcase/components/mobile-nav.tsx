"use client"

import React, { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Home, Zap, GitBranch, FileText, MessageSquare } from "lucide-react"
import { cn } from "@/lib/utils"

const navItems = [
  { name: "Home", href: "#", icon: Home },
  { name: "Features", href: "#features-section", icon: Zap },
  { name: "Architecture", href: "#architecture-section", icon: GitBranch },
  { name: "Docs", href: "#docs-section", icon: FileText },
  { name: "FAQ", href: "#faq-section", icon: MessageSquare },
]

export function MobileNav() {
  const [mounted, setMounted] = React.useState(false)
  const [activeTab, setActiveTab] = useState("Home")
  const [isVisible, setIsVisible] = useState(true)
  const [lastScrollY, setLastScrollY] = useState(0)

  useEffect(() => {
    setMounted(true)
  }, [])

  // Handle scroll visibility (hide on scroll down, show on scroll up)
  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY
      if (currentScrollY > lastScrollY && currentScrollY > 100) {
        setIsVisible(false)
      } else {
        setIsVisible(true)
      }
      setLastScrollY(currentScrollY)

      // Update active tab based on scroll position
      const sections = navItems.map(item => item.href.replace("#", ""))
      for (const sectionId of sections.reverse()) {
        if (!sectionId) continue
        const element = document.getElementById(sectionId)
        if (element) {
          const rect = element.getBoundingClientRect()
          if (rect.top <= 200) {
            const item = navItems.find(i => i.href === `#${sectionId}`)
            if (item) {
              setActiveTab(item.name)
              break
            }
          }
        }
      }
      if (window.scrollY < 100) setActiveTab("Home")
    }

    window.addEventListener("scroll", handleScroll)
    return () => window.removeEventListener("scroll", handleScroll)
  }, [lastScrollY])

  const handleNavClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string, name: string) => {
    e.preventDefault()
    setActiveTab(name)
    
    if (href === "#") {
      window.scrollTo({ top: 0, behavior: "smooth" })
    } else {
      const targetId = href.replace("#", "")
      const element = document.getElementById(targetId)
      if (element) {
        element.scrollIntoView({ behavior: "smooth" })
      }
    }
  }

  if (!mounted) return null

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 100, opacity: 0 }}
          transition={{ duration: 0.4, ease: [0.33, 1, 0.68, 1] }}
          className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 w-[95%] max-w-md lg:hidden"
        >
          <nav className="flex items-center justify-around p-2 bg-[#0c0f0e]/80 backdrop-blur-xl border border-white/10 rounded-full shadow-[0_8px_32px_rgba(0,0,0,0.4)]">
            {navItems.map((item) => {
              const isActive = activeTab === item.name
              return (
                <a
                  key={item.name}
                  href={item.href}
                  onClick={(e) => handleNavClick(e, item.href, item.name)}
                  className="relative flex flex-col items-center justify-center py-2 px-3 transition-colors"
                >
                  {isActive && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute inset-0 bg-primary/10 rounded-full"
                      transition={{ type: "spring", stiffness: 300, damping: 30 }}
                    />
                  )}
                  <item.icon
                    className={cn(
                      "w-5 h-5 transition-all duration-300",
                      isActive ? "text-primary scale-110" : "text-muted-foreground"
                    )}
                  />
                  <span
                    className={cn(
                      "text-[10px] font-medium mt-1 transition-all duration-300",
                      isActive ? "text-primary opacity-100" : "text-muted-foreground opacity-70"
                    )}
                  >
                    {item.name}
                  </span>
                  {isActive && (
                    <motion.div
                      layoutId="activeDot"
                      className="absolute -top-1 w-1 h-1 bg-primary rounded-full"
                      transition={{ type: "spring", stiffness: 300, damping: 30 }}
                    />
                  )}
                </a>
              )
            })}
          </nav>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

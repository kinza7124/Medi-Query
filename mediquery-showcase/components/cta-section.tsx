import { Button } from "@/components/ui/button"
import Link from "next/link"

export function CTASection() {
  return (
    <section className="w-full pt-20 md:pt-40 pb-20 px-5 relative flex flex-col justify-center items-center overflow-hidden rounded-3xl bg-[#0c0f0e] my-10 max-w-[1220px] mx-auto">
      {/* Dynamic Background Elements - Matching Hero Style */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-20%] left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-primary/20 rounded-full blur-[120px] animate-pulse" />
        
        {/* SVG Grid Overlay */}
        <svg className="absolute inset-0 w-full h-full opacity-[0.1]" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="grid-cta" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid-cta)" />
        </svg>
      </div>
      <div className="relative z-10 flex flex-col justify-start items-center gap-9 max-w-4xl mx-auto">
        <div className="flex flex-col justify-start items-center gap-6 text-center px-4">
          <h2 className="text-white text-4xl md:text-6xl lg:text-7xl font-bold leading-[1.1] tracking-tight max-w-3xl">
            Medical AI <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-primary-light to-primary-dark animate-gradient">Reimagined</span>
          </h2>
          <p className="text-gray-400 text-base md:text-lg font-medium leading-relaxed max-w-2xl">
            Experience evidence-based medical information powered by RAG technology. 
            92% accuracy, source-grounded responses, and production-ready deployment.
          </p>
        </div>
        <Link href="https://github.com/kinza7124/Medi-Query" target="_blank" rel="noopener noreferrer">
          <Button
            className="relative z-10 bg-primary text-primary-foreground hover:bg-primary/90 px-10 py-7 rounded-full font-bold text-lg shadow-[0_0_20px_rgba(120,252,214,0.3)] hover:shadow-[0_0_30px_rgba(120,252,214,0.5)] transition-all duration-300 group overflow-hidden"
            size="lg"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000" />
            View on GitHub
          </Button>
        </Link>
      </div>
    </section>
  )
}

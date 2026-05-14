"use client"

import { Twitter, Github, Linkedin } from "lucide-react"

export function FooterSection() {
  return (
    <footer className="w-full max-w-[1320px] mx-auto px-5 flex flex-col md:flex-row justify-between items-start gap-8 md:gap-0 py-10 md:py-[70px]">
      {/* Left Section: Logo, Description, Social Links */}
      <div className="flex flex-col justify-start items-start gap-8 p-4 md:p-8">
        <div className="flex gap-3 items-stretch justify-center">
          <div className="text-center text-foreground text-xl font-semibold leading-4">MediQuery</div>
        </div>
        <p className="text-foreground/90 text-sm font-medium leading-[18px] text-left">
          Precision medical intelligence powered by RAG.<br/>
          Developed by Kinza Afzal.
        </p>
        <div className="flex justify-start items-start gap-4">
          <a 
            href="https://github.com/kinza7124" 
            target="_blank" 
            rel="noopener noreferrer" 
            aria-label="GitHub" 
            className="w-5 h-5 flex items-center justify-center transition-colors hover:text-primary"
          >
            <Github className="w-full h-full text-muted-foreground" />
          </a>
          <a 
            href="https://www.linkedin.com/in/kinza-afzal7-/" 
            target="_blank" 
            rel="noopener noreferrer" 
            aria-label="LinkedIn" 
            className="w-5 h-5 flex items-center justify-center transition-colors hover:text-primary"
          >
            <Linkedin className="w-full h-full text-muted-foreground" />
          </a>
        </div>
      </div>
      {/* Right Section: Product, Company, Resources */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-8 md:gap-12 p-4 md:p-8 w-full md:w-auto">
        <div className="flex flex-col justify-start items-start gap-3">
          <h3 className="text-muted-foreground text-sm font-medium leading-5">Technical</h3>
          <div className="flex flex-col justify-end items-start gap-2">
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">
              RAG Architecture
            </a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">
              CI/CD Pipeline
            </a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">
              Testing Suite
            </a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">
              Performance Metrics
            </a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">
              Security
            </a>
          </div>
        </div>
        <div className="flex flex-col justify-start items-start gap-3">
          <h3 className="text-muted-foreground text-sm font-medium leading-5">Stack</h3>
          <div className="flex flex-col justify-center items-start gap-2">
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">
              Flask/Python
            </a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">
              LangChain
            </a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">
              Pinecone
            </a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">
              Groq API
            </a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">
              AWS EC2
            </a>
          </div>
        </div>
        <div className="flex flex-col justify-start items-start gap-3">
          <h3 className="text-muted-foreground text-sm font-medium leading-5">Resources</h3>
          <div className="flex flex-col justify-center items-start gap-2">
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">
              SRS Document
            </a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">
              API Reference
            </a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">
              RAGAS Evaluation
            </a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">
              GitHub Repo
            </a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">
              Support
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}

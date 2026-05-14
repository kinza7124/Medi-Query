# MediQuery AI Chatbot Push Script
# This script stages all changes, commits them, and pushes to GitHub.

Write-Host "Checking git status..." -ForegroundColor Cyan
if (!(Test-Path .git)) {
    Write-Host "Error: .git directory not found. Please run this script from the root of your repository." -ForegroundColor Red
    exit
}

Write-Host "Staging files..." -ForegroundColor Yellow
git add .

Write-Host "Committing changes..." -ForegroundColor Yellow
git commit -m "Add mediquery-showcase demonstration and project updates"

Write-Host "Pushing to GitHub (https://github.com/kinza7124/medical-chatbot-ai)..." -ForegroundColor Yellow
git push origin main

Write-Host "Done!" -ForegroundColor Green

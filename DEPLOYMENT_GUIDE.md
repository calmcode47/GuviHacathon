Deployment Guide

Prerequisites
- Docker and Docker Compose installed
- Railway CLI installed and authenticated
- .env configured with API_KEY and settings

Local Test
- docker-compose up
- Open http://localhost:8000/health

Railway Deploy
- powershell .\deploy_railway.ps1 -ApiKey "<token>"
- After deploy, open service URL and check /health

Render Alternative
- Create new web service from Dockerfile
- Set environment variables
- Expose port 8000

Troubleshooting
- Ensure API_KEY is set
- Check logs for ffmpeg availability
- Verify /health returns JSON

#!/bin/bash
# scripts/reset.sh - Cleanse knowledge base for re-ingestion
echo "🔥 Resetting Aviation RAG Knowledge Base..."
rm -rf vectorstore/*
echo "✅ Vectorstore cleared."

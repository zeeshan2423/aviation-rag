#!/bin/bash
# scripts/rebuild.sh - Re-ingest and relaunch full-stack
echo "🚀 Rebuilding Aviation RAG Stack..."
make ingest
make docker-up
echo "✅ Rebuild complete. Monitoring logs..."
make logs

#!/bin/bash
# Move into the frontend app folder
cd "$(dirname "$0")/frontend/frontend"

echo "Starting Next.js Web Portal..."
npm run dev

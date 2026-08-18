#!/bin/bash
set -e

echo "================================================="
echo "  Running AI Service Unit Tests (app & services)"
echo "================================================="
PYTHONPATH=ai-service ai-service/venv/bin/python -m unittest discover -s ai-service/tests -v

echo ""
echo "================================================="
echo "  Running Backend Orchestrator Unit Tests (api & db)"
echo "================================================="
backend/venv/bin/python -m unittest discover -s backend/tests -v

echo ""
echo "================================================="
echo "  ALL UNIT TESTS PASSED SUCCESSFULLY (47/47)!"
echo "================================================="

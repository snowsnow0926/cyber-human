#!/bin/bash
# Install Playwright Chromium - runs on VPS
cd /home/ubuntu/cyber-human
source venv/bin/activate
python3 -m playwright install --with-deps chromium 2>&1 | tee /tmp/playwright_done.log
echo "DONE" >> /tmp/playwright_done.log

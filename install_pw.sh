#!/bin/bash
cd /home/ubuntu/cyber-human
source venv/bin/activate
python3 -m playwright install chromium 2>&1 | tee /tmp/pw_done.log
echo "EXIT_CODE=$?" >> /tmp/pw_done.log

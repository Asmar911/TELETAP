#!/bin/bash

echo "Activating virtual environment..."
source venv/bin/activate

echo "Starting the bot..."
python3 main.py

read -p "Press Enter to continue..."

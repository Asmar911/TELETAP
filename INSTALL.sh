#!/bin/bash

# install_python() {
#     echo "Select the Python version to install:"
#     echo "1) Python 3.10"
#     echo "2) Python 3.11"
#     echo "3) Python 3.12"
#     read -p "Enter the number of your choice: " choice

#     case $choice in
#         1) version="3.10" ;;
#         2) version="3.11" ;;
#         3) version="3.12" ;;
#         *) echo "Invalid choice"; exit 1 ;;
#     esac

#     if command -v apt-get &> /dev/null; then
#         sudo apt-get update
#         sudo apt-get install -y python$version python$version-venv python3-pip
#     elif command -v yum &> /dev/null; then
#         sudo yum install -y https://repo.ius.io/ius-release-el$(rpm -E %{rhel}).rpm
#         sudo yum install -y python$version python$version-venv python$version-pip
#     elif command -v dnf &> /dev/null; then
#         sudo dnf install -y python$version python$version-venv python$version-pip
#     else
#         echo "Package manager not supported. Please install Python $version manually."
#         exit 1
#     fi

#     echo "Python $version installed successfully."
# }

# # Check if python3 is installed; if not, install the specified version
# if ! command -v python3 &> /dev/null; then
#     install_python
# else
#     echo "Python3 is already installed. Skipping installation."
# fi




echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip3 install -r requirements.txt

echo "Copying .env-example to .env..."
cp .env-example .env
nano .env  # Here you must specify your API_ID and API_HASH

echo "Please edit the .env file to add your API_ID and API_HASH."
read -p "Press Enter to continue..."

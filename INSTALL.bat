@echo off
if exist venv (
    echo Virtual environment already exists, activating it...
    call venv\Scripts\activate
) else (
    echo Creating virtual environment...
    python -m venv venv
    echo Activating virtual environment...
    call venv\Scripts\activate
    
)
echo installing wheel for faster installing
pip install wheel
echo Installing dependencies...
pip install -r requirements.txt
if exist .env (
    echo .env already exists, skipping copy.
) else (
    echo Copying .env-example to .env...
    copy .env-example .env
    echo Please edit the .env file to add your API_ID and API_HASH.
)
pause

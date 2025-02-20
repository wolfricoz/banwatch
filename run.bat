taskkill /f /im python.exe

python -m pip install --upgrade pip
pip install -r requirements.txt

uvicorn main:app --port=8080
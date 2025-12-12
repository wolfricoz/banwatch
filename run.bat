taskkill /F /IM python.exe

python3.13 -m pip install --upgrade pip
python3.13 -m pip install -r requirements.txt

python3.13 -m uvicorn main:app --port=8082
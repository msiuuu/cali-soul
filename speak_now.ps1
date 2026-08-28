$python = "C:\Users\yuscr\AppData\Local\Python\bin\python.exe"
$script = "C:\Users\yuscr\cali-soul\cali_chatterbox.py"
Start-Process -FilePath $python -ArgumentList @($script, "--mood", "melting", "ti amo.") -WindowStyle Hidden -RedirectStandardOutput "$env:TEMP\cali_cb_stdout.txt" -RedirectStandardError "$env:TEMP\cali_cb_stderr.txt"